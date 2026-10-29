import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from daybrief.config import Config
from daybrief.model import Brief
from daybrief.storage import ConflictError, StorageError, Store
from daybrief.time import Duration

NOW = datetime(2026, 10, 29, 14, tzinfo=UTC)


def brief(identifier: str = "b123", scope: str = "global") -> Brief:
    return Brief(identifier, "Use fixtures", scope, NOW, NOW, NOW + timedelta(hours=1), "UTC")


def test_roundtrip_selection_and_config(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.sqlite")
    config = Config("Europe/London", "repo", Duration(months=1))
    with store.transaction() as tx:
        tx.insert(brief())
        tx.insert(brief("other", "repo:other"))
        tx.insert(replace(brief("deleted"), deleted_at=NOW))
        tx.set_config(config)
    with store.transaction() as tx:
        assert tx.config() == config
        assert tx.list(("global",), NOW) == [brief()]
        assert tx.list(("global",), NOW + timedelta(hours=1)) == []
        assert len(tx.list(("global",), NOW + timedelta(hours=1), include_all=True)) == 2


def test_transaction_rolls_back_and_stale_update_fails(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.sqlite")
    with store.transaction() as tx:
        tx.insert(brief())
    with pytest.raises(RuntimeError, match="cancel"):
        with store.transaction() as tx:
            tx.insert(brief("cancelled"))
            raise RuntimeError("cancel")
    with store.transaction() as tx:
        with pytest.raises(KeyError):
            tx.get("cancelled")
        tx.replace(replace(brief(), revision=2), 1)
    with pytest.raises(ConflictError):
        with store.transaction() as tx:
            tx.replace(replace(brief(), message="stale", revision=2), 1)


def test_concurrent_writers_do_not_lose_updates(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.sqlite")
    with store.transaction() as tx:
        tx.insert(brief())

    def update(_: int) -> None:
        with store.transaction() as tx:
            current = tx.get("b123")
            tx.replace(replace(current, revision=current.revision + 1), current.revision)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(update, range(32)))
    with store.transaction() as tx:
        assert tx.get("b123").revision == 33


def test_unknown_schema_and_corrupt_file_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=99")
    original = path.read_bytes()
    with pytest.raises(StorageError, match="Unsupported"):
        with Store(path).transaction():
            pass
    assert path.read_bytes() == original
    path.write_bytes(b"not a database")
    with pytest.raises(StorageError):
        with Store(path).transaction():
            pass
    assert path.read_bytes() == b"not a database"


def test_malformed_record_and_lock_timeout_surface_errors(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite"
    store = Store(path, timeout=0.01)
    with store.transaction() as tx:
        tx.insert(brief())
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE briefs SET expires_at='nonsense'")
    with pytest.raises(StorageError, match="Invalid stored brief"):
        with store.transaction() as tx:
            tx.list(("global",), NOW)
    with store.transaction():
        with pytest.raises(StorageError, match="locked"):
            with store.transaction():
                pass
