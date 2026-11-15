"""The insights endpoints' work (docs/INSIGHTS.md): one call each from `app/main.py`.

Reads go through `app.memory.db`, rules are the pure modules `app.concerns` and `app.patterns`.
Every call logs one line with timings. Nothing here dials anyone: a concern waits for the family.
"""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, Field

from app import concerns as rules
from app.memory import db
from app.memory.schema import (
    Channel,
    Concern,
    ConcernAnswer,
    ConcernStatus,
    EventKind,
    LifeEvent,
    Urgency,
)
from app.patterns import Patterns, summarize
from app.perception.retry import describe

logger = logging.getLogger(__name__)

RECENT_CONCERNS = timedelta(hours=24)


class ConcernIn(BaseModel):
    """What the FaceTime agent's `report_concern` tool sends (`agent/concern.mjs`)."""

    kind: Literal["fall", "hurt", "help", "smoke", "scam", "lost_outside"]
    answer: ConcernAnswer | None = None
    channel: Channel = "facetime"


class ConcernOut(BaseModel):
    id: UUID
    urgency: Urgency
    room: str | None = None


class ConcernBoard(BaseModel):
    """What the family sees: the last day's concerns, open ones first, and a quiet-day note."""

    concerns: list[Concern]
    quiet_day: str | None = None


class HandleIn(BaseModel):
    status: Literal["on_my_way", "calling_911", "all_ok"]
    by: str = Field(min_length=1, max_length=60)


class EventIn(BaseModel):
    kind: EventKind
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    note: str | None = Field(default=None, max_length=200)


async def raise_concern(body: ConcernIn) -> ConcernOut:
    """Store a concern with its urgency and the last room the camera saw. Raises on a database
    failure; the agent swallows that and its spoken sentence does not change."""
    started = time.perf_counter()
    urgency = rules.urgency(body.kind, body.answer)
    try:
        room = await db.last_room()
    except Exception as exc:  # the room is a nice-to-have; the concern is not
        logger.warning("concern room=error error=%s", describe(exc))
        room = None
    concern_id = await db.add_concern(
        body.kind, body.answer, urgency, body.channel, room[0] if room else None
    )
    logger.info(
        "concern id=%s kind=%s answer=%s urgency=%s ms=%d",
        concern_id,
        body.kind,
        body.answer,
        urgency,
        _ms_since(started),
    )
    return ConcernOut(id=concern_id, urgency=urgency, room=room[1] if room else None)


async def concern_board(now: datetime | None = None) -> ConcernBoard:
    now = now or datetime.now(UTC)
    info = await db.home_info()
    local = now.astimezone(ZoneInfo(info.timezone))
    recent = await db.concerns(now - RECENT_CONCERNS)
    hours = await db.wear_hours(local.date() - timedelta(days=rules.QUIET_BASELINE_DAYS + 1))
    asked_today = await db.wearer_questions_since(
        local.replace(hour=0, minute=0, second=0, microsecond=0)
    )
    quiet = rules.quiet_day(hours, local.date(), local.hour, asked_today, info.person_name)
    ordered = sorted(recent, key=lambda c: (c.status != "open", -c.raised_at.timestamp()))
    return ConcernBoard(concerns=ordered, quiet_day=quiet)


async def handle_concern(concern_id: UUID, body: HandleIn) -> Concern | None:
    status: ConcernStatus = body.status
    concern = await db.handle_concern(concern_id, status, body.by)
    logger.info("concern id=%s handled=%s", concern_id, status if concern else "not_found")
    return concern


async def add_event(body: EventIn) -> LifeEvent:
    return await db.add_life_event(body.kind, body.starts_at, body.ends_at, body.note)


async def list_events(days: int) -> list[LifeEvent]:
    return await db.life_events(datetime.now(UTC) - timedelta(days=days))


async def patterns(days: int, now: datetime | None = None) -> Patterns:
    started = time.perf_counter()
    now = now or datetime.now(UTC)
    info = await db.home_info()
    tz = ZoneInfo(info.timezone)
    today = now.astimezone(tz).date()
    start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), tz)
    rows = await db.pattern_rows(start, start - timedelta(days=days))
    summary = summarize(rows, today, days)
    logger.info(
        "patterns days=%d status=%s changes=%d questions=%d ms=%d",
        days,
        summary.status,
        len(summary.changes),
        len(rows.questions),
        _ms_since(started),
    )
    return summary


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
