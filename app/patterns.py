"""Change from usual (docs/INSIGHTS.md design 2): daily facts from the memory log, compared only
with the person's own history, in plain sentences for the family. Pure: rows in, summary out.

It never names a disease, scores anyone or tells anyone what to do medically: that would make
Save It a medical device (FDA general wellness guidance, January 2026). `BANNED` lists the words
no sentence may contain; a test renders every sentence and checks.

Daily facts, per local day (`homes.timezone`):

    worn hours      minutes the camera was on and moving (`wear_daily`) / 60
    questions       questions from the wearer (FaceTime or phone; `web` is family, left out)
    asked again     a wearer question whose previous question about the same item, at most
                    10 minutes earlier, got a confident `seen` answer
    found           outcomes recorded for that day's questions (found / not found)
    put-downs       settled stays that started that day; "at its place": on the item's home landmark
    odd place       a confident put-down on a landmark that holds under 5% of at least 20 earlier
                    put-downs of that item

Sudden track (complete days only, the last 7): each day against the 28 days before it, leaving
out days the family tagged away, camera off or hospital, and days the camera was not worn.
A signal moves when its z-score is 2.5 or more either way: questions and asked-again as Poisson
counts against the daily mean (a call does not need the camera, so no exposure), wear against
the median and MAD. A day counts when two signals move, or one moves hugely (three times the
usual questions and at least 6; a third of the usual wear and usually at least 2 hours). A change
is two such days in a row, or one huge day.

Slow track (weeks ending yesterday): the last 3 weeks against up to 8 weeks before them (at
least 4). Questions per 10 worn hours, the asked-again share and the found share, each against
the median and MAD of the earlier weeks; a change is all 3 recent weeks at least 2 robust z the
same way.

Nothing is called a change in the first 28 days with data ("still learning the routine").
Every threshold is a starting guess: nobody has measured how much these numbers vary from week
to week (report: "Ranked recommendations", rank 11).
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from math import sqrt
from statistics import mean, median
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from app.memory.schema import PatternRows, QuestionRow

Signal = Literal["questions", "asked_again", "wear", "found"]
Direction = Literal["up", "down"]

WEARER_CHANNELS = ("facetime", "phone")
ASKED_AGAIN_WITHIN = timedelta(minutes=10)
ODD_SHARE = 0.05
ODD_MIN_HISTORY = 20
LEARNING_DAYS = 28
BASELINE_DAYS = 28
MIN_BASELINE_DAYS = 7
SUDDEN_LOOKBACK_DAYS = 7
SUDDEN_Z = 2.5
HUGE_RATIO = 3.0
HUGE_MIN_QUESTIONS = 6
HUGE_MIN_USUAL_WEAR_H = 2.0
MUTED = {"away", "camera_off", "hospital"}
SLOW_RECENT_WEEKS = 3
SLOW_BASELINE_WEEKS = 8
SLOW_MIN_BASELINE_WEEKS = 4
SLOW_Z = 2.0
MIN_WEEK_QUESTIONS = 5
MIN_WEEK_WORN_H = 3.0

BANNED = (
    "alzheimer",
    "abnormal",
    "cognitive",
    "decline",
    "delirium",
    "dementia",
    "diagnos",
    "disease",
    "infection",
    "mci",
    "patient",
    "risk",
    "score",
    "sundown",
    "symptom",
    "worsen",
)
NOTE = "Everyday observations compared with {person}'s own usual. Not a medical test."
ADVICE = "If this continues, you may want to mention it at the next appointment."


class Day(BaseModel):
    model_config = ConfigDict(frozen=True)

    day: date
    worn_hours: float
    questions: int
    asked_again: int
    found: int
    not_found: int
    put_downs: int
    at_its_place: int
    odd_places: int
    tags: list[str]


class OddPlace(BaseModel):
    model_config = ConfigDict(frozen=True)

    item: str
    landmark: str
    at: datetime  # local time


class Usual(BaseModel):
    """The person's own usual over the last 28 complete days with data."""

    model_config = ConfigDict(frozen=True)

    questions_per_day: float | None = None
    questions_per_10_worn_hours: float | None = None
    asked_again_share: float | None = None
    found_share: float | None = None
    worn_hours_per_day: float | None = None


