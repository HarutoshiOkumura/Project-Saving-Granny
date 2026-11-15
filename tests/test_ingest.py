"""The ingest worker with fixture frames and faked perceive() and database. No network."""

import asyncio
import io
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from PIL import Image

from app.config import get_settings
from app.memory import db
from app.memory.schema import HomeMap
from app.perception.perceive import PerceiveResult
from app.perception.schema import Perception
from app.worker import ingest as worker_module
from app.worker.ingest import IngestResult, Worker
from tests.perception_fakes import CHAIR, CONTEXT, FLOOR, FRAMES, ROOM, TABLE, gemini_answer

T0 = datetime(2026, 11, 15, 1, 0, tzinfo=UTC)


def uid(n: int) -> UUID:
    return UUID(int=n)


OBSERVATION, SIGHTING = uid(100), uid(200)


HOME = HomeMap(
    rooms={ROOM: uid(1), "bathroom": uid(2), "kitchen": uid(3)},
    capture_allowed={ROOM: True, "bathroom": False, "kitchen": True},
    landmarks={TABLE: uid(11), CHAIR: uid(12), FLOOR: uid(13), "kitchen > counter": uid(14)},
    landmark_rooms={TABLE: ROOM, CHAIR: ROOM, FLOOR: ROOM, "kitchen > counter": "kitchen"},
    items={"bag": uid(21), "glasses": uid(22), "keys": uid(23), "watch": uid(24),
           "water bottle": uid(25)},
)  # fmt: skip


def jpeg(name: str) -> bytes:
    return (FRAMES / f"{name}.jpg").read_bytes()


class FakeDB:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.keys: set[str] = set()
        self.invalid_place = False
        self.upload_fails = False
        self.insert_fails = False

    def writes(self) -> list[str]:
        return [name for name, _ in self.calls if name not in ("perception_context", "home_map")]

    def named(self, name: str) -> list[dict[str, Any]]:
        return [kwargs for n, kwargs in self.calls if n == name]

    async def perception_context(self) -> Any:
        self.calls.append(("perception_context", {}))
        return CONTEXT

    async def home_map(self) -> HomeMap:
        self.calls.append(("home_map", {}))
        return HOME

    async def insert_observation(self, **kwargs: Any) -> UUID | None:
        self.calls.append(("insert_observation", kwargs))
        if self.insert_fails:
            raise ConnectionError("database down")
        if kwargs["idempotency_key"] in self.keys:
            return None
        self.keys.add(kwargs["idempotency_key"])
        return OBSERVATION

    async def upload_crop(self, item: str, captured_at: datetime, jpeg: bytes) -> str:
        self.calls.append(("upload_crop", {"item": item, "captured_at": captured_at, "jpeg": jpeg}))
        if self.upload_fails:
            raise ConnectionError("storage down")
        return f"crops/home/{item}/x.jpg"

    async def log_sighting(self, **kwargs: Any) -> UUID | None:
        self.calls.append(("log_sighting", kwargs))
        if self.invalid_place:
            raise db.InvalidPlace("landmark is not in room")
        return SIGHTING

    async def mark_absent(self, landmark: UUID, seen_at: datetime, visible: list[UUID]) -> int:
        self.calls.append(("mark_absent", {"landmark": landmark, "visible": visible}))
        return 0


class FakePerceive:
    """Answers perceive() with a fixed result and records what the worker asked for."""

    def __init__(self) -> None:
        self.answer: str | None = gemini_answer()
        self.vlm = "answered"
        self.gate = "open"
        self.empty_looks: list[bool] = []

    async def __call__(
        self, frame: Any, context: Any, *, empty_look: bool, vlm_slots: Any, device: str
    ) -> PerceiveResult:
        self.empty_looks.append(empty_look)
        perception = None
        if self.vlm == "answered" and self.answer is not None:
            perception = Perception.model_validate_json(self.answer)
        return PerceiveResult(
            gate=self.gate,  # type: ignore[arg-type]
            vlm=self.vlm,  # type: ignore[arg-type]
            perception=perception,
            detections=[],
            detector_ms=400,
            vlm_ms=None if self.vlm in ("not_asked", "busy") else 2500,
        )


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> FakeDB:
    fake = FakeDB()
    for name in (
        "perception_context",
        "home_map",
        "insert_observation",
        "upload_crop",
        "log_sighting",
        "mark_absent",
    ):
        monkeypatch.setattr(db, name, getattr(fake, name))
    return fake


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> FakePerceive:
    fake = FakePerceive()
    monkeypatch.setattr(worker_module, "perceive", fake)
    return fake


