"""Brief lifecycle policy shared by the CLI and client adapters."""

import secrets
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

from daybrief.clock import Clock, SystemClock
from daybrief.config import Config
from daybrief.model import Brief
from daybrief.storage import Store, Transaction
from daybrief.time import Duration, instant, next_midnight


class Daybrief:
    def __init__(self, store: Store, defaults: Config, clock: Clock | None = None) -> None:
        self.store = store
        self.defaults = defaults
        self.clock = clock if clock is not None else SystemClock()

    def configuration(self) -> Config:
        with self.store.transaction() as tx:
            return self._configuration(tx)

    def _configuration(self, tx: Transaction) -> Config:
        config = tx.config()
        if config is None:
            config = self.defaults
            tx.set_config(config)
        return config

    def configure(self, config: Config) -> None:
        with self.store.transaction() as tx:
            tx.set_config(config)

    @staticmethod
    def _scope(scope: str) -> None:
        if scope != "global" and not (scope.startswith("repo:") and scope[5:]):
            raise ValueError("Select global or a resolved repository scope.")

    @staticmethod
    def _expiry(
        now: datetime, config: Config, duration: Duration | None, until: datetime | None
    ) -> datetime:
        if duration is not None and until is not None:
            raise ValueError("Choose a duration or deadline, not both.")
        if until is not None:
            expires = instant(until)
        else:
            lifetime = duration if duration is not None else config.expiry
            expires = (
                lifetime.after(now, config.zone) if lifetime else next_midnight(now, config.zone)
            )
        if expires <= now:
            raise ValueError("Expiry must be in the future.")
        return expires

    def create(
        self,
        message: str,
        scope: str,
        *,
        duration: Duration | None = None,
        until: datetime | None = None,
        timezone: str | None = None,
    ) -> Brief:
        self._scope(scope)
        with self.store.transaction() as tx:
            now = instant(self.clock.now())
            config = self._configuration(tx)
            if timezone is not None:
                config = replace(config, timezone=timezone)
            expires = self._expiry(now, config, duration, until)
            while True:
                identifier = secrets.token_hex(4)
                try:
                    tx.get(identifier)
                except KeyError:
                    break
            brief = Brief(identifier, message, scope, now, now, expires, config.timezone)
            tx.insert(brief)
            return brief

    def list(self, scopes: tuple[str, ...], *, include_all: bool = False) -> list[Brief]:
        for scope in scopes:
            self._scope(scope)
        with self.store.transaction() as tx:
            return tx.list(scopes, instant(self.clock.now()), include_all)

    @staticmethod
    def _get(tx: Transaction, identifier: str, scopes: tuple[str, ...]) -> Brief:
        brief = tx.get(identifier)
        if brief.scope not in scopes:
            raise KeyError(f"Brief {identifier} is outside the selected scope.")
        return brief

    def show(self, identifier: str, scopes: tuple[str, ...]) -> Brief:
        with self.store.transaction() as tx:
            return self._get(tx, identifier, scopes)

    @staticmethod
    def _mutable(brief: Brief) -> None:
        if brief.deleted_at is not None:
            raise ValueError("Deleted briefs cannot be changed; create a new brief.")

    def edit(
        self,
        identifier: str,
        scope: str,
        message: str,
        *,
        duration: Duration | None = None,
        until: datetime | None = None,
        timezone: str | None = None,
    ) -> Brief:
        with self.store.transaction() as tx:
            brief = self._get(tx, identifier, (scope,))
            self._mutable(brief)
            now = instant(self.clock.now())
            expires = brief.expires_at
            if duration is not None or until is not None:
                expires = self._expiry(now, Config(timezone or brief.timezone), duration, until)
            changed = replace(
                brief,
                message=message,
                timezone=timezone or brief.timezone,
                expires_at=expires,
                updated_at=now,
                revision=brief.revision + 1,
            )
            tx.replace(changed, brief.revision)
            return changed

    def extend(self, identifier: str, scope: str, duration: Duration) -> Brief:
        with self.store.transaction() as tx:
            brief = self._get(tx, identifier, (scope,))
            self._mutable(brief)
            now = instant(self.clock.now())
            expires = duration.after(brief.expires_at, ZoneInfo(brief.timezone))
            if expires <= now:
                raise ValueError("Extended expiry must be in the future.")
            changed = replace(
                brief, expires_at=expires, updated_at=now, revision=brief.revision + 1
            )
            tx.replace(changed, brief.revision)
            return changed

    def delete(self, identifier: str, scope: str) -> Brief:
        with self.store.transaction() as tx:
            brief = self._get(tx, identifier, (scope,))
            if brief.deleted_at is not None:
                return brief
            now = instant(self.clock.now())
            changed = replace(brief, deleted_at=now, updated_at=now, revision=brief.revision + 1)
            tx.replace(changed, brief.revision)
            return changed

    def clear(self, scope: str) -> int:
        self._scope(scope)
        with self.store.transaction() as tx:
            now = instant(self.clock.now())
            briefs = tx.list((scope,), now)
            for brief in briefs:
                tx.replace(
                    replace(brief, deleted_at=now, updated_at=now, revision=brief.revision + 1),
                    brief.revision,
                )
            return len(briefs)
