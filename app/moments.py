"""Moments: every stay of an item at a place, with its photo, searchable by description.

A caller on FaceTime does not always name a thing; they describe it ("the silver one I wear on
my wrist", "the green one with the gold letters"). This module finds the moment that best fits
those words and answers for that item, and it serves the photo of a moment for the card.

    write side   record_soon()   after a sighting: the moment photo, stored in the background
                 keep_current()  every few seconds: index what Postgres has and Typesense lacks
    read side    describe()      description -> the item meant -> its current answer (app/ask.py)
                 card()          one moment's photo as the FaceTime card's picture

Search is Typesense, hybrid: keywords over the item's names and looks, what the camera saw and
the place, fused with a vector made by Gemini from the item's crop and those same words
(`gemini-embedding-2` embeds picture and text into one vector, so a description matches what the
thing looks like, not only what it is called). The vectors are made here and stored in a plain
`float[]` field: Typesense's own CLIP model is a 600 MB download, which the hall network could
not deliver on 15 Nov.

Postgres stays the source of truth. The collection is a copy that `keep_current()` (started
with the backend) keeps in step and `scripts/sync_moments.py` rebuilds; a
description only ever picks the *item*, and the answer still comes from `ask()`. Without
Typesense or a Google key, or on any failure, `describe()` answers like `/find` and the index
is skipped.
"""

import asyncio
import json
import logging
import re
import time
from collections import OrderedDict
from uuid import UUID

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict

from app.ask import ask
from app.config import get_settings
from app.memory import db
from app.memory.schema import Channel, FindResult, Moment
from app.perception.frame import Frame
from app.perception.retry import describe as describe_error
from app.perception.schema import Box
from app.photo import CardPhoto, card_photo, moment_photo
from app.speak import FILLER_WORDS

logger = logging.getLogger(__name__)

COLLECTION = "moments"
EMBED_DIM = 768  # one of the sizes Google recommends; the model normalises it

EMBED_TIMEOUT_S = 4.0  # a description from a caller: one Gemini call
SEARCH_TIMEOUT_S = 1.5
RECORD_TIMEOUT_S = 25.0  # one moment photo, made and uploaded in the background
SYNC_TIMEOUT_S = 15.0
REFRESH_EVERY_S = 10.0  # how often the backend checks Postgres for stays to index

# Tuned on the five demo items on 15 Nov with 13 descriptions of them and 11 things that are not
# enrolled (docs/STATUS.md, "Moments"). A distance is the cosine distance between the description
# and a moment: lower is closer. Right items came back at 0.31 to 0.42, the best wrong guess for
# an unknown thing at 0.41 to 0.45, so both cuts lean towards "I don't know" over a wrong place.
MAX_DISTANCE = 0.425  # further than this and the description fits nothing we have seen
MARGIN = 0.035  # the best fit must beat the next item by this much, or it is not clearly meant
ALPHA = 0.7  # the vector's weight in Typesense's rank fusion; keywords get the rest
PER_PAGE = 12
PHOTO_CACHE = 48  # photos kept in memory, so the card does not wait on the network twice
MISSING_TTL_S = 60.0  # how long a photo that was not in storage is not asked for again

SCHEMA = {
    "name": COLLECTION,
    "fields": [
        {"name": "home_id", "type": "string"},
        {"name": "item", "type": "string", "facet": True, "stem": True},
        {"name": "aliases", "type": "string[]", "stem": True},
        {"name": "looks", "type": "string", "optional": True, "stem": True},
        {"name": "note", "type": "string", "optional": True, "stem": True},
        {"name": "place", "type": "string", "optional": True, "stem": True},
        {"name": "status", "type": "string", "facet": True},
        {"name": "in_hand", "type": "bool"},
        {"name": "seen_at", "type": "int64"},
        {"name": "photo", "type": "string", "optional": True, "index": False},
        {"name": "embedding", "type": "float[]", "num_dim": EMBED_DIM, "optional": True},
    ],
    "default_sorting_field": "seen_at",
}

# Spoken input, as in app/names.py: no half-typed words, typos allowed in longer words, and
# words that match nothing are dropped instead of emptying the result.
SEARCH_PARAMS = {
    "query_by": "item,aliases,looks,note,place",
    "prefix": "false",
    "num_typos": "2",
    "min_len_1typo": "5",
    "min_len_2typo": "8",
    "drop_tokens_threshold": str(PER_PAGE),
    "exclude_fields": "embedding",
    "per_page": str(PER_PAGE),
}


