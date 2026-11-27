"""Holds OAuth authorization codes for the minute between approval and
redemption, and remembers a redeemed code long enough to recognise a
second redemption."""

from typing import Protocol

from src.platform.domain.entities.oauth import AuthorizationCode


class IAuthorizationCodeStore(Protocol):
    async def put(self, code_hash: str, code: AuthorizationCode, ttl_seconds: int) -> None: ...

    async def take(self, code_hash: str) -> AuthorizationCode | None:
        """Returns the code and removes it in one step, so only one caller
        ever gets it; None when it is unknown, expired or already taken."""
        ...

    async def mark_redeemed(self, code_hash: str, grant_id: int, ttl_seconds: int) -> None: ...

    async def redeemed_grant(self, code_hash: str) -> int | None:
        """The grant a redeemed code produced, while the store remembers it."""
        ...
