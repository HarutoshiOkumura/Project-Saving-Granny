"""speak() against `.claude/rules/voice.md`. Expected sentences are the rule's own examples."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.memory.schema import FindResult
from app.speak import FALLBACK, speak

# Saturday 14 Nov 2026, 16:00 in New York (EST, UTC-5).
NOW = datetime(2026, 11, 14, 21, 0, tzinfo=UTC)
# Saturday 14 Nov 2026, 22:30 in New York.
NOW_LATE = datetime(2026, 11, 15, 3, 30, tzinfo=UTC)

BEDSIDE = {"room": "your bedroom", "landmark": "the table beside your bed", "pct": None}


def result(
    state: str = "seen", minutes: float = 40, now: datetime = NOW, **keys: Any
) -> FindResult:
    """A find_item answer shaped like the database's, for glasses on the kitchen counter."""
    data: dict[str, Any] = {
        "state": state,
        "item": "glasses",
        "plural": True,
        "sighting_id": "5f0c6a52-2d7e-4c5b-9a59-0f3f1d1b8a11",
        "room": "the kitchen",
        "landmark": "the kitchen counter",
        "relation": "on",
        "address": "kitchen > counter",
        "minutes_ago": round(minutes),
        "last_seen_at": now - timedelta(minutes=minutes),
        "timezone": "America/New_York",
        "confident": True,
        "photo": None,
        "previous": None,
        "usual": BEDSIDE,
        "wearer_went_to": None,
        "possible_newer_glimpse": False,
    }
    data.update(keys)
    return FindResult.model_validate(data)


def keys_in_hand(**keys: Any) -> FindResult:
    base: dict[str, Any] = {
        "item": "keys",
        "landmark": None,
        "relation": "unknown",
        "address": None,
        "usual": None,
    }
    return result("carried", minutes=10, **(base | keys))


# ---------- seen ----------


def test_seen() -> None:
    assert (
        speak(result(), NOW)
        == "I last saw your glasses on the kitchen counter about forty minutes ago."
    )


def test_seen_not_confident() -> None:
    assert (
        speak(result(confident=False), NOW)
        == "I think I saw your glasses on the kitchen counter about forty minutes ago."
    )


def test_seen_with_possible_newer_glimpse() -> None:
    assert speak(result(possible_newer_glimpse=True), NOW).startswith("I think I saw your glasses")


def test_missing_confident_is_not_confident() -> None:
    assert speak(result(confident=None), NOW).startswith("I think I saw")


def test_seen_room_only_when_landmark_missing() -> None:
    assert (
        speak(result(landmark=None, address=None), NOW)
        == "I last saw your glasses in the kitchen about forty minutes ago."
    )


@pytest.mark.parametrize(
    ("relation", "words"),
    [
        ("on", "on"),
        ("in", "in"),
        ("under", "under"),
        ("next_to", "next to"),
        ("unknown", "near"),
        (None, "near"),
    ],
)
def test_relation_words(relation: str | None, words: str) -> None:
    assert f"your glasses {words} the kitchen counter" in speak(result(relation=relation), NOW)


@pytest.mark.parametrize(
    "keys",
    [
        {"room": None, "landmark": None},
        {"last_seen_at": None},
        {"item": None},
    ],
)
def test_seen_with_missing_data_falls_back(keys: dict[str, Any]) -> None:
    assert speak(result(**keys), NOW) == FALLBACK


# ---------- carried ----------


def test_carried_then_went_elsewhere() -> None:
    assert (
        speak(keys_in_hand(wearer_went_to="your bedroom"), NOW)
        == "You had your keys in your hand in the kitchen about ten minutes ago, "
        "and then you went to your bedroom."
    )


def test_carried_without_wearer_went_to() -> None:
    assert (
        speak(keys_in_hand(), NOW)
        == "You had your keys in your hand in the kitchen about ten minutes ago."
    )


def test_carried_went_to_same_room_drops_clause() -> None:
    assert (
        speak(keys_in_hand(wearer_went_to="the kitchen"), NOW)
        == "You had your keys in your hand in the kitchen about ten minutes ago."
    )


def test_carried_without_room() -> None:
    assert (
        speak(keys_in_hand(room=None), NOW)
        == "You had your keys in your hand about ten minutes ago."
    )


def test_carried_not_confident() -> None:
    assert speak(keys_in_hand(confident=False), NOW).startswith("I think you had your keys")


# ---------- not_there_anymore ----------


def test_not_there_anymore_with_usual() -> None:
    assert (
        speak(result("not_there_anymore"), NOW)
        == "Your glasses aren't on the kitchen counter anymore, "
        "but they usually live on the table beside your bed."
    )


def test_not_there_anymore_singular() -> None:
    assert (
        speak(result("not_there_anymore", item="bag", plural=False), NOW)
        == "Your bag isn't on the kitchen counter anymore, "
        "but it usually lives on the table beside your bed."
    )


def test_not_there_anymore_without_usual() -> None:
    assert (
        speak(result("not_there_anymore", usual=None), NOW)
        == "Your glasses aren't on the kitchen counter anymore, and I haven't seen where they went."
    )


def test_not_there_anymore_without_usual_singular() -> None:
    assert (
        speak(result("not_there_anymore", item="bag", plural=False, usual=None), NOW)
        == "Your bag isn't on the kitchen counter anymore, and I haven't seen where it went."
    )


def test_never_offers_the_ruled_out_place_as_usual() -> None:
    counter = {"room": "the kitchen", "landmark": "the kitchen counter", "pct": 80}
    assert (
        speak(result("not_there_anymore", usual=counter), NOW)
        == "Your glasses aren't on the kitchen counter anymore, and I haven't seen where they went."
    )


