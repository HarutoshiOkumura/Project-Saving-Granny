"""db functions with a fake Supabase client: parameter names, parsing, timeouts. No network."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.memory import db
from app.memory.schema import FindResult

HOME_ID = "11111111-1111-1111-1111-111111111111"


class FakeClient:
    def __init__(self, data: Any, delay: float = 0.0) -> None:
        self.data = data
        self.delay = delay
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def rpc(self, name: str, params: dict[str, Any]) -> "FakeClient":
        self.calls.append((name, params))
        return self

    async def execute(self) -> SimpleNamespace:
        await asyncio.sleep(self.delay)
        return SimpleNamespace(data=self.data)


def use(monkeypatch: pytest.MonkeyPatch, fake: FakeClient) -> None:
    async def get_client() -> FakeClient:
        return fake

    monkeypatch.setattr(db, "_get_client", get_client)


def test_ask_item_calls_the_rpc_with_contract_names(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient({"state": "unknown_item", "heard": "my wallet", "query_id": HOME_ID})
    use(monkeypatch, fake)

    answer = asyncio.run(db.ask_item("my wallet", "phone"))

    assert fake.calls == [
        ("ask_item", {"p_home": HOME_ID, "p_query": "my wallet", "p_channel": "phone"})
    ]
    assert answer == FindResult(state="unknown_item", heard="my wallet", query_id=HOME_ID)


def test_ask_item_ignores_unknown_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, FakeClient({"state": "unknown_item", "heard": "x", "brand_new_key": 1}))

    assert asyncio.run(db.ask_item("x", "web")).state == "unknown_item"


@pytest.mark.parametrize(
    "data",
    [
        None,
        {"heard": "x"},
        {"state": "teleported"},
        {"state": "seen", "timezone": "Mars/Olympus_Mons"},
        {"state": "seen", "last_seen_at": "2026-11-14T21:03:06"},  # no zone
    ],
)
def test_ask_item_rejects_answers_that_do_not_fit(
    monkeypatch: pytest.MonkeyPatch, data: Any
) -> None:
    use(monkeypatch, FakeClient(data))

    with pytest.raises(ValidationError):
        asyncio.run(db.ask_item("x", "web"))


def test_ask_item_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, FakeClient({"state": "unknown_item"}, delay=5))
    monkeypatch.setattr(db, "READ_TIMEOUT_S", 0.05)

    with pytest.raises(TimeoutError):
        asyncio.run(db.ask_item("x", "web"))


CONTEXT = {
    "rooms": ["b_school_classroom", "bathroom"],
    "landmarks": [{"room": "b_school_classroom", "landmark": "chair", "kind": "surface"}],
    "items": [{"item": "glasses", "looks_like": "black, black reading glasses"}],
    "beliefs": None,
}


def test_perception_context_calls_the_rpc_with_contract_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeClient(CONTEXT)
    use(monkeypatch, fake)

    context = asyncio.run(db.perception_context())

    assert fake.calls == [("perception_context", {"p_home": HOME_ID, "p_room": None})]
    assert context.landmarks[0].address == "b_school_classroom > chair"
    assert context.beliefs == []  # jsonb_agg over no rows is null


def test_perception_context_passes_the_room(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(CONTEXT)
    use(monkeypatch, fake)
    room = "22222222-2222-2222-2222-222222222222"

    asyncio.run(db.perception_context(UUID(room)))

    assert fake.calls[0][1]["p_room"] == room


# ---------------------------------------------------------------------------------------------
# look_evidence and sign_photos (D33): table reads and Storage, with a fake query builder
# ---------------------------------------------------------------------------------------------


class FakeQuery:
    """Records one table read as (method, args) pairs; `execute` returns the table's rows."""

    def __init__(self, table: str, rows: list[dict[str, Any]], log: list["FakeQuery"]) -> None:
        self.table = table
        self.rows = rows
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        log.append(self)

    def __getattr__(self, method: str) -> Any:
        if method == "not_":
            self.calls.append(("not", ()))
            return self

        def record(*args: Any, **kwargs: Any) -> "FakeQuery":
            self.calls.append((method, args + tuple(sorted(kwargs.items()))))
            return self

        return record

    async def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self.rows)