class Candidate(BaseModel):
    """One item a description could mean."""

    model_config = ConfigDict(frozen=True)

    item: str
    looks: str | None = None
    sighting_id: UUID  # the moment that matched best
    distance: float | None = None  # None when the search ran on keywords alone (no vector)


class Described(BaseModel):
    """`GET /describe`: the answer for the item a description means.

    `item` is set when one item fits; `sentence` and `result` are then exactly what `/find` gives
    for it. With two or more equally good fits, `item` is None, `candidates` lists them and
    `sentence` asks which one. With none, `sentence` is what `/find` says for those words.
    """

    sentence: str
    result: FindResult | None = None
    item: str | None = None
    candidates: list[Candidate] = []


# ---------------------------------------------------------------------------------------------
# Read side
# ---------------------------------------------------------------------------------------------


async def describe(description: str, channel: Channel) -> Described:
    """Answer "where is the thing that looks like this?". Never raises."""
    started = time.perf_counter()
    candidates = await _candidates(description)
    chosen = choose(candidates)
    if len(chosen) == 1:
        answer = await ask(chosen[0].item, channel)
        out = Described(
            sentence=answer.sentence, result=answer.result, item=chosen[0].item, candidates=chosen
        )
    elif chosen:
        out = Described(sentence=which_one(chosen), candidates=chosen)
    else:
        answer = await ask(description, channel)
        found = (
            answer.result.item if answer.result and answer.result.state != "unknown_item" else None
        )
        out = Described(sentence=answer.sentence, result=answer.result, item=found)
    logger.info(
        "describe heard=%r item=%s candidates=%s ms=%d",
        description,
        out.item,
        ",".join(
            f"{c.item}:{c.distance:.2f}" if c.distance is not None else c.item
            for c in candidates[:4]
        )
        or "-",
        round((time.perf_counter() - started) * 1000),
    )
    return out


def choose(candidates: list[Candidate]) -> list[Candidate]:
    """Which items a description means, from the best moment per item: one item when it fits and
    clearly beats the rest; several when two or more fit about equally (look-alikes: ask which);
    none when nothing fits, or when the best fit is not clearly ahead of an item that does not
    fit (a guess). Candidates without a distance (no vector) never count."""
    ranked = sorted((c for c in candidates if c.distance is not None), key=_distance)
    fits = [c for c in ranked if _distance(c) <= MAX_DISTANCE]
    if not fits:
        return []
    close = [c for c in fits if _distance(c) - _distance(fits[0]) < MARGIN]
    if len(close) > 1:
        return close[:3]
    if len(ranked) > 1 and _distance(ranked[1]) - _distance(fits[0]) < MARGIN:
        return []
    return close


def _distance(candidate: Candidate) -> float:
    return candidate.distance if candidate.distance is not None else float("inf")


def which_one(candidates: list[Candidate]) -> str:
    """ "Do you mean your green bag or your brown bag?" (voice rules: one short question)."""
    names = [f"your {c.item}" for c in candidates]
    return f"Do you mean {', '.join(names[:-1])} or {names[-1]}?"


async def card(
    sighting_id: UUID, width: int, height: int, area: tuple[int, int, int, int]
) -> CardPhoto | None:
    """The picture for the FaceTime card: the moment photo of this stay when there is one (item
    ringed), else its tight crop, else None, shown whole inside `area`. Never raises."""
    try:
        rows = await db.list_moments(sighting_id)
        if not rows or not rows[0].photo:
            return None
        for path in (db.moment_path(rows[0].photo), rows[0].photo):
            jpeg = _photos.get(path)
            if (
                jpeg is None
                and time.monotonic() - _missing.get(path, -MISSING_TTL_S) >= MISSING_TTL_S
            ):
                jpeg = await db.download_photo(path)
                if jpeg is None:  # an older sighting has no moment photo: do not ask again at once
                    _missing[path] = time.monotonic()
            if jpeg is not None:
                _keep_photo(path, jpeg)
                return card_photo(jpeg, width, height, area)
    except Exception as exc:
        logger.warning("card sighting=%s error=%s", sighting_id, describe_error(exc))
    return None


# ---------------------------------------------------------------------------------------------
# Write side
# ---------------------------------------------------------------------------------------------


