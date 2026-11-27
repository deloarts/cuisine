"""
Resolves the user behind a web token on every request.

A session token is valid while its user exists, is active, still has the
token version the token was signed with (ForceLogout raises it) and its
session row is neither revoked nor past the idle timeout or the absolute
lifetime, which for the system user is a fixed 15 minutes. The activity
stamp is written at most once a minute.
"""

from dataclasses import dataclass

from src.platform.domain.entities.user import User
from src.platform.domain.entities.user_session import UserSession
from src.platform.domain.exceptions import InvalidTokenError
from src.platform.domain.services.session_rules import LAST_SEEN_WRITE_INTERVAL
from src.platform.domain.services.session_rules import session_expired
from src.platform.domain.value_objects import token_scope
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.repositories.user_session_repository import IUserSessionRepository
from src.platform.ports.outbound.token_service import ITokenService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import as_utc
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class WebIdentity:
    user: User
    scope: str
    # None for a setup token, which has no session row.
    session: UserSession | None


class ValidateWebToken:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        session_repo: IUserSessionRepository,
        settings_repo: ISettingsRepository,
        tokens: ITokenService,
        uow: IUnitOfWork,
    ) -> None:
        self._users = user_repo
        self._sessions = session_repo
        self._settings = settings_repo
        self._tokens = tokens
        self._uow = uow

    async def execute(
        self,
        token: str,
        *,
        allowed_scopes: frozenset[str] = frozenset({token_scope.SESSION}),
    ) -> WebIdentity:
        claims = self._tokens.read(token)
        if claims is None or claims.sub is None or claims.scope not in allowed_scopes:
            raise InvalidTokenError("Not authenticated")
        if claims.scope not in (token_scope.SESSION, token_scope.TOTP_SETUP):
            raise InvalidTokenError("Not authenticated")
        user = await self._users.get(int(claims.sub))
        if user is None or not user.is_active or user.is_service_account:
            raise InvalidTokenError("Not authenticated")
        if claims.ver != user.token_version:
            raise InvalidTokenError("Session invalidated")

        if claims.scope == token_scope.TOTP_SETUP:
            return WebIdentity(user=user, scope=claims.scope, session=None)

        session = await self._sessions.get_by_public_id(claims.sid or "")
        if session is None or session.user_id != user.id:
            raise InvalidTokenError("Session invalidated")
        now = now_utc()
        security = await self._settings.get_security()
        if session_expired(session, security, now, is_systemuser=user.is_systemuser):
            raise InvalidTokenError("Session expired")
        if now - as_utc(session.last_seen_at) >= LAST_SEEN_WRITE_INTERVAL:
            session.last_seen_at = now
            session = await self._sessions.save(session)
            await self._uow.commit()
        return WebIdentity(user=user, scope=claims.scope, session=session)
