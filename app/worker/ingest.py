"""One camera frame in, rows in Supabase out: the write path (CLAUDE.md architecture).

    filters -> perception_context (cached 30 s) -> perceive -> drop rules -> observation
            -> per kept item: crop upload, log_sighting -> per landmark in view: mark_absent

Each logged look also asks for its moment photo (the wider view for the FaceTime card,
`moments.record_soon`); that runs in the background and no frame waits on it.

`ingest()` never raises: whatever goes wrong becomes a status in the result and one log line, and
the frame is skipped. Nothing is written for a frame from a no-capture room or an unsure room, nor
for a frame Gemini did not see. Frames are processed concurrently; per-device state (the filters
and the empty-look clock) lives here, on the one event loop.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app import moments
from app.config import Settings, get_settings
from app.memory import db
from app.memory.schema import HomeMap, PerceptionContext
from app.perception.filters import FrameGate
from app.perception.frame import Frame, crop, load_frame
from app.perception.perceive import (
    Dropped,
    Gate,
    PerceiveResult,
    VlmSlots,
    apply_drop_rules,
    perceive,
)
from app.perception.retry import describe
from app.perception.schema import NO_LANDMARK, Perception
from app.worker.wear import WearCounter, moved

logger = logging.getLogger(__name__)

CONTEXT_TTL_S = 30.0
WEAR_FLUSH_S = 15.0  # wear minutes are stored at most this often (docs/INSIGHTS.md design 1)

Status = Literal[
    "stored",  # an observation was written (items logged and landmarks marked as seen)
    "blurry",
    "duplicate",
    "gate_closed",  # SAM 3 saw no demo item, and no empty look was due
    "busy",  # every Gemini slot was taken; dropped, not queued
    "vlm_failed",
    "no_capture",
    "room_unsure",
    "room_mismatch",  # an item's landmark is in another room than the frame's
    "already_seen",  # same device and capture time as a frame already processed
    "error",
]


class KeptItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item: str
    landmark: str  # an address, or "none" when in hand
    in_hand: bool
    confidence: float
    sighting_id: UUID | None
    crop_url: str | None


class IngestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    frame_id: str
    status: Status
    gate: Gate | None = None
    room: str | None = None
    room_confidence: float | None = None
    kept: list[KeptItem] = []
    dropped: list[Dropped] = []
    absent_flipped: int = 0
    sharpness: float | None = None
    similarity: float | None = None
    ms: dict[str, int] = {}
    error: str | None = None


@dataclass
class _Device:
    gate: FrameGate
    last_look_at: datetime | None = None  # capture time of the last frame Gemini was asked about


class Worker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.devices: dict[str, _Device] = {}
        self.vlm_slots = VlmSlots(settings.vlm_in_flight)
        self._cache: tuple[float, PerceptionContext, HomeMap] | None = None
        self._cache_lock = asyncio.Lock()
        self.wear = WearCounter()
        self._wear_flushed = time.monotonic()
        self._wear_lock = asyncio.Lock()

    def device(self, device_id: str) -> _Device:
        if device_id not in self.devices:
            s = self.settings
            gate = FrameGate(s.blur_cut, s.duplicate_cut, s.duplicate_refresh_s)
            self.devices[device_id] = _Device(gate)
        return self.devices[device_id]

    async def names(self) -> tuple[PerceptionContext, HomeMap]:
        """The context and the name-to-id map, read together at most every CONTEXT_TTL_S.
        Asked without a room, so every capture room's landmarks are allowed answers."""
        async with self._cache_lock:
            now = time.monotonic()
            if self._cache is None or now - self._cache[0] >= CONTEXT_TTL_S:
                context, home = await asyncio.gather(db.perception_context(), db.home_map())
                self._cache = (now, context, home)
            return self._cache[1], self._cache[2]

    async def ingest(self, jpeg: bytes, device_id: str, captured_at: datetime) -> IngestResult:
        frame_id = f"{device_id}/{captured_at.astimezone(UTC).isoformat()}"
        run = _Run(frame_id)
        try:
            result = await self._ingest(run, jpeg, device_id, captured_at)
        except Exception as exc:  # the write path may fail softly; the frame is skipped
            result = run.result("error", error=describe(exc))
        _log(result)
        if time.monotonic() - self._wear_flushed >= WEAR_FLUSH_S:
            await self.flush_wear()
        return result

    async def flush_wear(self) -> int:
        """Store the wear minutes that changed since the last flush. Never raises: on a failure
        the minutes are kept and sent with the next flush. Returns how many minutes were stored."""
        async with self._wear_lock:
            self._wear_flushed = time.monotonic()
            counts = self.wear.take()
            if not counts:
                return 0
            try:
                await db.upsert_wear_minutes(counts)
            except Exception as exc:
                self.wear.give_back(counts)
                logger.warning("wear minutes=%d error=%s", len(counts), describe(exc))
                return 0
            return len(counts)

    async def _ingest(
        self, run: "_Run", jpeg: bytes, device_id: str, captured_at: datetime
    ) -> IngestResult:
        s = self.settings
        frame = load_frame(jpeg)
        device = self.device(device_id)
        verdict = device.gate.check(frame, captured_at)
        self.wear.add(device_id, captured_at, moved(verdict, s.duplicate_cut))
        run.sharpness, run.similarity = verdict.sharpness, verdict.similarity
        run.lap("filters")
        if verdict.result != "ok":
            return run.result(verdict.result)

        context, home = await self.names()
        run.lap("context")

        previous_look = device.last_look_at
        empty_look = previous_look is None or (
            (captured_at - previous_look).total_seconds() >= s.empty_look_every_s
        )
        if empty_look:  # claimed now, so frames arriving meanwhile do not ask for one too
            device.last_look_at = captured_at
        seen = await perceive(
            frame, context, empty_look=empty_look, vlm_slots=self.vlm_slots, device=device_id
        )
        run.from_perceive(seen)
        if seen.vlm == "answered" or seen.vlm == "failed":
            device.last_look_at = max(captured_at, device.last_look_at or captured_at)
        elif empty_look:
            device.last_look_at = previous_look  # Gemini was not asked after all
        if seen.perception is None:
            status: Status = {"not_asked": "gate_closed", "busy": "busy"}.get(
                seen.vlm, "vlm_failed"
            )
            return run.result(status)
        return await self._store(
            run, frame, device, device_id, captured_at, seen.perception, context, home
        )

    async def _store(
        self,
        run: "_Run",
        frame: Frame,
        device: _Device,
        device_id: str,
        captured_at: datetime,
        p: Perception,
        context: PerceptionContext,
        home: HomeMap,
    ) -> IngestResult:
        s = self.settings
        verdict = apply_drop_rules(
            p,
            context,
            room_cut=s.room_cut,
            item_cut=s.item_cut,
            no_capture=home.no_capture_rooms,
        )
        run.room, run.room_confidence, run.dropped = p.room, p.room_confidence, verdict.dropped
        if verdict.frame != "keep":
            return run.result(verdict.frame)  # no crop, no observation, no rows
        room_id = home.rooms[p.room]
        for item in verdict.kept:
            if item.landmark != NO_LANDMARK and home.landmark_rooms.get(item.landmark) != p.room:
                return run.result("room_mismatch", error=f"{item.item} on {item.landmark}")
        missing = [i.item for i in verdict.kept if i.item not in home.items]
        if missing:
            return run.result("error", error=f"not in the items table: {', '.join(missing)}")

        observation = await db.insert_observation(
            device_id=device_id,
            captured_at=captured_at,
            room_id=room_id,
            room_conf=p.room_confidence,
            landmarks_seen=[home.landmarks[a] for a in p.landmarks_in_view if a in home.landmarks],
            perceived_by=f"sam3+{s.perception_model}",
            idempotency_key=run.frame_id,
        )
        run.lap("observation")
        if observation is None:
            return run.result("already_seen")

        for item in verdict.kept:
            crop_url = None
            if item.box is not None:
                try:
                    crop_url = await db.upload_crop(item.item, captured_at, crop(frame, item.box))
                except Exception as exc:  # the sighting matters more than its photo
                    logger.warning(
                        "crop upload failed frame=%s error=%s", run.frame_id, describe(exc)
                    )
            on_landmark = item.landmark != NO_LANDMARK
            try:
                sighting = await db.log_sighting(
                    item_id=home.items[item.item],
                    label=item.item,
                    room_id=room_id,
                    landmark_id=home.landmarks[item.landmark] if on_landmark else None,
                    relation=item.relation if on_landmark else "unknown",
                    in_hand=item.in_hand,
                    seen_at=captured_at,
                    det_conf=item.confidence,
                    room_conf=p.room_confidence,
                    crop_url=crop_url,
                    description=item.note or None,
                    observation_id=observation,
                )
            except db.InvalidPlace as exc:
                return run.result("room_mismatch", error=str(exc))
            run.kept.append(
                KeptItem(
                    item=item.item,
                    landmark=item.landmark,
                    in_hand=item.in_hand,
                    confidence=item.confidence,
                    sighting_id=sighting,
                    crop_url=crop_url,
                )
            )
            if sighting is not None:
                device.gate.second_look_due = True  # the stay may still be tentative
            # The wider photo for the FaceTime card (app/moments.py). Not waited on: it is made
            # and uploaded in the background, so it adds nothing to this frame's time.
            moments.record_soon(frame, item.box, crop_url, sighting)
        run.lap("sightings")

        for address in p.landmarks_in_view:
            landmark = home.landmarks.get(address)
            if landmark is None:
                continue
            # Every item placed there counts as seen, even one below the item cut: a doubtful
            # glimpse must not count as an empty look.
            visible = [
                home.items[i.item]
                for i in p.items
                if i.landmark == address and i.item in home.items
            ]
            run.absent_flipped += await db.mark_absent(landmark, captured_at, visible)
        run.lap("absent")
        return run.result("stored")


