"""Counts failed logins per key (a login e-mail or a client IP) inside a window and
locks the key once the count reaches the limit."""

from typing import Protocol


class ILoginAttemptTracker(Protocol):
    async def lock_ttl(self, key: str) -> int:
        """Seconds the key stays locked, 0 when it is not locked."""
        ...

    async def record_failure(self, key: str, *, limit: int, lockout_seconds: int) -> bool:
        """Counts a failure and returns True when this one locked the key."""
        ...

    async def reset(self, key: str) -> None: ...
