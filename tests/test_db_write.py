"""db's write path with a fake Supabase client: table reads, the observation insert, the crop
upload and the write RPCs. Parameter names must match 0001 exactly. No network."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from postgrest.exceptions import APIError

from app.memory import db

HOME = "11111111-1111-1111-1111-111111111111"
T0 = datetime(2026, 11, 15, 1, 2, 3, 456789, tzinfo=UTC)


def uid(n: int) -> UUID:
    return UUID(int=n)


class Query:
    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client, self.table, self.ops = client, table, []

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> "Query":
            self.ops.append((name, args, kwargs))
            return self

        return record

    async def execute(self) -> SimpleNamespace:
        self.client.queries.append((self.table, self.ops))
        answer = self.client.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return SimpleNamespace(data=answer)


class FakeClient:
    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.queries: list[tuple[str, list[Any]]] = []
        self.uploads: list[tuple[str, str, bytes, dict[str, str]]] = []
        self.storage = SimpleNamespace(from_=self._bucket)

    def table(self, name: str) -> Query:
        return Query(self, name)

    def rpc(self, name: str, params: dict[str, Any]) -> Query:
        query = Query(self, f"rpc:{name}")
        query.ops.append(("params", (params,), {}))
        return query

    def _bucket(self, bucket: str) -> SimpleNamespace:
        async def upload(path: str, data: bytes, options: dict[str, str]) -> None:
            self.uploads.append((bucket, path, data, options))

        return SimpleNamespace(upload=upload)


def use(monkeypatch: pytest.MonkeyPatch, fake: FakeClient) -> FakeClient:
    async def get_client() -> FakeClient:
        return fake

    monkeypatch.setattr(db, "_get_client", get_client)
    return fake


def test_home_map_reads_ids_by_name_and_the_no_capture_rooms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = use(
        monkeypatch,
        FakeClient(
            [
                {"id": str(uid(1)), "name": "b_school_classroom", "capture_allowed": True},
                {"id": str(uid(2)), "name": "bathroom", "capture_allowed": False},
            ],
            [{"landmark_id": str(uid(11)), "room": "b_school_classroom",
              "address": "b_school_classroom > table"}],
            [{"id": str(uid(21)), "name": "glasses"}],
        ),
    )  # fmt: skip

    home = asyncio.run(db.home_map())

    assert home.rooms == {"b_school_classroom": uid(1), "bathroom": uid(2)}
    assert home.no_capture_rooms == {"bathroom"}
    assert home.landmarks == {"b_school_classroom > table": uid(11)}
    assert home.landmark_rooms == {"b_school_classroom > table": "b_school_classroom"}
    assert home.items == {"glasses": uid(21)}
    assert [table for table, _ in fake.queries] == ["rooms", "places", "items"]
    for _, ops in fake.queries:
        assert ("eq", ("home_id", HOME), {}) in ops


def observe(**overrides: Any) -> UUID | None:
    kwargs: dict[str, Any] = {
        "device_id": "lanyard",
        "captured_at": T0.astimezone(timezone(timedelta(hours=-5))),
        "room_id": uid(1),
        "room_conf": 0.95,
        "landmarks_seen": [uid(11), uid(12)],
        "perceived_by": "sam3+gemini-3.6-flash",
        "idempotency_key": "lanyard/2026-11-15T01:02:03.456789+00:00",
    } | overrides
    return asyncio.run(db.insert_observation(**kwargs))


def test_insert_observation_upserts_on_the_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = use(monkeypatch, FakeClient([{"id": str(uid(100))}]))

    assert observe() == uid(100)
    ((table, ops),) = fake.queries
    assert table == "observations"
    ((name, (row,), kwargs),) = ops
    assert name == "upsert"
    assert kwargs == {"on_conflict": "home_id,idempotency_key", "ignore_duplicates": True}
    assert row == {
        "home_id": HOME,
        "device_id": "lanyard",
        "captured_at": "2026-11-15T01:02:03.456789+00:00",  # stored in UTC
        "room_id": str(uid(1)),
        "room_conf": 0.95,
        "landmarks_seen": [str(uid(11)), str(uid(12))],
        "source": "worn_cam",
        "perceived_by": "sam3+gemini-3.6-flash",
        "idempotency_key": "lanyard/2026-11-15T01:02:03.456789+00:00",
    }


def test_insert_observation_returns_none_for_a_frame_already_processed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use(monkeypatch, FakeClient([]))

    assert observe() is None


def test_crop_goes_to_the_private_bucket_under_home_item_and_utc_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = use(monkeypatch, FakeClient())
    local = T0.astimezone(timezone(timedelta(hours=-5)))

    path = asyncio.run(db.upload_crop("water bottle", local, b"\xff\xd8jpeg"))

    key = f"{HOME}/water-bottle/20261115T010203456789Z.jpg"
    assert path == f"crops/{key}"
    assert fake.uploads == [
        ("crops", key, b"\xff\xd8jpeg", {"content-type": "image/jpeg", "upsert": "true"})
    ]


def sight(**overrides: Any) -> UUID | None:
    kwargs: dict[str, Any] = {
        "item_id": uid(22),
        "label": "glasses",
        "room_id": uid(1),
        "landmark_id": uid(12),
        "relation": "on",
        "in_hand": False,
        "seen_at": T0,
        "det_conf": 0.98,
        "room_conf": 0.95,
        "crop_url": "crops/x.jpg",
        "description": "black glasses on the chair",
        "observation_id": uid(100),
    } | overrides
    return asyncio.run(db.log_sighting(**kwargs))


def test_log_sighting_sends_the_contract_parameter_names(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(monkeypatch, FakeClient(str(uid(200))))

    assert sight() == uid(200)
    ((name, ops),) = fake.queries
    assert name == "rpc:log_sighting"
    assert ops[0][1][0] == {
        "p_home": HOME,
        "p_item": str(uid(22)),
        "p_label": "glasses",
        "p_room": str(uid(1)),
        "p_landmark": str(uid(12)),
        "p_relation": "on",
        "p_in_hand": False,
        "p_seen_at": "2026-11-15T01:02:03.456789+00:00",
        "p_det_conf": 0.98,
        "p_room_conf": 0.95,
        "p_crop_url": "crops/x.jpg",
        "p_description": "black glasses on the chair",
        "p_observation": str(uid(100)),
        "p_event": "seen",
        "p_source": "worn_cam",
    }


def test_log_sighting_in_hand_sends_no_landmark(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(monkeypatch, FakeClient(None))

    assert sight(landmark_id=None, in_hand=True) is None  # nothing stored
    params = fake.queries[0][1][0][1][0]
    assert (params["p_landmark"], params["p_in_hand"]) == (None, True)


def test_log_sighting_turns_22023_into_invalid_place(monkeypatch: pytest.MonkeyPatch) -> None:
    error = APIError({"code": "22023", "message": "landmark x is not in home y"})
    use(monkeypatch, FakeClient(error))

    with pytest.raises(db.InvalidPlace, match="not in home"):
        sight()


def test_log_sighting_raises_other_database_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, FakeClient(APIError({"code": "42501", "message": "permission denied"})))

    with pytest.raises(APIError):
        sight()


@pytest.mark.parametrize(("visible", "sent"), [([], []), ([uid(22)], [str(uid(22))])])
def test_mark_absent_always_sends_a_list(
    monkeypatch: pytest.MonkeyPatch, visible: list[UUID], sent: list[str]
) -> None:
    fake = use(monkeypatch, FakeClient(1))

    assert asyncio.run(db.mark_absent(uid(11), T0, visible)) == 1
    assert fake.queries[0][1][0][1][0] == {
        "p_home": HOME,
        "p_landmark": str(uid(11)),
        "p_seen_at": "2026-11-15T01:02:03.456789+00:00",
        "p_visible": sent,
    }


def test_find_item_logs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(monkeypatch, FakeClient({"state": "unknown_item", "heard": "wallet"}))

    assert asyncio.run(db.find_item("wallet")).state == "unknown_item"
    assert fake.queries[0][0] == "rpc:find_item"
    assert fake.queries[0][1][0][1][0] == {"p_home": HOME, "p_query": "wallet"}


def test_the_client_brings_its_own_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without one, supabase-py passes postgrest-py its deprecated `timeout` and `verify`."""
    built: list[Any] = []

    async def fake_create(url: str, key: str, options: Any) -> str:
        built.append(options)
        return "client"

    monkeypatch.setattr(db, "acreate_client", fake_create)
    monkeypatch.setattr(db, "_client", None)

    assert asyncio.run(db._get_client()) == "client"
    (options,) = built
    assert options.httpx_client is not None
    assert options.httpx_client.timeout.read == db.WRITE_TIMEOUT_S
    monkeypatch.setattr(db, "_client", None)


