"""app/moments.py with Typesense faked at the HTTP layer and Gemini and the database faked.
No network. The distances in the choose() cases are the ones measured live on 15 Nov."""

import asyncio
import json
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest

from app import moments
from app.ask import Answer
from app.config import get_settings
from app.memory import db
from app.memory.schema import FindResult, Moment
from app.moments import Candidate, choose
from app.perception.frame import Frame, crop, load_frame
from app.photo import read_box
from tests.perception_fakes import FRAMES

HOST = "http://typesense.test:8108"
HOME_ID = "11111111-1111-1111-1111-111111111111"
T0 = datetime(2026, 11, 15, 3, 27, 16, tzinfo=UTC)
WATCH_BOX = (428.0, 465.0, 573.0, 535.0)


def uid(n: int) -> UUID:
    return UUID(int=n)


def moment(n: int, item: str, **overrides: Any) -> Moment:
    fields: dict[str, Any] = {
        "id": uid(n),
        "item": item,
        "aliases": [f"{item} alias"],
        "looks": f"silver, silver {item}",
        "note": f"{item} on the table surface",
        "room": "the classroom",
        "landmark": "the table",
        "relation": "on",
        "status": "active",
        "last_seen_at": T0,
        "photo": f"crops/{HOME_ID}/{item}/20261115T032716000000Z.jpg",
    }
    return Moment.model_validate({**fields, **overrides})


def candidate(item: str, distance: float | None, n: int = 1) -> Candidate:
    return Candidate(item=item, sighting_id=uid(n), distance=distance)


def chosen(*found: tuple[str, float | None]) -> list[str]:
    return [c.item for c in choose([candidate(item, d) for item, d in found])]


# --- choose(): which item a description means -------------------------------------------------


def test_one_clear_fit_is_chosen() -> None:
    # "the silver thing I wear on my wrist"
    assert chosen(("watch", 0.342), ("glasses", 0.451), ("keys", 0.459)) == ["watch"]
    # "what I use to tell the time": further away, still clearly ahead
    assert chosen(("watch", 0.401), ("glasses", 0.442), ("keys", 0.465)) == ["watch"]


def test_the_order_typesense_gave_does_not_matter() -> None:
    assert chosen(("glasses", 0.451), ("watch", 0.342)) == ["watch"]


def test_nothing_is_chosen_for_a_thing_that_is_not_enrolled() -> None:
    assert chosen(("bag", 0.432), ("keys", 0.441), ("glasses", 0.448)) == []  # "my wallet"
    assert chosen(("glasses", 0.442), ("bag", 0.484)) == []  # "my dentures": far, though alone


def test_a_fit_that_barely_beats_a_non_fit_is_a_guess_and_not_chosen() -> None:
    assert chosen(("keys", 0.413), ("glasses", 0.442)) == []  # "the tv remote"
    assert chosen(("water bottle", 0.421), ("glasses", 0.433)) == []  # "what I drink from"


def test_look_alikes_that_fit_equally_are_all_returned_so_the_voice_asks() -> None:
    assert chosen(("green bag", 0.34), ("brown bag", 0.35), ("keys", 0.47)) == [
        "green bag",
        "brown bag",
    ]


def test_candidates_without_a_distance_never_count() -> None:
    assert chosen(("watch", None), ("glasses", None)) == []
    assert chosen() == []


def test_which_one_asks_one_short_question() -> None:
    two = [candidate("green bag", 0.34), candidate("brown bag", 0.35)]
    three = [*two, candidate("glasses", 0.36)]

    assert moments.which_one(two) == "Do you mean your green bag or your brown bag?"
    assert moments.which_one(three) == (
        "Do you mean your green bag, your brown bag or your glasses?"
    )


# --- the words that are indexed ---------------------------------------------------------------


def test_caption_says_what_it_is_what_was_seen_and_where() -> None:
    assert moments.caption(moment(1, "watch")) == (
        "watch (silver, silver watch). watch on the table surface. on the table in the classroom"
    )


