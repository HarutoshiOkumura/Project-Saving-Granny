"""GET /snapshot with the database faked: every item's current answer, where to look, photo links
only with the token, and no question logged."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.memory import db
from app.memory.schema import FindResult, Item, LookEvidence, PlaceName
from app.speak import FALLBACK

client = TestClient(app)

TABLE = UUID("00000000-0000-0000-0000-00000000000a")
CHAIR = UUID("00000000-0000-0000-0000-00000000000b")
PHOTO = "crops/11111111-1111-1111-1111-111111111111/glasses/20261115T010203000000Z.jpg"
SIGNED = "https://fake-project.supabase.co/storage/v1/object/sign/crops/x.jpg?token=t"


def place(landmark_id: UUID, landmark: str) -> PlaceName:
    return PlaceName(
        landmark_id=landmark_id,
        address=f"classroom > {landmark}",
        room_spoken="the classroom",
        landmark_spoken=f"the {landmark}",
    )


@pytest.fixture(autouse=True)
def evidence(monkeypatch: pytest.MonkeyPatch) -> list[list[UUID]]:
    """The table and the chair, no habits and no glimpses; records which items were asked for."""
    asked: list[list[UUID]] = []

    async def fake_look_evidence(item_ids: list[UUID], since: datetime) -> LookEvidence:
        asked.append(item_ids)
        return LookEvidence(places=[place(TABLE, "table"), place(CHAIR, "chair")])

    async def no_signing(paths: list[str]) -> dict[str, str]:
        raise AssertionError("photo links only for a request with the token")

    monkeypatch.setattr(db, "look_evidence", fake_look_evidence)
    monkeypatch.setattr(db, "sign_photos", no_signing)
    return asked


@pytest.fixture
def token(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    monkeypatch.setenv("APP_TOKEN", "test-token")
    get_settings.cache_clear()
    yield {"Authorization": "Bearer test-token"}
    get_settings.cache_clear()


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
            "address": "classroom > table",
            "minutes_ago": minutes,
            "last_seen_at": last_seen.isoformat(),
            "timezone": "America/New_York",
            "confident": True,
            "photo": PHOTO,
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
                category="glasses",
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
    assert body[0]["kind"] == "glasses"
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
        "kind": None,
        "color": None,
        "looks_like": None,
        "sentence": FALLBACK,
        "result": None,
        "where_to_look": None,
        "photo_url": None,
    }


def test_where_to_look_ranks_the_last_place_first(looked_up: list[str]) -> None:
    body = client.get("/snapshot").json()
    look = body[0]["where_to_look"]
    assert look["band"] == "high"
    assert [(p["landmark"], p["why"]) for p in look["places"]] == [("the table", ["last_seen"])]
    assert look["places"][0]["pct"] + look["elsewhere_pct"] == 100
    assert look["places"][0]["pct"] >= 80
    assert look["places"][0]["minutes_ago"] == 40
    assert look["places"][0]["landmark_id"] == str(TABLE)
    never = body[1]["where_to_look"]
    assert never == {"band": "low", "places": [], "elsewhere_pct": 100, "ruled_out": None}


def test_the_habits_are_read_once_for_every_item(
    looked_up: list[str], evidence: list[list[UUID]]
) -> None:
    client.get("/snapshot")
    assert len(evidence) == 1
    assert len(evidence[0]) == 2


def test_no_photo_link_without_the_token(looked_up: list[str]) -> None:
    body = client.get("/snapshot").json()
    assert body[0]["result"]["photo"] == PHOTO
    assert body[0]["photo_url"] is None


def test_no_photo_link_with_a_wrong_token(looked_up: list[str], token: dict[str, str]) -> None:
    body = client.get("/snapshot", headers={"Authorization": "Bearer nope"}).json()
    assert body[0]["photo_url"] is None


def test_photo_link_with_the_token(
    looked_up: list[str], token: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    signed: list[list[str]] = []

    async def fake_sign(paths: list[str]) -> dict[str, str]:
        signed.append(paths)
        return {PHOTO: SIGNED}

    monkeypatch.setattr(db, "sign_photos", fake_sign)
    body = client.get("/snapshot", headers=token).json()
    assert body[0]["photo_url"] == SIGNED
    assert body[1]["photo_url"] is None  # never seen: no photo
    assert signed == [[PHOTO]]


def test_failed_photo_links_leave_the_rest(
    looked_up: list[str], token: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(paths: list[str]) -> dict[str, str]:
        raise TimeoutError

    monkeypatch.setattr(db, "sign_photos", broken)
    body = client.get("/snapshot", headers=token).json()
    assert body[0]["photo_url"] is None
    assert body[0]["sentence"].startswith("I last saw your glasses")
    assert body[0]["where_to_look"]["places"][0]["landmark"] == "the table"


def test_failed_habit_read_leaves_the_sentences(
    looked_up: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(item_ids: list[UUID], since: datetime) -> LookEvidence:
        raise TimeoutError

    monkeypatch.setattr(db, "look_evidence", broken)
    body = client.get("/snapshot").json()
    assert body[0]["sentence"].startswith("I last saw your glasses")
    assert body[0]["where_to_look"] is None
