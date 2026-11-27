"""
Setting up and turning off TOTP on the user's own account.

Enrolment stores a fresh secret that is not active until a code from the
authenticator confirms it, so a half-finished setup never locks anybody
out. A user who was forced into enrolment at login arrives with a setup
token and receives a real session from the confirmation. A signed-in
session must confirm the current password to enrol, so a stolen session
cookie cannot put the thief's authenticator on the account; the setup
token is issued only after the password was proven.
"""

from dataclasses import dataclass

from src.platform.application.dto.context import RequestContext
from src.platform.application.dto.login_dto import SessionIssued
from src.platform.application.services.login_session import LoginSession
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.use_cases.account.own_profile import confirm_password
from src.platform.application.use_cases.auth.totp_login import verify_totp_once
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidTotpCodeError
from src.platform.domain.exceptions import TotpAlreadyEnabledError
from src.platform.domain.exceptions import TotpNotEnrolledError
from src.platform.domain.exceptions import TotpRequiredError
from src.platform.domain.services.login_rules import assert_can_disable_totp
from src.platform.domain.value_objects.security_event_type import LoginMethod
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.password_hasher import IPasswordHasher
from src.platform.ports.outbound.replay_guard import IReplayGuard
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.trusted_device_repository import (
    ITrustedDeviceRepository,
)
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.totp_service import ITotpService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class TotpEnrolment:
    secret: str
    provisioning_uri: str


class ManageOwnTotp:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        trusted_device_repo: ITrustedDeviceRepository,
        totp: ITotpService,
        replay: IReplayGuard,
        hasher: IPasswordHasher,
        login_session: LoginSession,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._users = user_repo
        self._settings = settings_repo
        self._devices = trusted_device_repo
        self._totp = totp
        self._replay = replay
        self._hasher = hasher
        self._login_session = login_session
        self._audit = audit
        self._uow = uow

    async def enroll(
        self,
        user: User,
        *,
        password: str | None,
        via_setup_token: bool,
        context: RequestContext,
    ) -> TotpEnrolment:
        if user.totp_enabled:
            raise TotpAlreadyEnabledError("Two-factor authentication is already on.")
        if not via_setup_token:
            await confirm_password(
                self._hasher, self._audit, self._uow, user, password or "", context
            )
        secret = self._totp.generate_secret()
        user.totp_secret = secret
        await self._users.save(user)
        await self._uow.commit()
        issuer = (await self._settings.get_general()).instance_name
        return TotpEnrolment(
            secret=secret,
            provisioning_uri=self._totp.provisioning_uri(secret, user.email, issuer),
        )

    async def confirm(
        self, user: User, code: str, *, via_setup_token: bool, context: RequestContext
    ) -> SessionIssued | None:
        if user.totp_enabled:
            raise TotpAlreadyEnabledError("Two-factor authentication is already on.")
        if not user.totp_secret:
            raise TotpNotEnrolledError("Start the setup first.")
        if not await verify_totp_once(self._totp, self._replay, user.id, user.totp_secret, code):
            raise InvalidTotpCodeError("The code is wrong or expired.")
        user.totp_enabled = True
        await self._users.save(user)
        await self._audit.record(
            SecurityEventType.TOTP_ENABLED, actor=user, target=user, context=context
        )
        if via_setup_token:
            return await self._login_session.issue(
                user, method=LoginMethod.TOTP_ENROLMENT, context=context
            )
        await self._uow.commit()
        return None

    async def disable(self, user: User, password: str, *, context: RequestContext) -> None:
        assert_can_disable_totp(user)
        if (await self._settings.get_security()).enforce_totp:
            raise TotpRequiredError("Two-factor authentication is required on this instance.")
        await confirm_password(self._hasher, self._audit, self._uow, user, password, context)
        user.totp_enabled = False
        user.totp_secret = None
        await self._users.save(user)
        await self._devices.revoke_all(user.id, now_utc())
        await self._audit.record(
            SecurityEventType.TOTP_DISABLED, actor=user, target=user, context=context
        )
        await self._uow.commit()
