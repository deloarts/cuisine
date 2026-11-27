"""Finishing a login: the session row, the token, the login stamp and the
security log entry, committed together."""

from datetime import timedelta

from src.platform.application.dto.context import RequestContext
from src.platform.application.dto.login_dto import SessionIssued
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.trusted_device import TrustedDevice
from src.platform.domain.entities.user import User
from src.platform.domain.entities.user_session import UserSession
from src.platform.domain.services.session_rules import session_cookie_max_age
from src.platform.domain.services.session_rules import session_hard_expiry
from src.platform.domain.value_objects.security_event_type import LoginMethod
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.trusted_device_repository import (
    ITrustedDeviceRepository,
)
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.repositories.user_session_repository import IUserSessionRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.token_service import ITokenService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

TRUSTED_DEVICE_PREFIX = "td_"


class LoginSession:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        session_repo: IUserSessionRepository,
        trusted_device_repo: ITrustedDeviceRepository,
        settings_repo: ISettingsRepository,
        tokens: ITokenService,
        secrets: ISecretHasher,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._users = user_repo
        self._sessions = session_repo
        self._devices = trusted_device_repo
        self._settings = settings_repo
        self._tokens = tokens
        self._secrets = secrets
        self._audit = audit
        self._uow = uow

    async def issue(
        self,
        user: User,
        *,
        method: LoginMethod,
        context: RequestContext,
        trust_device_days: int = 0,
        trusted_device_used: bool = False,
    ) -> SessionIssued:
        now = now_utc()
        security = await self._settings.get_security()
        user.last_logged_in = now
        await self._users.save(user)
        session = await self._sessions.save(
            UserSession(
                user_id=user.id,
                created=now,
                last_seen_at=now,
                user_agent=(context.user_agent or "")[:512] or None,
                client_ip=context.client_ip,
            )
        )
        device_secret: str | None = None
        if trust_device_days > 0:
            device_secret = self._secrets.generate(TRUSTED_DEVICE_PREFIX)
            await self._devices.save(
                TrustedDevice(
                    user_id=user.id,
                    token_hash=self._secrets.hash(device_secret),
                    created=now,
                    expires_at=now + timedelta(days=trust_device_days),
                    user_agent=(context.user_agent or "")[:512] or None,
                )
            )
        detail: dict[str, object] = {"method": method.value}
        if trusted_device_used:
            detail["trusted_device"] = True
        await self._audit.record(
            SecurityEventType.LOGIN, actor=user, target=user, context=context, detail=detail
        )
        await self._uow.commit()
        return SessionIssued(
            access_token=self._tokens.session_token(
                user.id,
                user.token_version,
                str(session.public_id),
                expires_at=(
                    session_hard_expiry(session, security, is_systemuser=True)
                    if user.is_systemuser
                    else None
                ),
            ),
            cookie_max_age=session_cookie_max_age(security, is_systemuser=user.is_systemuser),
            session_public_id=str(session.public_id),
            trusted_device_secret=device_secret,
            trusted_device_max_age=trust_device_days * 24 * 60 * 60,
        )
