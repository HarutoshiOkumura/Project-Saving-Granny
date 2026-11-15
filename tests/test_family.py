"""The family dashboard (step 08): name rules, the photo-link cache, and the routes with the
database faked."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import family, photos
from app.config import get_settings
from app.family import ItemIn, LandmarkIn, RoomIn, clash, normalize, place_word, spoken
from app.main import app
from app.memory import db
from app.memory.schema import FindResult, HomeInfo, Item, Room, SetupPlace, TimelineRow

client = TestClient(app)
GLASSES = Item(id=uuid4(), name="glasses", aliases=["specs", "readers"])
BOTTLE = Item(id=uuid4(), name="water bottle", aliases=["bottle"])
KITCHEN = Room(id=uuid4(), name="kitchen", spoken_name="the kitchen", capture_allowed=True)
BATHROOM = Room(id=uuid4(), name="bathroom", spoken_name="the bathroom", capture_allowed=False)
TABLE = SetupPlace(landmark_id=uuid4(), room_id=KITCHEN.id, room="the kitchen",
                   landmark="the table", kind="surface", address="kitchen > table",
                   capture_allowed=True)  # fmt: skip


# ---------------------------------------------------------------------------------------------
# Name rules
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("said", "stored"),
    [
        ("My Glasses", "glasses"),
        ("  the   blue  bag ", "blue bag"),
        ("a hat", "hat"),
        ("map", "map"),
    ],
)
def test_names_are_stored_the_way_find_item_reads_a_question(said: str, stored: str) -> None:
    assert normalize(said) == stored


def test_a_name_or_alias_already_used_is_refused_with_whose_it_is() -> None:
    items = [GLASSES, BOTTLE]
    assert clash("bottle", [], items) == '"bottle" is already another name of your water bottle.'
    assert clash("my glasses", [], items) == '"glasses" is already the name of your glasses.'
    assert (
        clash("sunglasses", ["Specs"], items) == '"specs" is already another name of your glasses.'
    )
    assert clash("orange bottle", ["orange flask"], items) is None


def test_the_item_form_cleans_its_words() -> None:
    body = ItemIn(
        name="My Brown Bag", aliases=["the satchel", "", "satchel", "Brown Bag"], kind="Bag"
    )
    assert body.name == "brown bag"
    assert body.aliases == ["satchel", "brown bag"]
    assert body.kind == "bag"
    with pytest.raises(ValidationError):
        ItemIn(name="bag <script>")


@pytest.mark.parametrize("bad", ["unknown", "none", "kitchen > shelf", "", "x" * 41, "café"])
def test_room_and_place_names_must_be_words_the_camera_model_can_answer_with(bad: str) -> None:
    with pytest.raises(ValueError):
        place_word(bad)


def test_room_names_and_spoken_words() -> None:
    assert place_word("  Living   Room ") == "living room"
    assert spoken(None, "living_room") == "the living room"
    assert spoken("  Mum's  den ", "den") == "Mum's den"


def test_a_room_needs_a_capture_choice() -> None:
    with pytest.raises(ValidationError):
        RoomIn(name="hall")  # type: ignore[call-arg]
    assert RoomIn(name="Hall", capture_allowed=False).name == "hall"


# ---------------------------------------------------------------------------------------------
# Photo links
# ---------------------------------------------------------------------------------------------


def test_the_same_photo_keeps_the_same_link_while_it_is_fresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signed: list[list[str]] = []

    async def sign(paths: list[str]) -> dict[str, str]:
        signed.append(sorted(paths))
        return {p: f"https://x/{p}?token={len(signed)}" for p in paths if "gone" not in p}

    monkeypatch.setattr(db, "sign_photos", sign)
    first = asyncio.run(photos.links(["crops/a.jpg", "crops/gone.jpg"]))
    again = asyncio.run(photos.links(["crops/a.jpg", "crops/b.jpg"]))
    assert first == {"crops/a.jpg": "https://x/crops/a.jpg?token=1"}
    assert again["crops/a.jpg"] == first["crops/a.jpg"]  # not signed again
    assert signed == [["crops/a.jpg", "crops/gone.jpg"], ["crops/b.jpg"]]
    monkeypatch.setattr(photos.time, "monotonic", lambda: 1e12)  # an hour later
    later = asyncio.run(photos.links(["crops/a.jpg"]))
    assert later["crops/a.jpg"].endswith("token=3")


# ---------------------------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def auth(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    monkeypatch.setenv("APP_TOKEN", "test-token")
    get_settings.cache_clear()
    yield {"Authorization": "Bearer test-token"}
    get_settings.cache_clear()


class FakeDB:
    def __init__(self) -> None:
        self.items = [GLASSES, BOTTLE]
        self.added: list[dict[str, Any]] = []
        self.told: list[tuple[Any, ...]] = []
        self.duplicate = False

    async def list_items(self) -> list[Item]:
        return self.items

    async def rooms(self) -> list[Room]:
        return [BATHROOM, KITCHEN]

    async def setup_places(self) -> list[SetupPlace]:
        return [TABLE]

    async def timeline(self, include_glimpses: bool, limit: int = 50) -> list[TimelineRow]:
        now = datetime.now(UTC)
        rows = [
            TimelineRow(sighting_id=uuid4(), item="glasses", event_type="seen", status="active",
                        in_hand=False, first_seen_at=now, last_seen_at=now, room="the kitchen",
                        landmark="the table", photo="crops/g.jpg"),
            TimelineRow(sighting_id=uuid4(), item=None, event_type="seen", status="active",
                        in_hand=False, first_seen_at=now, last_seen_at=now, room="the kitchen"),
        ]  # fmt: skip
        if include_glimpses:
            rows.append(rows[0].model_copy(update={"status": "tentative", "photo": None}))
        return rows

    async def log_told(self, *args: Any) -> UUID:
        self.told.append(args)
        return UUID(int=9)

    async def find_item(self, query: str) -> FindResult:
        return FindResult.model_validate(
            {"state": "seen", "item": query, "plural": True, "room": "the kitchen",
             "landmark": "the table", "relation": "on", "confident": True,
             "last_seen_at": datetime.now(UTC).isoformat(), "timezone": "America/New_York"}
        )  # fmt: skip

    async def add_item(self, **row: Any) -> Item:
        if self.duplicate:
            raise db.Duplicate("23505")
        self.added.append(row)
        return Item(id=uuid4(), **{k: v for k, v in row.items() if k != "home_landmark_id"})

    async def add_room(self, **row: Any) -> Room:
        if self.duplicate:
            raise db.Duplicate("23505")
        self.added.append(row)
        return Room(id=uuid4(), **row)

    async def add_landmark(self, **row: Any) -> UUID:
        self.added.append(row)
        return TABLE.landmark_id

    async def home_info(self) -> HomeInfo:
        return HomeInfo(person_name="Rose", timezone="America/New_York")

    async def camera_today(self, day_start: datetime) -> tuple[int, datetime | None]:
        return 75, datetime.now(UTC) - timedelta(minutes=2)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeDB:
    f = FakeDB()
    for name in (
        "list_items", "rooms", "setup_places", "timeline", "log_told", "find_item", "add_item",
        "add_room", "add_landmark", "home_info", "camera_today",
    ):  # fmt: skip
        monkeypatch.setattr(db, name, getattr(f, name))

    async def sign(paths: list[str]) -> dict[str, str]:
        return {p: f"https://x/{p}?token=t" for p in paths}

    async def no_typesense(items: list[Item]) -> int:
        raise ConnectionError("typesense is not running")

    async def snapshot(*, with_photos: bool = False) -> list[Any]:
        assert with_photos
        return []

    async def concerns(now: datetime) -> family.ConcernBoard:
        raise TimeoutError

    monkeypatch.setattr(db, "sign_photos", sign)
    monkeypatch.setattr(family.names, "sync", no_typesense)
    monkeypatch.setattr(family, "snapshot", snapshot)
    monkeypatch.setattr(family, "concern_board", concerns)
    return f


def test_the_page_itself_needs_no_token() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "sb_secret" not in response.text and "SUPABASE" not in response.text


@pytest.mark.parametrize("path", ["/api/board", "/api/timeline", "/api/setup", "/api/places"])
def test_every_dashboard_read_needs_the_token(
    path: str, auth: dict[str, str], fake: FakeDB
) -> None:
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", ["/api/told", "/api/items", "/api/rooms", "/api/landmarks"])
def test_every_dashboard_write_needs_the_token(
    path: str, auth: dict[str, str], fake: FakeDB
) -> None:
    assert client.post(path, json={}).status_code == 401


def test_the_board_survives_a_failed_concern_read(auth: dict[str, str], fake: FakeDB) -> None:
    body = client.get("/api/board", headers=auth).json()
    assert body["person"] == "Rose"
    assert body["concerns"] == {"concerns": [], "quiet_day": None}
    assert body["camera"]["worn_minutes_today"] == 75


def test_the_timeline_signs_photos_and_keeps_unregistered_objects(
    auth: dict[str, str], fake: FakeDB
) -> None:
    rows = client.get("/api/timeline", headers=auth).json()
    assert rows[0]["photo_url"] == "https://x/crops/g.jpg?token=t"
    assert rows[1]["item"] is None and rows[1]["photo_url"] is None
    assert len(client.get("/api/timeline?debug=true", headers=auth).json()) == 3


def test_setup_lists_rooms_places_and_items(auth: dict[str, str], fake: FakeDB) -> None:
    body = client.get("/api/setup", headers=auth).json()
    assert [r["name"] for r in body["rooms"]] == ["bathroom", "kitchen"]
    assert body["places"][0]["landmark"] == "the table"
    assert [i["name"] for i in body["items"]] == ["glasses", "water bottle"]
    assert client.get("/api/places", headers=auth).json() == body["places"]


def test_telling_where_an_item_is(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post(
        "/api/told",
        json={"item": "My Glasses", "landmark_id": str(TABLE.landmark_id), "note": "by the fruit"},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["sentence"].startswith("I last saw your glasses on the table")
    assert fake.told == [(GLASSES.id, TABLE.landmark_id, "glasses", "by the fruit")]
    unknown = client.post(
        "/api/told", json={"item": "wallet", "landmark_id": str(TABLE.landmark_id)}, headers=auth
    )
    assert unknown.status_code == 422


def test_adding_an_item(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post(
        "/api/items",
        json={"name": "My Brown Bag", "color": "brown", "aliases": ["satchel"], "kind": "bag",
              "plural": False, "home_landmark_id": str(TABLE.landmark_id)},
        headers=auth,
    )  # fmt: skip
    assert response.status_code == 201
    assert response.json()["name"] == "brown bag"
    assert fake.added[0]["category"] == "bag"
    assert fake.added[0]["aliases"] == ["satchel"]


def test_an_item_that_would_shadow_another_is_refused(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post("/api/items", json={"name": "bottle"}, headers=auth)
    assert response.status_code == 409
    assert response.json()["detail"] == '"bottle" is already another name of your water bottle.'
    fake.duplicate = True  # the database's own unique check, if two people add at once
    raced = client.post("/api/items", json={"name": "hat"}, headers=auth)
    assert raced.status_code == 409
    away = client.post("/api/items", json={"name": "scarf", "home_landmark_id": str(uuid4())},
                       headers=auth)  # fmt: skip
    assert away.status_code == 422


def test_adding_a_room(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post(
        "/api/rooms", json={"name": "Living Room", "capture_allowed": True}, headers=auth
    )
    assert response.status_code == 201
    assert fake.added[0] == {"name": "living room", "spoken_name": "the living room",
                             "capture_allowed": True}  # fmt: skip
    assert client.post("/api/rooms", json={"name": "hall"}, headers=auth).status_code == 422
    fake.duplicate = True
    dup = client.post("/api/rooms", json={"name": "kitchen", "capture_allowed": True}, headers=auth)
    assert dup.status_code == 409


def test_adding_a_place(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post(
        "/api/landmarks",
        json={"room_id": str(KITCHEN.id), "name": "Table", "kind": "surface"},
        headers=auth,
    )
    assert response.status_code == 201
    assert response.json()["landmark"] == "the table"
    assert fake.added[0] == {"room_id": KITCHEN.id, "name": "table", "spoken_name": "the table",
                             "kind": "surface"}  # fmt: skip


def test_no_place_in_a_room_the_camera_never_records(auth: dict[str, str], fake: FakeDB) -> None:
    response = client.post(
        "/api/landmarks", json={"room_id": str(BATHROOM.id), "name": "shelf"}, headers=auth
    )
    assert response.status_code == 422
    assert "never records in the bathroom" in response.json()["detail"]
    assert fake.added == []


def test_landmark_form_rejects_reserved_words() -> None:
    with pytest.raises(ValidationError):
        LandmarkIn(room_id=uuid4(), name="none")
