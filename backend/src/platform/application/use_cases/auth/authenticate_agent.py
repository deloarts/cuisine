"""
Authenticates one request to the MCP surface. Every request carries its own
bearer token, a personal access token, an API key or the access token of an
app connected through OAuth, so a revoked token, a deactivated owner or a
permission taken away stops the agent on its next call. The token must
carry use:mcp; a PAT and an OAuth grant act as their owner narrowed to the
permissions they carry, an API key as its service account.
"""

from dataclasses import replace

from src.platform.application.dto.agent_dto import AgentPrincipal
from src.platform.application.use_cases.auth.validate_bearer import ValidateApiKey
from src.platform.application.use_cases.auth.validate_bearer import ValidatePat
from src.platform.const import API_KEY_PREFIX
from src.platform.const import OAUTH_ACCESS_PREFIX
from src.platform.const import PAT_PREFIX
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.oauth import TOKEN_KIND_ACCESS
from src.platform.domain.exceptions import AgentAccessDisabledError
from src.platform.domain.exceptions import ConsentRequiredError
from src.platform.domain.exceptions import InvalidTokenError
from src.platform.domain.exceptions import OAuthDisabledError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.exceptions import PrivacyAcknowledgementRequiredError
from src.platform.domain.services.legal_rules import acknowledgement_pending
from src.platform.domain.services.session_rules import LAST_SEEN_WRITE_INTERVAL
from src.platform.domain.value_objects.agent import AgentTokenKind
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.repositories.api_key_repository import IApiKeyRepository
from src.platform.ports.outbound.repositories.legal_repository import ILegalRepository
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthClientRepository
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthGrantRepository
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthTokenRepository
from src.platform.ports.outbound.repositories.pat_repository import IPatRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import as_utc
from src.shared_kernel.domain.services.clock import now_utc


class AuthenticateAgent:
    def __init__(
        self,
        *,
        pat_repo: IPatRepository,
        key_repo: IApiKeyRepository,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        secrets: ISecretHasher,
        uow: IUnitOfWork,
        legal: ILegalRepository | None = None,
        oauth_clients: IOAuthClientRepository | None = None,
        oauth_grants: IOAuthGrantRepository | None = None,
        oauth_tokens: IOAuthTokenRepository | None = None,
    ) -> None:
        self._legal = legal
        self._oauth_clients = oauth_clients
        self._oauth_grants = oauth_grants
        self._oauth_tokens = oauth_tokens
        self._pats = pat_repo
        self._keys = key_repo
        self._users = user_repo
        self._settings = settings_repo
        self._secrets = secrets
        self._uow = uow

    async def execute(self, token: str) -> AgentPrincipal:
        if not token:
            raise InvalidTokenError("Missing bearer token.")
        if not (await self._settings.get_agents()).enabled:
            raise AgentAccessDisabledError("Agent access is switched off on this instance.")
        if token.startswith(PAT_PREFIX):
            principal = await self._pat(token)
        elif token.startswith(API_KEY_PREFIX):
            principal = await self._api_key(token)
        elif token.startswith(OAUTH_ACCESS_PREFIX):
            principal = await self._oauth(token)
        else:
            raise InvalidTokenError("Invalid or expired token")
        if not principal.user.has_permission(Permission.USE_MCP):
            raise PermissionDeniedError("This token does not carry use:mcp.")
        user = principal.user
        # A person's agent needs that person's consent, and the person must
        # have acknowledged the current privacy statement. A service account
        # behind an API key is no person and gives neither.
        if not user.is_service_account:
            if user.consent_ai_agents_at is None:
                raise ConsentRequiredError("The AI agents consent was withdrawn or never given.")
            if self._legal is not None and acknowledgement_pending(
                user, await self._legal.current(LegalKind.PRIVACY)
            ):
                raise PrivacyAcknowledgementRequiredError(
                    "Acknowledge the current privacy statement in the web app first."
                )
        return principal

    async def _pat(self, token: str) -> AgentPrincipal:
        user = await ValidatePat(
            pat_repo=self._pats, user_repo=self._users, secrets=self._secrets, uow=self._uow
        ).execute(token)
        pat = await self._pats.get_by_token_hash(self._secrets.hash(token))
        if pat is None:
            raise InvalidTokenError("Invalid or expired token")
        return AgentPrincipal(
            user=user, token_kind=AgentTokenKind.PAT, token_id=pat.id, token_name=pat.name
        )

    async def _api_key(self, token: str) -> AgentPrincipal:
        if not (await self._settings.get_security()).enable_api_key_auth:
            raise InvalidTokenError("API key authentication is disabled")
        user = await ValidateApiKey(
            key_repo=self._keys, user_repo=self._users, secrets=self._secrets, uow=self._uow
        ).execute(token)
        key = await self._keys.get_by_token_hash(self._secrets.hash(token))
        if key is None:
            raise InvalidTokenError("Invalid or expired API key")
        return AgentPrincipal(
            user=user, token_kind=AgentTokenKind.API_KEY, token_id=key.id, token_name=key.name
        )

    async def _oauth(self, token: str) -> AgentPrincipal:
        if self._oauth_grants is None or self._oauth_tokens is None or self._oauth_clients is None:
            raise InvalidTokenError("Invalid or expired token")
        if not (await self._settings.get_agents()).oauth_enabled:
            raise OAuthDisabledError("OAuth connections are switched off on this instance.")
        stored = await self._oauth_tokens.get_by_token_hash(self._secrets.hash(token))
        if stored is None or stored.kind != TOKEN_KIND_ACCESS or not stored.is_usable:
            raise InvalidTokenError("Invalid or expired token")
        grant = await self._oauth_grants.get(stored.grant_id)
        owner = await self._users.get(grant.user_id) if grant is not None else None
        if (
            grant is None
            or owner is None
            or not owner.is_active
            or owner.is_systemuser
            or not grant.is_usable_for(owner.token_version)
        ):
            raise InvalidTokenError("Invalid or expired token")
        now = now_utc()
        if (
            grant.last_used_at is None
            or now - as_utc(grant.last_used_at) >= LAST_SEEN_WRITE_INTERVAL
        ):
            grant.last_used_at = now
            await self._oauth_grants.save(grant)
            await self._uow.commit()
        client = await self._oauth_clients.get(grant.client_id)
        # The approved permissions, still capped by what the owner holds now.
        allowed = sorted(set(grant.permissions) & set(owner.effective_permissions))
        user = replace(owner, permissions=allowed, group_permissions=[], is_systemuser=False)
        return AgentPrincipal(
            user=user,
            token_kind=AgentTokenKind.OAUTH,
            token_id=grant.id,
            token_name=client.name if client is not None else "OAuth app",
        )
