"""Guide the wearer to an item one step at a time: where they are now against where the item
was last seen.

"Where they are now" is the newest frame the write path has already stored (its room and the
landmarks in view), so this is read path: no vision model, three database reads at most (one of
them cached) and one pure function. `GET /guide` is polled by the FaceTime agent while the
caller walks, so it uses `find_item` and logs no question. It never raises: any failure becomes
the `unsure` step, and the agent keeps polling.

Wording follows `.claude/rules/voice.md`: one short sentence, spoken names only, "your glasses",
and "I think" wherever a sentence says where the item is and the memory is not sure. Sentences
that only give a direction ("walk to the kitchen") say nothing about the item and are not hedged.
"""

import asyncio
import logging
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.memory import db
from app.memory.schema import FindResult, HomeLayout, LayoutLandmark, LayoutRoom, Observation
from app.names import resolve
from app.speak import FALLBACK, RELATION_WORDS, UNKNOWN_RELATION, speak

logger = logging.getLogger(__name__)

# A camera held still sends one look every 10 s and perception takes up to 7 s more, so a view
# this old still says where the wearer is. Older than this, the camera has stopped.
VIEW_FRESH_S = 30.0
HELD_S = 60.0  # "in your hand now" only while the in-hand stay is this fresh
# The worker stamps a frame's observation and its sightings with the same capture time, so an
# item whose stay ends at the newest frame's time was in that frame.
SAME_FRAME = timedelta(milliseconds=1)
LAYOUT_TTL_S = 60.0

Step = Literal[
    "unsure",  # something failed; nothing to say, keep polling
    "none",  # nowhere to guide to: `sentence` is the plain answer
    "no_view",  # the place is known but not where the wearer is
    "other_floor",  # the place is on another floor: say so, never send them to the stairs
    "go_to_room",
    "look_for",  # in the right room; the landmark is not in view yet
    "in_view",  # the landmark is in front of them
    "item_in_view",  # the item itself was in the newest frame
    "in_hand",
]
PROGRESS: dict[str, int] = {
    "unsure": 0,
    "none": 0,
    "no_view": 0,
    "other_floor": 1,
    "go_to_room": 1,
    "look_for": 2,
    "in_view": 3,
    "item_in_view": 4,
    "in_hand": 5,
}


class Guidance(BaseModel):
    """One step of `GET /guide`."""

    step: Step
    key: str  # changes when there is something new to say
    progress: int  # 0 to 5, how close they are; the agent speaks up when it rises
    done: bool  # nothing more to guide: stop polling
    sentence: str
    item: str | None = None
    room: str | None = None  # where the item is, in the spoken names `find_item` gives
    landmark: str | None = None
    wearer_room: str | None = None  # where the newest fresh frame put the wearer
    view_age_s: int | None = None


UNSURE = Guidance(step="unsure", key="unsure", progress=0, done=False, sentence=FALLBACK)

_layout: tuple[float, HomeLayout] | None = None


async def guide_to(query: str) -> Guidance:
    """The next step toward `query`, for `GET /guide`. Never raises."""
    started = time.perf_counter()
    name = query
    try:
        name = await resolve(query)
        find, view, layout = await asyncio.gather(
            db.find_item(name), db.latest_view(), _home_layout(), return_exceptions=True
        )
        if isinstance(find, BaseException):
            raise find
        if isinstance(view, BaseException) or isinstance(layout, BaseException):
            # The item's place is still known: guide without the wearer's position.
            failed = view if isinstance(view, BaseException) else layout
            logger.warning("guide query=%r view unavailable: %s", query, _describe(failed))
            view, layout = None, HomeLayout()
        guidance = guide(find, view, layout, datetime.now(UTC))
    except Exception as exc:
        logger.warning(
            "guide query=%r resolved=%r step=unsure error=%s ms=%d",
            query,
            name,
            _describe(exc),
            _ms_since(started),
        )
        return UNSURE
    logger.info(
        "guide query=%r resolved=%r state=%s step=%s key=%r view_age_s=%s ms=%d",
        query,
        name,
        find.state,
        guidance.step,
        guidance.key,
        guidance.view_age_s,
        _ms_since(started),
    )
    return guidance


async def _home_layout() -> HomeLayout:
    global _layout
    now = time.monotonic()
    if _layout is None or now - _layout[0] >= LAYOUT_TTL_S:
        _layout = (now, await db.home_layout())
    return _layout[1]


