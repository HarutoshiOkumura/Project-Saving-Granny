"""The only module that talks to Supabase.

The memory functions go through `rpc(name, params)`. The write path also reads the home's names
and ids from the tables, inserts observations (there is no function for that) and uploads crops
to the private `crops` bucket. Every call has a hard `asyncio.timeout`.

On the read path, the table reads are `list_items` (item names and aliases for the Typesense
copy, step 09, and the FaceTime agent's call-start snapshot) and `list_moments` (stays with their
names, for the moments search and the FaceTime photo). `find_item` is the read that logs no
question. Photos are read with `download_photo` and never leave the backend as storage paths.
`list_pins` reads where each landmark is in the room's 3D scan, and `set_pin` is the one write
the room view makes: `landmarks.x/y/z` (D25 A), never a sighting.
"""

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
from storage3.exceptions import StorageApiError
from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import get_settings
from app.memory.schema import (
    Channel,
    FindResult,
    HomeMap,
    Item,
    Moment,
    PerceptionContext,
    Pin,
)

READ_TIMEOUT_S = 2.0  # the read path: a caller is waiting
WRITE_TIMEOUT_S = 10.0  # the write path: a background task, may fail softly
PHOTO_TIMEOUT_S = 8.0  # a photo for the FaceTime card; the spoken answer never waits on it
CROPS_BUCKET = "crops"

_client: AsyncClient | None = None
_client_lock = asyncio.Lock()


class InvalidPlace(Exception):
    """`log_sighting` raised 22023: room and landmark disagree, or one is not in this home."""


async def _get_client() -> AsyncClient:
    """One client per process, built on first use from the secret key (backend only).

    It gets its own httpx client: without one, supabase-py passes `timeout` and `verify` to
    postgrest-py, which deprecated them. That client is shared by PostgREST and Storage, so its
    timeout is the write path's; the read path is cut at READ_TIMEOUT_S by `asyncio.timeout`.
    """
    global _client
    async with _client_lock:
        if _client is None:
            settings = get_settings()
            _client = await acreate_client(
                settings.supabase_url,
                settings.supabase_secret_key.get_secret_value(),
                options=AsyncClientOptions(
                    auto_refresh_token=False,
                    persist_session=False,
                    httpx_client=httpx.AsyncClient(
                        timeout=WRITE_TIMEOUT_S, http2=True, follow_redirects=True
                    ),
                ),
            )
    return _client


def _home() -> str:
    return str(get_settings().home_id)


def _utc(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


# ---------------------------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------------------------


async def ask_item(query: str, channel: Channel) -> FindResult:
    """Answer "where is it?" and log the question, in one round trip.

    Raises TimeoutError after READ_TIMEOUT_S, the client's errors on a failed call, and
    pydantic.ValidationError if the answer does not fit FindResult. Callers fall back.
    """
    params = {"p_home": _home(), "p_query": query, "p_channel": channel}
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await client.rpc("ask_item", params).execute()
    return FindResult.model_validate(response.data)


async def find_item(query: str) -> FindResult:
    """The same answer as `ask_item`, logging nothing: for the snapshot (which nobody asked),
    scripts and checks."""
    params = {"p_home": _home(), "p_query": query}
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await client.rpc("find_item", params).execute()
    return FindResult.model_validate(response.data)


async def list_items() -> list[Item]:
    """Every item in this home with its aliases and looks, by name. Read-only. For the Typesense
    copy and the snapshot (looks let the FaceTime agent ask "the blue one or the green one?")."""
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("items")
            .select("id,name,aliases,category,color,description")
            .eq("home_id", _home())
            .order("name")
            .execute()
        )
    return [Item.model_validate(row) for row in response.data]


_MOMENT_COLUMNS = (
    "id,status,in_hand,relation,description,last_seen_at,crop_url,"
    "items(name,aliases,color,description),landmarks(spoken_name),rooms(spoken_name)"
)


