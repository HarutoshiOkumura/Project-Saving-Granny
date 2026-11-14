"""db.ask_item with a fake Supabase client: parameter names, parsing and the timeout. No network."""

import asyncio
from types import SimpleNamespace
from typing import Any

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
