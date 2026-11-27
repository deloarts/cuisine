"""The user's own signed-in browsers and trusted devices."""

from dataclasses import dataclass
from datetime import datetime

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.trusted_device import TrustedDevice
from src.platform.domain.entities.user import User
from src.platform.domain.entities.user_session import UserSession
from src.platform.domain.exceptions import SessionNotFoundError
from src.platform.domain.exceptions import TrustedDeviceNotFoundError
from src.platform.domain.services.session_rules import session_expired
from src.platform.domain.services.session_rules import session_hard_expiry
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.trusted_device_repository import (
    ITrustedDeviceRepository,
)
from src.platform.ports.outbound.repositories.user_session_repository import IUserSessionRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class CurrentSession:
    """When the session making the request ends at the latest, and the
    server's clock, so a client can correct for a skewed one."""

    expires_at: datetime | None
    server_time: datetime


class ManageOwnSessions:
    def __init__(
        self,
        *,
        session_repo: IUserSessionRepository,
        settings_repo: ISettingsRepository,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._sessions = session_repo
        self._settings = settings_repo
        self._audit = audit
        self._uow = uow

    async def list_all(self, user: User) -> list[UserSession]:
        security = await self._settings.get_security()
        now = now_utc()
        return [
            s
            for s in await self._sessions.list_active(user.id)
            if not session_expired(s, security, now, is_systemuser=user.is_systemuser)
        ]

    async def current(self, user: User, session: UserSession | None) -> CurrentSession:
        """The absolute end of the given session; None when it has no
        lifetime or when there is no session."""
        expires_at = None
        if session is not None and session.user_id == user.id:
            expires_at = session_hard_expiry(
                session,
                await self._settings.get_security(),
                is_systemuser=user.is_systemuser,
            )
        return CurrentSession(expires_at=expires_at, server_time=now_utc())

    async def revoke(self, user: User, public_id: str, *, context: RequestContext) -> None:
        session = await self._sessions.get_by_public_id(public_id)
        if session is None or session.user_id != user.id or session.revoked_at is not None:
            raise SessionNotFoundError("No such session.")
        session.revoked_at = now_utc()
        await self._sessions.save(session)
        await self._audit.record(
            SecurityEventType.SESSION_REVOKED,
            actor=user,
            target=user,
            context=context,
            detail={"session": public_id},
        )
        await self._uow.commit()

    async def revoke_others(
        self, user: User, current_public_id: str | None, *, context: RequestContext
    ) -> int:
        count = await self._sessions.revoke_all(
            user.id, now_utc(), except_public_id=current_public_id
        )
        await self._audit.record(
            SecurityEventType.SESSION_REVOKED,
            actor=user,
            target=user,
            context=context,
            detail={"others": count},
        )
        await self._uow.commit()
        return count


class ManageOwnTrustedDevices:
    def __init__(
        self,
        *,
        trusted_device_repo: ITrustedDeviceRepository,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._devices = trusted_device_repo
        self._audit = audit
        self._uow = uow

    async def list_all(self, user: User) -> list[TrustedDevice]:
        return await self._devices.list_usable(user.id)

    async def revoke(self, user: User, public_id: str, *, context: RequestContext) -> None:
        device = await self._devices.get_by_public_id(public_id)
        if device is None or device.user_id != user.id or device.revoked_at is not None:
            raise TrustedDeviceNotFoundError("No such trusted device.")
        device.revoked_at = now_utc()
        await self._devices.save(device)
        await self._audit.record(
            SecurityEventType.TRUSTED_DEVICE_REVOKED, actor=user, target=user, context=context
        )
        await self._uow.commit()

    async def revoke_all(self, user: User, *, context: RequestContext) -> int:
        count = await self._devices.revoke_all(user.id, now_utc())
        await self._audit.record(
            SecurityEventType.TRUSTED_DEVICE_REVOKED,
            actor=user,
            target=user,
            context=context,
            detail={"all": count},
        )
        await self._uow.commit()
        return count