async def list_moments(sighting_id: UUID | None = None, *, limit: int = 500) -> list[Moment]:
    """This home's stays of enrolled items, newest first, each with its item's names and looks and
    the spoken place: what the moments search indexes (`app/moments.py`). With `sighting_id`, that
    one stay (or []), within the read path's timeout. Read-only."""
    async with asyncio.timeout(READ_TIMEOUT_S if sighting_id else WRITE_TIMEOUT_S):
        client = await _get_client()
        query = (
            client.table("sightings")
            .select(_MOMENT_COLUMNS)
            .eq("home_id", _home())
            .filter("item_id", "not.is", "null")  # unowned detections are not moments
        )
        if sighting_id is not None:
            query = query.eq("id", str(sighting_id))
        response = await query.order("last_seen_at", desc=True).limit(limit).execute()
    return [Moment.from_row(row) for row in response.data]


def moment_path(crop_url: str) -> str:
    """Where the moment photo that goes with a tight crop is stored: beside it, `.moment.jpg`."""
    return crop_url.removesuffix(".jpg") + ".moment.jpg"


async def download_photo(path: str) -> bytes | None:
    """The JPEG at a storage path (`crops/<home>/<item>/<time>.jpg`), or None when there is no
    such file. Raises TimeoutError after PHOTO_TIMEOUT_S."""
    bucket, _, key = path.partition("/")
    async with asyncio.timeout(PHOTO_TIMEOUT_S):
        client = await _get_client()
        try:
            return await client.storage.from_(bucket).download(key)
        except StorageApiError:
            return None


async def list_pins() -> list[Pin]:
    """Every landmark of this home's capture-allowed rooms with its spoken name and its pin in
    the room's 3D scan (None until placed), by address. Read-only, for `GET /room/scene`."""
    home = _home()
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        places = await (
            client.table("places")
            .select("landmark_id,address,landmark_spoken")
            .eq("home_id", home)
            .eq("capture_allowed", True)
            .order("address")
            .execute()
        )
        ids = [row["landmark_id"] for row in places.data]
        spots = (
            await client.table("landmarks").select("id,x,y,z").in_("id", ids).execute()
            if ids
            else None
        )
    by_id = {row["id"]: row for row in (spots.data if spots else [])}
    return [
        Pin.model_validate(
            {
                "landmark_id": row["landmark_id"],
                "address": row["address"],
                "spoken": row["landmark_spoken"],
                **{axis: by_id.get(row["landmark_id"], {}).get(axis) for axis in ("x", "y", "z")},
            }
        )
        for row in places.data
    ]


async def set_pin(landmark_id: UUID, position: tuple[float, float, float] | None) -> None:
    """Store (or with None, clear) one landmark's place in the room's 3D scan. The caller takes
    `landmark_id` from `list_pins`, so it is always a landmark of this home."""
    x, y, z = position if position is not None else (None, None, None)
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        await (
            client.table("landmarks")
            .update({"x": x, "y": y, "z": z})
            .eq("id", str(landmark_id))
            .execute()
        )


async def perception_context(room_id: UUID | None = None) -> PerceptionContext:
    """What the vision model may answer with (rooms, landmarks, items) and the current beliefs.

    With `room_id`, landmarks are limited to that room and the rooms linked to it. No-capture
    rooms are listed in `rooms` but have no landmarks. Raises like `ask_item`.
    """
    params = {"p_home": _home(), "p_room": str(room_id) if room_id else None}
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await client.rpc("perception_context", params).execute()
    return PerceptionContext.model_validate(response.data)


# ---------------------------------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------------------------------


async def home_map() -> HomeMap:
    """The ids behind the names `perception_context` gives the model, and which rooms forbid
    capture. Read from the `rooms` and `items` tables and the `places` view."""
    home = _home()
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        rooms = await (
            client.table("rooms").select("id,name,capture_allowed").eq("home_id", home).execute()
        )
        places = await (
            client.table("places").select("landmark_id,room,address").eq("home_id", home).execute()
        )
        items = await client.table("items").select("id,name").eq("home_id", home).execute()
    return HomeMap.model_validate(
        {
            "rooms": {r["name"]: r["id"] for r in rooms.data},
            "capture_allowed": {r["name"]: r["capture_allowed"] for r in rooms.data},
            "landmarks": {p["address"]: p["landmark_id"] for p in places.data},
            "landmark_rooms": {p["address"]: p["room"] for p in places.data},
            "items": {i["name"]: i["id"] for i in items.data},
        }
    )


