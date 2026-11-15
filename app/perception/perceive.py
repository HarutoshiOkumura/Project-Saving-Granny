"""Combine SAM 3 and Gemini for one frame (D3), and the drop rules the worker applies after.

SAM 3 gates Gemini: a frame goes to Gemini only when SAM 3 scores some demo item at or above the
gate, or when the worker asks for an empty look (one at most every 30 s, so `mark_absent` keeps
seeing empty landmarks). Gemini places the items; SAM 3 only supplies tighter crop boxes. It never
vetoes an item: in step 04 Gemini made no false sightings, while SAM 3's labels were unreliable.
When SAM 3 fails, or cannot look for some item, the frame goes to Gemini anyway (fail open: the
gate saves calls, it is not a safety check).
"""

import logging
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.memory.schema import PerceptionContext
from app.perception import detector, vlm
from app.perception.frame import Frame
from app.perception.schema import (
    NO_LANDMARK,
    UNKNOWN_ROOM,
    Detection,
    ItemSeen,
    Perception,
    iou,
)

logger = logging.getLogger(__name__)

BOX_MATCH_IOU = 0.5  # a SAM 3 box replaces Gemini's only when they agree this well

# open: SAM 3 saw a demo item. closed: it did not, and Gemini was not asked. empty_look: it did
# not, but the worker asked for a look anyway. detector_failed, no_prompt: Gemini asked anyway.
Gate = Literal["open", "closed", "empty_look", "detector_failed", "no_prompt"]


class PerceiveResult(BaseModel):
    """What perceive() did with one frame. `perception` is None when Gemini was not asked
    (gate closed) or gave no usable answer; either way the worker writes nothing."""

    model_config = ConfigDict(frozen=True)

    gate: Gate
    perception: Perception | None
    detections: list[Detection]
    detector_ms: int
    vlm_ms: int | None = None
    error: str | None = None


async def perceive(
    frame: Frame, context: PerceptionContext, *, empty_look: bool = False
) -> PerceiveResult:
    """Never raises for a model failure: a failed SAM 3 opens the gate, a failed Gemini call
    gives `perception=None`."""
    settings = get_settings()
    started = time.perf_counter()
    detections: list[Detection] = []
    error = None
    try:
        detections = await detector.detect(frame)
        gate: Gate = (
            "open" if any(d.confidence >= settings.sam3_gate for d in detections) else "closed"
        )
    except detector.DetectorError as exc:
        gate, error = "detector_failed", str(exc)
        logger.warning("sam3 failed, asking gemini anyway error=%s", error)
    detector_ms = _ms_since(started)

    if gate == "closed" and any(i.item not in detector.PROMPTS for i in context.items):
        gate = "no_prompt"
    if gate == "closed":
        if not empty_look:
            return PerceiveResult(
                gate=gate, perception=None, detections=detections, detector_ms=detector_ms
            )
        gate = "empty_look"

    started = time.perf_counter()
    perception = await vlm.look(frame.jpeg, context)
    vlm_ms = _ms_since(started)
    if perception is not None:
        perception = with_crop_boxes(perception, detections)
    return PerceiveResult(
        gate=gate,
        perception=perception,
        detections=detections,
        detector_ms=detector_ms,
        vlm_ms=vlm_ms,
        error=error,
    )


def with_crop_boxes(perception: Perception, detections: list[Detection]) -> Perception:
    """For each item, the SAM 3 box that overlaps Gemini's box most, if their IoU is at least
    BOX_MATCH_IOU; otherwise Gemini's own box. SAM 3's label is ignored."""
    items = []
    for item in perception.items:
        if item.box is not None and detections:
            overlap, best = max(((iou(d.box, item.box), d) for d in detections), key=_first)
            if overlap >= BOX_MATCH_IOU:
                item = item.model_copy(update={"box": best.box, "box_source": "sam3"})
        items.append(item)
    return perception.model_copy(update={"items": items})


# ---------------------------------------------------------------------------------------------
# Drop rules (perception rules, in this order). The worker calls this after perceive().
# ---------------------------------------------------------------------------------------------

FrameVerdict = Literal["keep", "no_capture", "room_unsure"]
DropReason = Literal["no_place", "low_confidence", "duplicate"]


class Dropped(BaseModel):
    model_config = ConfigDict(frozen=True)

    item: str
    reason: DropReason
    confidence: float


class Verdict(BaseModel):
    """`frame` is "keep" only when the worker may write for this frame at all. `kept` holds at
    most one entry per item; `dropped` says why each other entry was left out, for the log."""

    model_config = ConfigDict(frozen=True)

    frame: FrameVerdict
    kept: list[ItemSeen]
    dropped: list[Dropped]


def no_capture_rooms(context: PerceptionContext) -> set[str]:
    """Rooms with no landmark in the context. `perception_context` lists landmarks only for
    capture-allowed rooms; asked with `p_room`, it also leaves out unlinked rooms, which then count
    as no-capture here. That fails closed (frames dropped, never stored)."""
    return set(context.rooms) - {lm.room for lm in context.landmarks}


def apply_drop_rules(
    perception: Perception, context: PerceptionContext, *, room_cut: float, item_cut: float
) -> Verdict:
    """1. no-capture room: drop the frame. 2. unknown room or room_confidence below the room cut:
    drop the frame (it could be a no-capture room). 3. landmark "none" and not in hand: drop the
    item. 4. confidence below the item cut: drop the item. 5. the same item twice: keep the most
    confident entry."""
    if perception.room in no_capture_rooms(context):
        return Verdict(frame="no_capture", kept=[], dropped=[])
    if perception.room == UNKNOWN_ROOM or perception.room_confidence < room_cut:
        return Verdict(frame="room_unsure", kept=[], dropped=[])
    dropped: list[Dropped] = []
    best: dict[str, ItemSeen] = {}
    for item in perception.items:
        if item.landmark == NO_LANDMARK and not item.in_hand:
            dropped.append(Dropped(item=item.item, reason="no_place", confidence=item.confidence))
        elif item.confidence < item_cut:
            dropped.append(
                Dropped(item=item.item, reason="low_confidence", confidence=item.confidence)
            )
        elif item.item in best:
            if item.confidence > best[item.item].confidence:  # a tie keeps the first entry
                best[item.item], item = item, best[item.item]
            dropped.append(Dropped(item=item.item, reason="duplicate", confidence=item.confidence))
        else:
            best[item.item] = item
    return Verdict(frame="keep", kept=list(best.values()), dropped=dropped)


def _first(pair: tuple[float, Detection]) -> float:
    return pair[0]


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
