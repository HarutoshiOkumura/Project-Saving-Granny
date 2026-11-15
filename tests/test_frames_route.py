"""POST /frames: the token, the parsing, and the hand-off to the background worker."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import get_settings
from tests.perception_fakes import FRAMES

JPEG = (FRAMES / "close_keys_table_01.jpg").read_bytes()
STAMP = "2026-11-15T01:00:00.250Z"


@pytest.fixture
def handed_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[Any, ...]]]:
    calls: list[tuple[Any, ...]] = []

    async def fake_ingest(jpeg: bytes, device_id: str, captured_at: datetime) -> None:
        calls.append((jpeg, device_id, captured_at))

    monkeypatch.setattr(main, "ingest", fake_ingest)
    monkeypatch.setenv("APP_TOKEN", "test-token")
    get_settings.cache_clear()
    yield calls
    get_settings.cache_clear()


def post(token: str | None = "test-token", **overrides: Any) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = {"device_id": "lanyard", "captured_at": STAMP}
    files = {"frame": ("f.jpg", JPEG, "image/jpeg")}
    data.update({k: v for k, v in overrides.items() if k != "frame"})
    if "frame" in overrides:
        files = {"frame": ("f.jpg", overrides["frame"], "image/jpeg")}
    return TestClient(main.app).post("/frames", headers=headers, data=data, files=files)


def test_a_frame_is_accepted_and_handed_to_the_worker(handed_off: list[tuple[Any, ...]]) -> None:
    response = post()

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    ((jpeg, device, captured_at),) = handed_off
    assert jpeg == JPEG
    assert device == "lanyard"
    assert captured_at == datetime(2026, 11, 15, 1, 0, 0, 250000, tzinfo=UTC)


@pytest.mark.parametrize("token", [None, "wrong", "test-token-and-more"])
def test_a_bad_or_missing_token_is_refused(
    handed_off: list[tuple[Any, ...]], token: str | None
) -> None:
    response = post(token)

    assert response.status_code == 401
    assert handed_off == []


def test_without_app_token_on_the_server_every_frame_is_refused() -> None:
    get_settings.cache_clear()

    response = post()

    assert response.status_code == 503
    assert "APP_TOKEN" in response.json()["detail"]


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"frame": b"\x89PNG not a jpeg"}, 415),
        ({"captured_at": "2026-11-15T01:00:00"}, 422),  # no time zone
        ({"captured_at": "yesterday"}, 422),
        ({"device_id": "../etc"}, 422),
        ({"device_id": ""}, 422),
    ],
)
def test_bad_frames_are_refused_before_the_worker(
    handed_off: list[tuple[Any, ...]], overrides: dict[str, Any], code: int
) -> None:
    assert post(**overrides).status_code == code
    assert handed_off == []


def test_an_oversized_frame_is_refused(
    handed_off: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main, "MAX_FRAME_BYTES", 1000)

    assert post().status_code == 413
    assert handed_off == []
