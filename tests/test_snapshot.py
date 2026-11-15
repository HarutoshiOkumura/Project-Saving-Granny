"""GET /snapshot with the database faked: every item's current answer, and no question logged."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.memory import db
from app.memory.schema import FindResult, Item
from app.speak import FALLBACK

client = TestClient(app)


def seen_on_the_table(item: str, minutes: int) -> FindResult:
    last_seen = datetime.now(UTC) - timedelta(minutes=minutes)
    return FindResult.model_validate(
        {
            "state": "seen",
            "item": item,
            "plural": item.endswith("s"),
            "room": "the classroom",
            "landmark": "the table",
            "relation": "on",
            "minutes_ago": minutes,
            "last_seen_at": last_seen.isoformat(),
            "timezone": "America/New_York",
            "confident": True,
        }
    )


@pytest.fixture
def looked_up(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    looked: list[str] = []

    async def fake_list_items() -> list[Item]:
        return [
            Item(
                id=uuid4(),
                name="glasses",
                aliases=["specs"],
                color="black",
                description="reading glasses",
            ),
            Item(id=uuid4(), name="watch"),
        ]

    async def fake_find_item(query: str) -> FindResult:
        looked.append(query)
        if query == "glasses":
            return seen_on_the_table("glasses", 40)
        return FindResult.model_validate({"state": "never_seen", "item": query, "plural": False})

    async def no_ask_item(*_: object) -> FindResult:
        raise AssertionError("the snapshot must not log questions")

    monkeypatch.setattr(db, "list_items", fake_list_items)
    monkeypatch.setattr(db, "find_item", fake_find_item)
    monkeypatch.setattr(db, "ask_item", no_ask_item)
    return looked


def test_snapshot_gives_every_items_sentence_without_logging_questions(
    looked_up: list[str],
) -> None:
    body = client.get("/snapshot").json()
    assert [k["item"] for k in body] == ["glasses", "watch"]
    assert body[0]["aliases"] == ["specs"]
    assert body[0]["looks_like"] == "black, reading glasses"
    assert body[0]["color"] == "black"
    assert body[1]["looks_like"] is None
    assert body[0]["sentence"] == "I last saw your glasses on the table about forty minutes ago."
    assert body[0]["result"]["landmark"] == "the table"
    assert body[1]["sentence"] == "I haven't seen your watch yet."
    assert looked_up == ["glasses", "watch"]


def test_snapshot_is_empty_when_the_database_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken() -> list[Item]:
        raise TimeoutError

    monkeypatch.setattr(db, "list_items", broken)
    assert client.get("/snapshot").json() == []


def test_one_failing_item_falls_back_on_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_list_items() -> list[Item]:
        return [Item(id=uuid4(), name="glasses"), Item(id=uuid4(), name="keys")]

    async def flaky_find_item(query: str) -> FindResult:
        if query == "keys":
            raise TimeoutError
        return seen_on_the_table("glasses", 40)

    monkeypatch.setattr(db, "list_items", fake_list_items)
    monkeypatch.setattr(db, "find_item", flaky_find_item)
    body = client.get("/snapshot").json()
    assert body[0]["sentence"].startswith("I last saw your glasses")
    assert body[1] == {
        "item": "keys",
        "aliases": [],
        "color": None,
        "looks_like": None,
        "sentence": FALLBACK,
        "result": None,
    }
