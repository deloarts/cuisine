"""Signs and reads the short-lived web tokens: sessions, TOTP challenges,
TOTP setup and passkey challenges."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class TokenClaims:
    sub: str | None
    ver: int | None
    scope: str
    sid: str | None
    chl: str | None


class ITokenService(Protocol):
    def session_token(
        self,
        user_id: int,
        token_version: int,
        session_public_id: str,
        *,
        expires_at: datetime | None = None,
    ) -> str: ...
    def partial_token(self, user_id: int) -> str: ...
    def setup_token(self, user_id: int, token_version: int) -> str: ...
    def passkey_challenge_token(
        self, challenge: str, scope: str, user_id: int | None = None
    ) -> str: ...
    def read(self, token: str) -> TokenClaims | None:
        """The claims of a valid, unexpired token, None otherwise."""
        ...