def test_place_words_follow_the_relation_and_the_hand() -> None:
    assert moments._place(moment(1, "keys", relation="next_to")) == (
        "next to the table in the classroom"
    )
    assert moments._place(moment(1, "keys", in_hand=True)) == "in their hand in the classroom"
    assert moments._place(moment(1, "keys", landmark=None, relation="unknown")) == "the classroom"
    assert moments._place(moment(1, "keys", landmark=None, room=None)) == ""


# --- Typesense and Gemini, faked --------------------------------------------------------------

Handler = Callable[[httpx.Request], httpx.Response]


class Search:
    """A fake Typesense and a fake embedding call, with what they were asked."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.embedded: list[Any] = []
        self.embed_fails = False
        self.handler: Handler = lambda request: httpx.Response(200, json={"results": [{}]})

    def hits(self, *found: tuple[int, str, float | None]) -> None:
        hits = [
            {"document": {"id": str(uid(n)), "item": item, "looks": f"{item} looks"},
             **({} if d is None else {"vector_distance": d})}
            for n, item, d in found
        ]  # fmt: skip
        self.handler = lambda request: httpx.Response(200, json={"results": [{"hits": hits}]})


@pytest.fixture
def search(monkeypatch: pytest.MonkeyPatch) -> Iterator[Search]:
    monkeypatch.setenv("TYPESENSE_HOST", HOST)
    monkeypatch.setenv("TYPESENSE_API_KEY", "ts_fake")
    monkeypatch.setenv("GOOGLE_API_KEY", "google_fake")
    monkeypatch.setenv("MOMENT_PHOTOS", "true")
    get_settings.cache_clear()
    fake = Search()

    async def answer(request: httpx.Request) -> httpx.Response:
        fake.requests.append(request)
        return fake.handler(request)

    client = httpx.AsyncClient(base_url=HOST, transport=httpx.MockTransport(answer))

    async def embed(contents: Any, timeout_s: float) -> list[float]:
        fake.embedded.append(contents)
        if fake.embed_fails:
            raise TimeoutError
        return [0.25, -0.5, 0.125]

    monkeypatch.setattr(moments, "_client", lambda timeout: client)
    monkeypatch.setattr(moments, "_embed", embed)
    monkeypatch.setattr(moments, "_indexed", None)
    moments._photos.clear()
    yield fake
    get_settings.cache_clear()


def searched(fake: Search) -> dict[str, Any]:
    [request] = [r for r in fake.requests if r.url.path == "/multi_search"]
    [search] = json.loads(request.content)["searches"]
    return search


def test_unconfigured_finds_no_candidates() -> None:
    assert get_settings().typesense_host is None
    assert asyncio.run(moments._candidates("the silver one")) == []


def test_a_description_is_searched_by_keywords_and_by_its_vector(search: Search) -> None:
    search.hits((1, "watch", 0.342), (2, "glasses", 0.451))

    found = asyncio.run(moments._candidates("Where is the silver thing I wear on my wrist?"))

    assert [(c.item, c.sighting_id, c.distance) for c in found] == [
        ("watch", uid(1), 0.342),
        ("glasses", uid(2), 0.451),
    ]
    sent = searched(search)
    assert sent["collection"] == "moments"
    assert sent["q"] == "silver wear on wrist"  # filler words are not sent as keywords
    assert sent["query_by"] == "item,aliases,looks,note,place"
    assert sent["filter_by"] == f"home_id:=`{HOME_ID}` && status:!=tentative"
    assert sent["vector_query"] == "embedding:([0.250000,-0.500000,0.125000], k:12, alpha:0.7)"
    assert sent["exclude_fields"] == "embedding"
    # The whole description is embedded, as a search query (Google's prefix for this model).
    assert search.embedded == [
        "task: search result | query: Where is the silver thing I wear on my wrist?"
    ]


def test_each_item_keeps_its_closest_moment(search: Search) -> None:
    search.hits((1, "watch", 0.40), (2, "glasses", 0.45), (3, "watch", 0.34))

    found = asyncio.run(moments._candidates("the silver one"))

    assert [(c.item, c.sighting_id, c.distance) for c in found] == [
        ("watch", uid(3), 0.34),
        ("glasses", uid(2), 0.45),
    ]


def test_without_a_vector_the_search_runs_on_keywords_and_chooses_nothing(search: Search) -> None:
    search.embed_fails = True
    search.hits((1, "watch", None))

    found = asyncio.run(moments._candidates("the silver one"))

    assert "vector_query" not in searched(search)
    assert [c.distance for c in found] == [None]
    assert choose(found) == []


def test_a_failed_search_finds_no_candidates(search: Search) -> None:
    search.handler = lambda request: httpx.Response(503, text="down")

    assert asyncio.run(moments._candidates("the silver one")) == []


# --- describe() -------------------------------------------------------------------------------


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Fake `ask()`: knows the watch, nothing else."""
    calls: list[tuple[str, str]] = []

    async def ask(query: str, channel: str) -> Answer:
        calls.append((query, channel))
        if query == "watch":
            result = FindResult.model_validate(
                {"state": "seen", "item": "watch", "sighting_id": str(uid(9)), "photo": "crops/x"}
            )
            return Answer(sentence="I last saw your watch on the table just now.", result=result)
        result = FindResult.model_validate({"state": "unknown_item", "heard": query})
        return Answer(sentence="I don't know your wallet yet.", result=result)

    monkeypatch.setattr(moments, "ask", ask)
    return calls


