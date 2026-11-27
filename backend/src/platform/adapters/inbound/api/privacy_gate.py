"""
Blocks a signed-in user who has not acknowledged the current privacy
statement. Every web and PAT request answers 403 with the code
PrivacyAcknowledgementRequiredError, except reading the own profile,
reading the statement, acknowledging or declining it, and signing out. The
current version is cached per worker for a few seconds; the worker that
publishes a version forgets it at once.
"""

import time

from fastapi import Request

from src.platform.adapters.outbound.persistence.repositories.legal_repository import (
    SqlAlchemyLegalRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.legal import LegalVersion
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PrivacyAcknowledgementRequiredError
from src.platform.domain.services.legal_rules import acknowledgement_pending

CACHE_SECONDS = 3.0
_OPEN = (
    ("GET", "/api/v1/web/users/me"),
    ("POST", "/api/v1/web/users/me/privacy/acknowledge"),
    ("POST", "/api/v1/web/users/me/privacy/decline"),
)
_OPEN_PREFIXES = ("/api/v1/auth/", "/api/v1/public/")


class PrivacyState:
    def __init__(self) -> None:
        self._value: LegalVersion | None = None
        self._read_at: float | None = None

    async def current(self) -> LegalVersion | None:
        if self._read_at is None or time.monotonic() - self._read_at > CACHE_SECONDS:
            async with SessionLocal() as db:
                self._value = await SqlAlchemyLegalRepository(db).current(LegalKind.PRIVACY)
            self._read_at = time.monotonic()
        return self._value

    def forget(self) -> None:
        self._read_at = None


privacy_state = PrivacyState()


async def enforce_privacy_acknowledgement(request: Request, user: User) -> None:
    path = request.url.path
    if (request.method, path) in _OPEN or path.startswith(_OPEN_PREFIXES):
        return
    if acknowledgement_pending(user, await privacy_state.current()):
        raise PrivacyAcknowledgementRequiredError(
            "Read and acknowledge the current privacy statement first."
        )
