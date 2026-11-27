"""
Resolves the user behind a personal access token or an API key.

A PAT acts as its owner, narrowed to the token's own permissions; the
returned user carries exactly those, so every later permission check sees
the narrowed set. An API key acts as its service account.
"""

from dataclasses import replace

from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidTokenError
from src.platform.domain.services.session_rules import LAST_SEEN_WRITE_INTERVAL
from src.platform.ports.outbound.repositories.api_key_repository import IApiKeyRepository
from src.platform.ports.outbound.repositories.pat_repository import IPatRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import as_utc
from src.shared_kernel.domain.services.clock import now_utc


class ValidatePat:
    def __init__(
        self,
        *,
        pat_repo: IPatRepository,
        user_repo: IUserRepository,
        secrets: ISecretHasher,
        uow: IUnitOfWork,
    ) -> None:
        self._pats = pat_repo
        self._users = user_repo
        self._secrets = secrets
        self._uow = uow

    async def execute(self, token: str) -> User:
        if not token:
            raise InvalidTokenError("Missing token")
        pat = await self._pats.get_by_token_hash(self._secrets.hash(token))
        if pat is None or not pat.is_usable:
            raise InvalidTokenError("Invalid or expired token")
        owner = await self._users.get(pat.user_id)
        if owner is None or not owner.is_active:
            raise InvalidTokenError("Invalid or expired token")
        now = now_utc()
        if pat.last_used_at is None or now - as_utc(pat.last_used_at) >= LAST_SEEN_WRITE_INTERVAL:
            pat.last_used_at = now
            await self._pats.save(pat)
            await self._uow.commit()
        # The token's permissions, still capped by what the owner holds now,
        # so revoking a grant from the owner also narrows their tokens.
        allowed = (
            sorted(set(pat.permissions) & set(owner.effective_permissions))
            if not (owner.is_systemuser)
            else sorted(pat.permissions)
        )
        return replace(owner, permissions=allowed, group_permissions=[], is_systemuser=False)


class ValidateApiKey:
    def __init__(
        self,
        *,
        key_repo: IApiKeyRepository,
        user_repo: IUserRepository,
        secrets: ISecretHasher,
        uow: IUnitOfWork,
    ) -> None:
        self._keys = key_repo
        self._users = user_repo
        self._secrets = secrets
        self._uow = uow

    async def execute(self, token: str) -> User:
        if not token:
            raise InvalidTokenError("Missing API key")
        key = await self._keys.get_by_token_hash(self._secrets.hash(token))
        if key is None or not key.is_usable:
            raise InvalidTokenError("Invalid or expired API key")
        user = await self._users.get(key.service_user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError("Invalid or expired API key")
        now = now_utc()
        if key.last_used_at is None or now - as_utc(key.last_used_at) >= LAST_SEEN_WRITE_INTERVAL:
            key.last_used_at = now
            await self._keys.save(key)
            await self._uow.commit()
        return user