class Change(BaseModel):
    model_config = ConfigDict(frozen=True)

    track: Literal["sudden", "slow"]
    signal: Signal
    direction: Direction
    since: date
    size: float  # this period against usual (a ratio), for the dashboard
    sentence: str


class Patterns(BaseModel):
    model_config = ConfigDict(frozen=True)

    person: str
    status: Literal["learning", "ready"]
    days_with_data: int
    note: str
    usual: Usual
    changes: list[Change]
    advice: str | None = None
    odd_places: list[OddPlace]
    days: list[Day]


def summarize(rows: PatternRows, today: date, days: int = 56) -> Patterns:
    """Daily facts for the last `days` local days up to `today`, and any change from usual."""
    tz = ZoneInfo(rows.home.timezone)
    person = rows.home.person_name
    window = [today - timedelta(days=n) for n in range(days - 1, -1, -1)]
    facts, odd = _days(rows, tz, window)
    with_data = [d for d in facts if d.day < today and (d.worn_hours > 0 or d.questions > 0)]
    learning = len(with_data) < LEARNING_DAYS
    changes = [] if learning else _sudden(facts, today, person) + _slow(facts, today, person)
    return Patterns(
        person=person,
        status="learning" if learning else "ready",
        days_with_data=len(with_data),
        note=NOTE.format(person=person),
        usual=_usual(with_data[-BASELINE_DAYS:]),
        changes=changes,
        advice=ADVICE if changes else None,
        odd_places=odd,
        days=facts,
    )


# ---------------------------------------------------------------------------------------------
# Daily facts
# ---------------------------------------------------------------------------------------------


def _days(rows: PatternRows, tz: ZoneInfo, window: list[date]) -> tuple[list[Day], list[OddPlace]]:
    def local(moment: datetime) -> date:
        return moment.astimezone(tz).date()

    first = window[0]
    worn = {w.day: w.worn_minutes / 60 for w in rows.wear}
    sure = {s.id for s in rows.answered_by if s.confident}
    counts: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    last_by_item: dict[UUID, QuestionRow] = {}
    for q in sorted(rows.questions, key=lambda q: q.asked_at):
        if q.channel not in WEARER_CHANNELS:
            continue
        day = local(q.asked_at)
        counts[day]["questions"] += 1
        if q.outcome:
            counts[day][q.outcome] += 1
        if q.item_id is None:
            continue
        prev = last_by_item.get(q.item_id)
        if (
            prev is not None
            and prev.state == "seen"
            and prev.sighting_id in sure
            and q.asked_at - prev.asked_at <= ASKED_AGAIN_WITHIN
        ):
            counts[day]["asked_again"] += 1
        last_by_item[q.item_id] = q

    homes = {i.id: i.home_landmark_id for i in rows.items}
    names = {i.id: i.name for i in rows.items}
    spoken = {p.landmark_id: p.landmark_spoken for p in rows.places}
    seen_at: dict[UUID, dict[UUID | None, int]] = defaultdict(lambda: defaultdict(int))
    odd: list[OddPlace] = []
    for s in sorted(rows.put_downs, key=lambda s: s.first_seen_at):
        history = seen_at[s.item_id]
        earlier = sum(history.values())
        day = local(s.first_seen_at)
        if day >= first:
            counts[day]["put_downs"] += 1
            if s.landmark_id is not None and s.landmark_id == homes.get(s.item_id):
                counts[day]["at_its_place"] += 1
            if (
                s.confident
                and earlier >= ODD_MIN_HISTORY
                and history[s.landmark_id] / earlier < ODD_SHARE
            ):
                counts[day]["odd_places"] += 1
                odd.append(
                    OddPlace(
                        item=names.get(s.item_id, "something"),
                        landmark=spoken.get(s.landmark_id, "somewhere new")
                        if s.landmark_id
                        else "somewhere new",
                        at=s.first_seen_at.astimezone(tz),
                    )
                )
        history[s.landmark_id] += 1

    tags: dict[date, set[str]] = defaultdict(set)
    for e in rows.events:
        start, end = local(e.starts_at), local(e.ends_at or e.starts_at)
        d = max(start, first)
        while d <= end and d <= window[-1]:
            tags[d].add(e.kind)
            d += timedelta(days=1)

    facts = [
        Day(
            day=d,
            worn_hours=round(worn.get(d, 0.0), 2),
            questions=counts[d]["questions"],
            asked_again=counts[d]["asked_again"],
            found=counts[d]["found"],
            not_found=counts[d]["not_found"],
            put_downs=counts[d]["put_downs"],
            at_its_place=counts[d]["at_its_place"],
            odd_places=counts[d]["odd_places"],
            tags=sorted(tags[d]),
        )
        for d in window
    ]
    return facts, sorted(odd, key=lambda o: o.at, reverse=True)[:5]


