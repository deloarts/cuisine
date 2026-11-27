"""Filters for the security log and the agent call log tables."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SecurityEventFilter:
    # Any of these event types; empty means all.
    event_types: tuple[str, ...] = ()
    outcome: str | None = None
    # created >= since and created < until.
    since: datetime | None = None
    until: datetime | None = None
    oldest_first: bool = False


@dataclass(frozen=True)
class AgentCallFilter:
    # Any of these tool names; empty means all.
    tools: tuple[str, ...] = ()
    outcome: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    oldest_first: bool = False