def test_room_only_ruled_out_skips_usual_in_that_room() -> None:
    table = {"room": "the kitchen", "landmark": "the kitchen table", "pct": None}
    assert (
        speak(result("not_there_anymore", landmark=None, usual=table), NOW)
        == "Your glasses aren't in the kitchen anymore, and I haven't seen where they went."
    )


def test_not_there_anymore_with_possible_newer_glimpse() -> None:
    assert speak(result("not_there_anymore", possible_newer_glimpse=True), NOW).startswith(
        "I think your glasses aren't on the kitchen counter anymore"
    )


def test_not_there_anymore_without_place_falls_back() -> None:
    assert speak(result("not_there_anymore", room=None, landmark=None), NOW) == FALLBACK


# ---------- never_seen ----------


def never_seen(**keys: Any) -> FindResult:
    base: dict[str, Any] = {
        "state": "never_seen",
        "item": "glasses",
        "plural": True,
        "usual": BEDSIDE,
        "timezone": "America/New_York",
        "possible_glimpse": False,
    }
    return FindResult.model_validate(base | keys)


def test_never_seen_with_usual() -> None:
    assert (
        speak(never_seen(), NOW)
        == "I haven't seen your glasses yet, but they usually live on the table beside your bed."
    )


def test_never_seen_without_usual() -> None:
    assert (
        speak(never_seen(usual=None), NOW)
        == "I haven't seen your glasses yet, so let me check with your family."
    )


def test_never_seen_singular() -> None:
    dresser = {"room": "your bedroom", "landmark": "the dresser", "pct": 60}
    assert (
        speak(never_seen(item="bag", plural=False, usual=dresser), NOW)
        == "I haven't seen your bag yet, but it usually lives on the dresser."
    )


def test_never_seen_usual_room_only() -> None:
    bedroom = {"room": "your bedroom", "landmark": None, "pct": None}
    assert (
        speak(never_seen(usual=bedroom), NOW)
        == "I haven't seen your glasses yet, but they usually live in your bedroom."
    )


# ---------- unknown_item ----------


def test_unknown_item_names_the_thing_heard() -> None:
    answer = FindResult.model_validate({"state": "unknown_item", "heard": "my wallet"})
    assert speak(answer, NOW) == "I don't know your wallet yet, but your family can teach me."


@pytest.mark.parametrize(
    ("heard", "sentence"),
    [
        ("where is my phone", "I don't know your phone yet, but your family can teach me."),
        ("reading lamp", "I don't know your reading lamp yet, but your family can teach me."),
        ("the thing", "I'm sorry, which thing are you looking for?"),
        ("um", "I'm sorry, which thing are you looking for?"),
        (
            "the thing my daughter gave me for christmas",
            "I'm sorry, which thing are you looking for?",
        ),
        (None, "I'm sorry, which thing are you looking for?"),
    ],
)
def test_unknown_item_asks_when_the_thing_is_unclear(heard: str | None, sentence: str) -> None:
    answer = FindResult.model_validate({"state": "unknown_item", "heard": heard})
    assert speak(answer, NOW) == sentence


# ---------- time words ----------


@pytest.mark.parametrize(
    ("minutes", "words"),
    [
        (-3, "just now"),  # clock skew: a frame stamped slightly ahead
        (0, "just now"),
        (1.99, "just now"),
        (2, "a few minutes ago"),
        (9.99, "a few minutes ago"),
        (10, "about ten minutes ago"),
        (12, "about ten minutes ago"),
        (13, "about fifteen minutes ago"),
        (40, "about forty minutes ago"),
        (57, "about fifty-five minutes ago"),
        (59.99, "about fifty-five minutes ago"),
        (60, "about an hour ago"),
        (89.99, "about an hour ago"),
        (90, "about two hours ago"),
        (149, "about two hours ago"),
        (150, "about three hours ago"),
        (240, "about four hours ago"),
        (300, "about five hours ago"),
        (301, "this morning"),  # 10:59 in New York
    ],
)
def test_time_bands_by_elapsed(minutes: float, words: str) -> None:
    assert speak(result(minutes=minutes), NOW).endswith(f" {words}.")


def at(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


@pytest.mark.parametrize(
    ("seen_at", "now", "words"),
    [
        (at(2026, 11, 14, 14), NOW, "this morning"),  # Sat 09:00 New York
        (at(2026, 11, 14, 17), NOW_LATE, "this afternoon"),  # Sat 12:00
        (at(2026, 11, 14, 22), NOW_LATE, "this afternoon"),  # Sat 17:00 exactly
        (at(2026, 11, 14, 22, 1), NOW_LATE, "this evening"),  # Sat 17:01
        (at(2026, 11, 13, 14), NOW, "yesterday morning"),  # Fri 09:00
        (at(2026, 11, 13, 19), NOW, "yesterday afternoon"),  # Fri 14:00
        (at(2026, 11, 14, 1), NOW, "yesterday evening"),  # Fri 20:00; already Saturday in UTC
        (at(2026, 11, 10, 15), NOW, "on Tuesday"),  # 4 days
        (at(2026, 11, 8, 15), NOW, "on Sunday"),  # 6 days
        (at(2026, 11, 7, 15), NOW, "a while ago"),  # 7 days
    ],
)
def test_time_bands_by_calendar(seen_at: datetime, now: datetime, words: str) -> None:
    assert speak(result(last_seen_at=seen_at), now).endswith(f" {words}.")


def test_calendar_band_needs_timezone() -> None:
    assert speak(result(minutes=600, timezone=None), NOW) == FALLBACK


def test_short_band_does_not_need_timezone() -> None:
    assert speak(result(timezone=None), NOW).endswith(" about forty minutes ago.")
