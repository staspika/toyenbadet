"""Parse the municipality's embedded schedule without executing JavaScript."""

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")


@dataclass(frozen=True)
class OpeningInterval:
    """One dated ticket-sales interval."""

    start: datetime
    end: datetime
    comment: str | None


@dataclass(frozen=True)
class OpeningSchedule:
    """Explicitly published days, including closed days."""

    days: frozenset[date]
    intervals: tuple[OpeningInterval, ...]


class _Scripts(HTMLParser):
    """Collect inline scripts, ignoring markup and external resources."""

    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self._inside = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._inside = tag == "script" and not dict(attrs).get("src")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside = False

    def handle_data(self, data: str) -> None:
        if self._inside:
            self.scripts.append(data)


class _CommentText(HTMLParser):
    """Extract readable text from the municipality's HTML exception notes."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _comment_text(value: object) -> str | None:
    """Normalize a daily comment object or a plain text note."""
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("text")
    if not isinstance(value, str):
        raise ValueError("Invalid comment")
    parser = _CommentText()
    parser.feed(value)
    return " ".join(part.strip() for part in parser.parts if part.strip()) or None


def parse_opening_hours(html: str) -> OpeningSchedule:
    """Validate the single embedded schedule; reject ambiguous or partial data."""
    parser = _Scripts()
    parser.feed(html)
    candidates = [
        script[match.end() :].lstrip()
        for script in parser.scripts
        for match in re.finditer(r"window\.ohData\.push\s*\(", script)
    ]
    if len(candidates) != 1:
        raise ValueError("Expected one opening-hours schedule")
    try:
        weeks, end = json.JSONDecoder().raw_decode(candidates[0])
        if not candidates[0][end:].lstrip().startswith(")"):
            raise ValueError("Unexpected schedule suffix")
        if not isinstance(weeks, list) or not weeks:
            raise ValueError("Missing weeks")
        days: set[date] = set()
        intervals: list[OpeningInterval] = []
        for week in weeks:
            if not isinstance(week["days"], list) or not week["days"]:
                raise ValueError("Missing days")
            for day in week["days"]:
                current = date.fromisoformat(day["date"])
                if current in days:
                    raise ValueError("Duplicate date")
                days.add(current)
                closed = day["isClosed"]
                hours = day["hours"]
                comment = _comment_text(day.get("comment"))
                if type(closed) is not bool or not isinstance(hours, list):
                    raise ValueError("Invalid day")
                if closed:
                    continue
                if not hours:
                    raise ValueError("Open day has no intervals")
                for span in hours:
                    values = [span["opensAt"], span["closesAt"]]
                    if any(
                        not isinstance(value, str)
                        or not re.fullmatch(r"\d{2}:\d{2}", value)
                        for value in values
                    ):
                        raise ValueError("Invalid time")
                    start, finish = (
                        datetime.combine(current, time.fromisoformat(value), OSLO)
                        for value in values
                    )
                    if finish <= start:
                        raise ValueError("Invalid interval")
                    intervals.append(OpeningInterval(start, finish, comment))
        intervals.sort(key=lambda interval: interval.start)
        if any(a.end > b.start for a, b in zip(intervals, intervals[1:], strict=False)):
            raise ValueError("Overlapping intervals")
        return OpeningSchedule(frozenset(days), tuple(intervals))
    except (KeyError, TypeError, AttributeError) as err:
        raise ValueError("Invalid opening-hours schema") from err
