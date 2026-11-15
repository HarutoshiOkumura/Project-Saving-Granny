"""Answer one "where is it?" question: resolve the words to an item name (Typesense, optional,
at most 300 ms), one database call, then speak().

Shared by `GET /find` and the voice tools, so the timeout, the fallback and the log line live in
one place. This never raises: any failure becomes the fallback sentence.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime

from pydantic import BaseModel

from app.memory import db
from app.memory.schema import Channel, FindResult, Item
from app.names import resolve
from app.speak import FALLBACK, speak

logger = logging.getLogger(__name__)


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
    color: str | None = None
    looks_like: str | None = None  # colour and description, so the agent can tell look-alikes apart
    sentence: str
    result: FindResult | None = None


async def snapshot() -> list[Known]:
    """Every item's current answer, logging no questions. The FaceTime agent loads this when a call
    starts, so it can answer in one model turn instead of a tool round trip. Never raises: on a
    database failure it returns [] and the agent falls back to asking per question."""
    started = time.perf_counter()
    try:
        names = await db.list_items()
        results = await asyncio.gather(
            *(db.find_item(n.name) for n in names), return_exceptions=True
        )
    except Exception as exc:
        logger.warning("snapshot error=%s ms=%d", _describe(exc), _ms_since(started))
        return []
    now = datetime.now(UTC)
    known = []
    for name, result in zip(names, results, strict=True):
        if isinstance(result, BaseException):
            known.append(
                Known(
                    item=name.name,
                    aliases=name.aliases,
                    color=name.color,
                    looks_like=_looks(name),
                    sentence=FALLBACK,
                )
            )
        else:
            known.append(
                Known(
                    item=name.name,
                    aliases=name.aliases,
                    color=name.color,
                    looks_like=_looks(name),
                    sentence=speak(result, now),
                    result=result,
                )
            )
    logger.info("snapshot items=%d ms=%d", len(known), _ms_since(started))
    return known


def _looks(item: Item) -> str | None:
    """ "blue, steel bottle with a dent": colour and description, or None."""
    return ", ".join(part for part in (item.color, item.description) if part) or None


def _describe(exc: Exception) -> str:
    detail = str(exc).replace("\n", " ")[:300]
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
