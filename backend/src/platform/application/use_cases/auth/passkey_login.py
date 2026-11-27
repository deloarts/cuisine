"""
The passkey login: options first, then the signed assertion. No server-side
state is kept in between; the challenge travels in a short-lived signed
token and is claimed once, so a token cannot be redeemed twice. A passkey
replaces the password and the second factor, because the authenticator
verified the user before it signed.
"""

from src.platform.application.dto.login_dto import PasskeyChallenge
from src.platform.application.dto.login_dto import PasskeyLoginCommand
from src.platform.application.dto.login_dto import SessionIssued
from src.platform.application.services.login_session import LoginSession
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.exceptions import InactiveUserError
from src.platform.domain.exceptions import InvalidTokenError
from src.platform.domain.exceptions import PasskeyRejectedError
from src.platform.domain.value_objects import token_scope
from src.platform.domain.value_objects.security_event_type import LoginMethod
from src.platform.domain.value_objects.security_event_type import LoginRefusal
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.passkey_verifier import IPasskeyVerifier
from src.platform.ports.outbound.replay_guard import IReplayGuard
from src.platform.ports.outbound.repositories.passkey_repository import IPasskeyRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.token_service import ITokenService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

CHALLENGE_TTL_SECONDS = 600


class PasskeyLogin:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        passkey_repo: IPasskeyRepository,
        verifier: IPasskeyVerifier,
        replay: IReplayGuard,
        tokens: ITokenService,
        login_session: LoginSession,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._users = user_repo
        self._passkeys = passkey_repo
        self._verifier = verifier
        self._replay = replay
        self._tokens = tokens
        self._login_session = login_session
        self._audit = audit
        self._uow = uow

    def options(self) -> PasskeyChallenge:
        opts = self._verifier.authentication_options()
        return PasskeyChallenge(
            options=opts.options,
            challenge_token=self._tokens.passkey_challenge_token(
                opts.challenge, token_scope.PASSKEY_LOGIN
            ),
        )

    async def execute(self, cmd: PasskeyLoginCommand) -> SessionIssued:
        claims = self._tokens.read(cmd.challenge_token)
        if claims is None or claims.scope != token_scope.PASSKEY_LOGIN or not claims.chl:
            raise InvalidTokenError("The passkey prompt expired. Try again.")
        if not await self._replay.consume_once(f"passkey:{claims.chl}", CHALLENGE_TTL_SECONDS):
            raise InvalidTokenError("The passkey prompt expired. Try again.")

        credential_id = self._verifier.credential_id_of(cmd.credential)
        passkey = (
            await self._passkeys.get_by_credential_id(credential_id) if credential_id else None
        )
        if passkey is None:
            raise PasskeyRejectedError("This passkey is not registered.")
        user = await self._users.get(passkey.user_id)
        if user is None or user.is_service_account:
            raise PasskeyRejectedError("This passkey is not registered.")

        try:
            new_count = self._verifier.verify_authentication(
                credential=cmd.credential,
                challenge=claims.chl,
                public_key=passkey.public_key,
                sign_count=passkey.sign_count,
            )
        except PasskeyRejectedError:
            await self._audit.record(
                SecurityEventType.LOGIN,
                actor=user,
                target=user,
                context=cmd.context,
                outcome=SecurityEventOutcome.FAILURE,
                detail={
                    "method": LoginMethod.PASSKEY.value,
                    "reason": LoginRefusal.PASSKEY_REJECTED.value,
                },
            )
            await self._uow.commit()
            raise
        if not user.is_active:
            raise InactiveUserError("This account is disabled.")
        # Registration refuses the system user, so such a passkey can only be
        # a leftover; its sign-in needs the password and the code.
        if user.is_systemuser:
            await self._audit.record(
                SecurityEventType.LOGIN,
                actor=user,
                target=user,
                context=cmd.context,
                outcome=SecurityEventOutcome.FAILURE,
                detail={
                    "method": LoginMethod.PASSKEY.value,
                    "reason": LoginRefusal.PASSKEY_REJECTED.value,
                },
            )
            await self._uow.commit()
            raise PasskeyRejectedError("This account cannot use passkeys.")

        passkey.sign_count = new_count
        passkey.last_used_at = now_utc()
        await self._passkeys.save(passkey)
        return await self._login_session.issue(
            user, method=LoginMethod.PASSKEY, context=cmd.context
        )
