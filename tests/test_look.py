"""where_to_look(): ranked places with chances, one test per answer state and per clue."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from app.look import WhereToLook, where_to_look
from app.memory.schema import FindResult, Glimpse, Item, LookEvidence, PlaceName, UsualPlace

NOW = datetime(2026, 11, 15, 6, 0, tzinfo=UTC)
GLASSES = UUID("00000000-0000-0000-0000-000000000001")
KEYS = UUID("00000000-0000-0000-0000-000000000002")
TABLE = UUID("00000000-0000-0000-0000-00000000000a")
CHAIR = UUID("00000000-0000-0000-0000-00000000000b")
FLOOR = UUID("00000000-0000-0000-0000-00000000000c")
SHELF = UUID("00000000-0000-0000-0000-00000000000d")  # in the hallway


def place(landmark_id: UUID, landmark: str, room: str = "classroom") -> PlaceName:
    return PlaceName(
        landmark_id=landmark_id,
        address=f"{room} > {landmark}",
        room_spoken=f"the {room}",
        landmark_spoken=f"the {landmark}",
    )


PLACES = [
    place(TABLE, "table"),
    place(CHAIR, "chair"),
    place(FLOOR, "floor"),
    place(SHELF, "shelf", "hallway"),
]


def glasses(home: UUID | None = None) -> Item:
    return Item(id=GLASSES, name="glasses", home_landmark_id=home)


def ago(minutes: float) -> datetime:
    return NOW - timedelta(minutes=minutes)


def answer(state: str, **keys: Any) -> FindResult:
    return FindResult.model_validate({"state": state, "item": "glasses", **keys})


def seen_on(landmark: str, minutes: float, confident: bool = True, **keys: Any) -> FindResult:
    return answer(
        "seen",
        address=f"classroom > {landmark}",
        room="the classroom",
        landmark=f"the {landmark}",
        last_seen_at=ago(minutes).isoformat(),
        minutes_ago=round(minutes),
        confident=confident,
        **keys,
    )


def evidence(
    usual: Sequence[tuple[UUID, int]] = (),
    glimpses: Sequence[tuple[UUID, float]] = (),
    item: UUID = GLASSES,
) -> LookEvidence:
    return LookEvidence(
        places=PLACES,
        usual=[
            UsualPlace(item_id=item, landmark_id=lm, episodes=n, last_seen_at=ago(600))
            for lm, n in usual
        ],
        glimpses=[Glimpse(item_id=item, landmark_id=lm, last_seen_at=ago(m)) for lm, m in glimpses],
    )


def ranked(look: WhereToLook | None) -> list[tuple[str, int]]:
    assert look is not None
    return [(p.landmark, p.pct) for p in look.places]


def test_no_ranking_for_an_unknown_item_or_a_failed_answer() -> None:
    unknown = FindResult(state="unknown_item", heard="wallet")
    assert where_to_look(glasses(), unknown, evidence(), NOW) is None
    assert where_to_look(glasses(), None, evidence(), NOW) is None


def test_seen_just_now_is_high_and_the_only_place() -> None:
    look = where_to_look(glasses(), seen_on("table", 1), evidence(), NOW)
    assert look.band == "high"
    assert ranked(look) == [("the table", 89)]
    assert look.elsewhere_pct == 11
    assert look.places[0].why == ["last_seen"]
    assert look.places[0].minutes_ago == 1
    assert look.places[0].address == "classroom > table"
    assert look.ruled_out is None


def test_pcts_always_add_up_to_100() -> None:
    look = where_to_look(
        glasses(home=FLOOR),
        seen_on("table", 90, confident=False),
        evidence(usual=[(TABLE, 1), (CHAIR, 3)], glimpses=[(CHAIR, 5), (SHELF, 30)]),
        NOW,
    )
    assert sum(p.pct for p in look.places) + look.elsewhere_pct == 100
    assert [p.pct for p in look.places] == sorted((p.pct for p in look.places), reverse=True)


def test_a_newer_glimpse_elsewhere_is_the_second_place() -> None:
    """The judge's example: "the table 70%, the chair 30%". Two sure frames still lead one."""
    look = where_to_look(glasses(), seen_on("table", 30), evidence(glimpses=[(CHAIR, 1)]), NOW)
    assert ranked(look) == [("the table", 67), ("the chair", 25)]
    assert look.band == "high"
    assert look.places[1].why == ["glimpse"]
    assert look.places[1].minutes_ago == 1


def test_a_newer_glimpse_against_an_unsure_sighting_is_a_split() -> None:
    unsure = seen_on("table", 30, confident=False)
    look = where_to_look(glasses(), unsure, evidence(glimpses=[(CHAIR, 1)]), NOW)
    assert ranked(look) == [("the chair", 43), ("the table", 43)]
    assert look.band == "split"


def test_a_glimpse_older_than_the_answer_does_not_count() -> None:
    look = where_to_look(glasses(), seen_on("table", 30), evidence(glimpses=[(CHAIR, 45)]), NOW)
    assert ranked(look) == [("the table", 89)]


