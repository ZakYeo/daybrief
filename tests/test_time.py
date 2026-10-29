from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from daybrief.model import Brief
from daybrief.time import Duration, local_instant, next_midnight

LONDON = ZoneInfo("Europe/London")


def test_midnight_uses_local_calendar_across_dst() -> None:
    start = datetime(2026, 3, 29, tzinfo=UTC)
    assert next_midnight(start, LONDON) == datetime(2026, 3, 29, 23, tzinfo=UTC)
    assert Duration(seconds=86400).after(start, LONDON) == start + timedelta(days=1)
    autumn = datetime(2026, 10, 24, 23, tzinfo=UTC)
    assert next_midnight(autumn, LONDON) - autumn == timedelta(hours=25)


def test_months_preserve_wall_clock_and_clamp_month_end() -> None:
    start = datetime(2026, 1, 31, 14, 30, tzinfo=UTC)
    assert Duration(months=1).after(start, LONDON) == datetime(2026, 2, 28, 14, 30, tzinfo=UTC)
    assert Duration(months=2).after(start, LONDON) == datetime(2026, 3, 31, 13, 30, tzinfo=UTC)
    assert Duration(seconds=30 * 86400).after(start, LONDON) != Duration(months=1).after(
        start, LONDON
    )


@pytest.mark.parametrize("wall", [datetime(2026, 3, 29, 1, 30), datetime(2026, 10, 25, 1, 30)])
def test_dst_gaps_and_folds_require_clarification(wall: datetime) -> None:
    with pytest.raises(ValueError, match="ambiguous or nonexistent"):
        local_instant(wall, LONDON)


def test_calendar_month_rejects_ambiguous_target() -> None:
    start = datetime(2026, 9, 25, 0, 30, tzinfo=UTC)
    with pytest.raises(ValueError, match="ambiguous"):
        Duration(months=1).after(start, LONDON)


def test_expiry_boundary_and_deleted_precedence() -> None:
    now = datetime(2026, 10, 29, 14, 30, tzinfo=UTC)
    brief = Brief("b123", "Use local fixtures", "global", now, now, now, "Europe/London")
    assert brief.status(now - timedelta(microseconds=1)) == "active"
    assert brief.status(now) == "expired"
    deleted = Brief("b124", "Use local fixtures", "global", now, now, now, "UTC", deleted_at=now)
    assert deleted.status(now - timedelta(seconds=1)) == "deleted"


def test_calendar_month_example_and_leap_year() -> None:
    start = datetime(2026, 10, 29, 14, 30, tzinfo=UTC)
    assert Duration(months=1).after(start, LONDON) == datetime(2026, 11, 29, 14, 30, tzinfo=UTC)
    leap = datetime(2024, 1, 31, 12, tzinfo=UTC)
    assert Duration(months=1).after(leap, LONDON) == datetime(2024, 2, 29, 12, tzinfo=UTC)


def test_midnight_at_midnight_means_following_day() -> None:
    now = datetime(2026, 10, 29, tzinfo=UTC)
    assert next_midnight(now, LONDON) == now + timedelta(days=1)


def test_naive_instants_and_nonpositive_duration_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        next_midnight(datetime(2026, 1, 1), LONDON)
    for seconds, months in [(0, 0), (-1, 0), (1, 1)]:
        with pytest.raises(ValueError):
            Duration(seconds=seconds, months=months)
