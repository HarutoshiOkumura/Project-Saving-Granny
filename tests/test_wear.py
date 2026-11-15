"""Wear time (docs/INSIGHTS.md design 1): the minute counter, "moved", and the worker's flush."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.config import get_settings
from app.memory import db
from app.perception.filters import FilterVerdict
from app.worker import ingest as worker_module
from app.worker.ingest import Worker
from app.worker.wear import WearCount, WearCounter, moved

T0 = datetime(2026, 11, 15, 14, 0, 5, tzinfo=UTC)


def test_a_blurry_or_first_frame_moved_and_a_duplicate_did_not() -> None:
    assert moved(FilterVerdict("blurry", 10.0, None), 0.95)
    assert moved(FilterVerdict("ok", 60.0, None), 0.95)
    assert moved(FilterVerdict("ok", 60.0, 0.4), 0.95)
    assert not moved(FilterVerdict("duplicate", 60.0, 0.97), 0.95)
    assert not moved(FilterVerdict("ok", 60.0, 0.97), 0.95)  # kept as a refresh, still still


def test_frames_are_counted_per_device_and_whole_minute() -> None:
    counter = WearCounter()
    counter.add("lanyard", T0, True)
    counter.add("lanyard", T0 + timedelta(seconds=30), False)
    counter.add("lanyard", T0 + timedelta(seconds=60), True)
    counter.add("spare", T0, True)
    assert counter.take() == [
        WearCount("lanyard", datetime(2026, 11, 15, 14, 0, tzinfo=UTC), 2, 1),
        WearCount("lanyard", datetime(2026, 11, 15, 14, 1, tzinfo=UTC), 1, 1),
        WearCount("spare", datetime(2026, 11, 15, 14, 0, tzinfo=UTC), 1, 1),
    ]
    assert counter.take() == []  # nothing changed since


def test_a_minute_taken_while_filling_comes_back_with_its_full_count() -> None:
    counter = WearCounter()
    counter.add("lanyard", T0, True)
    assert counter.take()[0].frames == 1
    counter.add("lanyard", T0 + timedelta(seconds=20), True)
    assert counter.take() == [WearCount("lanyard", datetime(2026, 11, 15, 14, 0, tzinfo=UTC), 2, 2)]


def test_a_failed_store_is_sent_again() -> None:
    counter = WearCounter()
    counter.add("lanyard", T0, True)
    taken = counter.take()
    counter.give_back(taken)
    assert counter.take() == taken


def test_old_minutes_are_forgotten() -> None:
    counter = WearCounter()
    counter.add("lanyard", T0, True)
    counter.take()
    counter.add("lanyard", T0 + timedelta(minutes=20), True)
    counter.take()
    counter.give_back([WearCount("lanyard", T0.replace(second=0), 1, 1)])
    assert counter.take() == []  # 20 minutes old: no longer remembered, not resent


class FakeWearDB:
    def __init__(self, fails: bool = False) -> None:
        self.stored: list[list[WearCount]] = []
        self.fails = fails

    async def upsert_wear_minutes(self, counts: list[Any]) -> None:
        if self.fails:
            raise ConnectionError("database down")
        self.stored.append(list(counts))


@pytest.fixture
def no_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """Frames stop at the filters: blank JPEGs are blurry, so no model or database is reached."""

    async def never(*_: Any, **__: Any) -> Any:
        raise AssertionError("a blurry frame must not reach the models")

    monkeypatch.setattr(worker_module, "perceive", never)


def blank_jpeg() -> bytes:
    from io import BytesIO

    from PIL import Image

    out = BytesIO()
    Image.new("RGB", (64, 48), "gray").save(out, "JPEG")
    return out.getvalue()


def test_the_worker_counts_every_frame_and_flushes_at_most_every_15_s(
    monkeypatch: pytest.MonkeyPatch, no_models: None
) -> None:
    fake = FakeWearDB()
    monkeypatch.setattr(db, "upsert_wear_minutes", fake.upsert_wear_minutes)
    worker = Worker(get_settings())
    jpeg = blank_jpeg()

    asyncio.run(worker.ingest(jpeg, "lanyard", T0))
    assert fake.stored == []  # under 15 s since the worker started
    worker._wear_flushed -= 16
    asyncio.run(worker.ingest(jpeg, "lanyard", T0 + timedelta(seconds=1)))
    assert fake.stored == [[WearCount("lanyard", T0.replace(second=0), 2, 2)]]


def test_a_failed_flush_keeps_the_minutes(monkeypatch: pytest.MonkeyPatch, no_models: None) -> None:
    fake = FakeWearDB(fails=True)
    monkeypatch.setattr(db, "upsert_wear_minutes", fake.upsert_wear_minutes)
    worker = Worker(get_settings())
    asyncio.run(worker.ingest(blank_jpeg(), "lanyard", T0))
    assert asyncio.run(worker.flush_wear()) == 0
    fake.fails = False
    assert asyncio.run(worker.flush_wear()) == 1
