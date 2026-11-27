"""Registering, renaming and removing the user's own passkeys."""

from typing import Any

from src.platform.application.dto.context import RequestContext
from src.platform.application.dto.login_dto import PasskeyChallenge
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.passkey import Passkey
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import DuplicatePasskeyError
from src.platform.domain.exceptions import InvalidTokenError
from src.platform.domain.exceptions import PasskeyNotFoundError
from src.platform.domain.services.login_rules import assert_can_use_passkeys
from src.platform.domain.value_objects import token_scope
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.passkey_verifier import IPasskeyVerifier
from src.platform.ports.outbound.replay_guard import IReplayGuard
from src.platform.ports.outbound.repositories.passkey_repository import IPasskeyRepository
from src.platform.ports.outbound.token_service import ITokenService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

CHALLENGE_TTL_SECONDS = 600


class ManageOwnPasskeys:
    def __init__(
        self,
        *,
        passkey_repo: IPasskeyRepository,
        verifier: IPasskeyVerifier,
        replay: IReplayGuard,
        tokens: ITokenService,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._passkeys = passkey_repo
        self._verifier = verifier
        self._replay = replay
        self._tokens = tokens
        self._audit = audit
        self._uow = uow

    async def list_all(self, user: User) -> list[Passkey]:
        return await self._passkeys.list_for_user(user.id)

    async def registration_options(self, user: User) -> PasskeyChallenge:
        assert_can_use_passkeys(user)
        existing = await self._passkeys.list_for_user(user.id)
        opts = self._verifier.registration_options(
            # The user handle is the account's opaque public id, never the
            # sequential id or the e-mail address.
            user_handle=user.public_id.bytes,
            account_name=user.email,
            display_name=user.full_name,
            exclude_credential_ids=[p.credential_id for p in existing],
        )
        return PasskeyChallenge(
            options=opts.options,
            challenge_token=self._tokens.passkey_challenge_token(
                opts.challenge, token_scope.PASSKEY_REGISTRATION, user.id
            ),
        )

    async def register(
        self,
        user: User,
        *,
        challenge_token: str,
        credential: dict[str, Any],
        name: str,
        context: RequestContext,
    ) -> Passkey:
        assert_can_use_passkeys(user)
        claims = self._tokens.read(challenge_token)
        if (
            claims is None
            or claims.scope != token_scope.PASSKEY_REGISTRATION
            or claims.sub != str(user.id)
            or not claims.chl
        ):
            raise InvalidTokenError("The passkey prompt expired. Try again.")
        if not await self._replay.consume_once(f"passkey:{claims.chl}", CHALLENGE_TTL_SECONDS):
            raise InvalidTokenError("The passkey prompt expired. Try again.")
        verified = self._verifier.verify_registration(credential=credential, challenge=claims.chl)
        if await self._passkeys.get_by_credential_id(verified.credential_id) is not None:
            raise DuplicatePasskeyError("This passkey is already registered.")
        passkey = await self._passkeys.save(
            Passkey(
                user_id=user.id,
                name=name.strip()[:64] or "Passkey",
                credential_id=verified.credential_id,
                public_key=verified.public_key,
                sign_count=verified.sign_count,
                backed_up=verified.backed_up,
                transports=verified.transports,
                created=now_utc(),
            )
        )
        await self._audit.record(
            SecurityEventType.PASSKEY_ADDED,
            actor=user,
            target=user,
            context=context,
            detail={"name": passkey.name},
        )
        await self._uow.commit()
        return passkey

    async def _own(self, user: User, public_id: str) -> Passkey:
        passkey = await self._passkeys.get_by_public_id(public_id)
        if passkey is None or passkey.user_id != user.id:
            raise PasskeyNotFoundError("No such passkey.")
        return passkey

    async def rename(self, user: User, public_id: str, name: str) -> Passkey:
        passkey = await self._own(user, public_id)
        passkey.name = name.strip()[:64] or passkey.name
        saved = await self._passkeys.save(passkey)
        await self._uow.commit()
        return saved

    async def remove(self, user: User, public_id: str, *, context: RequestContext) -> None:
        passkey = await self._own(user, public_id)
        await self._passkeys.delete(passkey)
        await self._audit.record(
            SecurityEventType.PASSKEY_REMOVED,
            actor=user,
            target=user,
            context=context,
            detail={"name": passkey.name},
        )
        await self._uow.commit()
