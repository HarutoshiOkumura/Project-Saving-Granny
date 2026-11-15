"""The safety loop's rules (docs/INSIGHTS.md design 3): urgency and the quiet-day check-in."""

from datetime import date, timedelta

import pytest

from app.concerns import quiet_day, urgency
from app.memory.schema import WearHour

TODAY = date(2026, 11, 15)


@pytest.mark.parametrize(
    ("kind", "answer", "expected"),
    [
        ("fall", "hurt", "urgent"),
        ("fall", "no_answer", "urgent"),
        ("fall", None, "urgent"),
        ("fall", "ok", "check_in"),  # "I'm fine" is still reported
        ("help", "ok", "check_in"),
        ("lost_outside", "no_answer", "urgent"),
        ("smoke", "ok", "urgent"),  # smoke is urgent whatever they say
        ("scam", None, "note"),
        ("quiet_day", None, "check_in"),
    ],
)
def test_urgency(kind: str, answer: str | None, expected: str) -> None:
    assert urgency(kind, answer) == expected  # type: ignore[arg-type]


def mornings(days: int, minutes_per_hour: int, today_minutes: int) -> list[WearHour]:
    """`days` past days worn 8:00 to 13:00, and today worn `today_minutes` at 9:00."""
    hours = [
        WearHour(day=TODAY - timedelta(days=n), hour=h, worn_minutes=minutes_per_hour)
        for n in range(1, days + 1)
        for h in range(8, 13)
    ]
    if today_minutes:
        hours.append(WearHour(day=TODAY, hour=9, worn_minutes=today_minutes))
    return hours


def test_a_quiet_afternoon_with_no_call_gets_a_gentle_check_in() -> None:
    sentence = quiet_day(mornings(10, 40, 10), TODAY, 14, 0, "Rose")
    assert sentence is not None
    assert sentence.startswith("Find It hasn't heard from Rose today")
    assert "charging" in sentence  # it says it may be nothing


def test_not_before_2_pm() -> None:
    assert quiet_day(mornings(10, 40, 0), TODAY, 13, 0, "Rose") is None


def test_not_when_she_called_today() -> None:
    assert quiet_day(mornings(10, 40, 0), TODAY, 15, 1, "Rose") is None


def test_not_when_today_is_a_normal_morning() -> None:
    assert quiet_day(mornings(10, 40, 60), TODAY, 15, 0, "Rose") is None


def test_not_without_five_days_of_history() -> None:
    assert quiet_day(mornings(4, 40, 0), TODAY, 15, 0, "Rose") is None


def test_not_when_the_camera_is_rarely_worn_anyway() -> None:
    assert quiet_day(mornings(10, 5, 0), TODAY, 15, 0, "Rose") is None  # 25 min a morning
