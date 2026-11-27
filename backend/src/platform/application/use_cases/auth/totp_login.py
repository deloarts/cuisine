"""
Step two of the web login: the TOTP code, redeemed with the partial token
the password step handed out. A code is accepted once only, so an
intercepted code cannot be replayed within its validity; a replay is
answered like a wrong code.
"""

from src.platform.application.dto.login_dto import SessionIssued
from src.platform.application.dto.login_dto import TotpLoginCommand
from src.platform.application.services.login_session import LoginSession
from src.platform.application.services.login_throttle import LOCKED_MESSAGE
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.exceptions import InvalidTokenError
from src.platform.domain.exceptions import InvalidTotpCodeError
from src.platform.domain.exceptions import LoginLockedError
from src.platform.domain.services.login_rules import effective_trusted_device_days
from src.platform.domain.value_objects import token_scope
from src.platform.domain.value_objects.security_event_type import LoginMethod
from src.platform.domain.value_objects.security_event_type import LoginRefusal
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.login_attempts import ILoginAttemptTracker
from src.platform.ports.outbound.replay_guard import IReplayGuard
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.token_service import ITokenService
from src.platform.ports.outbound.totp_service import ITotpService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork

TOTP_REPLAY_TTL_SECONDS = 90


def totp_attempt_key(user_id: int) -> str:
    return f"totp:{user_id}"


async def verify_totp_once(
    totp: ITotpService, replay: IReplayGuard, user_id: int, secret: str, code: str
) -> bool:
    """Whether the code is right and this is its first use."""
    normalised = code.strip().replace(" ", "")
    if not totp.verify(secret, normalised):
        return False
    return await replay.consume_once(f"totp:{user_id}:{normalised}", TOTP_REPLAY_TTL_SECONDS)


class TotpLogin:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        attempts: ILoginAttemptTracker,
        replay: IReplayGuard,
        totp: ITotpService,
        tokens: ITokenService,
        login_session: LoginSession,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._users = user_repo
        self._settings = settings_repo
        self._attempts = attempts
        self._replay = replay
        self._totp = totp
        self._tokens = tokens
        self._login_session = login_session
        self._audit = audit
        self._uow = uow

    async def execute(self, cmd: TotpLoginCommand) -> SessionIssued:
        claims = self._tokens.read(cmd.partial_token)
        if claims is None or claims.scope != token_scope.TOTP_PENDING or claims.sub is None:
            raise InvalidTokenError("The login step expired. Sign in again.")
        user = await self._users.get(int(claims.sub))
        if user is None or not user.is_active or not user.totp_enabled or not user.totp_secret:
            raise InvalidTokenError("The login step expired. Sign in again.")

        key = totp_attempt_key(user.id)
        locked_for = await self._attempts.lock_ttl(key)
        if locked_for > 0:
            raise LoginLockedError(LOCKED_MESSAGE, retry_after_seconds=locked_for)

        if not await verify_totp_once(
            self._totp, self._replay, user.id, user.totp_secret, cmd.code
        ):
            security = await self._settings.get_security()
            await self._attempts.record_failure(
                key,
                limit=security.max_login_attempts,
                lockout_seconds=security.lockout_duration_minutes * 60,
            )
            await self._audit.record(
                SecurityEventType.LOGIN,
                actor=user,
                target=user,
                context=cmd.context,
                outcome=SecurityEventOutcome.FAILURE,
                detail={
                    "method": LoginMethod.TOTP.value,
                    "reason": LoginRefusal.INVALID_TOTP.value,
                },
            )
            await self._uow.commit()
            raise InvalidTotpCodeError("The code is wrong or expired.")

        await self._attempts.reset(key)
        security = await self._settings.get_security()
        trust_days = (
            effective_trusted_device_days(user, security.totp_trusted_device_days)
            if cmd.trust_device
            else 0
        )
        return await self._login_session.issue(
            user, method=LoginMethod.TOTP, context=cmd.context, trust_device_days=trust_days
        )
