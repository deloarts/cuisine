"""
JWT creation and decoding for the web tokens.

A session token has no exp claim: it is bounded by its server-side session
row (idle timeout, absolute lifetime, revocation), so a stolen token dies the
moment the session is revoked. The system user's token is the exception: it
carries the session's fixed 15 minute end as exp as well, so it dies even if
a row check were ever bypassed. The bridge tokens of the login steps are
short-lived and carry a scope that only their own endpoint accepts.
"""

from datetime import datetime
from datetime import timedelta
from typing import Any

import jwt

from src.platform.domain.value_objects import token_scope
from src.platform.infrastructure.config.settings import cfg
from src.platform.ports.outbound.token_service import TokenClaims
from src.shared_kernel.domain.services.clock import now_utc

PARTIAL_TOKEN_MINUTES = 5
# Enrolment is slower than typing a code you already have: install an
# authenticator, scan a QR code, then type.
SETUP_TOKEN_MINUTES = 15
PASSKEY_CHALLENGE_MINUTES = 5


class JwtTokenService:
    def __init__(self, secret_key: str | None = None, algorithm: str | None = None) -> None:
        self._key = secret_key or cfg.security.secret_key
        self._algorithm = algorithm or cfg.security.algorithm

    def _encode(self, payload: dict[str, Any]) -> str:
        token: str = jwt.encode(payload, self._key, algorithm=self._algorithm)
        return token

    def session_token(
        self,
        user_id: int,
        token_version: int,
        session_public_id: str,
        *,
        expires_at: datetime | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "ver": token_version,
            "sid": session_public_id,
        }
        if expires_at is not None:
            payload["exp"] = expires_at
        return self._encode(payload)

    def partial_token(self, user_id: int) -> str:
        return self._encode(
            {
                "sub": str(user_id),
                "scope": token_scope.TOTP_PENDING,
                "exp": now_utc() + timedelta(minutes=PARTIAL_TOKEN_MINUTES),
            }
        )

    def setup_token(self, user_id: int, token_version: int) -> str:
        return self._encode(
            {
                "sub": str(user_id),
                "ver": token_version,
                "scope": token_scope.TOTP_SETUP,
                "exp": now_utc() + timedelta(minutes=SETUP_TOKEN_MINUTES),
            }
        )

    def passkey_challenge_token(
        self, challenge: str, scope: str, user_id: int | None = None
    ) -> str:
        payload: dict[str, Any] = {
            "scope": scope,
            "chl": challenge,
            "exp": now_utc() + timedelta(minutes=PASSKEY_CHALLENGE_MINUTES),
        }
        if user_id is not None:
            payload["sub"] = str(user_id)
        return self._encode(payload)

    def read(self, token: str) -> TokenClaims | None:
        if not token:
            return None
        try:
            raw = jwt.decode(token, self._key, algorithms=[self._algorithm])
        except jwt.PyJWTError:
            return None
        if not isinstance(raw, dict):
            return None
        ver = raw.get("ver")
        return TokenClaims(
            sub=str(raw["sub"]) if raw.get("sub") is not None else None,
            ver=ver if isinstance(ver, int) else None,
            scope=str(raw.get("scope") or token_scope.SESSION),
            sid=str(raw["sid"]) if raw.get("sid") is not None else None,
            chl=str(raw["chl"]) if raw.get("chl") is not None else None,
        )
