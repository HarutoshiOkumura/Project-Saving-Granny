"""The family dashboard's work (step 08): the board it polls, the history, the home's setup,
"tell Save It where it is", and adding items (D26 A), rooms and places.

Names follow the database's rules and `find_item`'s matching:

- An item name or alias is stored the way `find_item` reads a question: lower case, with a
  leading "my", "the", "a", "some", "her" or "his" dropped. A name or alias that is already any
  item's name or alias is refused, so a new item never shadows another ("bottle").
- Room and place names are the words the vision model must answer with (JSON-schema enums), so
  they are plain lower-case words: letters, digits, spaces, "-" and "_". Never "unknown" (the
  model's room for "not sure") or "none" (its landmark for "on no landmark"), never ">" (it joins
  a room and a place in an address).
- The camera picks up new items, rooms and places within 30 s (the worker's context cache); a new
  item is looked for by its own name until someone measures a better SAM 3 wording.
"""

import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from app import names, photos
from app.ask import Known, snapshot
from app.insights import ConcernBoard, concern_board
from app.memory import db
from app.memory.schema import Item, LandmarkKind, Room, SetupPlace, TimelineRow
from app.perception.retry import describe
from app.speak import speak

logger = logging.getLogger(__name__)

LEADING = re.compile(r"^(my|the|a|some|her|his)\s+")
ITEM_WORDS = re.compile(r"^[a-z0-9][a-z0-9 '\-]*$")
PLACE_WORDS = re.compile(r"^[a-z0-9][a-z0-9 _\-]*$")
RESERVED = {"unknown", "none"}
TYPESENSE_SYNC_S = 2.0


class NameTaken(Exception):
    """The name (or an alias) is already used; the message says by what."""


class NotAllowed(Exception):
    """A request the home's rules refuse (a place in a room the camera never records)."""


def normalize(words: str) -> str:
    """As `find_item` reads a question: trimmed, lower case, one leading "my"/"the"/... dropped,
    inner spaces collapsed."""
    return LEADING.sub("", re.sub(r"\s+", " ", words.strip().lower()))


def clash(name: str, aliases: list[str], items: list[Item]) -> str | None:
    """The sentence explaining why these names cannot be added, or None when they are free."""
    taken: dict[str, str] = {}
    for item in items:
        for word in (item.name, *item.aliases):
            taken.setdefault(normalize(word), item.name)
    for word in (name, *aliases):
        owner = taken.get(normalize(word))
        if owner is not None:
            what = "the name" if normalize(word) == normalize(owner) else "another name"
            return f'"{normalize(word)}" is already {what} of your {owner}.'
    return None


def place_word(words: str) -> str:
    """A room or place name the vision model can answer with, or ValueError."""
    word = re.sub(r"\s+", " ", words.strip().lower())
    if not PLACE_WORDS.match(word) or len(word) > 40:
        raise ValueError("use plain words: letters, numbers, spaces, - or _ (at most 40)")
    if word in RESERVED:
        raise ValueError(f'"{word}" has a special meaning for the camera; pick another word')
    return word


def spoken(given: str | None, word: str) -> str:
    """What Find It says out loud: as given, or "the" plus the name ("the kitchen")."""
    text = re.sub(r"\s+", " ", (given or "").strip())
    return text or f"the {word.replace('_', ' ')}"


