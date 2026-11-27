"""
Personal access tokens (a user's own, acting as them) and API keys
(admin-issued, acting as a service account of their own). The plain secret
is returned once at creation and never again.
"""

from dataclasses import dataclass
from datetime import datetime

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.const import API_KEY_PREFIX
from src.platform.const import PAT_PREFIX
from src.platform.domain.entities.api_key import ApiKey
from src.platform.domain.entities.personal_access_token import PersonalAccessToken
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import ConsentRequiredError
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import TokenNotFoundError
from src.platform.domain.services.permission_rules import assert_grantable_to_token
from src.platform.domain.services.token_lifetime import assert_token_lifetime
from src.platform.domain.value_objects.permission import Permission
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.api_key_repository import IApiKeyRepository
from src.platform.ports.outbound.repositories.pat_repository import IPatRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class TokenCommand:
    name: str
    permissions: list[str]
    expires_at: datetime | None = None


@dataclass(frozen=True)
class CreatedPat:
    token: PersonalAccessToken
    secret: str


@dataclass(frozen=True)
class CreatedApiKey:
    key: ApiKey
    service_user: User
    secret: str


def _name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise InvalidInputError("The name must not be empty.")
    return cleaned[:64]


class ManagePats:
    def __init__(
        self,
        *,
        pat_repo: IPatRepository,
        settings_repo: ISettingsRepository,
        secrets: ISecretHasher,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._pats = pat_repo
        self._settings = settings_repo
        self._secrets = secrets
        self._audit = audit
        self._uow = uow

    async def list_all(self, user: User) -> list[PersonalAccessToken]:
        return await self._pats.list_for_user(user.id)

    async def create(self, user: User, cmd: TokenCommand, *, context: RequestContext) -> CreatedPat:
        assert_grantable_to_token(user, cmd.permissions)
        now = now_utc()
        security = await self._settings.get_security()
        assert_token_lifetime(cmd.expires_at, security.token_max_lifetime_days, now)
        if Permission.USE_MCP in cmd.permissions and user.consent_ai_agents_at is None:
            raise ConsentRequiredError(
                "An agent token needs your consent to AI agents first (Account, Consents)."
            )
        if Permission.USE_MCP in cmd.permissions:
            # An agent token is held by software that reads untrusted
            # content, so its own, shorter cap applies on top.
            agents = await self._settings.get_agents()
            assert_token_lifetime(cmd.expires_at, agents.token_max_lifetime_days, now)
        secret = self._secrets.generate(PAT_PREFIX)
        token = await self._pats.save(
            PersonalAccessToken(
                user_id=user.id,
                name=_name(cmd.name),
                token_hash=self._secrets.hash(secret),
                token_prefix=self._secrets.display_prefix(secret, PAT_PREFIX),
                permissions=sorted(set(cmd.permissions)),
                created=now,
                expires_at=cmd.expires_at,
            )
        )
        await self._audit.record(
            SecurityEventType.PAT_CREATED,
            actor=user,
            target=user,
            context=context,
            detail={"name": token.name, "permissions": token.permissions},
        )
        await self._uow.commit()
        return CreatedPat(token=token, secret=secret)

    async def revoke(self, user: User, public_id: str, *, context: RequestContext) -> None:
        token = await self._pats.get_by_public_id(public_id)
        if token is None or token.user_id != user.id or token.revoked_at is not None:
            raise TokenNotFoundError("No such token.")
        token.revoked_at = now_utc()
        await self._pats.save(token)
        await self._audit.record(
            SecurityEventType.PAT_REVOKED,
            actor=user,
            target=user,
            context=context,
            detail={"name": token.name},
        )
        await self._uow.commit()


class ManageApiKeys:
    def __init__(
        self,
        *,
        key_repo: IApiKeyRepository,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        secrets: ISecretHasher,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._keys = key_repo
        self._users = user_repo
        self._settings = settings_repo
        self._secrets = secrets
        self._audit = audit
        self._uow = uow

    async def list_all(self) -> list[tuple[ApiKey, User | None]]:
        keys = await self._keys.list_all()
        return [(key, await self._users.get(key.service_user_id)) for key in keys]

    async def create(
        self, actor: User, cmd: TokenCommand, *, context: RequestContext
    ) -> CreatedApiKey:
        assert_grantable_to_token(actor, cmd.permissions)
        now = now_utc()
        security = await self._settings.get_security()
        assert_token_lifetime(cmd.expires_at, security.token_max_lifetime_days, now)
        if Permission.USE_MCP in cmd.permissions:
            # An agent token is held by software that reads untrusted
            # content, so its own, shorter cap applies on top.
            agents = await self._settings.get_agents()
            assert_token_lifetime(cmd.expires_at, agents.token_max_lifetime_days, now)
        name = _name(cmd.name)
        secret = self._secrets.generate(API_KEY_PREFIX)
        service_user = User(
            full_name=name,
            email="",
            created=now,
            # No password can ever match "!", so the account cannot log in.
            hashed_password="!",
            is_service_account=True,
            permissions=sorted(set(cmd.permissions)),
        )
        # E-mail addresses are unique; a service account takes one derived
        # from its public id under a domain nobody can register by hand.
        service_user.email = f"svc-{service_user.public_id.hex[:12]}@service.invalid"
        service_user = await self._users.save(service_user)
        key = await self._keys.save(
            ApiKey(
                name=name,
                token_hash=self._secrets.hash(secret),
                token_prefix=self._secrets.display_prefix(secret, API_KEY_PREFIX),
                service_user_id=service_user.id,
                creator_id=actor.id,
                created=now,
                expires_at=cmd.expires_at,
            )
        )
        await self._audit.record(
            SecurityEventType.API_KEY_CREATED,
            actor=actor,
            target=service_user,
            context=context,
            detail={"name": name, "permissions": service_user.permissions},
        )
        await self._uow.commit()
        return CreatedApiKey(key=key, service_user=service_user, secret=secret)

    async def revoke(self, actor: User, public_id: str, *, context: RequestContext) -> None:
        key = await self._keys.get_by_public_id(public_id)
        if key is None or key.revoked_at is not None:
            raise TokenNotFoundError("No such API key.")
        key.revoked_at = now_utc()
        await self._keys.save(key)
        service_user = await self._users.get(key.service_user_id)
        if service_user is not None:
            service_user.is_active = False
            await self._users.save(service_user)
        await self._audit.record(
            SecurityEventType.API_KEY_REVOKED,
            actor=actor,
            target=service_user,
            context=context,
            detail={"name": key.name},
        )
        await self._uow.commit()