def record_soon(
    frame: Frame, box: Box | None, crop_url: str | None, sighting_id: UUID | None
) -> None:
    """After `log_sighting` stored a look at an item: have its moment photo made and stored in
    the background. The ingest worker calls this once per kept item and does not wait: it returns
    at once, adds nothing to the frame's time and never raises.

    Per stay, one photo is in the works at a time. Looks that arrive meanwhile replace each other
    and only the newest is stored next, so a slow network delays photos but never piles them up.
    Does nothing when MOMENT_PHOTOS is off or the look left no crop."""
    if box is None or crop_url is None or sighting_id is None:
        return
    try:
        if not get_settings().moment_photos:
            return
        starting = sighting_id not in _latest
        _latest[sighting_id] = (frame, box, crop_url)
        if starting:
            task = asyncio.get_running_loop().create_task(_record_latest(sighting_id))
            _tasks.add(task)  # the loop keeps only a weak reference to a task
            task.add_done_callback(_tasks.discard)
    except Exception as exc:  # no running loop, bad settings: the sighting matters more
        _latest.pop(sighting_id, None)
        logger.warning("moment sighting=%s error=%s", sighting_id, describe_error(exc))


async def _record_latest(sighting_id: UUID) -> None:
    """Store the newest look's photo for one stay, then again while a newer look has arrived."""
    try:
        while True:
            look = _latest[sighting_id]
            await record(*look, sighting_id)
            if _latest[sighting_id] is look:
                return
    finally:
        _latest.pop(sighting_id, None)


async def record(frame: Frame, box: Box, crop_url: str, sighting_id: UUID) -> None:
    """Make one look's moment photo (off the event loop: it decodes the whole frame), store it
    beside the tight crop and keep it for the card. The search copy is not touched here:
    `keep_current()` picks the stay up within seconds. Never raises."""
    started = time.perf_counter()
    try:
        async with asyncio.timeout(RECORD_TIMEOUT_S):
            photo = await asyncio.to_thread(moment_photo, frame, box)
            made = time.perf_counter()
            _keep_photo(await db.upload_moment(crop_url, photo), photo)
        logger.info(
            "moment sighting=%s bytes=%d ms[photo=%d upload=%d]",
            sighting_id,
            len(photo),
            round((made - started) * 1000),
            round((time.perf_counter() - made) * 1000),
        )
    except Exception as exc:
        logger.warning("moment sighting=%s error=%s", sighting_id, describe_error(exc))


async def refresh() -> int:
    """Bring the Typesense copy in line with Postgres: index every stay that is new or changed
    since it was last indexed, and drop stays that are gone. Returns how many changed; 0 when
    search is not set up. One stay failing does not stop the others. Raises when Postgres or
    Typesense cannot be reached at all."""
    global _indexed
    if not _configured():
        return 0
    if _indexed is None:
        _indexed = await _load_indexed()
    moments = await db.list_moments()
    changed = 0
    for moment in moments:
        if _indexed.get(moment.id) == _stamp(moment):
            continue
        try:
            await _index(moment)
            changed += 1
        except Exception as exc:  # tried again on the next round
            logger.warning("moment index sighting=%s error=%s", moment.id, describe_error(exc))
    for gone in set(_indexed) - {m.id for m in moments}:
        deleted = await _client(SYNC_TIMEOUT_S).delete(
            f"/collections/{COLLECTION}/documents/{gone}"
        )
        if deleted.status_code != httpx.codes.NOT_FOUND:
            deleted.raise_for_status()
        del _indexed[gone]
        changed += 1
    return changed


async def keep_current(every_s: float = REFRESH_EVERY_S) -> None:
    """Run `refresh()` for as long as the backend lives, so a sighting can be found by
    description within seconds of being stored, whoever stored it. Never raises; after a failure
    (Typesense or Postgres down) it waits six times as long before trying again."""
    while True:
        started = time.perf_counter()
        wait = every_s
        try:
            changed = await refresh()
            if changed:
                ms = round((time.perf_counter() - started) * 1000)
                logger.info("moments refreshed changed=%d ms=%d", changed, ms)
        except Exception as exc:
            logger.warning("moments refresh error=%s", describe_error(exc))
            wait = 6 * every_s
        await asyncio.sleep(wait)


async def sync() -> int:
    """Rebuild the Typesense copy from Postgres from nothing. Safe to run repeatedly. Returns how
    many moments it holds. One Gemini embedding call per stay that has a photo."""
    global _indexed
    client = _client(SYNC_TIMEOUT_S)
    dropped = await client.delete(f"/collections/{COLLECTION}")
    if dropped.status_code != httpx.codes.NOT_FOUND:
        dropped.raise_for_status()
    (await client.post("/collections", json=SCHEMA)).raise_for_status()
    _indexed = {}
    await refresh()
    return len(_indexed)


