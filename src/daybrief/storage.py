"""SQLite transactions and validated records, independent of lifecycle policy."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from daybrief.config import Config
from daybrief.model import Brief
from daybrief.time import Duration, instant


class StorageError(RuntimeError):
    """State could not be read or safely persisted."""


class ConflictError(StorageError):
    """A record changed since the caller read it."""


class Store:
    def __init__(self, path: Path, timeout: float = 5) -> None:
        self.path = path
        self.timeout = timeout

    @contextmanager
    def transaction(self) -> Iterator["Transaction"]:
        connection: sqlite3.Connection | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=self.timeout, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            self._schema(connection)
            yield Transaction(connection)
            connection.commit()
        except (sqlite3.Error, OSError) as error:
            raise StorageError(f"Cannot access Daybrief storage at {self.path}: {error}") from error
        finally:
            if connection is not None:
                if connection.in_transaction:
                    connection.rollback()
                connection.close()

    @staticmethod
    def _schema(connection: sqlite3.Connection) -> None:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if tables:
                raise StorageError(
                    "Unversioned nonempty database; refusing to replace existing state."
                )
            connection.execute(
                "CREATE TABLE briefs (id TEXT PRIMARY KEY, message TEXT NOT NULL,"
                " scope TEXT NOT NULL,"
                " created_at TEXT NOT NULL, updated_at TEXT NOT NULL, expires_at TEXT NOT NULL,"
                " timezone TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision > 0),"
                " deleted_at TEXT) STRICT"
            )
            connection.execute("CREATE INDEX brief_scope ON briefs(scope)")
            connection.execute(
                "CREATE TABLE config (singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
                " timezone TEXT NOT NULL, scope TEXT NOT NULL,"
                " seconds INTEGER, months INTEGER) STRICT"
            )
            connection.execute("PRAGMA user_version=1")
        elif version != 1:
            raise StorageError(f"Unsupported database schema {version}; upgrade Daybrief.")


def decode_brief(row: sqlite3.Row) -> Brief:
    try:
        return Brief(
            id=row["id"],
            message=row["message"],
            scope=row["scope"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            timezone=row["timezone"],
            revision=row["revision"],
            deleted_at=(
                datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] is not None else None
            ),
        )
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise StorageError("Invalid stored brief; repair or restore the database.") from error


def brief_values(brief: Brief) -> tuple[str | int | None, ...]:
    return (
        brief.id,
        brief.message,
        brief.scope,
        instant(brief.created_at).isoformat(),
        instant(brief.updated_at).isoformat(),
        instant(brief.expires_at).isoformat(),
        brief.timezone,
        brief.revision,
        instant(brief.deleted_at).isoformat() if brief.deleted_at else None,
    )


class Transaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, identifier: str) -> Brief:
        row = self.connection.execute("SELECT * FROM briefs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise KeyError(f"Brief {identifier} does not exist.")
        return decode_brief(row)

    def list(
        self, scopes: tuple[str, ...], now: datetime, include_all: bool = False
    ) -> list[Brief]:
        # Validate before filtering: malformed state must not masquerade as no active briefs.
        rows = self.connection.execute(
            "SELECT * FROM briefs WHERE scope IN ("
            + ",".join("?" for _ in scopes)
            + ") ORDER BY id",
            scopes,
        ).fetchall()
        briefs = [decode_brief(row) for row in rows]
        return [brief for brief in briefs if include_all or brief.status(now) == "active"]

    def insert(self, brief: Brief) -> None:
        self.connection.execute(
            "INSERT INTO briefs VALUES (?,?,?,?,?,?,?,?,?)", brief_values(brief)
        )

    def replace(self, brief: Brief, expected_revision: int) -> None:
        if brief.revision != expected_revision + 1:
            raise ValueError("An update must increment the revision exactly once.")
        values = brief_values(brief)
        cursor = self.connection.execute(
            "UPDATE briefs SET message=?,scope=?,created_at=?,updated_at=?,expires_at=?,"
            "timezone=?,revision=?,deleted_at=? WHERE id=? AND revision=?",
            (*values[1:], brief.id, expected_revision),
        )
        if cursor.rowcount != 1:
            raise ConflictError("Brief changed concurrently; reload it and retry.")

    def config(self) -> Config | None:
        row = self.connection.execute("SELECT * FROM config WHERE singleton=1").fetchone()
        if row is None:
            return None
        try:
            expiry = None
            if row["seconds"] is not None or row["months"] is not None:
                expiry = Duration(seconds=row["seconds"], months=row["months"])
            return Config(row["timezone"], row["scope"], expiry)
        except (ValueError, TypeError, KeyError) as error:
            raise StorageError(
                "Invalid stored configuration; repair or restore the database."
            ) from error

    def set_config(self, config: Config) -> None:
        self.connection.execute(
            "INSERT INTO config VALUES (1,?,?,?,?) ON CONFLICT(singleton) DO UPDATE SET "
            "timezone=excluded.timezone,scope=excluded.scope,seconds=excluded.seconds,"
            "months=excluded.months",
            (
                config.timezone,
                config.scope,
                config.expiry.seconds if config.expiry else None,
                config.expiry.months if config.expiry else None,
            ),
        )
