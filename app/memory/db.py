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
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import get_settings
from app.memory.schema import (
    Channel,
    Concern,
    ConcernAnswer,
    ConcernKind,
    ConcernStatus,
    EventKind,
    FindResult,
    Glimpse,
    HomeInfo,
    HomeMap,
    Item,
    LandmarkKind,
    LifeEvent,
    LookEvidence,
    PatternRows,
    PerceptionContext,
    PlaceName,
    Room,
    SetupPlace,
    TimelineRow,
    Urgency,
    UsualPlace,
    WearHour,
)

READ_TIMEOUT_S = 2.0  # the read path: a caller is waiting
WRITE_TIMEOUT_S = 10.0  # the write path: a background task, may fail softly
CROPS_BUCKET = "crops"
PHOTO_LINK_S = 3600  # signed crop links last an hour (memory-db rules)
PAGE = 1000  # PostgREST returns at most this many rows per request on Supabase

_client: AsyncClient | None = None
_client_lock = asyncio.Lock()


class InvalidPlace(Exception):
    """`log_sighting` raised 22023: room and landmark disagree, or one is not in this home."""


class Duplicate(Exception):
    """An insert hit a unique constraint (23505): that name is already used here."""


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
            .select("id,name,aliases,category,color,description,plural,home_landmark_id")
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


# ---------------------------------------------------------------------------------------------
# Insights (0005, docs/INSIGHTS.md): wear time, family tags, the safety loop, pattern rows.
# None of this is on the voice path; reads use WRITE_TIMEOUT_S.
# ---------------------------------------------------------------------------------------------


async def upsert_wear_minutes(counts: list[Any]) -> None:
    """Store wear minutes (`app.worker.wear.WearCount`): full counts, so a later flush of the same
    minute replaces the earlier, smaller one."""
    rows = [
        {
            "home_id": _home(),
            "device_id": c.device_id,
            "minute": _utc(c.minute),
            "frames": c.frames,
            "moving": c.moving,
        }
        for c in counts
    ]
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        await (
            client.table("wear_minutes")
            .upsert(rows, on_conflict="home_id,device_id,minute")
            .execute()
        )


async def add_life_event(
    kind: EventKind, starts_at: datetime, ends_at: datetime | None, note: str | None
) -> LifeEvent:
    row = {
        "home_id": _home(),
        "kind": kind,
        "starts_at": _utc(starts_at),
        "ends_at": _utc(ends_at) if ends_at else None,
        "note": note,
    }
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await client.table("life_events").insert(row).execute()
    return LifeEvent.model_validate(response.data[0])


async def life_events(since: datetime) -> list[LifeEvent]:
    """Family tags that start after `since`, oldest first."""
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("life_events")
            .select("id,kind,starts_at,ends_at,note")
            .eq("home_id", _home())
            .gte("starts_at", _utc(since))
            .order("starts_at")
            .limit(PAGE)
            .execute()
        )
    return [LifeEvent.model_validate(row) for row in response.data]


async def last_room() -> tuple[UUID, str] | None:
    """The last room the camera saw (id, spoken name), for a concern. Observations never hold a
    no-capture room (0001's trigger), so this never names the bathroom."""
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("observations")
            .select("room_id,rooms(name,spoken_name)")
            .eq("home_id", _home())
            .not_.is_("room_id", "null")
            .order("captured_at", desc=True)
            .limit(1)
            .execute()
        )
    if not response.data:
        return None
    row = response.data[0]
    room = row.get("rooms") or {}
    return UUID(row["room_id"]), room.get("spoken_name") or room.get("name") or ""


async def add_concern(
    kind: ConcernKind,
    answer: ConcernAnswer | None,
    urgency: Urgency,
    channel: Channel,
    room_id: UUID | None,
) -> UUID:
    row = {
        "home_id": _home(),
        "kind": kind,
        "answer": answer,
        "urgency": urgency,
        "channel": channel,
        "room_id": str(room_id) if room_id else None,
    }
    async with asyncio.timeout(READ_TIMEOUT_S):  # a person may be on the floor: fail fast
        client = await _get_client()
        response = await client.table("concerns").insert(row).execute()
    return UUID(response.data[0]["id"])