async def _index(moment: Moment) -> None:
    """Copy one stay into Typesense. The vector is made again only when the stay's photo changed."""
    global _indexed
    if _indexed is None:
        _indexed = await _load_indexed()
    doc = _document(moment)
    known = _indexed.get(moment.id)
    if moment.photo and (known is None or known[2] != moment.photo):
        jpeg = _photos.get(moment.photo) or await db.download_photo(moment.photo)
        doc["embedding"] = await _embed_moment(moment, jpeg)
        action = "upsert"
    else:
        action = "emplace"  # creates it, or updates it and leaves the vector that is there
    await _import([doc], action, _client(SYNC_TIMEOUT_S))
    _indexed[moment.id] = _stamp(moment)


Stamp = tuple[str, int, str, str]


def _stamp(moment: Moment) -> Stamp:
    """What Typesense holds of a stay. When Postgres differs, the stay is indexed again."""
    return (
        moment.status,
        int(moment.last_seen_at.timestamp()),
        moment.photo or "",
        moment.note or "",
    )


class _Stored(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    status: str
    seen_at: int
    photo: str = ""
    note: str = ""


async def _load_indexed() -> dict[UUID, Stamp]:
    """What the collection already holds, so a restarted backend does not embed it all again.
    Creates the collection when it is not there."""
    client = _client(SYNC_TIMEOUT_S)
    exported = await client.get(
        f"/collections/{COLLECTION}/documents/export",
        params={"include_fields": "id,status,seen_at,photo,note"},
    )
    if exported.status_code == httpx.codes.NOT_FOUND:
        (await client.post("/collections", json=SCHEMA)).raise_for_status()
        return {}
    exported.raise_for_status()
    stored = [_Stored.model_validate_json(line) for line in exported.text.splitlines() if line]
    return {doc.id: (doc.status, doc.seen_at, doc.photo, doc.note) for doc in stored}


# ---------------------------------------------------------------------------------------------
# Typesense and Gemini
# ---------------------------------------------------------------------------------------------


class _Doc(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    item: str
    looks: str | None = None


class _Hit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document: _Doc
    vector_distance: float | None = None


class _Result(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hits: list[_Hit] = []


class _Results(BaseModel):
    results: list[_Result]


async def _candidates(description: str) -> list[Candidate]:
    """The closest moment per item for these words, items in Typesense's order (keywords and
    vector fused). [] when search is not set up or fails; without a vector (Gemini failed) the
    candidates carry no distance, and `choose` then picks none: plain names are `ask()`'s job."""
    words = [w for w in re.findall(r"[a-z0-9']+", description.lower()) if w not in FILLER_WORDS]
    if not words or not _configured():
        return []
    settings = get_settings()
    search = {
        **SEARCH_PARAMS,
        "collection": COLLECTION,
        "q": " ".join(words),
        "filter_by": f"home_id:=`{settings.home_id}` && status:!=tentative",
    }
    try:
        vector = await _embed_query(description)
        search["vector_query"] = (
            f"embedding:([{','.join(f'{v:.6f}' for v in vector)}], k:{PER_PAGE}, alpha:{ALPHA})"
        )
    except Exception as exc:
        logger.warning("describe embedding error=%s", describe_error(exc))
    try:
        async with asyncio.timeout(SEARCH_TIMEOUT_S):
            response = await _client(SEARCH_TIMEOUT_S).post(
                "/multi_search", json={"searches": [search]}
            )
        response.raise_for_status()
        hits = _Results.model_validate(response.json()).results[0].hits
    except Exception as exc:
        logger.warning("describe search error=%s", describe_error(exc))
        return []
    best: dict[str, Candidate] = {}
    for hit in hits:
        doc = hit.document
        seen = best.get(doc.item)
        if seen is None or (
            hit.vector_distance is not None and hit.vector_distance < _distance(seen)
        ):
            best[doc.item] = Candidate(
                item=doc.item, looks=doc.looks, sighting_id=doc.id, distance=hit.vector_distance
            )
    return list(best.values())


def _document(moment: Moment) -> dict[str, object]:
    return {
        "id": str(moment.id),
        "home_id": str(get_settings().home_id),
        "item": moment.item,
        "aliases": moment.aliases,
        "looks": moment.looks or "",
        "note": moment.note or "",
        "place": _place(moment),
        "status": moment.status,
        "in_hand": moment.in_hand,
        "seen_at": int(moment.last_seen_at.timestamp()),
        "photo": moment.photo or "",
    }


def _place(moment: Moment) -> str:
    """ "on the table in the classroom", from the spoken names; "" when nothing is known."""
    if moment.in_hand:
        return f"in their hand in {moment.room}" if moment.room else "in their hand"
    relation = {"next_to": "next to", "unknown": "near"}.get(moment.relation, moment.relation)
    parts = [f"{relation} {moment.landmark}" if moment.landmark else "", moment.room or ""]
    return " in ".join(part for part in parts if part)


def caption(moment: Moment) -> str:
    """The words embedded with the photo: what it is, what the camera saw, where."""
    looks = f" ({moment.looks})" if moment.looks else ""
    lines = [f"{moment.item}{looks}", moment.note or "", _place(moment)]
    return ". ".join(line for line in lines if line)


async def _embed_moment(moment: Moment, jpeg: bytes | None) -> list[float]:
    """One vector for the photo and the caption together (no task prefix on multimodal input,
    as Google's embeddings page says)."""
    parts: list[object] = [caption(moment)]
    if jpeg is not None:
        parts.append(types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"))
    return await _embed(parts, SYNC_TIMEOUT_S)


async def _embed_query(description: str) -> list[float]:
    # gemini-embedding-2 takes the task as a prefix in the text, not as `task_type`.
    return await _embed(f"task: search result | query: {description}", EMBED_TIMEOUT_S)


async def _embed(contents: object, timeout_s: float) -> list[float]:
    settings = get_settings()
    async with asyncio.timeout(timeout_s):
        result = await _genai().aio.models.embed_content(
            model=settings.embedding_model,
            contents=contents,  # type: ignore[arg-type]
            config=types.EmbedContentConfig(output_dimensionality=EMBED_DIM),
        )
    if not result.embeddings or not result.embeddings[0].values:
        raise ValueError("Gemini returned no embedding")
    return list(result.embeddings[0].values)


async def _import(docs: list[dict[str, object]], action: str, client: httpx.AsyncClient) -> None:
    imported = await client.post(
        f"/collections/{COLLECTION}/documents/import",
        params={"action": action},
        content="\n".join(json.dumps(doc) for doc in docs),
    )
    imported.raise_for_status()
    failed = [line for line in imported.text.splitlines() if not json.loads(line).get("success")]
    if failed:
        raise RuntimeError(f"Typesense refused {len(failed)} of {len(docs)} moments: {failed[:2]}")


def _configured() -> bool:
    s = get_settings()
    return bool(s.typesense_host and s.typesense_api_key and s.google_api_key)


_photos: OrderedDict[str, bytes] = OrderedDict()  # storage path -> JPEG, newest last
_missing: dict[str, float] = {}  # storage path -> when it was last found missing (monotonic)
_latest: dict[UUID, tuple[Frame, Box, str]] = {}  # stay -> its newest look still to be stored
_tasks: set[asyncio.Task[None]] = set()  # the background photo tasks, one per stay at most
_indexed: dict[UUID, Stamp] | None = None  # what Typesense holds; None until first read from it
_clients: dict[tuple[int, float], httpx.AsyncClient] = {}
_genai_client: tuple[asyncio.AbstractEventLoop, genai.Client] | None = None


def _keep_photo(path: str, jpeg: bytes) -> None:
    _photos[path] = jpeg
    _photos.move_to_end(path)
    while len(_photos) > PHOTO_CACHE:
        _photos.popitem(last=False)


def _client(timeout: float) -> httpx.AsyncClient:
    """One Typesense client per event loop and timeout, so connections are reused."""
    settings = get_settings()
    if not settings.typesense_host or settings.typesense_api_key is None:
        raise RuntimeError("Set TYPESENSE_HOST and TYPESENSE_API_KEY in .env")
    key = (id(asyncio.get_running_loop()), timeout)
    if key not in _clients:
        _clients[key] = httpx.AsyncClient(
            base_url=settings.typesense_host,
            headers={"X-TYPESENSE-API-KEY": settings.typesense_api_key.get_secret_value()},
            timeout=timeout,
        )
    return _clients[key]


def _genai() -> genai.Client:
    """One Gemini client per event loop, with the SDK's own retries off (perception rules)."""
    global _genai_client
    loop = asyncio.get_running_loop()
    if _genai_client is None or _genai_client[0] is not loop:
        key = get_settings().google_api_key
        if key is None:
            raise RuntimeError("Set GOOGLE_API_KEY in .env")
        options = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
        _genai_client = (loop, genai.Client(api_key=key.get_secret_value(), http_options=options))
    return _genai_client[1]
