"""The room's 3D scan, meshed with the memory: `GET /room` and its data.

The scan is a picture of the room at one moment; the things in it move all day. So the view
never trusts where an item was when the room was scanned. It asks the memory where each item is
now (`ask.snapshot()`, the same answers the FaceTime agent loads) and puts it at that landmark's
pin (`landmarks.x/y/z`). The scan is the stage; the database is still the only memory.

The files come from `scripts/build_room.py` (`ROOM_DIR`: `preview.spz`, `full.spz`,
`scene.json`). A pin is placed by tapping the landmark in the 3D view: the tap's ray is matched
here against the scan's points, and only the landmark's position is stored. This module calls no
model and never touches sightings.
"""

import asyncio
import json
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field

from app.ask import snapshot
from app.config import get_settings
from app.memory import db
from app.memory.schema import State
from splat import geometry, spz

logger = logging.getLogger(__name__)

Level = Literal["preview", "full"]
Vector = tuple[float, float, float]
MAX_PICK_POINTS = 400_000  # enough to find a table top; keeps a tap under a tenth of a second


class View(BaseModel):
    eye: Vector
    target: Vector


class RoomPin(BaseModel):
    address: str
    spoken: str
    position: Vector | None = None


class Thing(BaseModel):
    """One enrolled item as the room view shows it: the sentence, and which pin it is at."""

    item: str
    sentence: str
    state: State | None = None
    address: str | None = None  # the landmark to fly to; None when it is carried or never seen
    sighting_id: UUID | None = None  # for the last-seen photo, `GET /moments/{id}/photo`


class RoomScene(BaseModel):
    version: str  # changes whenever a new file is ready: the view reloads the splat
    levels: list[Level]
    built_at: str | None = None
    source: str | None = None
    gaussians: dict[str, int] = Field(default_factory=dict)
    start: View
    bounds: dict[str, Vector]
    views: list[View] = Field(default_factory=list)  # where the scan's own cameras stood
    pins: list[RoomPin]
    things: list[Thing]


class PinRequest(BaseModel):
    address: str = Field(min_length=1, max_length=200)
    origin: Vector
    direction: Vector


class NoScan(Exception):
    """No room has been built yet."""


class UnknownLandmark(Exception):
    pass


class NothingThere(Exception):
    """The tap's ray passes no part of the scan."""


def _folder() -> Path:
    return get_settings().room_dir


def splat_path(level: Level) -> Path | None:
    path = _folder() / f"{level}.spz"
    return path if path.is_file() else None


def _description() -> dict:
    try:
        return json.loads((_folder() / "scene.json").read_text())
    except (OSError, ValueError) as exc:
        raise NoScan("no room scan yet: run scripts/build_room.py") from exc


def _version(levels: list[Level]) -> str:
    stamps = [f"{level}:{splat_path(level).stat().st_mtime_ns}" for level in levels]
    return "|".join(stamps)


def _place_of(state: State | None) -> bool:
    """States whose answer names a place the view can point at."""
    return state in ("seen", "not_there_anymore")


async def scene() -> RoomScene:
    """Everything the room view needs in one call. Raises NoScan when no room was built."""
    description = _description()
    levels: list[Level] = [level for level in ("preview", "full") if splat_path(level)]
    if not levels:
        raise NoScan("no room scan yet: run scripts/build_room.py")
    pins, known = await asyncio.gather(_pins(), snapshot())
    return RoomScene(
        version=_version(levels),
        levels=levels,
        built_at=description.get("built_at"),
        source=description.get("source"),
        gaussians={k: v for k, v in description.get("gaussians", {}).items() if k in levels},
        start=View.model_validate(description["start"]),
        bounds=description["bounds"],
        views=[View.model_validate(c["view"]) for c in description.get("cameras", [])],
        pins=pins,
        things=[
            Thing(
                item=k.item,
                sentence=k.sentence,
                state=k.result.state if k.result else None,
                address=k.result.address if k.result and _place_of(k.result.state) else None,
                sighting_id=k.result.sighting_id if k.result else None,
            )
            for k in known
        ],
    )


async def _pins() -> list[RoomPin]:
    """The landmarks and their pins; [] when the database cannot be reached, so the room still
    opens (the things then have nowhere to point, and the view says so)."""
    try:
        return [
            RoomPin(address=p.address, spoken=p.spoken, position=p.position)
            for p in await db.list_pins()
        ]
    except Exception as exc:
        logger.warning("room pins error=%s: %s", type(exc).__name__, str(exc)[:200])
        return []


@lru_cache(maxsize=2)
def _points(path: Path, stamp: int) -> np.ndarray:
    """The scan's point positions, thinned, cached per file version (`stamp` is its mtime)."""
    positions = spz.decode(path.read_bytes())["positions"].astype(np.float32)
    if len(positions) > MAX_PICK_POINTS:
        keep = np.random.default_rng(0).choice(len(positions), MAX_PICK_POINTS, replace=False)
        positions = positions[keep]
    return positions


async def place_pin(request: PinRequest) -> RoomPin:
    """Put a landmark's pin where a tap in the 3D view lands, and store it."""
    started = time.perf_counter()
    path = splat_path("full") or splat_path("preview")
    if path is None:
        raise NoScan("no room scan yet")
    pin = next((p for p in await db.list_pins() if p.address == request.address), None)
    if pin is None:
        raise UnknownLandmark(request.address)
    if not np.isfinite(request.direction).all() or np.linalg.norm(request.direction) < 1e-9:
        raise NothingThere(request.address)
    points = await asyncio.to_thread(_points, path, path.stat().st_mtime_ns)
    hit = await asyncio.to_thread(
        geometry.pick_on_ray, points, np.asarray(request.origin), np.asarray(request.direction)
    )
    if hit is None:
        raise NothingThere(request.address)
    position = (round(float(hit[0]), 4), round(float(hit[1]), 4), round(float(hit[2]), 4))
    await db.set_pin(pin.landmark_id, position)
    logger.info(
        "room pin address=%r position=%s ms=%d",
        pin.address,
        position,
        (time.perf_counter() - started) * 1000,
    )
    return RoomPin(address=pin.address, spoken=pin.spoken, position=position)


async def clear_pin(address: str) -> None:
    pin = next((p for p in await db.list_pins() if p.address == address), None)
    if pin is None:
        raise UnknownLandmark(address)
    await db.set_pin(pin.landmark_id, None)
    logger.info("room pin address=%r cleared", pin.address)