_CONCERN_COLUMNS = (
    "id,kind,answer,urgency,channel,raised_at,status,handled_at,handled_by,rooms(name,spoken_name)"
)


def _concern(row: dict[str, Any]) -> Concern:
    room = row.pop("rooms", None) or {}
    return Concern.model_validate({**row, "room": room.get("spoken_name") or room.get("name")})


async def concerns(since: datetime) -> list[Concern]:
    """Concerns raised after `since`, newest first, with the room's spoken name."""
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("concerns")
            .select(_CONCERN_COLUMNS)
            .eq("home_id", _home())
            .gte("raised_at", _utc(since))
            .order("raised_at", desc=True)
            .limit(PAGE)
            .execute()
        )
    return [_concern(row) for row in response.data]


async def handle_concern(concern_id: UUID, status: ConcernStatus, by: str) -> Concern | None:
    """The family's answer to a concern. None when no such concern is in this home."""
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("concerns")
            .update({"status": status, "handled_at": _utc(datetime.now(UTC)), "handled_by": by})
            .eq("id", str(concern_id))
            .eq("home_id", _home())
            .execute()
        )
        if not response.data:
            return None
        again = await (
            client.table("concerns").select(_CONCERN_COLUMNS).eq("id", str(concern_id)).execute()
        )
    return _concern(again.data[0])


async def wear_hours(since: date) -> list[WearHour]:
    """Worn minutes per local hour from `since` (`wear_hourly`), for the quiet-day check."""
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        rows = await _all_pages(
            lambda: (
                client.table("wear_hourly")
                .select("day,hour,worn_minutes")
                .eq("home_id", _home())
                .gte("day", since.isoformat())
                .order("day")
                .order("hour")
            )
        )
    return [WearHour.model_validate(row) for row in rows]


async def wearer_questions_since(since: datetime) -> int:
    """How many questions the wearer asked (FaceTime or phone) since `since`."""
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("queries")
            .select("id", count="exact")
            .eq("home_id", _home())
            .in_("channel", ["facetime", "phone"])
            .gte("asked_at", _utc(since))
            .limit(1)
            .execute()
        )
    return int(response.count or 0)


async def home_info() -> HomeInfo:
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("homes")
            .select("person_name,timezone,share_summary_with_clinician,share_decided_at")
            .eq("id", _home())
            .execute()
        )
    return HomeInfo.model_validate(response.data[0])


async def pattern_rows(since: datetime, history_since: datetime) -> PatternRows:
    """Everything the pattern summary needs from `since` (questions, wear, tags), plus put-downs
    from `history_since` so an odd place can be judged against the item's own past. Read-only."""
    home = _home()
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        info, items, events = await asyncio.gather(home_info(), list_items(), life_events(since))
        places = await (
            client.table("places")
            .select("landmark_id,address,room_spoken,landmark_spoken")
            .eq("home_id", home)
            .execute()
        )
        wear, questions, put_downs = await asyncio.gather(
            _all_pages(
                lambda: (
                    client.table("wear_daily")
                    .select("day,worn_minutes")
                    .eq("home_id", home)
                    .gte("day", since.date().isoformat())
                    .order("day")
                )
            ),
            _all_pages(
                lambda: (
                    client.table("queries")
                    .select("asked_at,channel,item_id,state,outcome,sighting_id")
                    .eq("home_id", home)
                    .gte("asked_at", _utc(since))
                    .order("asked_at")
                    .order("id")
                )
            ),
            _all_pages(
                lambda: (
                    client.table("sightings")
                    .select("id,item_id,landmark_id,first_seen_at,det_conf,room_conf,id_conf")
                    .eq("home_id", home)
                    .eq("event_type", "seen")
                    .eq("in_hand", "false")
                    .neq("status", "tentative")
                    .not_.is_("item_id", "null")
                    .not_.is_("landmark_id", "null")
                    .gte("first_seen_at", _utc(history_since))
                    .order("first_seen_at")
                    .order("id")
                )
            ),
        )
        asked_from = sorted({q["sighting_id"] for q in questions if q.get("sighting_id")})
        answered_by: list[dict[str, Any]] = []
        for start in range(0, len(asked_from), 100):  # keep each URL short
            response = await (
                client.table("sightings")
                .select("id,item_id,landmark_id,first_seen_at,det_conf,room_conf,id_conf")
                .in_("id", asked_from[start : start + 100])
                .execute()
            )
            answered_by.extend(response.data)
    return PatternRows.model_validate(
        {
            "home": info,
            "items": items,
            "places": places.data,
            "wear": wear,
            "events": events,
            "questions": questions,
            "answered_by": answered_by,
            "put_downs": put_downs,
        }
    )