def _usual(days: list[Day]) -> Usual:
    if not days:
        return Usual()
    worn = sum(d.worn_hours for d in days)
    questions = sum(d.questions for d in days)
    outcomes = sum(d.found + d.not_found for d in days)
    return Usual(
        questions_per_day=round(questions / len(days), 2),
        questions_per_10_worn_hours=round(10 * questions / worn, 2) if worn else None,
        asked_again_share=round(sum(d.asked_again for d in days) / questions, 3)
        if questions
        else None,
        found_share=round(sum(d.found for d in days) / outcomes, 3) if outcomes else None,
        worn_hours_per_day=round(median(d.worn_hours for d in days), 2),
    )


# ---------------------------------------------------------------------------------------------
# Sudden track
# ---------------------------------------------------------------------------------------------


def _counts(day: Day) -> bool:
    return day.worn_hours > 0 and not MUTED.intersection(day.tags)


def _moves(day: Day, base: list[Day]) -> dict[Signal, tuple[Direction, float, bool]]:
    """Signals that moved on `day`: direction, ratio to usual, and whether the move is huge."""
    moves: dict[Signal, tuple[Direction, float, bool]] = {}
    for signal in ("questions", "asked_again"):
        expected = mean(getattr(d, signal) for d in base)
        seen = getattr(day, signal)
        z = (seen - expected) / sqrt(max(expected, 1.0))
        if abs(z) >= SUDDEN_Z:
            ratio = seen / max(expected, 0.5)
            huge = signal == "questions" and ratio >= HUGE_RATIO and seen >= HUGE_MIN_QUESTIONS
            moves[signal] = ("up" if z > 0 else "down", round(ratio, 1), huge)  # type: ignore[index]
    usual = median(d.worn_hours for d in base)
    spread = max(1.4826 * median(abs(d.worn_hours - usual) for d in base), 0.5)
    z = (day.worn_hours - usual) / spread
    if abs(z) >= SUDDEN_Z:
        ratio = day.worn_hours / usual if usual else 0.0
        huge = usual >= HUGE_MIN_USUAL_WEAR_H and day.worn_hours <= usual / HUGE_RATIO
        moves["wear"] = ("up" if z > 0 else "down", round(ratio, 2), huge)
    return moves


def _sudden(facts: list[Day], today: date, person: str) -> list[Change]:
    by_day = {d.day: d for d in facts}
    flagged: dict[date, dict[Signal, tuple[Direction, float, bool]]] = {}
    for n in range(SUDDEN_LOOKBACK_DAYS, 0, -1):
        day = by_day.get(today - timedelta(days=n))
        if day is None or MUTED.intersection(day.tags):
            continue
        base = [
            d
            for d in facts
            if day.day - timedelta(days=BASELINE_DAYS) <= d.day < day.day and _counts(d)
        ]
        if len(base) < MIN_BASELINE_DAYS:
            continue
        moves = _moves(day, base)
        if len(moves) >= 2 or any(huge for _, _, huge in moves.values()):
            flagged[day.day] = moves

    changes: dict[tuple[Signal, Direction], Change] = {}
    for day in sorted(flagged):
        prev = flagged.get(day - timedelta(days=1))
        for signal, (direction, ratio, huge) in flagged[day].items():
            in_a_row = prev is not None and prev.get(signal, ("",))[0] == direction
            key = (signal, direction)
            if (huge or in_a_row) and key not in changes:
                since = day - timedelta(days=1) if in_a_row and not huge else day
                sentence = _say("sudden", signal, direction, since, today, person, ratio)
                if sentence:
                    changes[key] = Change(
                        track="sudden",
                        signal=signal,
                        direction=direction,
                        since=since,
                        size=ratio,
                        sentence=sentence,
                    )
    return list(changes.values())