def test_a_description_that_fits_one_item_is_answered_like_find(
    search: Search, asked: list[tuple[str, str]]
) -> None:
    search.hits((1, "watch", 0.342), (2, "glasses", 0.451))

    out = asyncio.run(moments.describe("the silver thing I wear on my wrist", "facetime"))

    assert asked == [("watch", "facetime")]  # the question is logged for the item, once
    assert out.item == "watch"
    assert out.sentence == "I last saw your watch on the table just now."
    assert out.result is not None and out.result.sighting_id == uid(9)
    assert [c.item for c in out.candidates] == ["watch"]


def test_look_alikes_get_a_question_and_no_answer(
    search: Search, asked: list[tuple[str, str]]
) -> None:
    search.hits((1, "green bag", 0.34), (2, "brown bag", 0.35))

    out = asyncio.run(moments.describe("my bag", "facetime"))

    assert asked == []  # nothing is logged until they choose
    assert out.item is None and out.result is None
    assert out.sentence == "Do you mean your green bag or your brown bag?"
    assert [c.item for c in out.candidates] == ["green bag", "brown bag"]


def test_a_description_that_fits_nothing_is_answered_as_find_would(
    search: Search, asked: list[tuple[str, str]]
) -> None:
    search.hits((1, "bag", 0.432), (2, "keys", 0.441))

    out = asyncio.run(moments.describe("my wallet", "facetime"))

    assert asked == [("my wallet", "facetime")]
    assert out.item is None and out.candidates == []
    assert out.sentence == "I don't know your wallet yet."


def test_describe_works_without_search(asked: list[tuple[str, str]]) -> None:
    assert get_settings().typesense_host is None

    out = asyncio.run(moments.describe("watch", "web"))

    assert out.item == "watch"  # a plain name still resolves through ask()
    assert out.sentence == "I last saw your watch on the table just now."


# --- the copy in Typesense --------------------------------------------------------------------


class Copy:
    """A fake `moments` collection: what was imported and deleted."""

    def __init__(self, fake: Search, exported: list[dict[str, Any]] | None) -> None:
        self.imports: list[tuple[str, dict[str, Any]]] = []
        self.deleted: list[str] = []
        self.created = 0
        self.refuse: set[str] = set()

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path.endswith("/documents/export"):
                if exported is None:
                    return httpx.Response(404, json={"message": "Not Found"})
                return httpx.Response(200, text="\n".join(json.dumps(doc) for doc in exported))
            if path == "/collections" and request.method == "POST":
                self.created += 1
                return httpx.Response(201, json={})
            if path.endswith("/documents/import"):
                lines = [json.loads(line) for line in request.content.decode().splitlines()]
                self.imports += [(request.url.params["action"], doc) for doc in lines]
                return httpx.Response(200, text="\n".join('{"success": true}' for _ in lines))
            if request.method == "DELETE":
                self.deleted.append(path.rsplit("/", 1)[-1])
                return httpx.Response(200, json={})
            return httpx.Response(500, text=f"unexpected {request.method} {path}")

        fake.handler = handler


