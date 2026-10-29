"""Explicit instant and calendar arithmetic; no filesystem or clock reads."""

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo


def instant(value: datetime) -> datetime:
    """Normalize an aware timestamp; never infer a timezone for naive input."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("A timezone or explicit UTC offset is required.")
    return value.astimezone(UTC)


def local_instant(value: datetime, zone: ZoneInfo) -> datetime:
    """Resolve a wall clock time only when it identifies exactly one instant."""
    if value.tzinfo is not None:
        raise ValueError("Expected a local time without an offset.")
    candidates = set()
    for fold in (0, 1):
        candidate = value.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if candidate.astimezone(zone).replace(tzinfo=None) == value:
            candidates.add(candidate)
    if len(candidates) != 1:
        raise ValueError("Local time is ambiguous or nonexistent; specify an explicit UTC offset.")
    return candidates.pop()


def next_midnight(now: datetime, zone: ZoneInfo) -> datetime:
    tomorrow = instant(now).astimezone(zone).date() + timedelta(days=1)
    return local_instant(datetime.combine(tomorrow, time()), zone)


@dataclass(frozen=True)
class Duration:
    """Either elapsed seconds or calendar months, both strictly positive."""

    seconds: int = 0
    months: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.seconds) is not int
            or type(self.months) is not int
            or self.seconds < 0
            or self.months < 0
            or (self.seconds == 0) == (self.months == 0)
        ):
            raise ValueError("Specify positive elapsed seconds or calendar months, not both.")

    def after(self, start: datetime, zone: ZoneInfo) -> datetime:
        start = instant(start)
        if self.seconds:
            return start + timedelta(seconds=self.seconds)
        local = start.astimezone(zone)
        year, month_index = divmod(local.year * 12 + local.month - 1 + self.months, 12)
        month = month_index + 1
        day = min(local.day, calendar.monthrange(year, month)[1])
        target = local.replace(year=year, month=month, day=day, tzinfo=None)
        return local_instant(target, zone)
