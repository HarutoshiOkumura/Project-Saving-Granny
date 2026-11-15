"""db's two reads for guidance with a fake Supabase client: which tables, which filters, and
how the rows are parsed. No network."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from app.memory import db
from app.memory.schema import HomeLayout, Observation

HOME = "11111111-1111-1111-1111-111111111111"


def uid(n: int) -> str:
    return str(UUID(int=n))


class Query:
    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client, self.table, self.ops = client, table, []

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> "Query":
            self.ops.append((name, args, kwargs))
            return self

        return record

    async def execute(self) -> SimpleNamespace:
        await asyncio.sleep(self.client.delay)
        self.client.queries.append((self.table, self.ops))
        return SimpleNamespace(data=self.client.rows[self.table])


class FakeClient:
    def __init__(self, delay: float = 0.0, **rows: Any) -> None:
        self.rows, self.delay = rows, delay
        self.queries: list[tuple[str, list[Any]]] = []

    def table(self, name: str) -> Query:
        return Query(self, name)


def use(monkeypatch: pytest.MonkeyPatch, fake: FakeClient) -> FakeClient:
    async def get_client() -> FakeClient:
        return fake

    monkeypatch.setattr(db, "_get_client", get_client)
    return fake


def test_latest_view_reads_the_newest_worn_camera_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "captured_at": "2026-11-15T06:00:01.250000+00:00",
        "room_id": uid(3),
        "landmarks_seen": [uid(11), uid(12)],
    }
    fake = use(monkeypatch, FakeClient(observations=[row]))

    view = asyncio.run(db.latest_view())

    assert fake.queries == [
        (
            "observations",
            [
                ("select", ("captured_at,room_id,landmarks_seen",), {}),
                ("eq", ("home_id", HOME), {}),
                ("eq", ("source", "worn_cam"), {}),
                ("order", ("captured_at",), {"desc": True}),
                ("limit", (1,), {}),
            ],
        )
    ]
    assert view == Observation(
        captured_at=datetime(2026, 11, 15, 6, 0, 1, 250000, tzinfo=UTC),
        room_id=UUID(int=3),
        landmarks_seen=[UUID(int=11), UUID(int=12)],
    )


def test_latest_view_is_none_before_the_first_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, FakeClient(observations=[]))

    assert asyncio.run(db.latest_view()) is None


def test_latest_view_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, FakeClient(delay=1.0, observations=[]))
    monkeypatch.setattr(db, "READ_TIMEOUT_S", 0.05)

    with pytest.raises(TimeoutError):
        asyncio.run(db.latest_view())


def test_home_layout_reads_rooms_places_and_links(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(
        monkeypatch,
        FakeClient(
            rooms=[
                {"id": uid(1), "name": "bedroom", "spoken_name": "your bedroom", "floor": 1},
                {"id": uid(2), "name": "hallway", "spoken_name": None, "floor": None},
            ],
            places=[{"landmark_id": uid(12), "room_id": uid(1), "address": "bedroom > nightstand"}],
            room_links=[{"room_a": uid(1), "room_b": uid(2)}],
        ),
    )

    layout = asyncio.run(db.home_layout())

    assert [(table, ops[0], ops[-1]) for table, ops in fake.queries] == [
        ("rooms", ("select", ("id,name,spoken_name,floor",), {}), ("eq", ("home_id", HOME), {})),
        ("places", ("select", ("landmark_id,room_id,address",), {}), ("eq", ("home_id", HOME), {})),
        (
            "room_links",
            ("select", ("room_a,room_b",), {}),
            ("in_", ("room_a", [uid(1), uid(2)]), {}),
        ),
    ]
    assert layout == HomeLayout.model_validate(
        {
            "rooms": [
                {"id": uid(1), "spoken": "your bedroom", "floor": 1},
                {"id": uid(2), "spoken": "hallway", "floor": None},  # no spoken name: the name
            ],
            "landmarks": [{"id": uid(12), "room_id": uid(1), "address": "bedroom > nightstand"}],
            "links": [(uid(1), uid(2))],
        }
    )


def test_home_layout_of_an_empty_home_asks_for_no_links(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(monkeypatch, FakeClient(rooms=[], places=[]))

    assert asyncio.run(db.home_layout()) == HomeLayout()
    assert [table for table, _ in fake.queries] == ["rooms", "places"]
