"""GET /room and its data routes, with the database and the snapshot faked. No network."""

import json
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import room
from app.ask import Known
from app.config import get_settings
from app.main import app
from app.memory import db
from app.memory.schema import FindResult, Pin
from splat import spz

client = TestClient(app)  # not entered as a context manager: the refresher is not started

TOKEN = {"Authorization": "Bearer app_token_fake"}
TABLE, CHAIR = UUID(int=1), UUID(int=2)
SIGHTING = UUID(int=9)


@pytest.fixture
def scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A tiny room on disk: a table top at y = -0.3 in front of the start camera."""
    rng = np.random.default_rng(0)
    table = np.column_stack(
        [rng.uniform(-0.4, 0.4, 3000), np.full(3000, -0.3), rng.uniform(-2.4, -1.6, 3000)]
    )
    count = len(table)
    identity = np.tile([0.0, 0.0, 0.0, 1.0], (count, 1))
    data = spz.encode(
        table, np.full((count, 3), 0.02), identity, np.ones(count), np.zeros((count, 3))
    )
    (tmp_path / "preview.spz").write_bytes(data)
    (tmp_path / "full.spz").write_bytes(data)
    view = {"eye": [0, 0, 0], "target": [0, -0.3, -2]}
    (tmp_path / "scene.json").write_text(
        json.dumps(
            {
                "built_at": "2026-11-15T07:00:00Z",
                "source": "scan.mov",
                "gaussians": {"preview": count, "full": count, "model": count},
                "start": view,
                "bounds": {"min": [-0.4, -0.3, -2.4], "max": [0.4, -0.3, -1.6]},
                "cameras": [{"view": view}],
            }
        )
    )
    monkeypatch.setenv("APP_TOKEN", "app_token_fake")
    monkeypatch.setenv("ROOM_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def home(monkeypatch: pytest.MonkeyPatch) -> dict[UUID, tuple[float, float, float] | None]:
    """Fake landmarks (the table and the chair), their pins, and one item on the table."""
    pins: dict[UUID, tuple[float, float, float] | None] = {TABLE: None, CHAIR: None}

    async def list_pins() -> list[Pin]:
        names = {TABLE: ("room > table", "the table"), CHAIR: ("room > chair", "the chair")}
        return [
            Pin(
                landmark_id=landmark,
                address=names[landmark][0],
                spoken=names[landmark][1],
                **dict(zip("xyz", spot or (None, None, None), strict=True)),
            )
            for landmark, spot in pins.items()
        ]

    async def set_pin(landmark: UUID, position: tuple[float, float, float] | None) -> None:
        pins[landmark] = position

    async def snapshot() -> list[Known]:
        seen = FindResult(
            state="seen", item="glasses", address="room > table", sighting_id=SIGHTING
        )
        return [
            Known(item="glasses", aliases=[], sentence="On the table.", result=seen),
            Known(
                item="keys",
                aliases=[],
                sentence="In your hand.",
                result=FindResult(state="carried"),
            ),
            Known(item="bag", aliases=[], sentence="I'm not sure."),
        ]

    monkeypatch.setattr(db, "list_pins", list_pins)
    monkeypatch.setattr(db, "set_pin", set_pin)
    monkeypatch.setattr(room, "snapshot", snapshot)
    return pins


def test_the_page_is_served_without_a_token() -> None:
    page = client.get("/room")
    assert page.status_code == 200 and "Your room" in page.text
    assert "sb_secret" not in page.text and "SUPABASE" not in page.text


def test_room_data_needs_the_token(scan: Path, home: dict) -> None:
    assert client.get("/room/scene").status_code == 401
    assert client.get("/room/splat").status_code == 401
    assert client.put("/room/pins", json={}).status_code == 401
    assert client.delete("/room/pins", params={"address": "room > table"}).status_code == 401


def test_scene_joins_the_scan_with_the_memory(scan: Path, home: dict) -> None:
    body = client.get("/room/scene", headers=TOKEN).json()
    assert body["levels"] == ["preview", "full"] and body["source"] == "scan.mov"
    assert body["start"] == {"eye": [0, 0, 0], "target": [0, -0.3, -2]}
    assert [p["address"] for p in body["pins"]] == ["room > table", "room > chair"]
    assert all(p["position"] is None for p in body["pins"])
    things = {t["item"]: t for t in body["things"]}
    assert things["glasses"]["address"] == "room > table"  # a place the view can point at
    assert things["glasses"]["sighting_id"] == str(SIGHTING)
    assert things["keys"]["address"] is None  # carried: nowhere to point
    assert things["bag"]["state"] is None and things["bag"]["sentence"] == "I'm not sure."


def test_scene_version_changes_when_a_new_file_lands(scan: Path, home: dict) -> None:
    first = client.get("/room/scene", headers=TOKEN).json()["version"]
    (scan / "full.spz").unlink()
    second = client.get("/room/scene", headers=TOKEN).json()
    assert second["levels"] == ["preview"] and second["version"] != first


def test_no_scan_is_a_404(tmp_path: Path, home: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TOKEN", "app_token_fake")
    monkeypatch.setenv("ROOM_DIR", str(tmp_path / "nothing"))
    get_settings.cache_clear()
    try:
        assert client.get("/room/scene", headers=TOKEN).status_code == 404
        assert client.get("/room/splat", headers=TOKEN).status_code == 404
    finally:
        get_settings.cache_clear()


def test_splat_is_served_privately(scan: Path, home: dict) -> None:
    response = client.get("/room/splat", params={"level": "preview"}, headers=TOKEN)
    assert response.status_code == 200 and spz.count_of(response.content) == 3000
    assert response.headers["cache-control"] == "private, no-store"
    assert client.get("/room/splat", params={"level": "huge"}, headers=TOKEN).status_code == 422


def test_a_tap_places_a_pin_on_the_surface_it_hits(scan: Path, home: dict) -> None:
    tap = {"address": "room > table", "origin": [0, 0, 0], "direction": [0, -0.3, -2]}
    placed = client.put("/room/pins", json=tap, headers=TOKEN)
    assert placed.status_code == 200
    x, y, z = placed.json()["position"]
    assert y == pytest.approx(-0.3, abs=0.02) and abs(x) < 0.1 and -2.2 < z < -1.8
    assert home[TABLE] == (x, y, z) and home[CHAIR] is None
    body = client.get("/room/scene", headers=TOKEN).json()
    assert body["pins"][0]["position"] == [x, y, z]


def test_a_tap_on_nothing_or_an_unknown_place_stores_nothing(scan: Path, home: dict) -> None:
    sky = {"address": "room > table", "origin": [0, 0, 0], "direction": [0, 1, 0]}
    assert client.put("/room/pins", json=sky, headers=TOKEN).status_code == 422
    still = {"address": "room > table", "origin": [0, 0, 0], "direction": [0, 0, 0]}
    assert client.put("/room/pins", json=still, headers=TOKEN).status_code == 422
    attic = {"address": "attic > box", "origin": [0, 0, 0], "direction": [0, -0.3, -2]}
    assert client.put("/room/pins", json=attic, headers=TOKEN).status_code == 404
    assert home == {TABLE: None, CHAIR: None}


def test_a_pin_can_be_cleared(scan: Path, home: dict) -> None:
    home[CHAIR] = (1.0, 2.0, 3.0)
    gone = client.delete("/room/pins", params={"address": "room > chair"}, headers=TOKEN)
    assert gone.status_code == 204 and home[CHAIR] is None
    missing = client.delete("/room/pins", params={"address": "attic > box"}, headers=TOKEN)
    assert missing.status_code == 404


def test_the_room_still_opens_when_the_database_is_down(
    scan: Path, home: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def down() -> list[Pin]:
        raise TimeoutError

    monkeypatch.setattr(db, "list_pins", down)
    body = client.get("/room/scene", headers=TOKEN).json()
    assert body["pins"] == [] and body["levels"] == ["preview", "full"]
