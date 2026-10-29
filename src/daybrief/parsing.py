"""Deterministic expiry grammar; broader language interpretation belongs to agents."""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from daybrief.time import Duration, instant, local_instant, next_midnight

UNITS = {
    "s": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "w": 604800,
    "week": 604800,
    "weeks": 604800,
}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def duration(value: str) -> Duration:
    match = re.fullmatch(r"(\d+|one|an?|a)\s*([a-z]+)", value.strip().lower())
    if not match:
        raise ValueError("Use a positive duration such as '2 days', '24h', or '1mo'.")
    count_text, unit = match.groups()
    count = 1 if count_text in ("a", "an", "one") else int(count_text)
    if unit in ("mo", "month", "months"):
        return Duration(months=count)
    if unit not in UNITS:
        raise ValueError(f"Unknown duration unit: {unit}.")
    return Duration(seconds=count * UNITS[unit])


def deadline(value: str, zone: ZoneInfo) -> datetime:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return local_instant(datetime.combine(date.fromisoformat(value), time()), zone)
        parsed = datetime.fromisoformat(value)
        return instant(parsed) if parsed.tzinfo else local_instant(parsed, zone)
    except ValueError as error:
        raise ValueError(f"Invalid deadline '{value}': {error}") from error


def weekday_deadline(value: str, now: datetime, zone: ZoneInfo) -> datetime:
    match = re.fullmatch(r"([a-z]+) at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?", value.strip().lower())
    if not match or match[1] not in WEEKDAYS:
        raise ValueError("Specify a weekday and time, such as 'Friday at 5pm', or use --until.")
    weekday, hour_text, minute_text, meridian = match.groups()
    hour, minute = int(hour_text), int(minute_text or 0)
    if meridian:
        if not 1 <= hour <= 12:
            raise ValueError("Use hours 1–12 with am/pm.")
        hour = hour % 12 + (12 if meridian == "pm" else 0)
    elif minute_text is None:
        raise ValueError("Specify am/pm or a 24-hour HH:MM time.")
    local = instant(now).astimezone(zone)
    target = local.date() + timedelta(days=(WEEKDAYS.index(weekday) - local.weekday()) % 7)
    resolved = local_instant(datetime.combine(target, time(hour, minute)), zone)
    if resolved <= instant(now):
        resolved = local_instant(
            datetime.combine(target + timedelta(days=7), time(hour, minute)), zone
        )
    return resolved


@dataclass(frozen=True)
class ParsedMessage:
    message: str
    duration: Duration | None = None
    until: datetime | None = None


def message_expiry(
    message: str, now: datetime, zone: ZoneInfo, *, literal: bool = False, explicit: bool = False
) -> ParsedMessage:
    """Recognize trailing expiry phrases without interpreting arbitrary prose."""
    if literal:
        return ParsedMessage(message)
    match = re.search(
        r"\s+(have this last|for|until)\s+(.+?)\.?$|\s+(today)\.?$", message, re.IGNORECASE
    )
    if not match:
        return ParsedMessage(message)
    prefix = message[: match.start()].rstrip()
    kind, value, today = match.groups()
    # Ordinary prose containing 'for' is not necessarily a lifetime expression.
    if kind and kind.lower() == "for" and not re.match(r"\d|one\b|an?\b", value, re.IGNORECASE):
        return ParsedMessage(message)
    if explicit:
        raise ValueError(
            "Conflicting expiry phrase and explicit flag; use --literal to keep the text."
        )
    if today:
        return ParsedMessage(prefix, until=next_midnight(now, zone))
    if kind.lower() in ("for", "have this last"):
        return ParsedMessage(prefix, duration=duration(value))
    return ParsedMessage(prefix, until=weekday_deadline(value, now, zone))
