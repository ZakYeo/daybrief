"""Immutable brief records and their time-dependent state."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from daybrief.time import instant

Status = Literal["active", "expired", "deleted"]


@dataclass(frozen=True)
class Brief:
    id: str
    message: str
    scope: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    timezone: str
    revision: int = 1
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.message.strip() or not self.scope:
            raise ValueError("Brief ID, message and scope must not be empty.")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("Brief revision must be a positive integer.")
        ZoneInfo(self.timezone)
        for value in (self.created_at, self.updated_at, self.expires_at, self.deleted_at):
            if value is not None:
                instant(value)
        if instant(self.updated_at) < instant(self.created_at):
            raise ValueError("Update timestamp precedes creation.")

    def status(self, now: datetime) -> Status:
        now = instant(now)
        if self.deleted_at is not None:
            return "deleted"
        return "active" if now < instant(self.expires_at) else "expired"