async def _all_pages(make: Callable[[], Any]) -> list[dict[str, Any]]:
    """Every row of an ordered read, PAGE rows at a time. `make` builds a fresh query each call."""
    rows: list[dict[str, Any]] = []
    while True:
        response = await make().range(len(rows), len(rows) + PAGE - 1).execute()
        rows.extend(response.data)
        if len(response.data) < PAGE:
            return rows


# ---------------------------------------------------------------------------------------------
# Family dashboard (step 08): setup, history, "tell Save It", adding items, rooms and places.
# Not on the voice path; reads and writes use WRITE_TIMEOUT_S.
# ---------------------------------------------------------------------------------------------


async def rooms() -> list[Room]:
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("rooms")
            .select("id,name,spoken_name,capture_allowed")
            .eq("home_id", _home())
            .order("name")
            .execute()
        )
    return [Room.model_validate(row) for row in response.data]


async def setup_places() -> list[SetupPlace]:
    """Every landmark with its spoken words, no-capture rooms included (they are marked)."""
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        response = await (
            client.table("places")
            .select("landmark_id,room_id,room_spoken,landmark_spoken,kind,address,capture_allowed")
            .eq("home_id", _home())
            .order("address")
            .execute()
        )
    return [
        SetupPlace.model_validate(
            {**row, "room": row["room_spoken"], "landmark": row["landmark_spoken"]}
        )
        for row in response.data
    ]


async def timeline(include_glimpses: bool, limit: int = 50) -> list[TimelineRow]:
    """The newest stays, newest first. Without glimpses this is the `timeline` view (settled
    stays only); with them, `sightings` itself, so one-frame (`tentative`) stays show too."""
    home = _home()
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        rooms_q = client.table("rooms").select("id,name,spoken_name").eq("home_id", home).execute()
        places_q = (
            client.table("places")
            .select("landmark_id,address,room_spoken,landmark_spoken")
            .eq("home_id", home)
            .execute()
        )
        items_q = client.table("items").select("id,name").eq("home_id", home).execute()
        if include_glimpses:
            rows_q = (
                client.table("sightings")
                .select(
                    "sighting_id:id,item_id,event_type,status,in_hand,first_seen_at,"
                    "last_seen_at,landmark_id,room_id,crop_url"
                )
                .eq("home_id", home)
                .order("last_seen_at", desc=True)
                .limit(limit)
                .execute()
            )
        else:
            rows_q = (
                client.table("timeline")
                .select(
                    "sighting_id,item_id,event_type,status,in_hand,first_seen_at,last_seen_at,"
                    "address,crop_url"
                )
                .eq("home_id", home)
                .order("last_seen_at", desc=True)
                .limit(limit)
                .execute()
            )
        room_rows, place_rows, item_rows, rows = await asyncio.gather(
            rooms_q, places_q, items_q, rows_q
        )
    room_words = {r["id"]: r["spoken_name"] or r["name"] for r in room_rows.data}
    room_by_name = {r["name"]: r["spoken_name"] or r["name"] for r in room_rows.data}
    by_landmark = {p["landmark_id"]: p for p in place_rows.data}
    by_address = {p["address"]: p for p in place_rows.data}
    names = {i["id"]: i["name"] for i in item_rows.data}
    out = []
    for row in rows.data:
        place = by_landmark.get(row.get("landmark_id")) or by_address.get(row.get("address"))
        room = (
            place["room_spoken"]
            if place
            else room_words.get(row.get("room_id")) or room_by_name.get(row.get("address"))
        )
        out.append(
            TimelineRow.model_validate(
                {
                    **row,
                    "item": names.get(row.get("item_id")),
                    "room": room,
                    "landmark": place["landmark_spoken"] if place else None,
                    "photo": row.get("crop_url"),
                }
            )
        )
    return out


