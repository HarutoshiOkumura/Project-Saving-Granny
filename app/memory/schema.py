"""Pydantic models for what the memory functions return. Keys follow `find_item` in 0001."""

from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

Channel = Literal["phone", "facetime", "web"]
State = Literal["seen", "carried", "not_there_anymore", "never_seen", "unknown_item"]


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