# ---------------------------------------------------------------------------------------------
# Slow track
# ---------------------------------------------------------------------------------------------


def _weekly(week: list[Day], signal: Signal) -> float | None:
    worn = sum(d.worn_hours for d in week)
    questions = sum(d.questions for d in week)
    outcomes = sum(d.found + d.not_found for d in week)
    if signal == "questions":
        return 10 * questions / worn if worn >= MIN_WEEK_WORN_H else None
    if signal == "asked_again":
        return (
            sum(d.asked_again for d in week) / questions
            if questions >= MIN_WEEK_QUESTIONS
            else None
        )
    if signal == "found":
        return sum(d.found for d in week) / outcomes if outcomes >= MIN_WEEK_QUESTIONS else None
    return None


def _slow(facts: list[Day], today: date, person: str) -> list[Change]:
    complete = [d for d in facts if d.day < today]
    weeks = [complete[max(0, end - 7) : end] for end in range(len(complete), 0, -7)][::-1]
    weeks = [w for w in weeks if len(w) == 7]
    recent = weeks[-SLOW_RECENT_WEEKS:]
    earlier = weeks[:-SLOW_RECENT_WEEKS][-SLOW_BASELINE_WEEKS:]
    if len(recent) < SLOW_RECENT_WEEKS or len(earlier) < SLOW_MIN_BASELINE_WEEKS:
        return []
    changes = []
    for signal in ("questions", "asked_again", "found"):
        base = [v for w in earlier if (v := _weekly(w, signal)) is not None]
        now = [_weekly(w, signal) for w in recent]
        if len(base) < SLOW_MIN_BASELINE_WEEKS or any(v is None for v in now):
            continue
        usual = median(base)
        spread = max(1.4826 * median(abs(v - usual) for v in base), 0.1 * abs(usual), 0.01)
        zs = [(v - usual) / spread for v in now if v is not None]
        if all(z >= SLOW_Z for z in zs) or all(z <= -SLOW_Z for z in zs):
            direction: Direction = "up" if zs[0] > 0 else "down"
            size = round(mean(v for v in now if v is not None) / usual, 2) if usual else 0.0
            since = recent[0][0].day
            sentence = _say("slow", signal, direction, since, today, person, size)
            if sentence:
                changes.append(
                    Change(
                        track="slow",
                        signal=signal,  # type: ignore[arg-type]
                        direction=direction,
                        since=since,
                        size=size,
                        sentence=sentence,
                    )
                )
    return changes


# ---------------------------------------------------------------------------------------------
# Wording: the observation and the person's own usual, nothing more
# ---------------------------------------------------------------------------------------------


def _when(since: date, today: date) -> str:
    return f"since {since:%A}" if (today - since).days <= 6 else f"since {since.day} {since:%B}"


def _say(
    track: str,
    signal: Signal,
    direction: Direction,
    since: date,
    today: date,
    person: str,
    size: float,
) -> str | None:
    when = _when(since, today)
    times = max(2, round(size))
    sentences = {
        ("sudden", "questions", "up"): f"{person} asked Find It about {times} times as often "
        f"as usual {when}.",
        ("sudden", "questions", "down"): f"{person} asked Find It much less than usual {when}.",
        ("sudden", "asked_again", "up"): f"{person} asked again soon after an answer more "
        f"often than usual {when}.",
        ("sudden", "wear", "down"): f"The camera was worn much less than usual {when}.",
        ("slow", "questions", "up"): f"For three weeks in a row, {person} asked Find It more "
        "than usual.",
        ("slow", "questions", "down"): f"For three weeks in a row, {person} asked Find It less "
        "than usual.",
        ("slow", "asked_again", "up"): f"For three weeks in a row, {person} asked again soon "
        "after an answer more often than usual.",
        ("slow", "found", "down"): "For three weeks in a row, fewer things were found after "
        "asking than usual.",
        ("slow", "found", "up"): "For three weeks in a row, more things were found after asking "
        "than usual.",
    }
    return sentences.get((track, signal, direction))
