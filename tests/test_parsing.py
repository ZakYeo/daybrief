from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from daybrief.parsing import deadline, duration, message_expiry

NOW = datetime(2026, 10, 29, 14, 30, tzinfo=UTC)
ZONE = ZoneInfo("Europe/London")


def test_product_natural_examples() -> None:
    month = message_expiry("Use the staging API. Have this last one month.", NOW, ZONE)
    assert month.message == "Use the staging API."
    assert month.duration is not None and month.duration.months == 1
    friday = message_expiry("Avoid deployments until Friday at 5pm.", NOW, ZONE)
    assert friday.until == datetime(2026, 10, 30, 17, tzinfo=UTC)
    today = message_expiry("Use fixtures today.", NOW, ZONE)
    assert today.until == datetime(2026, 10, 30, tzinfo=UTC)


def test_explicit_durations_and_deadlines() -> None:
    assert duration("1mo").months == 1
    assert duration("30 days").seconds == 2592000
    assert deadline("2026-11-30", ZONE) == datetime(2026, 11, 30, tzinfo=UTC)
    assert deadline("2026-07-01T12:00:00+02:00", ZONE) == datetime(2026, 7, 1, 10, tzinfo=UTC)


@pytest.mark.parametrize("text", ["0d", "-2h", "one year", "next week", "1.5h"])
def test_invalid_duration(text: str) -> None:
    with pytest.raises(ValueError):
        duration(text)


def test_ambiguity_conflicts_and_literal_escape() -> None:
    with pytest.raises(ValueError, match="weekday and time"):
        message_expiry("Avoid deployments until Friday", NOW, ZONE)
    with pytest.raises(ValueError, match="Conflicting"):
        message_expiry("Use fixtures for 2 days", NOW, ZONE, explicit=True)
    text = "Wait until further notice"
    assert message_expiry(text, NOW, ZONE, literal=True).message == text
    assert message_expiry("Use fixtures for integration tests", NOW, ZONE).message.endswith("tests")
