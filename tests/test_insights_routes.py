"""The insights routes with the database faked: token, shapes, and failure handling."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.memory import db
from app.memory.schema import Concern, HomeInfo, LifeEvent, PatternRows, WearHour

client = TestClient(app)
ROOM = UUID("10000000-0000-0000-0000-000000000001")
HOME = HomeInfo(person_name="Rose", timezone="America/New_York")


@pytest.fixture
def auth(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    monkeypatch.setenv("APP_TOKEN", "test-token")
    get_settings.cache_clear()
    yield {"Authorization": "Bearer test-token"}
    get_settings.cache_clear()


class FakeDB:
    def __init__(self) -> None:
        self.added: list[tuple[Any, ...]] = []
        self.room_fails = False
        self.store_fails = False

    async def last_room(self) -> tuple[UUID, str] | None:
        if self.room_fails:
            raise TimeoutError
        return ROOM, "the kitchen"

    async def add_concern(self, *args: Any) -> UUID:
        if self.store_fails:
            raise ConnectionError("database down")
        self.added.append(args)
        return UUID(int=7)

    async def concerns(self, since: datetime) -> list[Concern]:
        now = datetime.now(UTC)
        return [
            Concern(id=uuid4(), kind="scam", urgency="note", channel="facetime",
                    raised_at=now, status="all_ok"),
            Concern(id=uuid4(), kind="fall", answer="no_answer", urgency="urgent",
                    channel="facetime", raised_at=now - timedelta(hours=1), room="the kitchen",
                    status="open"),
        ]  # fmt: skip

    async def home_info(self) -> HomeInfo:
        return HOME

    async def wear_hours(self, since: date) -> list[WearHour]:
        return []

    async def wearer_questions_since(self, since: datetime) -> int:
        return 0

    async def handle_concern(self, concern_id: UUID, status: str, by: str) -> Concern | None:
        if concern_id != UUID(int=7):
            return None
        return Concern(id=concern_id, kind="fall", urgency="urgent", channel="facetime",
                       raised_at=datetime.now(UTC), status=status, handled_by=by)  # type: ignore[arg-type]  # fmt: skip

    async def add_life_event(self, kind: str, starts_at: datetime, *_: Any) -> LifeEvent:
        return LifeEvent(id=uuid4(), kind=kind, starts_at=starts_at)  # type: ignore[arg-type]

    async def life_events(self, since: datetime) -> list[LifeEvent]:
        return []

    async def pattern_rows(self, since: datetime, history_since: datetime) -> PatternRows:
        return PatternRows(home=HOME, items=[], places=[], wear=[], events=[], questions=[],
                           answered_by=[], put_downs=[])  # fmt: skip


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeDB:
    f = FakeDB()
    for name in (
        "last_room", "add_concern", "concerns", "home_info", "wear_hours",
        "wearer_questions_since", "handle_concern", "add_life_event", "life_events",
        "pattern_rows",
    ):  # fmt: skip
        monkeypatch.setattr(db, name, getattr(f, name))
    return f


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/concerns"),
        ("get", "/api/concerns"),
        ("post", f"/api/concerns/{UUID(int=7)}/handle"),
        ("post", "/api/events"),
        ("get", "/api/events"),
        ("get", "/api/patterns"),
    ],
)
def test_every_insights_route_needs_the_token(
    method: str, path: str, auth: dict[str, str], fake: FakeDB
) -> None:
    response = getattr(client, method)(path, headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_a_fall_with_no_answer_is_urgent_and_names_the_last_room(
    auth: dict[str, str], fake: FakeDB
) -> None:
    response = client.post("/concerns", json={"kind": "fall", "answer": "no_answer"}, headers=auth)
    assert response.status_code == 201
    assert response.json() == {"id": str(UUID(int=7)), "urgency": "urgent", "room": "the kitchen"}
    assert fake.added == [("fall", "no_answer", "urgent", "facetime", ROOM)]


def test_a_concern_is_stored_even_when_the_room_lookup_fails(
    auth: dict[str, str], fake: FakeDB
) -> None:
    fake.room_fails = True
    response = client.post("/concerns", json={"kind": "scam"}, headers=auth)
    assert response.json() == {"id": str(UUID(int=7)), "urgency": "note", "room": None}


def test_a_failed_store_is_a_503_the_agent_can_swallow(auth: dict[str, str], fake: FakeDB) -> None:
    fake.store_fails = True
    response = client.post("/concerns", json={"kind": "fall", "answer": "hurt"}, headers=auth)
    assert response.status_code == 503


@pytest.mark.parametrize("body", [{"kind": "quiet_day"}, {"kind": "fall", "answer": "maybe"}, {}])
def test_the_agent_cannot_send_unknown_kinds_or_answers(
    body: dict[str, str], auth: dict[str, str], fake: FakeDB
) -> None:
    assert client.post("/concerns", json=body, headers=auth).status_code == 422


def test_the_board_puts_open_concerns_first(auth: dict[str, str], fake: FakeDB) -> None:
    body = client.get("/api/concerns", headers=auth).json()
    assert [c["status"] for c in body["concerns"]] == ["open", "all_ok"]
    assert body["concerns"][0]["room"] == "the kitchen"
    assert body["quiet_day"] is None


def test_the_family_answers_a_concern(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post(
        f"/api/concerns/{UUID(int=7)}/handle",
        json={"status": "on_my_way", "by": "June"},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "on_my_way"
    missing = client.post(
        f"/api/concerns/{uuid4()}/handle", json={"status": "all_ok", "by": "June"}, headers=auth
    )
    assert missing.status_code == 404
    no_dispatch = client.post(
        f"/api/concerns/{UUID(int=7)}/handle",
        json={"status": "dispatched", "by": "x"},
        headers=auth,
    )
    assert no_dispatch.status_code == 422


def test_a_family_tag(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post(
        "/api/events",
        json={"kind": "new_medicine", "starts_at": "2026-11-14T09:00:00-05:00"},
        headers=auth,
    )
    assert response.status_code == 201
    assert response.json()["kind"] == "new_medicine"
    assert (
        client.post(
            "/api/events",
            json={"kind": "diagnosis", "starts_at": "2026-11-14T09:00:00Z"},
            headers=auth,
        ).status_code
        == 422
    )


def test_patterns_with_no_history_is_still_learning(auth: dict[str, str], fake: FakeDB) -> None:
    body = client.get("/api/patterns?days=14", headers=auth).json()
    assert body["status"] == "learning"
    assert body["changes"] == []
    assert len(body["days"]) == 14
    assert (
        body["note"] == "Everyday observations compared with Rose's own usual. Not a medical test."
    )