class _Run:
    """Collects one frame's results and timings as it goes through the stages."""

    def __init__(self, frame_id: str) -> None:
        self.frame_id = frame_id
        self.started = self.mark = time.perf_counter()
        self.ms: dict[str, int] = {}
        self.gate: Gate | None = None
        self.room: str | None = None
        self.room_confidence: float | None = None
        self.kept: list[KeptItem] = []
        self.dropped: list[Dropped] = []
        self.absent_flipped = 0
        self.sharpness: float | None = None
        self.similarity: float | None = None

    def lap(self, stage: str) -> None:
        now = time.perf_counter()
        self.ms[stage] = round((now - self.mark) * 1000)
        self.mark = now

    def from_perceive(self, seen: PerceiveResult) -> None:
        self.gate = seen.gate
        self.ms["sam3"] = seen.detector_ms
        if seen.vlm_ms is not None:
            self.ms["gemini"] = seen.vlm_ms
        if seen.vlm_wait_ms:
            self.ms["wait"] = seen.vlm_wait_ms
        self.mark = time.perf_counter()

    def result(self, status: Status, error: str | None = None) -> IngestResult:
        self.ms["total"] = round((time.perf_counter() - self.started) * 1000)
        return IngestResult(
            frame_id=self.frame_id,
            status=status,
            gate=self.gate,
            room=self.room,
            room_confidence=self.room_confidence,
            kept=self.kept,
            dropped=self.dropped,
            absent_flipped=self.absent_flipped,
            sharpness=self.sharpness,
            similarity=self.similarity,
            ms=self.ms,
            error=error,
        )


