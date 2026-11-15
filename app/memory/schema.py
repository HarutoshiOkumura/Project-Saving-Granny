"""Pydantic models for what the memory functions return. Keys follow `find_item` in 0001."""

from datetime import date
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

Channel = Literal["phone", "facetime", "web"]
State = Literal["seen", "carried", "not_there_anymore", "never_seen", "unknown_item"]


class Item(BaseModel):
    """One enrolled item and the other words for it, as `db.list_items` reads them."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: UUID
    name: str
    aliases: list[str] = []
    category: str | None = None  # the detector's class: items of one category are look-alikes
    color: str | None = None
    description: str | None = None
    home_landmark_id: UUID | None = None  # where the family says it belongs


class Place(BaseModel):
    """`usual` ({room, landmark, pct}) or `previous` ({room, landmark, minutes_ago})."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    room: str | None = None
    landmark: str | None = None
    pct: int | None = None
    minutes_ago: int | None = None


class FindResult(BaseModel):
    """`find_item` / `ask_item` jsonb. Only `state` is always there; which keys come depends on it.

    Missing keys are None and unknown keys are ignored, so a new key in the database never breaks
    the read path.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    state: State
    item: str | None = None
    plural: bool | None = None
    sighting_id: UUID | None = None
    room: str | None = None
    landmark: str | None = None
    relation: str | None = None
    address: str | None = None
    minutes_ago: int | None = None
    last_seen_at: AwareDatetime | None = None
    timezone: str | None = None
    confident: bool | None = None
    photo: str | None = None
    previous: Place | None = None
    usual: Place | None = None
    wearer_went_to: str | None = None
    possible_newer_glimpse: bool | None = None
    possible_glimpse: bool | None = None
    heard: str | None = None
    query_id: UUID | None = None

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError(f"unknown timezone {value!r}") from exc
        return value


class PlaceName(BaseModel):
    """One row of the `places` view: a landmark's address and the words the voice says for it."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    landmark_id: UUID
    address: str
    room_spoken: str
    landmark_spoken: str


class UsualPlace(BaseModel):
    """One row of the `item_usual_places` view: settled, not-in-hand stays of an item at a place."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    item_id: UUID
    landmark_id: UUID
    episodes: int
    last_seen_at: AwareDatetime


class Glimpse(BaseModel):
    """A one-frame (`tentative`) stay of an item on a landmark: a hint, never an answer."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    item_id: UUID
    landmark_id: UUID
    last_seen_at: AwareDatetime


class LookEvidence(BaseModel):
    """What "where to look" weighs besides `find_item`'s answer, read once for the whole home."""

    model_config = ConfigDict(frozen=True)

    places: list[PlaceName] = []
    usual: list[UsualPlace] = []
    glimpses: list[Glimpse] = []


# ---------------------------------------------------------------------------------------------
# Insights (0005, docs/INSIGHTS.md): wear time, family tags, the safety loop, and the rows the
# pattern summary reads.
# ---------------------------------------------------------------------------------------------

EventKind = Literal[
    "visitor",
    "unwell",
    "hospital",
    "new_medicine",
    "new_item",
    "away",
    "camera_off",
    "new_hearing_aid",
    "other",
]
ConcernKind = Literal["fall", "hurt", "help", "smoke", "scam", "lost_outside", "quiet_day"]
ConcernAnswer = Literal["hurt", "ok", "no_answer"]
Urgency = Literal["urgent", "check_in", "note"]
ConcernStatus = Literal["open", "on_my_way", "calling_911", "all_ok"]


class HomeInfo(BaseModel):
    """The `homes` row: whose home, its zone, and whether the wearer agreed to share a summary."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    person_name: str
    timezone: str
    share_summary_with_clinician: bool = False
    share_decided_at: AwareDatetime | None = None


class WearDay(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    day: date
    worn_minutes: int


class WearHour(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    day: date
    hour: int
    worn_minutes: int


class LifeEvent(BaseModel):
    """A family tag that explains a day ("new medicine", "visitor")."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: UUID
    kind: EventKind
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    note: str | None = None


class Concern(BaseModel):
    """One `concerns` row: the person said they fell, needed help, smelled smoke..."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: UUID
    kind: ConcernKind
    answer: ConcernAnswer | None = None
    urgency: Urgency
    channel: Channel
    raised_at: AwareDatetime
    room: str | None = None  # spoken name of the last room the camera saw
    status: ConcernStatus
    handled_at: AwareDatetime | None = None
    handled_by: str | None = None


class QuestionRow(BaseModel):
    """One `queries` row, as the pattern summary reads it."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    asked_at: AwareDatetime
    channel: Channel
    item_id: UUID | None = None
    state: str | None = None
    outcome: Literal["found", "not_found"] | None = None
    sighting_id: UUID | None = None


class StayRow(BaseModel):
    """A settled stay of an item on a landmark (a put-down), with what it took to believe it."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: UUID
    item_id: UUID
    landmark_id: UUID | None = None
    first_seen_at: AwareDatetime
    det_conf: float | None = None
    room_conf: float | None = None
    id_conf: float | None = None

    @property
    def confident(self) -> bool:
        """As `find_item`: detector x room x identity confidence, cut at 0.5."""
        return (self.det_conf or 1) * (self.room_conf or 1) * (self.id_conf or 1) >= 0.5


class PatternRows(BaseModel):
    """Everything the pattern summary reads, in one bundle (read by `db.pattern_rows`)."""

    model_config = ConfigDict(frozen=True)

    home: HomeInfo
    items: list[Item]
    places: list["PlaceName"]
    wear: list[WearDay]
    events: list[LifeEvent]
    questions: list[QuestionRow]
    answered_by: list[StayRow]  # the stays the questions were answered from
    put_downs: list[StayRow]


def _none_to_list(value: object) -> object:
    """`jsonb_agg` over no rows gives null; an empty home has no beliefs, not a missing key."""
    return [] if value is None else value


class ContextLandmark(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    room: str
    landmark: str
    kind: str

    @property
    def address(self) -> str:
        """The `places.address` form ("room > landmark") that beliefs and the schema use."""
        return f"{self.room} > {self.landmark}"


class ContextItem(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    item: str
    looks_like: str = ""


class Belief(BaseModel):
    """One row of `item_last_seen`: where an item is believed to be. `address` is null in hand."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    item: str
    address: str | None = None
    in_hand: bool = False
    status: str
    minutes_ago: int | None = None


class HomeMap(BaseModel):
    """Names to ids for the write path, keyed by the names `perception_context` uses
    (landmarks by address, "room > landmark")."""

    model_config = ConfigDict(frozen=True)

    rooms: dict[str, UUID]
    capture_allowed: dict[str, bool]
    landmarks: dict[str, UUID]
    landmark_rooms: dict[str, str]
    items: dict[str, UUID]

    @property
    def no_capture_rooms(self) -> set[str]:
        return {room for room, allowed in self.capture_allowed.items() if not allowed}


class PerceptionContext(BaseModel):
    """`perception_context` jsonb: the names the vision model may answer with, and the beliefs."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    rooms: list[str]
    landmarks: list[ContextLandmark]
    items: list[ContextItem]
    beliefs: list[Belief]

    @field_validator("rooms", "landmarks", "items", "beliefs", mode="before")
    @classmethod
    def _empty_is_a_list(cls, value: object) -> object:
        return _none_to_list(value)
