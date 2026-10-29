"""Validated user defaults, independent of storage and environment discovery."""

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from daybrief.time import Duration


@dataclass(frozen=True)
class Config:
    timezone: str
    scope: str = "repo"
    expiry: Duration | None = None

    def __post_init__(self) -> None:
        ZoneInfo(self.timezone)
        if self.scope not in ("repo", "global"):
            raise ValueError("Default scope must be repo or global.")
        if self.expiry is not None and not isinstance(self.expiry, Duration):
            raise ValueError("Default expiry must be a duration or local midnight.")

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)
