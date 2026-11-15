"""GET /find with the database faked."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import names
from app.config import get_settings
from app.main import app
from app.memory import db
from app.memory.schema import Channel, FindResult
from app.speak import FALLBACK

client = TestClient(app)

QUERY_ID = "8a6f3c1e-7d2b-4e0a-9c55-3b1d2e4f6a70"
SIGHTING_ID = "5f0c6a52-2d7e-4c5b-9a59-0f3f1d1b8a11"


def seen_forty_minutes_ago() -> FindResult:
    last_seen = datetime.now(UTC) - timedelta(minutes=40)
    return FindResult.model_validate(
        {
            "state": "seen",
            "item": "glasses",
            "plural": True,
            "sighting_id": SIGHTING_ID,
            "room": "the kitchen",
            "landmark": "the kitchen counter",
            "relation": "on",
            "address": "kitchen > counter",
            "minutes_ago": 40,
            "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
            "timezone": "America/New_York",
            "confident": True,
            "photo": None,
            "previous": None,
            "usual": {"room": "your bedroom", "landmark": "the table beside your bed", "pct": None},
            "wearer_went_to": None,
            "possible_newer_glimpse": False,
            "query_id": QUERY_ID,
        }
    )


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Channel]]:
    seen: list[tuple[str, Channel]] = []

    async def fake_ask_item(query: str, channel: Channel) -> FindResult:
        seen.append((query, channel))
        return seen_forty_minutes_ago()

    monkeypatch.setattr(db, "ask_item", fake_ask_item)
    return seen


def test_find_answers_in_one_sentence(calls: list[tuple[str, Channel]]) -> None:
    response = client.get("/find", params={"item": "my specs"})

    assert response.status_code == 200
    body = response.json()
    assert body["sentence"] == (
        "I last saw your glasses on the kitchen counter about forty minutes ago."
    )
    assert body["result"]["state"] == "seen"
    assert body["result"]["query_id"] == QUERY_ID
    assert body["result"]["last_seen_at"].endswith("Z")
    assert calls == [("my specs", "web")]


def test_find_passes_channel(calls: list[tuple[str, Channel]]) -> None:
    client.get("/find", params={"item": "glasses", "channel": "facetime"})

    assert calls == [("glasses", "facetime")]


@pytest.mark.parametrize(
    "params",
    [{}, {"item": ""}, {"item": "glasses", "channel": "fax"}],
)
def test_find_rejects_bad_requests(calls: list[tuple[str, Channel]], params: Any) -> None:
    assert client.get("/find", params=params).status_code == 422
    assert calls == []


def test_find_logs_one_line(
    calls: list[tuple[str, Channel]], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.ask"):
        client.get("/find", params={"item": "my specs"})

    [record] = [r for r in caplog.records if r.name == "app.ask"]
    line = record.getMessage()
    assert "query='my specs'" in line
    assert "state=seen" in line
    assert f"sighting={SIGHTING_ID}" in line
    assert " ms=" in line


@pytest.mark.parametrize(
    "error",
    [TimeoutError(), RuntimeError("connection refused"), ValueError("bad answer")],
)
def test_find_falls_back_when_database_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, error: Exception
) -> None:
    async def failing_ask_item(query: str, channel: Channel) -> FindResult:
        raise error

    monkeypatch.setattr(db, "ask_item", failing_ask_item)

    with caplog.at_level(logging.INFO, logger="app.ask"):
        response = client.get("/find", params={"item": "my specs"})

    assert response.status_code == 200
    assert response.json() == {"sentence": FALLBACK, "result": None}
    [record] = [r for r in caplog.records if r.name == "app.ask"]
    assert record.levelno == logging.WARNING
    assert "state=error" in record.getMessage()
    assert type(error).__name__ in record.getMessage()


def test_find_asks_for_the_resolved_name(
    calls: list[tuple[str, Channel]],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def fake_resolve(spoken: str) -> str:
        return "glasses"

    monkeypatch.setattr(ask_module, "resolve", fake_resolve)

    with caplog.at_level(logging.INFO, logger="app.ask"):
        response = client.get("/find", params={"item": "my spectecles"})

    assert response.json()["result"]["state"] == "seen"
    assert calls == [("glasses", "web")]
    [record] = [r for r in caplog.records if r.name == "app.ask"]
    assert "query='my spectecles' resolved='glasses'" in record.getMessage()


def test_find_still_answers_when_typesense_is_down(
    calls: list[tuple[str, Channel]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TYPESENSE_HOST", "http://127.0.0.1:9")  # nothing listens on port 9
    monkeypatch.setenv("TYPESENSE_API_KEY", "ts_fake")
    monkeypatch.setattr(names, "_client", None)
    get_settings.cache_clear()
    try:
        response = client.get("/find", params={"item": "my specs"})
    finally:
        get_settings.cache_clear()

    assert response.json()["sentence"] == (
        "I last saw your glasses on the kitchen counter about forty minutes ago."
    )
    assert calls == [("my specs", "web")]