@pytest.fixture
def stays(monkeypatch: pytest.MonkeyPatch) -> list[Moment]:
    """What Postgres holds; `db.list_moments` and `db.download_photo` read from here."""
    rows: list[Moment] = []

    async def list_moments(sighting_id: UUID | None = None, *, limit: int = 500) -> list[Moment]:
        return [m for m in rows if sighting_id is None or m.id == sighting_id]

    async def download_photo(path: str) -> bytes | None:
        return b"\xff\xd8crop of " + path.encode()

    monkeypatch.setattr(db, "list_moments", list_moments)
    monkeypatch.setattr(db, "download_photo", download_photo)
    return rows


def test_refresh_indexes_new_stays_with_a_vector_from_photo_and_words(
    search: Search, stays: list[Moment]
) -> None:
    copy = Copy(search, exported=None)
    stays += [moment(1, "watch"), moment(2, "keys", photo=None, status="tentative")]

    assert asyncio.run(moments.refresh()) == 2

    assert copy.created == 1  # the collection was missing
    (action, watch), (_, keys) = copy.imports
    assert action == "upsert"
    assert watch["id"] == str(uid(1)) and watch["home_id"] == HOME_ID
    assert watch["item"] == "watch" and watch["aliases"] == ["watch alias"]
    assert watch["note"] == "watch on the table surface"
    assert watch["place"] == "on the table in the classroom"
    assert watch["status"] == "active" and watch["seen_at"] == int(T0.timestamp())
    assert watch["embedding"] == [0.25, -0.5, 0.125]
    assert "embedding" not in keys and keys["status"] == "tentative"  # no photo: keywords only
    # One embedding call: the caption first, then the photo, with no task prefix.
    [(text, photo)] = search.embedded
    assert text == moments.caption(stays[0])
    assert photo.inline_data.mime_type == "image/jpeg"
    assert photo.inline_data.data.startswith(b"\xff\xd8crop of crops/")


def test_refresh_leaves_what_is_already_there_and_updates_what_changed(
    search: Search, stays: list[Moment]
) -> None:
    watch, keys = moment(1, "watch"), moment(2, "keys")
    stored = [
        {"id": str(m.id), "status": m.status, "seen_at": int(m.last_seen_at.timestamp()),
         "photo": m.photo, "note": m.note}
        for m in (watch, keys)
    ]  # fmt: skip
    copy = Copy(search, exported=stored)
    stays += [watch, keys.model_copy(update={"status": "superseded"})]

    assert asyncio.run(moments.refresh()) == 1

    assert copy.created == 0 and search.embedded == []  # same photo: the vector stays
    [(action, doc)] = copy.imports
    assert action == "emplace" and doc["id"] == str(uid(2)) and doc["status"] == "superseded"
    assert "embedding" not in doc
    assert asyncio.run(moments.refresh()) == 0  # nothing changed since


def test_refresh_embeds_again_when_the_photo_changed_and_drops_stays_that_are_gone(
    search: Search, stays: list[Moment]
) -> None:
    watch, keys = moment(1, "watch"), moment(2, "keys")
    stored = [
        {"id": str(m.id), "status": m.status, "seen_at": int(m.last_seen_at.timestamp()),
         "photo": m.photo, "note": m.note}
        for m in (watch, keys)
    ]  # fmt: skip
    copy = Copy(search, exported=stored)
    stays.append(watch.model_copy(update={"photo": "crops/home/watch/better.jpg"}))

    assert asyncio.run(moments.refresh()) == 2

    [(action, doc)] = copy.imports
    assert action == "upsert" and doc["photo"] == "crops/home/watch/better.jpg"
    assert doc["embedding"] == [0.25, -0.5, 0.125]
    assert copy.deleted == [str(uid(2))]  # the rehearsal reset removed the keys' stay