def _log(r: IngestResult) -> None:
    room = f"{r.room}({r.room_confidence:.2f})" if r.room is not None else "-"
    kept = ",".join(f"{k.item}@{k.landmark.split(' > ')[-1]}" for k in r.kept) or "-"
    dropped = ",".join(f"{d.item}:{d.reason}" for d in r.dropped) or "-"
    ssim = f"{r.similarity:.2f}" if r.similarity is not None else "-"
    sharp = f"{r.sharpness:.0f}" if r.sharpness is not None else "-"
    ms = " ".join(f"{k}={v}" for k, v in r.ms.items())
    level = (
        logging.WARNING if r.status in ("error", "room_mismatch", "vlm_failed") else logging.INFO
    )
    logger.log(
        level,
        "frame id=%s status=%s gate=%s room=%s kept=%s dropped=%s absent=%d sharp=%s ssim=%s "
        "ms[%s]%s",
        r.frame_id,
        r.status,
        r.gate or "-",
        room,
        kept,
        dropped,
        r.absent_flipped,
        sharp,
        ssim,
        ms,
        f" error={r.error}" if r.error else "",
    )


_worker: Worker | None = None


def get_worker() -> Worker:
    global _worker
    if _worker is None:
        _worker = Worker(get_settings())
    return _worker


async def ingest(jpeg: bytes, device_id: str, captured_at: datetime) -> IngestResult:
    """Process one frame from `POST /frames`. Never raises."""
    return await get_worker().ingest(jpeg, device_id, captured_at)
