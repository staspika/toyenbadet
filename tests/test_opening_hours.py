"""Exercise parsing and time semantics of the municipal schedule."""

import json
from datetime import date, datetime

import pytest

from custom_components.toyenbadet.opening_hours import OSLO, parse_opening_hours


def document(days: list[dict[str, object]]) -> str:
    """Wrap a schedule in the same inline script as the municipal page."""
    return "<script>window.ohData.push(" + json.dumps([{"days": days}]) + ");</script>"


def day(value: str = "2026-11-15") -> dict[str, object]:
    """Build an open day with two intervals and an exception note."""
    return {
        "date": value,
        "isClosed": False,
        "hours": [
            {"opensAt": "10:00", "closesAt": "12:00"},
            {"opensAt": "13:00", "closesAt": "16:30"},
        ],
        "comment": "Special opening hours",
    }


def test_schedule() -> None:
    """Preserve split intervals, comments, and explicit closed dates."""
    schedule = parse_opening_hours(
        document(
            [
                day(),
                {"date": "2026-11-16", "isClosed": True, "hours": []},
            ]
        )
    )
    assert schedule.days == {date(2026, 11, 15), date(2026, 11, 16)}
    assert len(schedule.intervals) == 2
    assert schedule.intervals[0].start == datetime(2026, 11, 15, 10, tzinfo=OSLO)
    assert schedule.intervals[1].comment == "Special opening hours"


@pytest.mark.parametrize("value,offset", [("2026-03-28", 3600), ("2026-03-29", 7200)])
def test_oslo_daylight_saving(value: str, offset: int) -> None:
    """Interpret wall-clock times in Oslo regardless of HA's configured zone."""
    interval = parse_opening_hours(document([day(value)])).intervals[0]
    assert interval.start.utcoffset().total_seconds() == offset


@pytest.mark.parametrize(
    "changes",
    [
        {"hours": []},
        {"date": "invalid"},
        {"isClosed": "false"},
        {"hours": [{"opensAt": "19:00", "closesAt": "10:00"}]},
        {"hours": [{"opensAt": "25:00", "closesAt": "26:00"}]},
        {"comment": {}},
    ],
)
def test_invalid_day(changes: dict[str, object]) -> None:
    """Reject incomplete or malformed values instead of guessing closed."""
    with pytest.raises(ValueError):
        parse_opening_hours(document([{**day(), **changes}]))


@pytest.mark.parametrize(
    "html",
    [
        "<html>Unavailable</html>",
        "<script>window.ohData.push({broken});</script>",
        document([day()]) * 2,
        document([day(), day()]),
    ],
)
def test_invalid_document(html: str) -> None:
    """Reject missing, ambiguous, malformed, and duplicate schedules."""
    with pytest.raises(ValueError):
        parse_opening_hours(html)


def test_structured_comment() -> None:
    """Accept the object-shaped exception notes used by the website renderer."""
    schedule = parse_opening_hours(
        document(
            [
                {
                    **day(),
                    "comment": {
                        "id": "holiday",
                        "text": "<p>Shorter hours &amp; fewer lanes.</p>",
                    },
                    "isDeviation": True,
                }
            ]
        )
    )
    assert schedule.intervals[0].comment == "Shorter hours & fewer lanes."


def test_overlapping_intervals() -> None:
    """Reject overlapping spans rather than choosing an arbitrary closing time."""
    with pytest.raises(ValueError, match="Overlapping"):
        parse_opening_hours(
            document(
                [
                    {
                        **day(),
                        "hours": [
                            {"opensAt": "10:00", "closesAt": "14:00"},
                            {"opensAt": "13:00", "closesAt": "16:30"},
                        ],
                    }
                ]
            )
        )
