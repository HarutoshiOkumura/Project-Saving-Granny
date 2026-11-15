"""names.resolve and names.sync with Typesense faked at the HTTP layer. No network.

The hit shapes copy what Typesense 30.2 returned for the seeded items (step 09).
"""

import asyncio
import json
import time
from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

import httpx
import pytest

from app import names
from app.config import get_settings
from app.memory.schema import Item

HOST = "http://typesense.test:8108"
HOME_ID = "11111111-1111-1111-1111-111111111111"

GLASSES = {"name": "glasses", "aliases": ["specs", "spectacles", "reading glasses"]}
KEYS = {"name": "keys", "aliases": ["key", "house keys", "door keys"]}


def hit(doc: dict[str, Any], name: list[str], aliases: dict[str, list[str]]) -> dict[str, Any]:
    """A search hit whose name matched `name` and whose aliases matched as given."""
    return {
        "document": {"id": "x", "home_id": HOME_ID, **doc},
        "highlight": {
            "name": {"matched_tokens": name, "snippet": doc["name"]},
            "aliases": [
                {"matched_tokens": aliases.get(a, []), "snippet": a} for a in doc["aliases"]
            ],
        },
        "text_match_info": {"num_tokens_dropped": 0},
    }


Handler = Callable[[httpx.Request], Any]
AnswerWith = Callable[[Handler], list[httpx.Request]]


@pytest.fixture
def typesense(monkeypatch: pytest.MonkeyPatch) -> Iterator[AnswerWith]:
    """Point settings at a fake Typesense; call the result with a handler to answer requests."""
    monkeypatch.setenv("TYPESENSE_HOST", HOST)
    monkeypatch.setenv("TYPESENSE_API_KEY", "ts_fake")
    get_settings.cache_clear()

    def answer_with(handler: Handler) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        async def record(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            result = handler(request)
            return await result if asyncio.iscoroutine(result) else result

        def client(timeout: float = names.TIMEOUT_S) -> httpx.AsyncClient:
            return httpx.AsyncClient(
                base_url=HOST, transport=httpx.MockTransport(record), timeout=timeout
            )

        monkeypatch.setattr(names, "_client", client())
        monkeypatch.setattr(names, "_new_client", client)
        return seen

    yield answer_with
    get_settings.cache_clear()


def hits(*found: dict[str, Any]) -> Handler:
    return lambda request: httpx.Response(200, json={"found": len(found), "hits": list(found)})


def resolve(spoken: str) -> str:
    return asyncio.run(names.resolve(spoken))


def test_unconfigured_returns_the_words_unchanged() -> None:
    assert get_settings().typesense_host is None
    assert resolve("my spectecles") == "my spectecles"


def test_typo_resolves_to_the_item_name(typesense: AnswerWith) -> None:
    seen = typesense(hits(hit(GLASSES, [], {"spectacles": ["spectacles"]})))

    assert resolve("where are my spectecles") == "glasses"

    params = seen[0].url.params
    assert seen[0].url.path == "/collections/items/documents/search"
    assert params["q"] == "spectecles"  # filler words are not sent
    assert params["query_by"] == "name,aliases"
    assert params["filter_by"] == f"home_id:=`{HOME_ID}`"
    assert params["prefix"] == "false"


def test_extra_words_resolve_when_a_whole_alias_matched(typesense: AnswerWith) -> None:
    typesense(hits(hit(GLASSES, ["glasses"], {"reading glasses": ["reading", "glasses"]})))

    assert resolve("my black reading glasses") == "glasses"


def test_part_of_an_alias_is_not_enough(typesense: AnswerWith) -> None:
    typesense(hits(hit(KEYS, [], {"house keys": ["house"]})))

    assert resolve("house phone") == "house phone"


def test_a_later_hit_that_fully_matched_wins(typesense: AnswerWith) -> None:
    typesense(
        hits(
            hit(KEYS, [], {"house keys": ["house"]}),
            hit(GLASSES, [], {"specs": ["specs"]}),
        )
    )

    assert resolve("house specs") == "glasses"


def test_no_hit_returns_the_words_unchanged(typesense: AnswerWith) -> None:
    typesense(hits())

    assert resolve("my dentures") == "my dentures"


def test_only_filler_words_skip_typesense(typesense: AnswerWith) -> None:
    seen = typesense(hits(hit(GLASSES, ["glasses"], {})))

    assert resolve("where is it") == "where is it"
    assert seen == []


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(404, json={"message": "Not found."}),
        lambda request: httpx.Response(503, json={"message": "Not Ready or Lagging"}),
        lambda request: httpx.Response(200, text="not json"),
        lambda request: httpx.Response(200, json={"hits": [{"document": {}}]}),
    ],
    ids=["collection-missing", "server-error", "not-json", "bad-shape"],
)
def test_bad_answers_return_the_words_unchanged(typesense: AnswerWith, handler: Handler) -> None:
    typesense(handler)

    assert resolve("spectecles") == "spectecles"


def test_typesense_down_returns_the_words_unchanged(typesense: AnswerWith) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    typesense(refuse)

    assert resolve("spectecles") == "spectecles"


def test_slow_typesense_gives_up_at_the_timeout(typesense: AnswerWith) -> None:
    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(2)
        return httpx.Response(200, json={"hits": []})

    typesense(slow)
    started = time.perf_counter()

    assert resolve("spectecles") == "spectecles"
    assert time.perf_counter() - started < names.TIMEOUT_S + 0.3


ITEMS = [
    Item(id=UUID(int=1), name="glasses", aliases=["specs"]),
    Item(id=UUID(int=2), name="keys", aliases=[]),
]


def test_sync_rebuilds_the_collection(typesense: AnswerWith) -> None:
    def server(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/import"):
            lines = request.content.decode().splitlines()
            return httpx.Response(200, text="\n".join('{"success":true}' for _ in lines))
        return httpx.Response(200, json={})

    seen = typesense(server)

    assert asyncio.run(names.sync(ITEMS)) == 2

    assert [(r.method, r.url.path) for r in seen] == [
        ("DELETE", "/collections/items"),
        ("POST", "/collections"),
        ("POST", "/collections/items/documents/import"),
    ]
    assert json.loads(seen[1].content) == names.SCHEMA
    docs = [json.loads(line) for line in seen[2].content.decode().splitlines()]
    assert docs[0] == {
        "id": str(UUID(int=1)),
        "name": "glasses",
        "aliases": ["specs"],
        "home_id": HOME_ID,
    }


def test_sync_works_on_a_fresh_server(typesense: AnswerWith) -> None:
    def server(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE":
            return httpx.Response(404, json={"message": "Not found."})
        if request.url.path.endswith("/import"):
            return httpx.Response(200, text='{"success":true}\n{"success":true}')
        return httpx.Response(201, json={})

    typesense(server)

    assert asyncio.run(names.sync(ITEMS)) == 2


def test_sync_raises_when_an_item_is_refused(typesense: AnswerWith) -> None:
    def server(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/import"):
            return httpx.Response(200, text='{"success":true}\n{"success":false,"error":"bad"}')
        return httpx.Response(200, json={})

    typesense(server)

    with pytest.raises(RuntimeError, match="refused 1 of 2"):
        asyncio.run(names.sync(ITEMS))
