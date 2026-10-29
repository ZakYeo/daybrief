from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from daybrief.config import Config
from daybrief.service import Daybrief
from daybrief.storage import Store
from daybrief.time import Duration


class TestClock:
    __test__ = False

    def __init__(self) -> None:
        self.value = datetime(2026, 10, 29, 14, 30, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value


def service(tmp_path: Path) -> tuple[Daybrief, TestClock]:
    clock = TestClock()
    return Daybrief(Store(tmp_path / "state.sqlite"), Config("Europe/London"), clock), clock


def test_creation_defaults_and_configuration_persist(tmp_path: Path) -> None:
    app, clock = service(tmp_path)
    first = app.create("Use fixtures", "global")
    assert first.expires_at == datetime(2026, 10, 30, tzinfo=UTC)
    month = app.create("Migration", "global", duration=Duration(months=1))
    assert month.expires_at == datetime(2026, 11, 29, 14, 30, tzinfo=UTC)
    app.configure(Config("UTC", "global", Duration(seconds=3600)))
    reopened = Daybrief(app.store, Config("Europe/Paris"), clock)
    assert reopened.configuration().timezone == "UTC"
    assert reopened.create("New defaults", "global").expires_at == clock.now() + timedelta(hours=1)


def test_edit_preserves_expiry_and_extend_adds_to_existing_expiry(tmp_path: Path) -> None:
    app, clock = service(tmp_path)
    brief = app.create("First", "repo:one", duration=Duration(seconds=3600))
    clock.value += timedelta(minutes=30)
    edited = app.edit(brief.id, "repo:one", "Changed")
    assert edited.expires_at == brief.expires_at
    assert edited.id == brief.id
    assert edited.created_at == brief.created_at
    extended = app.extend(brief.id, "repo:one", Duration(seconds=3600))
    assert extended.expires_at == brief.expires_at + timedelta(hours=1)
    changed = app.edit(brief.id, "repo:one", "New deadline", duration=Duration(seconds=60))
    assert changed.expires_at == clock.now() + timedelta(minutes=1)
    assert changed.revision == 4


def test_expiry_history_reactivation_and_deletion(tmp_path: Path) -> None:
    app, clock = service(tmp_path)
    brief = app.create("Temporary", "global", duration=Duration(seconds=60))
    clock.value = brief.expires_at
    assert app.list(("global",)) == []
    assert app.list(("global",), include_all=True)[0].status(clock.now()) == "expired"
    app.extend(brief.id, "global", Duration(seconds=60))
    assert len(app.list(("global",))) == 1
    deleted = app.delete(brief.id, "global")
    assert app.delete(brief.id, "global") == deleted
    assert app.list(("global",)) == []
    assert app.show(brief.id, ("global",)).status(clock.now()) == "deleted"
    with pytest.raises(ValueError, match="Deleted"):
        app.extend(brief.id, "global", Duration(seconds=60))
    with pytest.raises(ValueError, match="Deleted"):
        app.edit(brief.id, "global", "Revive")


def test_scope_isolation_and_clear_only_active_target(tmp_path: Path) -> None:
    app, clock = service(tmp_path)
    global_brief = app.create("Global", "global")
    repo = app.create("Repo", "repo:one")
    expired = app.create("Old", "repo:one", duration=Duration(seconds=1))
    other = app.create("Other", "repo:two")
    clock.value += timedelta(seconds=1)
    assert {item.id for item in app.list(("global", "repo:one"))} == {global_brief.id, repo.id}
    with pytest.raises(KeyError, match="scope"):
        app.delete(global_brief.id, "repo:one")
    assert app.clear("repo:one") == 1
    assert app.show(expired.id, ("repo:one",)).deleted_at is None
    assert {item.id for item in app.list(("global", "repo:two"))} == {global_brief.id, other.id}


def test_invalid_creation_rolls_back_and_explicit_deadline_is_precise(tmp_path: Path) -> None:
    app, clock = service(tmp_path)
    with pytest.raises(ValueError, match="empty"):
        app.create("   ", "global")
    with pytest.raises(ValueError, match="future"):
        app.create("Past", "global", until=clock.now())
    with pytest.raises(ValueError, match="not both"):
        app.create("Conflict", "global", duration=Duration(seconds=1), until=clock.now())
    assert app.list(("global",), include_all=True) == []
    deadline = clock.now() + timedelta(seconds=123)
    assert app.create("Exact", "global", until=deadline).expires_at == deadline