@pytest.fixture
def worker() -> Worker:
    return Worker(get_settings())


def run(worker: Worker, name: str = "close_keys_table_01", at: datetime = T0) -> IngestResult:
    return asyncio.run(worker.ingest(jpeg(name), "lanyard", at))


# --------------------------------------------------------------------------------------------
# A frame that is stored
# --------------------------------------------------------------------------------------------


def test_a_placed_item_is_logged_with_its_crop_and_the_landmarks_are_marked_seen(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.answer = gemini_answer(landmarks_in_view=[TABLE, CHAIR])

    result = run(worker)

    assert result.status == "stored"
    assert fake_db.writes() == [
        "insert_observation",
        "upload_crop",
        "log_sighting",
        "mark_absent",
        "mark_absent",
    ]
    (observation,) = fake_db.named("insert_observation")
    assert observation == {
        "device_id": "lanyard",
        "captured_at": T0,
        "room_id": uid(1),
        "room_conf": 0.95,
        "landmarks_seen": [uid(11), uid(12)],
        "perceived_by": "sam3+gemini-3.6-flash",
        "idempotency_key": "lanyard/2026-11-15T01:00:00+00:00",
    }
    (upload,) = fake_db.named("upload_crop")
    assert upload["item"] == "keys" and upload["jpeg"][:2] == b"\xff\xd8"
    (sighting,) = fake_db.named("log_sighting")
    assert sighting == {
        "item_id": uid(23),
        "label": "keys",
        "room_id": uid(1),
        "landmark_id": uid(11),
        "relation": "on",
        "in_hand": False,
        "seen_at": T0,
        "det_conf": 0.9,
        "room_conf": 0.95,
        "crop_url": "crops/home/keys/x.jpg",
        "description": "black key fob",
        "observation_id": OBSERVATION,
    }
    assert fake_db.named("mark_absent") == [
        {"landmark": uid(11), "visible": [uid(23)]},  # the keys are on the table
        {"landmark": uid(12), "visible": []},  # the chair was seen empty
    ]
    assert [(k.item, k.sighting_id, k.crop_url) for k in result.kept] == [
        ("keys", SIGHTING, "crops/home/keys/x.jpg")
    ]
    assert set(result.ms) >= {"filters", "context", "sam3", "gemini", "observation", "total"}


def test_each_logged_look_asks_for_its_moment_photo_and_does_not_wait_for_it(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[tuple[Any, ...]] = []

    def record_soon(frame: Any, box: Any, crop_url: Any, sighting_id: Any) -> None:
        asked.append((frame.width, frame.height, box, crop_url, sighting_id))

    monkeypatch.setattr(worker_module.moments, "record_soon", record_soon)  # a plain function

    result = run(worker)

    assert result.status == "stored"
    [(width, height, box, crop_url, sighting_id)] = asked
    assert (width, height) == (1440, 1920)  # the frame the crop came from
    assert box is not None and len(box) == 4
    assert (crop_url, sighting_id) == ("crops/home/keys/x.jpg", SIGHTING)


def test_a_look_whose_crop_failed_still_reports_to_the_hook_which_then_skips_it(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[Any] = []
    monkeypatch.setattr(
        worker_module.moments, "record_soon", lambda frame, box, url, sid: asked.append(url)
    )
    fake_db.upload_fails = True

    assert run(worker).status == "stored"
    assert asked == [None]  # record_soon does nothing without a crop


def test_an_item_in_hand_is_logged_with_its_room_and_no_landmark(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.answer = gemini_answer([{"landmark": "none", "in_hand": True, "relation": "on"}])

    run(worker)

    (sighting,) = fake_db.named("log_sighting")
    assert (sighting["room_id"], sighting["landmark_id"]) == (uid(1), None)
    assert (sighting["in_hand"], sighting["relation"]) == (True, "unknown")


def test_a_crop_that_fails_to_upload_still_logs_the_sighting(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    fake_db.upload_fails = True

    result = run(worker)

    assert result.status == "stored"
    assert fake_db.named("log_sighting")[0]["crop_url"] is None


def test_an_empty_look_marks_every_landmark_in_view(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.gate = "empty_look"
    seen.answer = gemini_answer([], landmarks_in_view=[TABLE, CHAIR, FLOOR])

    result = run(worker, "empty_table_01")

    assert result.status == "stored"
    assert fake_db.writes() == ["insert_observation", *["mark_absent"] * 3]
    assert all(call["visible"] == [] for call in fake_db.named("mark_absent"))


# --------------------------------------------------------------------------------------------
# Drop rules: what reaches the database
# --------------------------------------------------------------------------------------------


def test_rule_1_a_no_capture_room_writes_nothing_at_all(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.answer = gemini_answer(room="bathroom")

    result = run(worker)

    assert result.status == "no_capture"
    assert fake_db.writes() == []


@pytest.mark.parametrize(("room", "confidence"), [("unknown", 0.9), (ROOM, 0.4)])
def test_rule_2_an_unsure_room_writes_nothing(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive, room: str, confidence: float
) -> None:
    seen.answer = gemini_answer(room=room, room_confidence=confidence)

    assert run(worker).status == "room_unsure"
    assert fake_db.writes() == []


def test_rule_3_an_item_at_no_place_is_not_logged_and_makes_nothing_visible(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.answer = gemini_answer([{"landmark": "none"}])

    result = run(worker)

    assert result.status == "stored"
    assert fake_db.named("log_sighting") == []
    assert [(d.item, d.reason) for d in result.dropped] == [("keys", "no_place")]
    assert fake_db.named("mark_absent") == [{"landmark": uid(11), "visible": []}]


def test_rule_4_a_doubtful_item_is_not_logged_but_still_counts_as_seen(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    """A glimpse below the item cut must not count as the table seen empty."""
    seen.answer = gemini_answer([{"confidence": 0.3}])

    result = run(worker)

    assert fake_db.named("log_sighting") == []
    assert [(d.item, d.reason) for d in result.dropped] == [("keys", "low_confidence")]
    assert fake_db.named("mark_absent") == [{"landmark": uid(11), "visible": [uid(23)]}]


def test_rule_5_the_same_item_twice_is_logged_once(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.answer = gemini_answer(
        [{"confidence": 0.7}, {"landmark": CHAIR, "confidence": 0.9}],
        landmarks_in_view=[TABLE, CHAIR],
    )

    run(worker)

    (sighting,) = fake_db.named("log_sighting")
    assert sighting["landmark_id"] == uid(12)
    # Both places had the keys in view as far as absence goes.
    assert [c["visible"] for c in fake_db.named("mark_absent")] == [[uid(23)], [uid(23)]]


def test_an_item_on_a_landmark_of_another_room_skips_the_frame(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.answer = gemini_answer(room="kitchen")

    result = run(worker)

    assert result.status == "room_mismatch"
    assert fake_db.writes() == []


def test_a_22023_from_the_database_stops_the_frame(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    fake_db.invalid_place = True
    seen.answer = gemini_answer(landmarks_in_view=[TABLE, CHAIR])

    result = run(worker)

    assert result.status == "room_mismatch"
    assert fake_db.named("mark_absent") == []


# --------------------------------------------------------------------------------------------
# Frames that never reach the database
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("gate", "vlm", "status"),
    [
        ("closed", "not_asked", "gate_closed"),
        ("open", "busy", "busy"),
        ("open", "failed", "vlm_failed"),
    ],
)
def test_frames_gemini_did_not_see_write_nothing(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive, gate: str, vlm: str, status: str
) -> None:
    seen.gate, seen.vlm = gate, vlm

    result = run(worker)

    assert result.status == status
    assert fake_db.writes() == []


def test_a_blurry_frame_never_reaches_the_models(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), "gray").save(buffer, "JPEG")

    result = asyncio.run(worker.ingest(buffer.getvalue(), "lanyard", T0))

    assert result.status == "blurry"
    assert seen.empty_looks == []
    assert fake_db.calls == []


def test_a_duplicate_frame_never_reaches_the_models(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.gate, seen.vlm = "closed", "not_asked"

    statuses = [run(worker, at=T0 + timedelta(seconds=s)).status for s in (0, 2)]

    assert statuses == ["gate_closed", "duplicate"]
    assert len(seen.empty_looks) == 1


def test_a_retried_frame_writes_once(worker: Worker, fake_db: FakeDB, seen: FakePerceive) -> None:
    first = run(worker)
    # The first frame logged a sighting, so the filters let the identical retry through as a
    # possible second look; the observation's idempotency key then stops it.
    again = run(worker)
    after_restart = run(Worker(get_settings()))

    assert (first.status, again.status, after_restart.status) == (
        "stored",
        "already_seen",
        "already_seen",
    )
    assert len(fake_db.named("log_sighting")) == 1
    assert len(fake_db.named("upload_crop")) == 1


def test_not_an_image_is_an_error_not_an_exception(worker: Worker, fake_db: FakeDB) -> None:
    result = asyncio.run(worker.ingest(b"\xff\xd8\xffnot really", "lanyard", T0))

    assert result.status == "error"
    assert result.error


def test_a_database_failure_is_an_error_not_an_exception(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    fake_db.insert_fails = True

    result = run(worker)

    assert result.status == "error"
    assert "database down" in (result.error or "")


# --------------------------------------------------------------------------------------------
# Timing: the empty-look clock and the context cache
# --------------------------------------------------------------------------------------------


def test_an_empty_look_is_asked_for_at_most_every_30_seconds(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.gate, seen.vlm = "closed", "not_asked"
    frames = ["empty_table_01", "empty_chair_01", "empty_floor_01", "empty_table_02"]

    for name, seconds in zip(frames, (0, 10, 29, 30), strict=True):
        run(worker, name, T0 + timedelta(seconds=seconds))

    # The gate stayed closed, so Gemini never looked: each frame was due an empty look again.
    assert seen.empty_looks == [True, True, True, True]


def test_a_look_by_gemini_resets_the_empty_look_clock(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    run(worker, "close_keys_table_01", T0)  # SAM 3 opened the gate and Gemini looked
    seen.gate, seen.vlm = "closed", "not_asked"
    run(worker, "empty_chair_01", T0 + timedelta(seconds=29))
    run(worker, "empty_floor_01", T0 + timedelta(seconds=30))

    assert seen.empty_looks == [True, False, True]


def test_a_busy_gemini_gives_the_empty_look_back(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    seen.vlm = "busy"
    run(worker, "empty_table_01", T0)
    run(worker, "empty_chair_01", T0 + timedelta(seconds=1))

    assert seen.empty_looks == [True, True]


def test_the_context_is_read_once_for_frames_close_together(
    worker: Worker, fake_db: FakeDB, seen: FakePerceive
) -> None:
    run(worker, "close_keys_table_01", T0)
    run(worker, "close_bag_table_01", T0 + timedelta(seconds=2))

    assert [name for name, _ in fake_db.calls].count("perception_context") == 1
    assert [name for name, _ in fake_db.calls].count("home_map") == 1
