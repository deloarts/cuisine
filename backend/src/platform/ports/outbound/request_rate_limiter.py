"""Counts requests per key (such as a client address) in a fixed window, for
the surfaces anyone may call without signing in."""

from typing import Protocol


class IRequestRateLimiter(Protocol):
    async def hit(self, key: str, *, limit: int, window_seconds: int) -> int:
        """Counts one request for the key. Returns 0 while the key stays
        within `limit` requests per window, else the seconds until its
        window ends."""
        ...
