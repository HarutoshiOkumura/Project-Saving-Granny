"""guide(): one test per step, the voice rules on every sentence, and GET /guide with the
database faked. No network."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app import guide as guide_module
from app.guide import VIEW_FRESH_S, Guidance, guide
from app.main import app
from app.memory import db
from app.memory.schema import FindResult, HomeLayout, Observation
from app.speak import FALLBACK

client = TestClient(app)

NOW = datetime(2026, 11, 15, 6, 0, 0, tzinfo=UTC)


def uid(n: int) -> UUID:
    return UUID(int=n)


BEDROOM, HALLWAY, KITCHEN, ATTIC, GARDEN = uid(1), uid(2), uid(3), uid(4), uid(5)
COUNTER, BED_TABLE = uid(11), uid(12)

LAYOUT = HomeLayout.model_validate(
    {
        "rooms": [
            {"id": BEDROOM, "spoken": "your bedroom", "floor": 1},
            {"id": HALLWAY, "spoken": "the hallway", "floor": 1},
            {"id": KITCHEN, "spoken": "the kitchen", "floor": 1},
            {"id": ATTIC, "spoken": "the attic", "floor": 2},
            {"id": GARDEN, "spoken": "the garden", "floor": None},
        ],
        "landmarks": [
            {"id": COUNTER, "room_id": KITCHEN, "address": "kitchen > counter"},
            {"id": BED_TABLE, "room_id": BEDROOM, "address": "bedroom > nightstand"},
        ],
        # bedroom - hallway - kitchen; the attic hangs off the hallway; the garden is not linked
        "links": [(BEDROOM, HALLWAY), (KITCHEN, HALLWAY), (HALLWAY, ATTIC)],
    }
)


def glasses(**changes: Any) -> FindResult:
    """Glasses on the kitchen counter, forty minutes ago, confident."""
    base: dict[str, Any] = {
        "state": "seen",
        "item": "glasses",
        "plural": True,
        "room": "the kitchen",
        "landmark": "the kitchen counter",
        "relation": "on",
        "address": "kitchen > counter",
        "last_seen_at": NOW - timedelta(minutes=40),
        "timezone": "America/New_York",
        "confident": True,
        "possible_newer_glimpse": False,
    }
    return FindResult.model_validate({**base, **changes})


def view(room: UUID | None, *landmarks: UUID, seconds_ago: float = 3.0) -> Observation:
    return Observation(
        captured_at=NOW - timedelta(seconds=seconds_ago),
        room_id=room,
        landmarks_seen=list(landmarks),
    )


def follows_voice_rules(sentence: str) -> None:
    assert sentence.endswith(".")
    assert sentence.count(".") == 1, f"more than one sentence: {sentence}"
    assert len(sentence.split()) <= 20, f"over 20 words: {sentence}"
    assert sentence[0].isupper()
    lowered = sentence.lower()
    for banned in ("camera", "database", "sighting", "confidence", " ai ", "%", ">", "stairs"):
        assert banned not in lowered, f"{banned!r} in: {sentence}"


# ---------- one test per step ----------


def test_no_view_gives_the_place_as_a_direction() -> None:
    g = guide(glasses(), None, LAYOUT, NOW)

    assert (g.step, g.progress, g.done) == ("no_view", 0, False)
    assert g.sentence == "Look for your glasses on the kitchen counter in the kitchen."
    assert g.wearer_room is None and g.view_age_s is None


def test_a_stale_view_is_no_view() -> None:
    g = guide(glasses(), view(BEDROOM, seconds_ago=VIEW_FRESH_S + 1), LAYOUT, NOW)

    assert g.step == "no_view"
    assert g.wearer_room is None
    assert g.view_age_s == round(VIEW_FRESH_S + 1)


def test_a_view_just_inside_the_limit_still_counts() -> None:
    assert guide(glasses(), view(BEDROOM, seconds_ago=VIEW_FRESH_S), LAYOUT, NOW).step == (
        "go_to_room"
    )


def test_two_rooms_away_names_only_the_next_room() -> None:
    g = guide(glasses(), view(BEDROOM), LAYOUT, NOW)

    assert (g.step, g.progress, g.done) == ("go_to_room", 1, False)
    assert g.sentence == "From your bedroom, walk to the hallway first."
    assert g.key == "go_to_room:your bedroom>the hallway"
    assert g.wearer_room == "your bedroom"
    assert (g.room, g.landmark) == ("the kitchen", "the kitchen counter")


def test_next_door_names_the_room_itself() -> None:
    g = guide(glasses(), view(HALLWAY), LAYOUT, NOW)

    assert g.step == "go_to_room"
    assert g.sentence == "From the hallway, walk to the kitchen, and I'll help you from there."
    assert g.key == "go_to_room:the hallway>the kitchen"


def test_rooms_with_no_link_between_them_still_name_the_target_room() -> None:
    g = guide(glasses(), view(GARDEN), LAYOUT, NOW)

    assert g.sentence == "From the garden, walk to the kitchen, and I'll help you from there."


def test_another_floor_is_said_but_never_walked_to() -> None:
    g = guide(glasses(), view(ATTIC), LAYOUT, NOW)

    assert (g.step, g.progress) == ("other_floor", 1)
    assert g.sentence == "I last saw your glasses in the kitchen, and that is on another floor."
    assert "walk" not in g.sentence


def test_right_room_names_the_landmark_to_look_for() -> None:
    g = guide(glasses(), view(KITCHEN), LAYOUT, NOW)

    assert (g.step, g.progress) == ("look_for", 2)
    assert g.sentence == "You're in the right room, so look for the kitchen counter."


def test_right_room_with_no_landmark() -> None:
    g = guide(glasses(landmark=None, address=None), view(KITCHEN), LAYOUT, NOW)

    assert g.step == "look_for"
    assert g.sentence == "You're in the right room, and I last saw your glasses in here."


def test_landmark_in_view() -> None:
    g = guide(glasses(), view(KITCHEN, COUNTER), LAYOUT, NOW)

    assert (g.step, g.progress, g.done) == ("in_view", 3, False)
    assert g.sentence == (
        "You're close, so look on the kitchen counter in front of you for your glasses."
    )


def test_another_landmark_in_view_is_not_the_one() -> None:
    assert guide(glasses(), view(KITCHEN, BED_TABLE), LAYOUT, NOW).step == "look_for"


def test_item_in_the_newest_frame() -> None:
    newest = view(KITCHEN, COUNTER, seconds_ago=2)
    g = guide(glasses(last_seen_at=newest.captured_at), newest, LAYOUT, NOW)

    assert (g.step, g.progress, g.done) == ("item_in_view", 4, False)
    assert g.sentence == "I can see your glasses on the kitchen counter in front of you."


def test_item_seen_a_moment_before_the_newest_frame_is_not_in_view() -> None:
    newest = view(KITCHEN, COUNTER, seconds_ago=2)
    earlier = newest.captured_at - timedelta(seconds=1)

    assert guide(glasses(last_seen_at=earlier), newest, LAYOUT, NOW).step == "in_view"


def test_in_hand_now_ends_the_guiding() -> None:
    held = glasses(
        state="carried", landmark=None, address=None, last_seen_at=NOW - timedelta(seconds=5)
    )
    g = guide(held, view(KITCHEN), LAYOUT, NOW)

    assert (g.step, g.progress, g.done) == ("in_hand", 5, True)
    assert g.sentence == "You have your glasses in your hand now."


def test_carried_a_while_ago_is_the_plain_answer() -> None:
    held = glasses(
        state="carried", landmark=None, address=None, last_seen_at=NOW - timedelta(minutes=10)
    )
    g = guide(held, view(BEDROOM), LAYOUT, NOW)

    assert (g.step, g.done) == ("none", True)
    assert g.sentence == "You had your glasses in your hand in the kitchen about ten minutes ago."


@pytest.mark.parametrize(
    ("find", "sentence"),
    [
        (
            FindResult(state="never_seen", item="glasses", plural=True),
            "I haven't seen your glasses yet.",
        ),
        (
            glasses(state="not_there_anymore"),
            "Your glasses aren't on the kitchen counter anymore, "
            "and I haven't seen where they went.",
        ),
        (
            FindResult(state="unknown_item", heard="wallet"),
            "I don't know your wallet yet, but your family can teach me.",
        ),
        (glasses(room=None, landmark=None, address=None), FALLBACK),
    ],
)
def test_nowhere_to_guide_to_gives_the_plain_answer_and_stops(
    find: FindResult, sentence: str
) -> None:
    g = guide(find, view(KITCHEN, COUNTER), LAYOUT, NOW)

    assert (g.step, g.progress, g.done) == ("none", 0, True)
    assert g.sentence == sentence
    assert g.key == f"none:{find.state}"


# ---------- honesty and wording ----------


@pytest.mark.parametrize(
    ("observation", "sentence"),
    [
        (None, "I think your glasses are on the kitchen counter in the kitchen."),
        (view(ATTIC), "I think I saw your glasses in the kitchen, and that is on another floor."),
        (
            view(KITCHEN, COUNTER),
            "I think your glasses are on the kitchen counter in front of you.",
        ),
    ],
)
def test_unsure_memory_starts_with_i_think(observation: Observation | None, sentence: str) -> None:
    for unsure in (
        glasses(confident=False),
        glasses(confident=None),
        glasses(possible_newer_glimpse=True),
    ):
        assert guide(unsure, observation, LAYOUT, NOW).sentence == sentence


def test_unsure_memory_hedges_what_it_sees_and_holds() -> None:
    newest = view(KITCHEN, COUNTER)
    seen = glasses(confident=False, last_seen_at=newest.captured_at)
    held = glasses(state="carried", confident=False, last_seen_at=NOW - timedelta(seconds=5))

    assert guide(seen, newest, LAYOUT, NOW).sentence == (
        "I think I can see your glasses on the kitchen counter in front of you."
    )
    assert guide(held, newest, LAYOUT, NOW).sentence == (
        "I think you have your glasses in your hand now."
    )


def test_directions_are_not_hedged_because_they_claim_nothing_about_the_item() -> None:
    unsure = glasses(confident=False)

    assert guide(unsure, view(BEDROOM), LAYOUT, NOW).sentence == (
        "From your bedroom, walk to the hallway first."
    )
    assert guide(unsure, view(KITCHEN), LAYOUT, NOW).sentence == (
        "You're in the right room, so look for the kitchen counter."
    )


def test_singular_items_and_other_relations() -> None:
    watch = glasses(item="watch", plural=False, relation="next_to", confident=False)

    assert guide(watch, None, LAYOUT, NOW).sentence == (
        "I think your watch is next to the kitchen counter in the kitchen."
    )
    assert guide(glasses(relation="unknown"), view(KITCHEN, COUNTER), LAYOUT, NOW).sentence == (
        "You're close, so look near the kitchen counter in front of you for your glasses."
    )


def test_item_in_a_room_on_no_landmark_is_matched_by_the_room_name() -> None:
    loose = glasses(landmark=None, address=None)

    assert guide(loose, view(HALLWAY), LAYOUT, NOW).sentence == (
        "From the hallway, walk to the kitchen, and I'll help you from there."
    )
    assert guide(loose, None, LAYOUT, NOW).sentence == "Look for your glasses in the kitchen."


def test_an_unknown_layout_falls_back_to_the_plain_direction() -> None:
    g = guide(glasses(), view(BEDROOM), HomeLayout(), NOW)

    assert g.step == "no_view"
    assert g.sentence == "Look for your glasses on the kitchen counter in the kitchen."


def test_every_step_follows_the_voice_rules() -> None:
    newest = view(KITCHEN, COUNTER)
    long_names = glasses(
        item="reading glasses",
        landmark="the table beside your bed",
        relation="next_to",
        address="bedroom > nightstand",
        room="your bedroom",
    )
    cases = [
        guide(find, observation, LAYOUT, NOW)
        for find in (glasses(), glasses(confident=False), long_names)
        for observation in (None, view(BEDROOM), view(HALLWAY), view(KITCHEN), view(ATTIC), newest)
    ]
    cases.append(guide(glasses(last_seen_at=newest.captured_at), newest, LAYOUT, NOW))
    cases.append(guide(long_names, view(BEDROOM, BED_TABLE), LAYOUT, NOW))
    cases.append(guide(glasses(state="carried", last_seen_at=NOW), view(KITCHEN), LAYOUT, NOW))

    assert {g.step for g in cases} >= {
        "no_view",
        "go_to_room",
        "other_floor",
        "look_for",
        "in_view",
        "item_in_view",
        "in_hand",
    }
    for g in cases:
        follows_voice_rules(g.sentence)


def test_progress_only_rises_along_the_walk() -> None:
    newest = view(KITCHEN, COUNTER)
    walk = [
        guide(glasses(), None, LAYOUT, NOW),
        guide(glasses(), view(BEDROOM), LAYOUT, NOW),
        guide(glasses(), view(HALLWAY), LAYOUT, NOW),
        guide(glasses(), view(KITCHEN), LAYOUT, NOW),
        guide(glasses(), newest, LAYOUT, NOW),
        guide(glasses(last_seen_at=newest.captured_at), newest, LAYOUT, NOW),
        guide(glasses(state="carried", last_seen_at=NOW), newest, LAYOUT, NOW),
    ]

    assert [g.progress for g in walk] == [0, 1, 1, 2, 3, 4, 5]
    assert len({g.key for g in walk}) == len(walk)  # each step is something new to say


# ---------- GET /guide ----------


@pytest.fixture
def home(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """The database behind /guide, faked: change `find` and `view`, read `asked` and `layouts`."""
    state: dict[str, Any] = {"find": None, "view": None, "asked": [], "layouts": 0}

    async def fake_find_item(query: str) -> FindResult:
        state["asked"].append(query)
        if isinstance(state["find"], Exception):
            raise state["find"]
        return state["find"]

    async def fake_latest_view() -> Observation | None:
        if isinstance(state["view"], Exception):
            raise state["view"]
        return state["view"]

    async def fake_home_layout() -> HomeLayout:
        state["layouts"] += 1
        return LAYOUT

    async def no_ask_item(*args: Any) -> FindResult:
        raise AssertionError("/guide must not log a question")

    monkeypatch.setattr(db, "find_item", fake_find_item)
    monkeypatch.setattr(db, "ask_item", no_ask_item)
    monkeypatch.setattr(db, "latest_view", fake_latest_view)
    monkeypatch.setattr(db, "home_layout", fake_home_layout)
    monkeypatch.setattr(guide_module, "_layout", None)
    return state


def live_find() -> FindResult:
    return glasses(last_seen_at=datetime.now(UTC) - timedelta(minutes=40))


def live_view(room: UUID, *landmarks: UUID) -> Observation:
    return Observation(
        captured_at=datetime.now(UTC) - timedelta(seconds=2),
        room_id=room,
        landmarks_seen=list(landmarks),
    )


def test_route_gives_the_step_for_where_the_wearer_is(home: dict[str, Any]) -> None:
    home["find"], home["view"] = live_find(), live_view(KITCHEN, COUNTER)

    response = client.get("/guide", params={"item": "glasses"})

    assert response.status_code == 200
    body = response.json()
    assert Guidance.model_validate(body).step == "in_view"
    assert body["sentence"] == (
        "You're close, so look on the kitchen counter in front of you for your glasses."
    )
    assert body["wearer_room"] == "the kitchen"
    assert home["asked"] == ["glasses"]


def test_route_reads_the_layout_once_for_many_polls(home: dict[str, Any]) -> None:
    home["find"], home["view"] = live_find(), live_view(BEDROOM)

    for _ in range(3):
        assert client.get("/guide", params={"item": "glasses"}).json()["step"] == "go_to_room"

    assert home["layouts"] == 1


@pytest.mark.parametrize("params", [{}, {"item": ""}, {"item": "x" * 201}])
def test_route_rejects_bad_requests(home: dict[str, Any], params: dict[str, str]) -> None:
    assert client.get("/guide", params=params).status_code == 422
    assert home["asked"] == []


@pytest.mark.parametrize("error", [TimeoutError(), RuntimeError("connection refused")])
def test_route_is_unsure_and_keeps_going_when_the_item_cannot_be_read(
    home: dict[str, Any], caplog: pytest.LogCaptureFixture, error: Exception
) -> None:
    home["find"] = error

    with caplog.at_level(logging.INFO, logger="app.guide"):
        response = client.get("/guide", params={"item": "glasses"})

    assert response.status_code == 200
    body = response.json()
    assert (body["step"], body["done"], body["sentence"]) == ("unsure", False, FALLBACK)
    [record] = [r for r in caplog.records if r.name == "app.guide"]
    assert record.levelno == logging.WARNING
    assert type(error).__name__ in record.getMessage()


def test_route_still_gives_the_place_when_the_view_cannot_be_read(home: dict[str, Any]) -> None:
    home["find"], home["view"] = live_find(), TimeoutError()

    body = client.get("/guide", params={"item": "glasses"}).json()

    assert body["step"] == "no_view"
    assert body["sentence"] == "Look for your glasses on the kitchen counter in the kitchen."


def test_route_logs_one_line_per_poll(
    home: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    home["find"], home["view"] = live_find(), live_view(HALLWAY)

    with caplog.at_level(logging.INFO, logger="app.guide"):
        client.get("/guide", params={"item": "glasses"})

    [record] = [r for r in caplog.records if r.name == "app.guide"]
    line = record.getMessage()
    assert "query='glasses'" in line
    assert "state=seen" in line
    assert "step=go_to_room" in line
    assert "view_age_s=2" in line
    assert " ms=" in line


def test_route_guides_to_the_resolved_name(
    home: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_resolve(spoken: str) -> str:
        return "glasses"

    monkeypatch.setattr(guide_module, "resolve", fake_resolve)
    home["find"] = live_find()

    client.get("/guide", params={"item": "my spectecles"})

    assert home["asked"] == ["glasses"]