# --- moments: the stays behind the description search and the FaceTime photo --------------------

SIGHTING_ROW = {
    "id": str(uid(31)),
    "status": "active",
    "in_hand": False,
    "relation": "on",
    "description": "silver wristwatch on the table surface",
    "last_seen_at": "2026-11-15T03:26:45.564972+00:00",
    "crop_url": f"crops/{HOME}/watch/20261115T032645564972Z.jpg",
    "items": {"name": "watch", "aliases": ["wristwatch"], "color": "silver",
              "description": "silver wristwatch"},
    "landmarks": {"spoken_name": "the table"},
    "rooms": {"spoken_name": "the classroom"},
}  # fmt: skip


def test_list_moments_reads_stays_with_their_names_and_places(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    told = {**SIGHTING_ROW, "id": str(uid(32)), "crop_url": None, "landmarks": None,
            "description": None}  # fmt: skip
    fake = use(monkeypatch, FakeClient([SIGHTING_ROW, told]))

    watch, bare = asyncio.run(db.list_moments())

    assert watch.id == uid(31) and watch.item == "watch" and watch.aliases == ["wristwatch"]
    assert watch.looks == "silver, silver wristwatch"
    assert watch.note == "silver wristwatch on the table surface"
    assert (watch.landmark, watch.room, watch.relation) == ("the table", "the classroom", "on")
    assert watch.photo == SIGHTING_ROW["crop_url"]
    assert (bare.landmark, bare.note, bare.photo) == (None, None, None)
    [(table, ops)] = fake.queries
    assert table == "sightings"
    assert ("eq", ("home_id", HOME), {}) in ops
    assert ("filter", ("item_id", "not.is", "null"), {}) in ops  # no unowned detections
    assert ("order", ("last_seen_at",), {"desc": True}) in ops
    assert not [op for op in ops if op[0] == "eq" and op[1][0] == "id"]


def test_list_moments_can_read_one_stay(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(monkeypatch, FakeClient([]))

    assert asyncio.run(db.list_moments(uid(31))) == []

    assert ("eq", ("id", str(uid(31))), {}) in fake.queries[0][1]


def test_the_moment_photo_is_stored_beside_its_crop(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(monkeypatch, FakeClient())
    crop_url = f"crops/{HOME}/watch/20261115T032645564972Z.jpg"

    path = asyncio.run(db.upload_moment(crop_url, b"\xff\xd8moment"))

    assert path == f"crops/{HOME}/watch/20261115T032645564972Z.moment.jpg"
    assert fake.uploads == [
        ("crops", f"{HOME}/watch/20261115T032645564972Z.moment.jpg", b"\xff\xd8moment",
         {"content-type": "image/jpeg", "upsert": "true"})
    ]  # fmt: skip


def test_download_photo_gives_the_bytes_or_none_when_there_is_no_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from storage3.exceptions import StorageApiError

    asked: list[tuple[str, str]] = []

    def bucket(name: str) -> SimpleNamespace:
        async def download(key: str) -> bytes:
            asked.append((name, key))
            if key.endswith(".moment.jpg"):
                raise StorageApiError("Object not found", "not_found", 404)
            return b"\xff\xd8crop"

        return SimpleNamespace(download=download)

    fake = use(monkeypatch, FakeClient())
    fake.storage = SimpleNamespace(from_=bucket)

    assert asyncio.run(db.download_photo(f"crops/{HOME}/watch/a.jpg")) == b"\xff\xd8crop"
    assert asyncio.run(db.download_photo(f"crops/{HOME}/watch/a.moment.jpg")) is None
    assert asked == [("crops", f"{HOME}/watch/a.jpg"), ("crops", f"{HOME}/watch/a.moment.jpg")]
