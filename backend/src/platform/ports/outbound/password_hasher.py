"""Hashes and verifies passwords. Async, because the work is deliberately
slow and must not stall the event loop."""

from typing import Protocol


class IPasswordHasher(Protocol):
    async def hash(self, plain: str) -> str: ...
    async def verify(self, plain: str, hashed: str) -> bool: ...
