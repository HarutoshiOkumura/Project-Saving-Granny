"""The only module that talks to Supabase.

The memory functions go through `rpc(name, params)`. The write path also reads the home's names
and ids from the tables, inserts observations (there is no function for that) and uploads crops
to the private `crops` bucket. Every call has a hard `asyncio.timeout`.

On the read path, the table reads are `list_items` (item names and aliases for the Typesense copy,
step 09, and the FaceTime agent's call-start snapshot) and `look_evidence` (habits and glimpses for
"where to look" in the snapshot, D33). `find_item` is the read that logs no question.
`sign_photos` turns crop paths into links that work for an hour.
"""

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import get_settings
from app.memory.schema import (
    Channel,
    FindResult,
    Glimpse,
    HomeMap,
    Item,
    LookEvidence,
    PerceptionContext,
    PlaceName,
    UsualPlace,
)

READ_TIMEOUT_S = 2.0  # the read path: a caller is waiting
WRITE_TIMEOUT_S = 10.0  # the write path: a background task, may fail softly
CROPS_BUCKET = "crops"
PHOTO_LINK_S = 3600  # signed crop links last an hour (memory-db rules)

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
            .select("id,name,aliases,category,color,description,home_landmark_id")
            .eq("home_id", _home())
            .order("name")
            .execute()
        )
    return [Item.model_validate(row) for row in response.data]


async def look_evidence(item_ids: list[UUID], glimpses_since: datetime) -> LookEvidence:
    """Everything "where to look" weighs besides `find_item`: the home's place names, each item's
    settled stays per place (`item_usual_places`) and its one-frame glimpses on a landmark since
    `glimpses_since`, newest first. Three reads at once, read-only. Raises like `ask_item`."""
    home = _home()
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        places_q = (
            client.table("places")
            .select("landmark_id,address,room_spoken,landmark_spoken")
            .eq("home_id", home)
            .execute()
        )
        glimpses_q = (
            client.table("sightings")
            .select("item_id,landmark_id,last_seen_at")
            .eq("home_id", home)
            .eq("status", "tentative")
            .eq("in_hand", "false")
            .not_.is_("item_id", "null")
            .not_.is_("landmark_id", "null")
            .gte("last_seen_at", _utc(glimpses_since))
            .order("last_seen_at", desc=True)
            .limit(500)
            .execute()
        )
        if item_ids:  # the view has no home_id: it is limited to this home's items
            usual_q = (
                client.table("item_usual_places")
                .select("item_id,landmark_id,episodes,last_seen_at")
                .in_("item_id", [str(i) for i in item_ids])
                .execute()
            )
            places, glimpses, usual = await asyncio.gather(places_q, glimpses_q, usual_q)
            usual_rows = usual.data
        else:
            places, glimpses = await asyncio.gather(places_q, glimpses_q)
            usual_rows = []
    return LookEvidence(
        places=[PlaceName.model_validate(row) for row in places.data],
        usual=[UsualPlace.model_validate(row) for row in usual_rows],
        glimpses=[Glimpse.model_validate(row) for row in glimpses.data],
    )


async def sign_photos(paths: list[str]) -> dict[str, str]:
    """Storage paths (`crops/<home>/<item>/<time>.jpg`, as in `crop_url` and `find_item`'s
    `photo`) to links that work for PHOTO_LINK_S, one request per bucket. A path whose file is
    missing is left out. Raises like `ask_item`."""
    by_bucket: dict[str, list[str]] = {}
    for path in dict.fromkeys(paths):
        bucket, _, key = path.partition("/")
        if bucket and key:
            by_bucket.setdefault(bucket, []).append(key)
    links: dict[str, str] = {}
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        for bucket, keys in by_bucket.items():
            signed = await client.storage.from_(bucket).create_signed_urls(keys, PHOTO_LINK_S)
            for entry in signed:
                if entry["signedURL"] and not entry["error"]:
                    links[f"{bucket}/{entry['path']}"] = entry["signedURL"]
    return links


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