async def log_told(item_id: UUID, landmark_id: UUID, label: str, note: str | None) -> UUID | None:
    """The family says where an item is: a `told` stay from a `manual` source, active at once."""
    params: dict[str, Any] = {
        "p_home": _home(),
        "p_item": str(item_id),
        "p_label": label,
        "p_room": None,
        "p_landmark": str(landmark_id),
        "p_relation": "on",
        "p_in_hand": False,
        "p_seen_at": _utc(datetime.now(UTC)),
        "p_description": note,
        "p_event": "told",
        "p_source": "manual",
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


async def _insert(table: str, row: dict[str, Any]) -> dict[str, Any]:
    try:
        async with asyncio.timeout(WRITE_TIMEOUT_S):
            client = await _get_client()
            response = await client.table(table).insert(row).execute()
    except APIError as exc:
        if exc.code == "23505":
            raise Duplicate(exc.message or "23505") from exc
        raise
    return response.data[0]


async def add_item(
    *,
    name: str,
    aliases: list[str],
    category: str,
    color: str | None,
    description: str | None,
    plural: bool,
    home_landmark_id: UUID | None,
) -> Item:
    row = await _insert(
        "items",
        {
            "home_id": _home(),
            "name": name,
            "aliases": aliases,
            "category": category,
            "color": color,
            "description": description,
            "plural": plural,
            "home_landmark_id": str(home_landmark_id) if home_landmark_id else None,
        },
    )
    return Item.model_validate(row)


async def add_room(*, name: str, spoken_name: str, capture_allowed: bool) -> Room:
    row = await _insert(
        "rooms",
        {
            "home_id": _home(),
            "name": name,
            "spoken_name": spoken_name,
            "capture_allowed": capture_allowed,
        },
    )
    return Room.model_validate(row)


async def add_landmark(*, room_id: UUID, name: str, spoken_name: str, kind: LandmarkKind) -> UUID:
    row = await _insert(
        "landmarks",
        {"room_id": str(room_id), "name": name, "spoken_name": spoken_name, "kind": kind},
    )
    return UUID(row["id"])


async def camera_today(day_start: datetime) -> tuple[int, datetime | None]:
    """Worn minutes since `day_start` and the newest minute any frame arrived (`wear_minutes`)."""
    home = _home()
    async with asyncio.timeout(WRITE_TIMEOUT_S):
        client = await _get_client()
        worn, last = await asyncio.gather(
            client.table("wear_minutes")
            .select("minute", count="exact")
            .eq("home_id", home)
            .gte("minute", _utc(day_start))
            .gte("moving", 2)
            .limit(1)
            .execute(),
            client.table("wear_minutes")
            .select("minute")
            .eq("home_id", home)
            .order("minute", desc=True)
            .limit(1)
            .execute(),
        )
    newest = datetime.fromisoformat(last.data[0]["minute"]) if last.data else None
    return int(worn.count or 0), newest
