"""Claims a key once, so a one-time code or a challenge cannot be redeemed
twice within its validity."""

from typing import Protocol


class IReplayGuard(Protocol):
    async def consume_once(self, key: str, ttl_seconds: int) -> bool:
        """True for the first claim of `key`, False for every later one."""
        ...
