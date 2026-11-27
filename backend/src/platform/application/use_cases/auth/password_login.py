"""
Step one of the web login: e-mail address (or `system` for the system user)
plus password. The outcome is
a session, a TOTP challenge, or a forced 2FA enrolment.

The order of the checks is the security contract. The throttle runs before
the password, every wrong password counts whether or not the address exists,
and an unknown address still costs one bcrypt verification, so neither timing
nor the answer tells whether an account exists. An inactive account is only
reported after its password was proven.
"""

from src.platform.application.dto.login_dto import PasswordLoginCommand
from src.platform.application.dto.login_dto import PasswordLoginResult
from src.platform.application.dto.login_dto import TotpChallengeIssued
from src.platform.application.dto.login_dto import TotpSetupRequired
from src.platform.application.services.login_session import LoginSession
from src.platform.application.services.login_throttle import LoginThrottle
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InactiveUserError
from src.platform.domain.exceptions import InvalidCredentialsError
from src.platform.domain.services.login_rules import effective_trusted_device_days
from src.platform.domain.services.login_rules import totp_enrolment_required
from src.platform.domain.value_objects.security_event_type import LoginMethod
from src.platform.domain.value_objects.security_event_type import LoginRefusal
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.login_attempts import ILoginAttemptTracker
from src.platform.ports.outbound.password_hasher import IPasswordHasher
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.trusted_device_repository import (
    ITrustedDeviceRepository,
)
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.token_service import ITokenService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# A bcrypt hash of a random string, verified against when the address is
# unknown, so that path costs as much as a wrong password.
_DUMMY_HASH = "$2b$12$fuSIX6TgMhryDjy9gxMCau0TYvGep111hpImJ01kir.DPro1YzoC."


class PasswordLogin:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        trusted_device_repo: ITrustedDeviceRepository,
        attempts: ILoginAttemptTracker,
        hasher: IPasswordHasher,
        tokens: ITokenService,
        secrets: ISecretHasher,
        login_session: LoginSession,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._users = user_repo
        self._settings = settings_repo
        self._devices = trusted_device_repo
        self._throttle = LoginThrottle(attempts)
        self._hasher = hasher
        self._tokens = tokens
        self._secrets = secrets
        self._login_session = login_session
        self._audit = audit
        self._uow = uow

    async def execute(self, cmd: PasswordLoginCommand) -> PasswordLoginResult:
        security = await self._settings.get_security()
        await self._throttle.assert_allowed(cmd.login, cmd.context.client_ip)

        user = await self._users.get_by_login(cmd.login)
        if user is None or user.is_service_account:
            await self._hasher.verify(cmd.password, _DUMMY_HASH)
            await self._refuse(cmd, None, LoginRefusal.INVALID_CREDENTIALS, security_count=True)
            raise InvalidCredentialsError("Invalid e-mail address or password.")
        if not await self._hasher.verify(cmd.password, user.hashed_password):
            await self._refuse(cmd, user, LoginRefusal.INVALID_CREDENTIALS, security_count=True)
            raise InvalidCredentialsError("Invalid e-mail address or password.")
        if not user.is_active:
            await self._refuse(cmd, user, LoginRefusal.INACTIVE)
            raise InactiveUserError("This account is disabled.")

        await self._throttle.record_success(cmd.login)

        if user.totp_enabled:
            trust_days = effective_trusted_device_days(user, security.totp_trusted_device_days)
            if (
                trust_days > 0
                and cmd.trusted_device_secret
                and await self._redeem_trusted_device(user, cmd.trusted_device_secret)
            ):
                return await self._login_session.issue(
                    user,
                    method=LoginMethod.PASSWORD,
                    context=cmd.context,
                    trusted_device_used=True,
                )
            return TotpChallengeIssued(
                partial_token=self._tokens.partial_token(user.id),
                trusted_device_days=trust_days,
            )

        # Required but never set up: rather than refusing, which would lock
        # everyone out the moment an admin flips the switch, hand back a
        # token good only for the enrolment endpoints. The system user
        # always lands here until it has enrolled.
        if totp_enrolment_required(user, enforce_totp=security.enforce_totp):
            return TotpSetupRequired(
                setup_token=self._tokens.setup_token(user.id, user.token_version)
            )

        return await self._login_session.issue(
            user, method=LoginMethod.PASSWORD, context=cmd.context
        )

    async def _refuse(
        self,
        cmd: PasswordLoginCommand,
        user: User | None,
        reason: LoginRefusal,
        *,
        security_count: bool = False,
    ) -> None:
        locked: list[str] = []
        if security_count:
            security = await self._settings.get_security()
            locked = await self._throttle.record_failure(cmd.login, cmd.context.client_ip, security)
        await self._audit.record(
            SecurityEventType.LOGIN,
            actor=user,
            target=user,
            context=cmd.context,
            outcome=SecurityEventOutcome.FAILURE,
            detail={"method": LoginMethod.PASSWORD.value, "reason": reason.value},
        )
        if locked:
            await self._audit.record(
                SecurityEventType.LOGIN_THROTTLED,
                actor=user,
                target=user,
                context=cmd.context,
                outcome=SecurityEventOutcome.FAILURE,
                detail={"scopes": locked},
            )
        await self._uow.commit()

    async def _redeem_trusted_device(self, user: User, secret: str) -> bool:
        device = await self._devices.get_by_token_hash(self._secrets.hash(secret))
        if device is None or device.user_id != user.id or not device.is_usable:
            return False
        device.last_used_at = now_utc()
        await self._devices.save(device)
        return True