def guide(
    find: FindResult, view: Observation | None, layout: HomeLayout, now: datetime
) -> Guidance:
    """One step toward the item. Pure: no I/O, no clock; `now` must be timezone-aware."""
    age = None if view is None else max(0.0, (now - view.captured_at).total_seconds())
    fresh = view if view is not None and age is not None and age <= VIEW_FRESH_S else None
    here = _room(layout, fresh.room_id) if fresh else None

    def step(name: Step, detail: str | None, sentence: str, *, done: bool = False) -> Guidance:
        return Guidance(
            step=name,
            key=f"{name}:{detail}" if detail else name,
            progress=PROGRESS[name],
            done=done,
            sentence=sentence[:1].upper() + sentence[1:],
            item=find.item,
            room=find.room,
            landmark=find.landmark,
            wearer_room=here.spoken if here else None,
            view_age_s=None if age is None else round(age),
        )

    if find.state == "carried" and find.item and _within(find.last_seen_at, now, HELD_S):
        return step(
            "in_hand",
            None,
            _think(find, f"you have your {find.item} in your hand now."),
            done=True,
        )
    if find.state != "seen" or not find.item or not (find.room or find.landmark):
        return step("none", find.state, speak(find, now), done=True)

    item = f"your {find.item}"
    place = find.address or find.room
    on = RELATION_WORDS.get(find.relation or "", UNKNOWN_RELATION)
    be = "are" if find.plural else "is"

    if fresh and find.last_seen_at and abs(find.last_seen_at - fresh.captured_at) <= SAME_FRAME:
        where = f" {on} {find.landmark}" if find.landmark else ""
        return step(
            "item_in_view", place, _think(find, f"I can see {item}{where} in front of you.")
        )

    target = _landmark(layout, find.address)
    target_room = _room(layout, target.room_id) if target else _room_named(layout, find.room)

    if fresh is None or here is None or target_room is None:
        where = " ".join(
            part
            for part in (
                f"{on} {find.landmark}" if find.landmark else None,
                f"in {find.room}" if find.room else None,
            )
            if part
        )
        if _unsure(find):
            return step("no_view", place, f"I think {item} {be} {where}.")
        return step("no_view", place, f"look for {item} {where}.")

    if here.id != target_room.id:
        if (
            here.floor is not None
            and target_room.floor is not None
            and here.floor != target_room.floor
        ):
            saw = "I think I saw" if _unsure(find) else "I last saw"
            return step(
                "other_floor",
                target_room.spoken,
                f"{saw} {item} in {target_room.spoken}, and that is on another floor.",
            )
        hop = _room(layout, _next_hop(layout, here.id, target_room.id))
        if hop is not None and hop.id != target_room.id:
            return step(
                "go_to_room",
                f"{here.spoken}>{hop.spoken}",
                f"from {here.spoken}, walk to {hop.spoken} first.",
            )
        return step(
            "go_to_room",
            f"{here.spoken}>{target_room.spoken}",
            f"from {here.spoken}, walk to {target_room.spoken}, and I'll help you from there.",
        )

    if target is not None and find.landmark and target.id in fresh.landmarks_seen:
        if _unsure(find):
            return step(
                "in_view", place, f"I think {item} {be} {on} {find.landmark} in front of you."
            )
        return step(
            "in_view",
            place,
            f"you're close, so look {on} {find.landmark} in front of you for {item}.",
        )
    if find.landmark:
        return step("look_for", place, f"you're in the right room, so look for {find.landmark}.")
    saw = "I think I saw" if _unsure(find) else "I last saw"
    return step("look_for", place, f"you're in the right room, and {saw} {item} in here.")


# ---------- pieces ----------


def _unsure(find: FindResult) -> bool:
    """The same test `speak()` uses for "I think"."""
    return find.confident is not True or find.possible_newer_glimpse is True


def _think(find: FindResult, sentence: str) -> str:
    return f"I think {sentence}" if _unsure(find) else sentence


def _within(moment: datetime | None, now: datetime, seconds: float) -> bool:
    return moment is not None and (now - moment).total_seconds() <= seconds


def _room(layout: HomeLayout, room_id: UUID | None) -> LayoutRoom | None:
    return next((r for r in layout.rooms if r.id == room_id), None) if room_id else None


def _room_named(layout: HomeLayout, spoken: str | None) -> LayoutRoom | None:
    """The room `find_item` named, for an item seen in a room but on no landmark."""
    if not spoken:
        return None
    wanted = spoken.strip().casefold()
    return next((r for r in layout.rooms if r.spoken.strip().casefold() == wanted), None)


def _landmark(layout: HomeLayout, address: str | None) -> LayoutLandmark | None:
    return next((lm for lm in layout.landmarks if lm.address == address), None) if address else None


def _next_hop(layout: HomeLayout, start: UUID, goal: UUID) -> UUID | None:
    """The first room to walk into on the shortest way from `start` to `goal`, or None when the
    home's room links do not connect them."""
    neighbours: dict[UUID, list[UUID]] = {}
    for a, b in layout.links:
        neighbours.setdefault(a, []).append(b)
        neighbours.setdefault(b, []).append(a)
    first: dict[UUID, UUID | None] = {start: None}
    queue = deque([start])
    while queue:
        room = queue.popleft()
        if room == goal:
            return first[room]
        for nxt in neighbours.get(room, []):
            if nxt not in first:
                first[nxt] = first[room] or nxt
                queue.append(nxt)
    return None


def _describe(exc: BaseException) -> str:
    detail = str(exc).replace("\n", " ")[:300]
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