def test_glimpses_fade_within_hours() -> None:
    fresh = where_to_look(glasses(), seen_on("table", 600), evidence(glimpses=[(CHAIR, 5)]), NOW)
    stale = where_to_look(glasses(), seen_on("table", 600), evidence(glimpses=[(CHAIR, 300)]), NOW)
    assert fresh.places[1].pct > stale.places[1].pct


def test_an_unsure_sighting_weighs_less_than_a_sure_one() -> None:
    sure = where_to_look(glasses(), seen_on("table", 10), evidence(), NOW)
    unsure = where_to_look(glasses(), seen_on("table", 10, confident=False), evidence(), NOW)
    assert ranked(unsure) == [("the table", 75)]
    assert unsure.places[0].pct < sure.places[0].pct


def test_the_last_place_fades_over_days_but_never_below_a_quarter() -> None:
    day = where_to_look(glasses(), seen_on("table", 24 * 60), evidence(), NOW)
    week = where_to_look(glasses(), seen_on("table", 7 * 24 * 60), evidence(), NOW)
    assert ranked(day) == [("the table", 80)]
    assert ranked(week) == [("the table", 67)]  # 8 x 0.25 = 2 against 1 elsewhere


def test_not_there_anymore_never_offers_the_ruled_out_place() -> None:
    gone = answer(
        "not_there_anymore",
        address="classroom > table",
        room="the classroom",
        landmark="the table",
        last_seen_at=ago(60).isoformat(),
        confident=True,
    )
    look = where_to_look(glasses(home=TABLE), gone, evidence(usual=[(TABLE, 5), (CHAIR, 3)]), NOW)
    assert look.ruled_out.landmark == "the table"
    assert look.ruled_out.room == "the classroom"
    assert ranked(look) == [("the chair", 64)]  # its 5 stays on the table no longer count
    assert look.places[0].why == ["usual"]


def test_a_glimpse_after_the_place_was_ruled_out_brings_it_back() -> None:
    gone = answer(
        "not_there_anymore", address="classroom > table", last_seen_at=ago(60).isoformat()
    )
    look = where_to_look(glasses(), gone, evidence(glimpses=[(TABLE, 2)]), NOW)
    assert [(p.landmark, p.why) for p in look.places] == [("the table", ["glimpse"])]


def test_never_seen_ranks_habits_and_the_home_place() -> None:
    never = answer("never_seen", plural=True)
    look = where_to_look(
        glasses(home=FLOOR),
        never,
        evidence(usual=[(CHAIR, 4), (TABLE, 1)], glimpses=[(SHELF, 240)]),
        NOW,
    )
    assert [(p.landmark, p.why) for p in look.places] == [
        ("the chair", ["usual"]),
        ("the floor", ["home"]),
        ("the shelf", ["glimpse"]),  # never seen: any glimpse in the window counts
        ("the table", []),  # one settled stay is a clue, not a habit
    ]
    assert ranked(look) == [
        ("the chair", 32),
        ("the floor", 28),
        ("the shelf", 14),
        ("the table", 8),
    ]
    assert look.elsewhere_pct == 18
    assert look.places[1].minutes_ago is None  # the family's say, not a sighting


def test_never_seen_with_no_clue_has_no_place() -> None:
    look = where_to_look(glasses(), answer("never_seen"), evidence(), NOW)
    assert look.places == []
    assert look.elsewhere_pct == 100
    assert look.band == "low"


def test_carried_favours_places_in_the_room_the_wearer_went_to() -> None:
    held = answer(
        "carried",
        room="the classroom",
        last_seen_at=ago(20).isoformat(),
        wearer_went_to="the hallway",
    )
    look = where_to_look(glasses(), held, evidence(usual=[(TABLE, 2), (SHELF, 2)]), NOW)
    assert ranked(look) == [("the shelf", 43), ("the table", 29)]


def test_other_items_clues_are_ignored() -> None:
    look = where_to_look(
        glasses(),
        seen_on("table", 1),
        evidence(usual=[(CHAIR, 9)], glimpses=[(CHAIR, 1)], item=KEYS),
        NOW,
    )
    assert ranked(look) == [("the table", 89)]


def test_a_place_not_in_this_home_is_skipped() -> None:
    stray = UUID("00000000-0000-0000-0000-0000000000ff")
    look = where_to_look(glasses(home=stray), seen_on("table", 1), evidence(), NOW)
    assert ranked(look) == [("the table", 89)]


def test_at_most_four_places_and_tiny_ones_go_to_elsewhere() -> None:
    lots = [place(UUID(int=100 + i), f"spot {i}") for i in range(8)]
    ev = LookEvidence(
        places=lots,
        usual=[
            UsualPlace(item_id=GLASSES, landmark_id=p.landmark_id, episodes=1, last_seen_at=ago(9))
            for p in lots
        ],
    )
    look = where_to_look(glasses(), answer("never_seen"), ev, NOW)
    assert len(look.places) == 4
    assert sum(p.pct for p in look.places) + look.elsewhere_pct == 100
    assert look.elsewhere_pct > look.places[0].pct


@pytest.mark.parametrize("minutes", [0, 0.2])
def test_a_clue_from_the_future_counts_as_now(minutes: float) -> None:
    look = where_to_look(glasses(), seen_on("table", -minutes), evidence(), NOW)
    assert look.places[0].minutes_ago == 0