# ---------------------------------------------------------------------------------------------
# Request and reply shapes (docs/DASHBOARD.md, "Dashboard API")
# ---------------------------------------------------------------------------------------------


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=120)
    aliases: list[str] = Field(default_factory=list, max_length=8)
    kind: str | None = Field(default=None, max_length=30)  # look-alikes share one
    plural: bool = False
    home_landmark_id: UUID | None = None

    @field_validator("name", "kind")
    @classmethod
    def _item_words(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        word = normalize(value)
        if not ITEM_WORDS.match(word):
            raise ValueError("use plain words: letters, numbers, spaces, ' or -")
        return word

    @field_validator("aliases")
    @classmethod
    def _alias_words(cls, values: list[str]) -> list[str]:
        out: list[str] = []
        for value in values:
            word = normalize(value)
            if not word:
                continue
            if len(word) > 40 or not ITEM_WORDS.match(word):
                raise ValueError(f'"{value}": use plain words: letters, numbers, spaces, \' or -')
            if word not in out:
                out.append(word)
        return out

    @field_validator("color", "description")
    @classmethod
    def _text(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    spoken_name: str | None = Field(default=None, max_length=60)
    capture_allowed: bool  # no default: the family must choose

    @field_validator("name")
    @classmethod
    def _word(cls, value: str) -> str:
        return place_word(value)


class LandmarkIn(BaseModel):
    room_id: UUID
    name: str = Field(min_length=1, max_length=40)
    spoken_name: str | None = Field(default=None, max_length=60)
    kind: LandmarkKind = "surface"

    @field_validator("name")
    @classmethod
    def _word(cls, value: str) -> str:
        return place_word(value)


class ToldIn(BaseModel):
    item: str = Field(min_length=1, max_length=40)
    landmark_id: UUID
    note: str | None = Field(default=None, max_length=120)


class ToldOut(BaseModel):
    sighting_id: UUID | None
    sentence: str  # what Find It says about the item now


class Camera(BaseModel):
    worn_minutes_today: int | None = None  # None when wear time could not be read
    last_frame_at: AwareDatetime | None = None


class Board(BaseModel):
    """Everything the dashboard's "Now" tab shows, in one poll."""

    person: str
    timezone: str
    now: AwareDatetime
    items: list[Known]
    concerns: ConcernBoard
    camera: Camera


class TimelineEntry(BaseModel):
    sighting_id: UUID
    item: str | None  # None: an object nobody registered
    event_type: str
    status: str
    in_hand: bool
    first_seen_at: AwareDatetime
    last_seen_at: AwareDatetime
    room: str | None
    landmark: str | None
    photo_url: str | None


class Setup(BaseModel):
    rooms: list[Room]
    places: list[SetupPlace]
    items: list[Item]


# ---------------------------------------------------------------------------------------------
# Work
# ---------------------------------------------------------------------------------------------


async def board(now: datetime | None = None) -> Board:
    """Never fails as a whole once the home is read: the items come from the snapshot (which
    never raises), and a failed concern or camera read leaves that part empty."""
    started = time.perf_counter()
    now = now or datetime.now(UTC)
    info, items, concerns = await asyncio.gather(
        db.home_info(), snapshot(with_photos=True), _concerns(now)
    )
    midnight = now.astimezone(ZoneInfo(info.timezone)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    try:
        worn, last = await db.camera_today(midnight)
        camera = Camera(worn_minutes_today=worn, last_frame_at=last)
    except Exception as exc:
        logger.warning("board camera=error error=%s", describe(exc))
        camera = Camera()
    logger.info("board items=%d ms=%d", len(items), round((time.perf_counter() - started) * 1000))
    return Board(
        person=info.person_name,
        timezone=info.timezone,
        now=now,
        items=items,
        concerns=concerns,
        camera=camera,
    )


async def _concerns(now: datetime) -> ConcernBoard:
    try:
        return await concern_board(now)
    except Exception as exc:
        logger.warning("board concerns=error error=%s", describe(exc))
        return ConcernBoard(concerns=[])


async def history(include_glimpses: bool) -> list[TimelineEntry]:
    rows: list[TimelineRow] = await db.timeline(include_glimpses)
    try:
        links = await photos.links([r.photo for r in rows if r.photo])
    except Exception as exc:  # the history is still worth having without pictures
        logger.warning("timeline photos=error error=%s", describe(exc))
        links = {}
    return [
        TimelineEntry(
            **r.model_dump(exclude={"photo"}),
            photo_url=links.get(r.photo) if r.photo else None,
        )
        for r in rows
    ]


async def setup() -> Setup:
    rooms, places, items = await asyncio.gather(db.rooms(), db.setup_places(), db.list_items())
    return Setup(rooms=rooms, places=places, items=items)


async def told(body: ToldIn) -> ToldOut:
    """The family says where an item is. Raises LookupError for an unknown item or place."""
    items, places = await asyncio.gather(db.list_items(), db.setup_places())
    item = next((i for i in items if normalize(i.name) == normalize(body.item)), None)
    if item is None:
        raise LookupError(f"no item called {body.item!r}")
    if not any(p.landmark_id == body.landmark_id and p.capture_allowed for p in places):
        raise LookupError("no such place in this home")
    sighting = await db.log_told(item.id, body.landmark_id, item.name, body.note)
    sentence = speak(await db.find_item(item.name), datetime.now(UTC))
    logger.info("told item=%s landmark=%s sighting=%s", item.name, body.landmark_id, sighting)
    return ToldOut(sighting_id=sighting, sentence=sentence)


async def add_item(body: ItemIn) -> Item:
    """Raises NameTaken for a clash (also when the database finds one first), LookupError for a
    usual place not in this home."""
    items = await db.list_items()
    problem = clash(body.name, body.aliases, items)
    if problem:
        raise NameTaken(problem)
    if body.home_landmark_id is not None:
        places = await db.setup_places()
        if not any(p.landmark_id == body.home_landmark_id for p in places):
            raise LookupError("no such place in this home")
    try:
        item = await db.add_item(
            name=body.name,
            aliases=[a for a in body.aliases if a != body.name],
            category=body.kind or body.name,
            color=body.color,
            description=body.description,
            plural=body.plural,
            home_landmark_id=body.home_landmark_id,
        )
    except db.Duplicate as exc:
        raise NameTaken(f'"{body.name}" is already one of your items.') from exc
    await _sync_names()
    logger.info("item added name=%s aliases=%s", item.name, item.aliases)
    return item


async def add_room(body: RoomIn) -> Room:
    try:
        room = await db.add_room(
            name=body.name,
            spoken_name=spoken(body.spoken_name, body.name),
            capture_allowed=body.capture_allowed,
        )
    except db.Duplicate as exc:
        raise NameTaken(f'There is already a room called "{body.name}".') from exc
    logger.info("room added name=%s capture=%s", room.name, room.capture_allowed)
    return room


async def add_landmark(body: LandmarkIn) -> SetupPlace:
    rooms = {r.id: r for r in await db.rooms()}
    room = rooms.get(body.room_id)
    if room is None:
        raise LookupError("no such room in this home")
    if not room.capture_allowed:
        raise NotAllowed(
            f"The camera never records in {room.spoken_name or room.name}, "
            "so a place there would never be used."
        )
    try:
        landmark_id = await db.add_landmark(
            room_id=room.id,
            name=body.name,
            spoken_name=spoken(body.spoken_name, body.name),
            kind=body.kind,
        )
    except db.Duplicate as exc:
        raise NameTaken(f'{room.spoken_name or room.name} already has "{body.name}".') from exc
    logger.info("place added room=%s name=%s", room.name, body.name)
    places = await db.setup_places()
    return next(p for p in places if p.landmark_id == landmark_id)


async def _sync_names() -> None:
    """Copy the items to Typesense so a typo of the new name resolves too. Optional (step 09):
    Typesense may not run here (Coder), so any failure or TYPESENSE_SYNC_S is only logged."""
    try:
        async with asyncio.timeout(TYPESENSE_SYNC_S):
            await names.sync(await db.list_items())
    except Exception as exc:
        logger.info("typesense sync skipped: %s", describe(exc))
