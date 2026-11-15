"""Change from usual (docs/INSIGHTS.md design 2): daily facts, the two tracks, and the wording.

All rows are built in memory: no database, no sample home."""

import re
from datetime import UTC, date, datetime, timedelta
from itertools import product
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.concerns import quiet_day
from app.memory.schema import (
    HomeInfo,
    Item,
    LifeEvent,
    PatternRows,
    PlaceName,
    QuestionRow,
    StayRow,
    WearDay,
    WearHour,
)
from app.patterns import ADVICE, BANNED, NOTE, _say, summarize

NY = ZoneInfo("America/New_York")
TODAY = date(2026, 11, 15)
GLASSES = UUID("00000000-0000-0000-0000-000000000001")
TABLE = UUID("00000000-0000-0000-0000-00000000000a")
FRIDGE = UUID("00000000-0000-0000-0000-00000000000f")
SURE = UUID("00000000-0000-0000-0000-0000000000aa")
UNSURE = UUID("00000000-0000-0000-0000-0000000000bb")


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=NY)


def rows(
    questions_per_day: dict[date, int] | None = None,
    worn_hours: dict[date, float] | None = None,
    questions: list[QuestionRow] = (),  # type: ignore[assignment]
    put_downs: list[StayRow] = (),  # type: ignore[assignment]
    events: list[LifeEvent] = (),  # type: ignore[assignment]
) -> PatternRows:
    qs = list(questions)
    for day, n in (questions_per_day or {}).items():
        qs += [
            QuestionRow(
                asked_at=at(day, 9 + i // 2, 30 * (i % 2)),
                channel="facetime",
                item_id=GLASSES,
                state="never_seen",
            )
            for i in range(n)
        ]
    return PatternRows(
        home=HomeInfo(person_name="Rose", timezone="America/New_York"),
        items=[Item(id=GLASSES, name="glasses", home_landmark_id=TABLE)],
        places=[
            PlaceName(
                landmark_id=TABLE,
                address="kitchen > table",
                room_spoken="the kitchen",
                landmark_spoken="the table",
            ),
            PlaceName(
                landmark_id=FRIDGE,
                address="kitchen > fridge",
                room_spoken="the kitchen",
                landmark_spoken="the fridge",
            ),
        ],
        wear=[WearDay(day=d, worn_minutes=round(h * 60)) for d, h in (worn_hours or {}).items()],
        events=list(events),
        questions=qs,
        answered_by=[
            StayRow(
                id=SURE,
                item_id=GLASSES,
                landmark_id=TABLE,
                first_seen_at=at(TODAY, 8),
                det_conf=0.9,
                room_conf=0.9,
                id_conf=0.9,
            ),
            StayRow(
                id=UNSURE,
                item_id=GLASSES,
                landmark_id=TABLE,
                first_seen_at=at(TODAY, 8),
                det_conf=0.4,
                room_conf=0.9,
                id_conf=0.9,
            ),
        ],
        put_downs=list(put_downs),
    )


def steady(days: int, per_day: int = 3, hours: float = 6.0) -> tuple[dict, dict]:
    """`days` complete days before today, each with the same questions and wear."""
    span = [TODAY - timedelta(days=n) for n in range(1, days + 1)]
    return {d: per_day for d in span}, {d: hours for d in span}


# ---------------------------------------------------------------------------------------------
# Daily facts
# ---------------------------------------------------------------------------------------------


def test_daily_facts_count_only_the_wearers_questions_and_outcomes() -> None:
    day = TODAY - timedelta(days=1)
    qs = [
        QuestionRow(
            asked_at=at(day, 10),
            channel="facetime",
            item_id=GLASSES,
            state="seen",
            sighting_id=SURE,
            outcome="found",
        ),
        QuestionRow(
            asked_at=at(day, 10, 5),
            channel="facetime",
            item_id=GLASSES,
            state="seen",
            sighting_id=SURE,
            outcome="not_found",
        ),  # asked again 5 min after a sure answer
        QuestionRow(
            asked_at=at(day, 11),
            channel="facetime",
            item_id=GLASSES,
            state="seen",
            sighting_id=UNSURE,
        ),
        QuestionRow(asked_at=at(day, 11, 3), channel="facetime", item_id=GLASSES, state="seen"),
        QuestionRow(asked_at=at(day, 12), channel="web", item_id=GLASSES, state="seen"),  # family
    ]
    summary = summarize(rows(questions=qs, worn_hours={day: 2.5}), TODAY, days=7)
    facts = summary.days[-2]
    assert facts.day == day
    assert facts.questions == 4
    assert facts.asked_again == 1  # the 11:03 one followed an unsure answer: not counted
    assert (facts.found, facts.not_found) == (1, 1)
    assert facts.worn_hours == 2.5
    assert summary.days[-1].day == TODAY


def test_local_days_follow_the_homes_timezone() -> None:
    late = datetime(2026, 11, 15, 3, 30, tzinfo=UTC)  # 22:30 on the 14th in New York
    qs = [QuestionRow(asked_at=late, channel="facetime", item_id=GLASSES, state="never_seen")]
    summary = summarize(rows(questions=qs), TODAY, days=3)
    assert [d.questions for d in summary.days] == [0, 1, 0]


def test_put_downs_at_its_place_and_an_odd_place() -> None:
    history = [
        StayRow(
            id=uuid4(),
            item_id=GLASSES,
            landmark_id=TABLE,
            first_seen_at=at(TODAY - timedelta(days=26 - n), 9),
            det_conf=0.9,
        )
        for n in range(25)
    ]
    fridge = StayRow(
        id=uuid4(),
        item_id=GLASSES,
        landmark_id=FRIDGE,
        first_seen_at=at(TODAY - timedelta(days=1), 15),
        det_conf=0.9,
    )
    unsure = StayRow(
        id=uuid4(),
        item_id=GLASSES,
        landmark_id=FRIDGE,
        first_seen_at=at(TODAY - timedelta(days=1), 16),
        det_conf=0.3,
    )
    summary = summarize(rows(put_downs=[*history, fridge, unsure]), TODAY, days=14)
    yesterday = summary.days[-2]
    assert yesterday.put_downs == 2
    assert yesterday.odd_places == 1  # the unsure one could be a recognition error
    assert summary.odd_places[0].item == "glasses"
    assert summary.odd_places[0].landmark == "the fridge"
    assert summary.odd_places[0].at.hour == 15
    assert sum(d.at_its_place for d in summary.days) == 12  # table stays 13 to 2 days ago


def test_tags_cover_every_day_they_span() -> None:
    away = LifeEvent(
        id=uuid4(),
        kind="away",
        starts_at=at(TODAY - timedelta(days=3), 9),
        ends_at=at(TODAY - timedelta(days=2), 18),
    )
    summary = summarize(rows(events=[away]), TODAY, days=5)
    assert [d.tags for d in summary.days] == [[], ["away"], ["away"], [], []]


# ---------------------------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------------------------


def test_nothing_is_called_a_change_while_learning_the_routine() -> None:
    q, w = steady(20)
    q[TODAY - timedelta(days=1)] = 30
    summary = summarize(rows(q, w), TODAY)
    assert summary.status == "learning"
    assert summary.days_with_data == 20
    assert summary.changes == []
    assert summary.advice is None
    assert summary.usual.questions_per_day is not None


def test_a_sudden_burst_of_questions_is_a_change_from_yesterday() -> None:
    q, w = steady(40)
    yesterday = TODAY - timedelta(days=1)
    q[yesterday] = 12
    summary = summarize(rows(q, w), TODAY)
    assert summary.status == "ready"
    [change] = summary.changes
    assert (change.track, change.signal, change.direction) == ("sudden", "questions", "up")
    assert change.since == yesterday
    assert change.sentence == "Rose asked Find It about 4 times as often as usual since Saturday."
    assert summary.advice == ADVICE
    assert summary.usual.questions_per_10_worn_hours == 5.54  # (27 x 3 + 12) / 168 h x 10


def test_a_quiet_withdrawn_stretch_counts_too() -> None:
    """Less wear and fewer questions, two days running: the hypoactive pattern."""
    q, w = steady(40, per_day=8)
    for n in (1, 2):
        q[TODAY - timedelta(days=n)] = 0
        w[TODAY - timedelta(days=n)] = 1.0
    summary = summarize(rows(q, w), TODAY)
    found = {(c.signal, c.direction): c for c in summary.changes}
    assert set(found) == {("questions", "down"), ("wear", "down")}
    assert found[("wear", "down")].since == TODAY - timedelta(days=2)
    assert found[("wear", "down")].sentence == (
        "The camera was worn much less than usual since Friday."
    )


def test_one_ordinary_odd_day_is_not_a_change() -> None:
    q, w = steady(40, per_day=8)
    q[TODAY - timedelta(days=1)] = 2  # fewer questions, wear as usual: one signal, not huge
    assert summarize(rows(q, w), TODAY).changes == []


def test_tagged_days_are_never_called_a_change() -> None:
    q, w = steady(40)
    yesterday = TODAY - timedelta(days=1)
    q[yesterday] = 12
    hospital = LifeEvent(id=uuid4(), kind="hospital", starts_at=at(yesterday, 8))
    assert summarize(rows(q, w, events=[hospital]), TODAY).changes == []


def test_three_weeks_above_usual_is_a_slow_change() -> None:
    q, w = steady(77, per_day=2)
    for n in range(1, 22):
        q[TODAY - timedelta(days=n)] = 5
    summary = summarize(rows(q, w), TODAY, days=84)
    slow = [c for c in summary.changes if c.track == "slow"]
    assert [(c.signal, c.direction) for c in slow] == [("questions", "up")]
    assert slow[0].since == TODAY - timedelta(days=21)
    assert slow[0].sentence == "For three weeks in a row, Rose asked Find It more than usual."


# ---------------------------------------------------------------------------------------------
# Wording: no disease words, no scores, no orders
# ---------------------------------------------------------------------------------------------


def test_no_sentence_names_a_disease_or_gives_a_score() -> None:
    sentences = [NOTE.format(person="Rose"), ADVICE]
    for track, signal, direction in product(
        ("sudden", "slow"), ("questions", "asked_again", "wear", "found"), ("up", "down")
    ):
        for since in (TODAY - timedelta(days=1), TODAY - timedelta(days=30)):
            said = _say(track, signal, direction, since, TODAY, "Rose", 3.2)  # type: ignore[arg-type]
            if said:
                sentences.append(said)
    hours = [WearHour(day=TODAY - timedelta(days=n), hour=9, worn_minutes=60) for n in range(1, 9)]
    sentences.append(quiet_day(hours, TODAY, 15, 0, "Rose") or "")
    assert len(sentences) > 10
    for sentence in sentences:
        words = sentence.lower()
        assert not [b for b in BANNED if b in words], sentence
        assert "%" not in sentence and not re.search(r"\bpoints?\b", words), sentence