class FakeBucket:
    def __init__(self, name: str, signed: list[list[str]]) -> None:
        self.name = name
        self.signed = signed

    async def create_signed_urls(self, keys: list[str], expires_in: int) -> list[dict[str, Any]]:
        assert expires_in == 3600
        self.signed.append([self.name, *keys])
        return [
            {"path": k, "error": None, "signedURL": f"https://x/sign/{self.name}/{k}?token=t"}
            if "missing" not in k
            else {"path": k, "error": "Either the object does not exist", "signedURL": None}
            for k in keys
        ]


class FakeTables:
    def __init__(self, rows: dict[str, list[dict[str, Any]]]) -> None:
        self.rows = rows
        self.reads: list[FakeQuery] = []
        self.signed: list[list[str]] = []
        self.storage = SimpleNamespace(from_=lambda bucket: FakeBucket(bucket, self.signed))

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(name, self.rows.get(name, []), self.reads)


LM = "00000000-0000-0000-0000-00000000000a"
ITEM = "00000000-0000-0000-0000-000000000001"


def test_look_evidence_reads_places_habits_and_glimpses_for_this_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeTables(
        {
            "places": [
                {
                    "landmark_id": LM,
                    "address": "classroom > table",
                    "room_spoken": "the classroom",
                    "landmark_spoken": "the table",
                }
            ],
            "item_usual_places": [
                {
                    "item_id": ITEM,
                    "landmark_id": LM,
                    "episodes": 3,
                    "pct": 100,
                    "last_seen_at": "2026-11-15T05:00:00+00:00",
                }
            ],
            "sightings": [
                {"item_id": ITEM, "landmark_id": LM, "last_seen_at": "2026-11-15T05:59:00Z"}
            ],
        }
    )
    use(monkeypatch, fake)  # type: ignore[arg-type]
    since = datetime(2026, 11, 14, 6, 0, tzinfo=UTC)

    ev = asyncio.run(db.look_evidence([UUID(ITEM)], since))

    assert ev.places[0].landmark_spoken == "the table"
    assert ev.usual[0].episodes == 3
    assert ev.glimpses[0].landmark_id == UUID(LM)
    reads = {q.table: q.calls for q in fake.reads}
    assert ("eq", ("home_id", HOME_ID)) in reads["places"]
    assert ("in_", ("item_id", [ITEM])) in reads["item_usual_places"]
    glimpses = reads["sightings"]
    assert ("eq", ("home_id", HOME_ID)) in glimpses
    assert ("eq", ("status", "tentative")) in glimpses
    assert ("eq", ("in_hand", "false")) in glimpses
    assert ("gte", ("last_seen_at", "2026-11-14T06:00:00+00:00")) in glimpses
    assert ("order", ("last_seen_at", ("desc", True))) in glimpses


def test_look_evidence_skips_the_habit_read_with_no_items(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeTables({})
    use(monkeypatch, fake)  # type: ignore[arg-type]

    ev = asyncio.run(db.look_evidence([], datetime(2026, 11, 14, tzinfo=UTC)))

    assert ev.usual == [] and ev.places == [] and ev.glimpses == []
    assert sorted(q.table for q in fake.reads) == ["places", "sightings"]


def test_sign_photos_signs_each_path_once_and_drops_missing_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeTables({})
    use(monkeypatch, fake)  # type: ignore[arg-type]
    a = f"crops/{HOME_ID}/glasses/20261115T010203000000Z.jpg"
    gone = f"crops/{HOME_ID}/keys/missing.jpg"

    links = asyncio.run(db.sign_photos([a, gone, a, "no-bucket"]))

    assert fake.signed == [["crops", a.removeprefix("crops/"), gone.removeprefix("crops/")]]
    assert links == {a: f"https://x/sign/{a}?token=t"}
