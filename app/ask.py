"""Answer one "where is it?" question: one database call, then speak().

Shared by `GET /find` and the voice tools, so the timeout, the fallback and the log line live in
one place. This never raises: any failure becomes the fallback sentence.
"""

import logging
import time
from datetime import UTC, datetime

from pydantic import BaseModel

from app.memory import db
from app.memory.schema import Channel, FindResult
from app.speak import FALLBACK, speak

logger = logging.getLogger(__name__)


class Answer(BaseModel):
    sentence: str
    result: FindResult | None = None


async def ask(query: str, channel: Channel) -> Answer:
    started = time.perf_counter()
    try:
        result = await db.ask_item(query, channel)
        sentence = speak(result, datetime.now(UTC))
    except Exception as exc:
        logger.warning(
            "question query=%r channel=%s state=error error=%s ms=%d",
            query,
            channel,
            _describe(exc),
            _ms_since(started),
        )
        return Answer(sentence=FALLBACK)
    logger.info(
        "question query=%r channel=%s state=%s sighting=%s query_id=%s ms=%d",
        query,
        channel,
        result.state,
        result.sighting_id,
        result.query_id,
        _ms_since(started),
    )
    return Answer(sentence=sentence, result=result)


def _describe(exc: Exception) -> str:
    detail = str(exc).replace("\n", " ")[:300]
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
