"""
Centralises "now" so everything the app stores or stamps is UTC, not the
host's local time. Routing every call through here keeps dev, tests and the
container behaving the same way and gives a single place to patch when a
test needs a fixed clock.
"""

from datetime import UTC
from datetime import datetime


def now_utc() -> datetime:
    """Return the current instant as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    """Normalise to timezone-aware UTC, reading a naive value as UTC."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
