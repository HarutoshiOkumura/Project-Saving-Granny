"""Answer one "where is it?" question: resolve the words to an item name (Typesense, optional,
at most 300 ms), one database call, then speak().

Shared by `GET /find` and the voice tools, so the timeout, the fallback and the log line live in
one place. This never raises: any failure becomes the fallback sentence.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from app.look import WhereToLook, where_to_look
from app.memory import db
from app.memory.schema import Channel, FindResult, Item
from app.names import resolve
from app.speak import FALLBACK, speak

logger = logging.getLogger(__name__)

GLIMPSE_WINDOW = timedelta(hours=24)  # one-frame stays older than this are not worth a look


class Answer(BaseModel):
    sentence: str
    result: FindResult | None = None


async def ask(query: str, channel: Channel) -> Answer:
    started = time.perf_counter()
    name = query
    try:
        name = await resolve(query)
        result = await db.ask_item(name, channel)
        sentence = speak(result, datetime.now(UTC))
    except Exception as exc:
        logger.warning(
            "question query=%r resolved=%r channel=%s state=error error=%s ms=%d",
            query,
            name,
            channel,
            _describe(exc),
            _ms_since(started),
        )
        return Answer(sentence=FALLBACK)
    logger.info(
        "question query=%r resolved=%r channel=%s state=%s sighting=%s query_id=%s ms=%d",
        query,
        name,
        channel,
        result.state,
        result.sighting_id,
        result.query_id,
        _ms_since(started),
    )
    return Answer(sentence=sentence, result=result)


class Known(BaseModel):
    """What Save It can say about one item right now (one entry of `GET /snapshot`)."""

    item: str
    aliases: list[str]
    kind: str | None = None  # items of one kind are look-alikes: the agent asks which one
    color: str | None = None
    looks_like: str | None = None  # colour and description, so the agent can tell look-alikes apart
    sentence: str
    result: FindResult | None = None
    where_to_look: WhereToLook | None = None  # places ranked with chances (D33)
    photo_url: str | None = None  # the last-seen crop, a link that works for an hour


async def snapshot(*, with_photos: bool = False) -> list[Known]:
    """Every item's current answer and where to look, logging no questions. The FaceTime agent
    loads this when a call starts, so it can answer in one model turn instead of a tool round
    trip. Never raises: on a database failure it returns [] and the agent falls back to asking per
    question; when only the habits, the glimpses or the photo links fail, those fields are None.
    `with_photos` adds signed links to the last-seen crops (only for a caller holding the token)."""
    started = time.perf_counter()
    now = datetime.now(UTC)
    try:
        names = await db.list_items()
        evidence_and_results = await asyncio.gather(
            db.look_evidence([n.id for n in names], now - GLIMPSE_WINDOW),
            *(db.find_item(n.name) for n in names),
            return_exceptions=True,
        )
    except Exception as exc:
        logger.warning("snapshot error=%s ms=%d", _describe(exc), _ms_since(started))
        return []
    evidence, *results = evidence_and_results
    if isinstance(evidence, BaseException):
        logger.warning("snapshot look=error error=%s", _describe(evidence))
        evidence = None
    found = [r if isinstance(r, FindResult) else None for r in results]
    links = await _photo_links(found) if with_photos else {}
    known = [
        Known(
            item=name.name,
            aliases=name.aliases,
            kind=name.category,
            color=name.color,
            looks_like=_looks(name),
            sentence=speak(result, now) if result else FALLBACK,
            result=result,
            where_to_look=where_to_look(name, result, evidence, now) if evidence else None,
            photo_url=links.get(result.photo) if result and result.photo else None,
        )
        for name, result in zip(names, found, strict=True)
    ]
    logger.info(
        "snapshot items=%d look=%s photos=%d ms=%d",
        len(known),
        "ok" if evidence else "none",
        len(links),
        _ms_since(started),
    )
    return known


async def _photo_links(results: list[FindResult | None]) -> dict[str, str]:
    """Signed links for every answer's crop, by storage path. {} on any failure: the snapshot
    is still worth having without photos."""
    paths = [r.photo for r in results if r and r.photo]
    if not paths:
        return {}
    try:
        return await db.sign_photos(paths)
    except Exception as exc:
        logger.warning("snapshot photos=error error=%s", _describe(exc))
        return {}


def _looks(item: Item) -> str | None:
    """ "blue, steel bottle with a dent": colour and description, or None."""
    return ", ".join(part for part in (item.color, item.description) if part) or None


def _describe(exc: Exception) -> str:
    detail = str(exc).replace("\n", " ")[:300]
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
