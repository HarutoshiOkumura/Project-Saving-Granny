"""GET /describe and GET /moments/{sighting_id}/photo with app/moments.py faked. No network."""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app import moments
from app.config import get_settings
from app.main import app
from app.moments import Candidate, Described
from app.photo import CardPhoto

client = TestClient(app)  # not entered as a context manager: the refresher is not started

SIGHTING = UUID(int=7)
TOKEN = {"Authorization": "Bearer app_token_fake"}
JPEG = b"\xff\xd8\xff a card"


@pytest.fixture
def token(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("APP_TOKEN", "app_token_fake")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def cards(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """Fake `moments.card`: a ringed photo for SIGHTING, nothing for any other stay."""
    calls: list[tuple[Any, ...]] = []

    async def card(sighting_id: UUID, width: int, height: int, safe: Any) -> CardPhoto | None:
        calls.append((sighting_id, width, height, safe))
        return CardPhoto(JPEG, (640, 294, 95)) if sighting_id == SIGHTING else None

    monkeypatch.setattr(moments, "card", card)
    return calls


def test_describe_passes_the_words_and_the_channel_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def describe(description: str, channel: str) -> Described:
        assert (description, channel) == ("the silver one I wear on my wrist", "facetime")
        return Described(
            sentence="I last saw your watch on the table just now.",
            item="watch",
            candidates=[Candidate(item="watch", sighting_id=SIGHTING, distance=0.342)],
        )

    monkeypatch.setattr(moments, "describe", describe)

    response = client.get(
        "/describe", params={"q": "the silver one I wear on my wrist", "channel": "facetime"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sentence"] == "I last saw your watch on the table just now."
    assert body["item"] == "watch" and body["result"] is None
    assert body["candidates"][0]["sighting_id"] == str(SIGHTING)


def test_describe_needs_words() -> None:
    assert client.get("/describe").status_code == 422
    assert client.get("/describe", params={"q": ""}).status_code == 422


def test_a_photo_needs_the_app_token(token: None, cards: list[tuple[Any, ...]]) -> None:
    path = f"/moments/{SIGHTING}/photo"

    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert cards == []


def test_photos_are_refused_while_no_app_token_is_set(cards: list[tuple[Any, ...]]) -> None:
    assert get_settings().app_token is None

    assert client.get(f"/moments/{SIGHTING}/photo", headers=TOKEN).status_code == 503


def test_the_photo_comes_sized_for_the_card_with_the_ring_place(
    token: None, cards: list[tuple[Any, ...]]
) -> None:
    response = client.get(
        f"/moments/{SIGHTING}/photo",
        params={"w": 1280, "h": 720, "safe": "100,0,1180,590"},
        headers=TOKEN,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-item-circle"] == "640,294,95"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content == JPEG
    assert cards == [(SIGHTING, 1280, 720, (100, 0, 1180, 590))]


def test_without_safe_the_photo_may_fill_the_whole_picture(
    token: None, cards: list[tuple[Any, ...]]
) -> None:
    assert client.get(f"/moments/{SIGHTING}/photo", headers=TOKEN).status_code == 200
    assert (
        client.get(
            f"/moments/{SIGHTING}/photo", params={"w": 640, "h": 360}, headers=TOKEN
        ).status_code
        == 200
    )  # as the room page asks

    assert cards == [
        (SIGHTING, 1280, 720, (0, 0, 1280, 720)),
        (SIGHTING, 640, 360, (0, 0, 640, 360)),
    ]


def test_no_ring_header_when_the_picture_has_no_ring(
    token: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def card(*_: Any) -> CardPhoto:
        return CardPhoto(JPEG, None)

    monkeypatch.setattr(moments, "card", card)

    response = client.get(f"/moments/{SIGHTING}/photo", headers=TOKEN)

    assert response.status_code == 200 and "x-item-circle" not in response.headers


def test_a_stay_without_a_photo_is_404(token: None, cards: list[tuple[Any, ...]]) -> None:
    assert client.get(f"/moments/{UUID(int=8)}/photo", headers=TOKEN).status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"safe": "1,2,3"},  # not four numbers
        {"safe": "900,130,220,450"},  # right is left of left
        {"safe": "220,130,1060,900"},  # below the card
        {"w": 20000},
        {"h": 10},
    ],
)
def test_bad_sizes_are_refused(
    token: None, cards: list[tuple[Any, ...]], params: dict[str, Any]
) -> None:
    response = client.get(f"/moments/{SIGHTING}/photo", params=params, headers=TOKEN)

    assert response.status_code == 422 and cards == []


def test_a_sighting_id_must_be_a_uuid(token: None) -> None:
    assert client.get("/moments/not-a-uuid/photo", headers=TOKEN).status_code == 422
