"""Turn the caller's words into an enrolled item name with Typesense (step 09, optional).

Keyword search only, no embeddings: typo tolerance ("spectecles"), word stems ("spectacle",
"bags") and dropping extra words ("black reading glasses"). A hit counts only when every word of
the item's name, or of one alias, matched, so "house phone" does not become the house keys.

Postgres stays the source of truth: the `items` collection is a copy that
`scripts/sync_typesense.py` rebuilds. `resolve` returns the words unchanged when Typesense is not
set up, slow, down or unsure, so `find_item` still runs on what was said. To turn this off, leave
TYPESENSE_HOST empty.
"""

import asyncio
import json
import logging
import re

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings
from app.memory.schema import Item
from app.speak import FILLER_WORDS

logger = logging.getLogger(__name__)

COLLECTION = "items"
TIMEOUT_S = 0.3
SYNC_TIMEOUT_S = 10.0

SCHEMA = {
    "name": COLLECTION,
    "fields": [
        {"name": "name", "type": "string", "stem": True},
        {"name": "aliases", "type": "string[]", "stem": True},
        {"name": "home_id", "type": "string"},
    ],
}

# Tuned on spoken phrases against the seeded items on Typesense 30.2 (docs/STATUS.md, step 09).
# Typo lengths count the word's stem: "glases" -> "glase" (5 letters) may have one typo, while
# "nurse" -> "nurs" (4) may not, so "nurse" does not turn into "purse".
SEARCH_PARAMS = {
    "query_by": "name,aliases",
    "prefix": "false",  # speech has no half-typed words
    "num_typos": "2",
    "min_len_1typo": "5",
    "min_len_2typo": "8",
    "typo_tokens_threshold": "1",
    "drop_tokens_threshold": "1",
    "prioritize_exact_match": "true",
    "per_page": "5",
}


class _Matched(BaseModel):
    matched_tokens: list[str] = []


class _Highlight(BaseModel):
    name: _Matched | None = None
    aliases: list[_Matched] = []  # one per alias, in the document's order


class _Document(BaseModel):
    name: str
    aliases: list[str] = []


class _Hit(BaseModel):
    document: _Document
    highlight: _Highlight = Field(default_factory=_Highlight)


class _SearchResult(BaseModel):
    hits: list[_Hit] = []


_client: httpx.AsyncClient | None = None


async def resolve(spoken: str) -> str:
    """The enrolled item name `spoken` points to, or `spoken` unchanged. Never raises."""
    words = [w for w in re.findall(r"[a-z0-9']+", spoken.lower()) if w not in FILLER_WORDS]
    settings = get_settings()
    if not words or not settings.typesense_host or settings.typesense_api_key is None:
        return spoken
    params = {**SEARCH_PARAMS, "q": " ".join(words), "filter_by": f"home_id:=`{settings.home_id}`"}
    try:
        async with asyncio.timeout(TIMEOUT_S):
            response = await _get_client().get(
                f"/collections/{COLLECTION}/documents/search", params=params
            )
        response.raise_for_status()
        hits = _SearchResult.model_validate(response.json()).hits
    except Exception as exc:
        logger.warning("resolve heard=%r error=%s %s", spoken, type(exc).__name__, str(exc)[:200])
        return spoken
    return next((hit.document.name for hit in hits if _whole_name_matched(hit)), spoken)


async def sync(items: list[Item]) -> int:
    """Rebuild the Typesense copy from `items`. Safe to run repeatedly. Returns how many."""
    home_id = str(get_settings().home_id)
    docs = [
        {"id": str(i.id), "name": i.name, "aliases": i.aliases, "home_id": home_id} for i in items
    ]
    async with _new_client(SYNC_TIMEOUT_S) as client:
        dropped = await client.delete(f"/collections/{COLLECTION}")
        if dropped.status_code != httpx.codes.NOT_FOUND:
            dropped.raise_for_status()
        (await client.post("/collections", json=SCHEMA)).raise_for_status()
        if not docs:
            return 0
        imported = await client.post(
            f"/collections/{COLLECTION}/documents/import",
            params={"action": "create"},
            content="\n".join(json.dumps(doc) for doc in docs),
        )
        imported.raise_for_status()
    failed = [line for line in imported.text.splitlines() if not json.loads(line).get("success")]
    if failed:
        raise RuntimeError(f"Typesense refused {len(failed)} of {len(docs)} items: {failed[:3]}")
    return len(docs)


def _whole_name_matched(hit: _Hit) -> bool:
    """True when every word of the name, or of one alias, matched (typos and stems count)."""
    phrases = [(hit.document.name, hit.highlight.name)]
    phrases += zip(hit.document.aliases, hit.highlight.aliases, strict=False)
    for phrase, matched in phrases:
        needed = _tokens(phrase)
        if matched and needed and needed <= _tokens(" ".join(matched.matched_tokens)):
            return True
    return False


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _get_client() -> httpx.AsyncClient:
    """One client per process, so the connection to Typesense is reused between questions."""
    global _client
    if _client is None:
        _client = _new_client(TIMEOUT_S)
    return _client


def _new_client(timeout: float) -> httpx.AsyncClient:
    settings = get_settings()
    if not settings.typesense_host or settings.typesense_api_key is None:
        raise RuntimeError("Set TYPESENSE_HOST and TYPESENSE_API_KEY in .env")
    return httpx.AsyncClient(
        base_url=settings.typesense_host,
        headers={"X-TYPESENSE-API-KEY": settings.typesense_api_key.get_secret_value()},
        timeout=timeout,
    )