async def insert_observation(
    *,
    device_id: str,
    captured_at: datetime,
    room_id: UUID,
    room_conf: float,
    landmarks_seen: list[UUID],
    perceived_by: str,
    idempotency_key: str,
) -> UUID | None:
    """One row per processed frame (text only, no image). None when `idempotency_key` is
    already there: the frame was processed before, and the caller must skip it."""
    row = {
        "home_id": _home(),
        "device_id": device_id,
        "captured_at": _utc(captured_at),
        "room_id": str(room_id),
        "room_conf": room_conf,
        "landmarks_seen": [str(lm) for lm in landmarks_seen],
        "source": "worn_cam",
        "perceived_by": perceived_by,
        "idempotency_key": idempotency_key,
    }
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("observations")
            .upsert(row, on_conflict="home_id,idempotency_key", ignore_duplicates=True)
            .execute()
        )
    return UUID(response.data[0]["id"]) if response.data else None


def crop_key(item: str, captured_at: datetime) -> str:
    """`<home>/<item>/<utc timestamp>.jpg` inside the bucket; the item name as a slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", item.lower()).strip("-")
    return f"{_home()}/{slug}/{captured_at.astimezone(UTC):%Y%m%dT%H%M%S%fZ}.jpg"


async def upload_crop(item: str, captured_at: datetime, jpeg: bytes) -> str:
    """Store one crop in the private bucket; returns the storage path for `crop_url`
    (`crops/<home>/<item>/<utc timestamp>.jpg`, signed at read time)."""
    key = crop_key(item, captured_at)
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        await client.storage.from_(CROPS_BUCKET).upload(
            key, jpeg, {"content-type": "image/jpeg", "upsert": "true"}
        )
    return f"{CROPS_BUCKET}/{key}"


async def upload_moment(crop_url: str, jpeg: bytes) -> str:
    """Store the moment photo (the wider view of where the item sits, `app/photo.py`) beside its
    tight crop in the private bucket; returns its storage path. Never a full frame."""
    path = moment_path(crop_url)
    bucket, _, key = path.partition("/")
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        await client.storage.from_(bucket).upload(
            key, jpeg, {"content-type": "image/jpeg", "upsert": "true"}
        )
    return path


async def log_sighting(
    *,
    item_id: UUID,
    label: str,
    room_id: UUID | None,
    landmark_id: UUID | None,
    relation: str,
    in_hand: bool,
    seen_at: datetime,
    det_conf: float,
    room_conf: float,
    crop_url: str | None,
    description: str | None,
    observation_id: UUID,
) -> UUID | None:
    """One detection. Returns the stay's id, or None when nothing may be stored. Raises
    InvalidPlace for 22023 (room and landmark disagree, or not in this home)."""
    params: dict[str, Any] = {
        "p_home": _home(),
        "p_item": str(item_id),
        "p_label": label,
        "p_room": str(room_id) if room_id else None,
        "p_landmark": str(landmark_id) if landmark_id else None,
        "p_relation": relation,
        "p_in_hand": in_hand,
        "p_seen_at": _utc(seen_at),
        "p_det_conf": det_conf,
        "p_room_conf": room_conf,
        "p_crop_url": crop_url,
        "p_description": description,
        "p_observation": str(observation_id),
        "p_event": "seen",
        "p_source": "worn_cam",
    }
    try:
        async with asyncio.timeout(WRITE_TIMEOUT_S):
            client = await _get_client()
            response = await client.rpc("log_sighting", params).execute()
    except APIError as exc:
        if exc.code == "22023":
            raise InvalidPlace(exc.message or "22023") from exc
        raise
    return UUID(response.data) if response.data else None


async def mark_absent(landmark_id: UUID, seen_at: datetime, visible: list[UUID]) -> int:
    """A landmark was clearly in view; `visible` lists the items seen on it (never null).
    Returns how many stays flipped to `contradicted`."""
    params = {
        "p_home": _home(),
        "p_landmark": str(landmark_id),
        "p_seen_at": _utc(seen_at),
        "p_visible": [str(item) for item in visible],
    }
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await client.rpc("mark_absent", params).execute()
    return int(response.data or 0)