def test_one_stay_failing_does_not_stop_the_others(search: Search, stays: list[Moment]) -> None:
    copy = Copy(search, exported=[])
    stays += [moment(1, "watch"), moment(2, "keys", photo=None)]
    search.embed_fails = True  # the watch needs a vector and cannot get one

    assert asyncio.run(moments.refresh()) == 1

    assert [doc["item"] for _, doc in copy.imports] == ["keys"]
    search.embed_fails = False
    assert asyncio.run(moments.refresh()) == 1  # the watch is tried again
    assert [doc["item"] for _, doc in copy.imports] == ["keys", "watch"]


def test_refresh_does_nothing_without_search(stays: list[Moment]) -> None:
    stays.append(moment(1, "watch"))

    assert asyncio.run(moments.refresh()) == 0


# --- record_soon(): the ingest worker's hook ---------------------------------------------------


class Storage:
    """A fake bucket that can be slow: every upload waits for `gate` before it finishes."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.stored: list[tuple[str, bytes]] = []
        self.gate: asyncio.Event | None = None
        self.fails = False

    async def upload_moment(self, crop_url: str, jpeg: bytes) -> str:
        self.started.append(crop_url)
        if self.gate is not None:
            await self.gate.wait()
        if self.fails:
            raise ConnectionError("storage down")
        self.stored.append((crop_url, jpeg))
        return db.moment_path(crop_url)


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> Iterator[Storage]:
    monkeypatch.setenv("MOMENT_PHOTOS", "true")
    get_settings.cache_clear()
    fake = Storage()
    monkeypatch.setattr(db, "upload_moment", fake.upload_moment)
    moments._photos.clear()
    moments._latest.clear()
    yield fake
    get_settings.cache_clear()


def watch_frame() -> Frame:
    return load_frame((FRAMES / "medium_watch_chair_01.jpg").read_bytes())


async def settled() -> None:
    """Wait for the background photo tasks to finish."""
    while moments._tasks:
        await asyncio.gather(*moments._tasks)


def test_the_hook_returns_at_once_and_the_photo_is_stored_in_the_background(
    storage: Storage,
) -> None:
    frame = watch_frame()

    async def look() -> float:
        storage.gate = asyncio.Event()  # the upload cannot finish yet
        started = time.perf_counter()
        moments.record_soon(frame, WATCH_BOX, "crops/home/watch/a.jpg", uid(1))
        took = time.perf_counter() - started
        assert storage.stored == []  # nothing was waited for
        storage.gate.set()
        await settled()
        return took

    took = asyncio.run(look())

    assert took < 0.005  # no image work and no network on the frame's own path
    [(crop_url, photo)] = storage.stored
    assert crop_url == "crops/home/watch/a.jpg"
    assert read_box(photo) is not None  # the wider photo, with the item's place inside it
    assert moments._photos[db.moment_path(crop_url)] == photo  # kept for the card
    assert moments._latest == {} and moments._tasks == set()


def test_on_a_slow_network_only_the_newest_look_of_a_stay_waits_its_turn(
    storage: Storage,
) -> None:
    frame = watch_frame()

    async def looks() -> None:
        storage.gate = asyncio.Event()
        for name in ("a", "b", "c", "d"):  # four frames arrive while the first upload hangs
            moments.record_soon(frame, WATCH_BOX, f"crops/home/watch/{name}.jpg", uid(1))
            await asyncio.sleep(0.05)
        moments.record_soon(frame, WATCH_BOX, "crops/home/keys/k.jpg", uid(2))  # another stay
        await asyncio.sleep(0.05)
        assert storage.started == ["crops/home/watch/a.jpg", "crops/home/keys/k.jpg"]
        storage.gate.set()
        await settled()

    asyncio.run(looks())

    # One upload at a time per stay; b and c were replaced by d before their turn came.
    assert storage.started == [
        "crops/home/watch/a.jpg",
        "crops/home/keys/k.jpg",
        "crops/home/watch/d.jpg",
    ]


def test_the_hook_does_nothing_when_switched_off_or_when_the_look_left_no_crop(
    storage: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = watch_frame()

    async def looks() -> None:
        moments.record_soon(frame, None, "crops/x.jpg", uid(1))  # no box
        moments.record_soon(frame, WATCH_BOX, None, uid(1))  # the crop upload failed
        moments.record_soon(frame, WATCH_BOX, "crops/x.jpg", None)  # nothing was stored
        monkeypatch.setenv("MOMENT_PHOTOS", "false")
        get_settings.cache_clear()
        moments.record_soon(frame, WATCH_BOX, "crops/x.jpg", uid(1))
        await settled()

    asyncio.run(looks())

    assert storage.started == [] and moments._latest == {}


def test_the_hook_never_raises(storage: Storage) -> None:
    frame = watch_frame()
    storage.fails = True

    async def look() -> None:
        moments.record_soon(frame, WATCH_BOX, "crops/x.jpg", uid(1))
        await settled()

    asyncio.run(look())  # a failed upload is a log line
    moments.record_soon(frame, WATCH_BOX, "crops/x.jpg", uid(1))  # no event loop: also a log line

    assert storage.stored == [] and moments._latest == {}


# --- card(): the photo for FaceTime -----------------------------------------------------------

SAFE = (100, 0, 1180, 590)


@pytest.fixture
def stored_photos(monkeypatch: pytest.MonkeyPatch, stays: list[Moment]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    moments._photos.clear()
    moments._missing.clear()

    async def download_photo(path: str) -> bytes | None:
        return files.get(path)

    monkeypatch.setattr(db, "download_photo", download_photo)
    return files


def test_the_card_prefers_the_moment_photo_and_rings_the_item(
    stays: list[Moment], stored_photos: dict[str, bytes]
) -> None:
    from app.photo import moment_photo

    watch = moment(1, "watch")
    stays.append(watch)
    frame = load_frame((FRAMES / "medium_watch_chair_01.jpg").read_bytes())
    assert watch.photo is not None
    stored_photos[watch.photo] = crop(frame, WATCH_BOX)
    stored_photos[db.moment_path(watch.photo)] = moment_photo(frame, WATCH_BOX)

    card = asyncio.run(moments.card(watch.id, 1280, 720, SAFE))

    assert card is not None and card.circle is not None


def test_the_card_falls_back_to_the_tight_crop(
    stays: list[Moment], stored_photos: dict[str, bytes]
) -> None:
    watch = moment(1, "watch")
    stays.append(watch)
    frame = load_frame((FRAMES / "medium_watch_chair_01.jpg").read_bytes())
    assert watch.photo is not None
    stored_photos[watch.photo] = crop(frame, WATCH_BOX)

    card = asyncio.run(moments.card(watch.id, 1280, 720, SAFE))

    assert card is not None and card.circle is None


def test_a_missing_moment_photo_is_not_asked_for_again_at_once(
    stays: list[Moment], stored_photos: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    watch = moment(1, "watch")
    stays.append(watch)
    frame = load_frame((FRAMES / "medium_watch_chair_01.jpg").read_bytes())
    assert watch.photo is not None
    stored_photos[watch.photo] = crop(frame, WATCH_BOX)
    asked: list[str] = []

    async def download_photo(path: str) -> bytes | None:
        asked.append(path)
        return stored_photos.get(path)

    monkeypatch.setattr(db, "download_photo", download_photo)

    assert asyncio.run(moments.card(watch.id, 1280, 720, SAFE)) is not None
    assert asyncio.run(moments.card(watch.id, 1280, 720, SAFE)) is not None

    # The second card needs no download at all: the crop is kept, the missing photo remembered.
    assert asked == [db.moment_path(watch.photo), watch.photo]


def test_no_card_without_a_photo_or_a_stay_or_when_storage_fails(
    stays: list[Moment], stored_photos: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    stays += [moment(1, "watch", photo=None), moment(2, "keys")]

    assert asyncio.run(moments.card(uid(1), 1280, 720, SAFE)) is None  # told, never photographed
    assert asyncio.run(moments.card(uid(2), 1280, 720, SAFE)) is None  # the files are gone
    assert asyncio.run(moments.card(uid(3), 1280, 720, SAFE)) is None  # no such stay

    async def broken(path: str) -> bytes | None:
        raise TimeoutError

    monkeypatch.setattr(db, "download_photo", broken)
    assert asyncio.run(moments.card(uid(2), 1280, 720, SAFE)) is None  # never raises
