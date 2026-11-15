"""The safety loop's rules (docs/INSIGHTS.md design 3): confirm with the person, then the family
decides. Pure: no database, no clock. Nothing here, or anywhere in Save It, dials 911.

    urgency     smoke: urgent, always. scam: a note. A fall, being hurt, needing help or being
                lost outside: urgent unless the person answered "I'm fine" (then a check-in;
                "fine" is still reported, because people with dementia sometimes deny a fall).
    quiet day   from 2 pm local: the camera was worn under a quarter of its usual time so far
                today (median of the last 14 days with any wear, at least 5 of them and at least
                an hour usually), and no question came in today. A check-in, never an alarm:
                a charging phone looks the same as a withdrawn person, and the sentence says so.
"""

from datetime import date
from statistics import median

from app.memory.schema import ConcernAnswer, ConcernKind, Urgency, WearHour

QUIET_FROM_HOUR = 14
QUIET_SHARE = 0.25
QUIET_MIN_USUAL_MINUTES = 60
QUIET_BASELINE_DAYS = 14
QUIET_MIN_DAYS = 5


def urgency(kind: ConcernKind, answer: ConcernAnswer | None) -> Urgency:
    if kind == "smoke":
        return "urgent"
    if kind == "scam":
        return "note"
    if kind == "quiet_day":
        return "check_in"
    return "check_in" if answer == "ok" else "urgent"


def quiet_day(
    hours: list[WearHour], today: date, hour_now: int, questions_today: int, person: str
) -> str | None:
    """The family's check-in sentence when today is unusually quiet, else None."""
    if hour_now < QUIET_FROM_HOUR or questions_today > 0:
        return None
    by_day: dict[date, int] = {}
    for h in hours:
        if h.hour < hour_now:
            by_day[h.day] = by_day.get(h.day, 0) + h.worn_minutes
    past_days = [d for d in sorted(by_day) if d < today and by_day[d] > 0][-QUIET_BASELINE_DAYS:]
    if len(past_days) < QUIET_MIN_DAYS:
        return None
    usual = median(by_day[d] for d in past_days)
    if usual < QUIET_MIN_USUAL_MINUTES or by_day.get(today, 0) >= QUIET_SHARE * usual:
        return None
    return (
        f"Find It hasn't heard from {person} today, and the camera has been worn much less "
        "than usual. It may just be charging; a quick call could help."
    )
