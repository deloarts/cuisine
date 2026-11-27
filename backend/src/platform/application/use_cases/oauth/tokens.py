"""
The token endpoint of the OAuth code flow and token revocation (RFC 7009).

A redeemed authorization code becomes a grant with an access token (one
hour) and a refresh token (until the grant ends). Every refresh hands out a
new pair and retires the refresh token it used; presenting a retired one
again means it leaked, so the whole grant ends. The same holds for an
authorization code redeemed twice.
"""

import hmac
from dataclasses import dataclass
from datetime import datetime

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.use_cases.oauth.grants import end_grant
from src.platform.application.use_cases.oauth.register_client import assert_oauth_open
from src.platform.const import OAUTH_ACCESS_PREFIX
from src.platform.const import OAUTH_REFRESH_PREFIX
from src.platform.domain.entities.oauth import AUTH_METHOD_NONE
from src.platform.domain.entities.oauth import TOKEN_KIND_ACCESS
from src.platform.domain.entities.oauth import TOKEN_KIND_REFRESH
from src.platform.domain.entities.oauth import OAuthClient
from src.platform.domain.entities.oauth import OAuthGrant
from src.platform.domain.entities.oauth import OAuthToken
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import OAuthClientError
from src.platform.domain.exceptions import OAuthGrantError
from src.platform.domain.services.oauth_rules import access_token_expiry
from src.platform.domain.services.oauth_rules import grant_expiry
from src.platform.domain.services.oauth_rules import pkce_matches
from src.platform.domain.services.oauth_rules import redirect_matches
from src.platform.domain.services.oauth_rules import scope_string
from src.platform.domain.value_objects.permission import Permission
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.authorization_codes import IAuthorizationCodeStore
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthClientRepository
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthGrantRepository
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthTokenRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# How long a redeemed code is remembered, to recognise a second redemption.
_REDEEMED_MEMORY_SECONDS = 600


@dataclass(frozen=True)
class ClientCredentials:
    """How the client identified itself: the client id, and the secret from
    the form body or from HTTP Basic."""

    client_id: str | None
    client_secret: str | None = None


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    scope: str


class IssueOAuthTokens:
    def __init__(
        self,
        *,
        client_repo: IOAuthClientRepository,
        grant_repo: IOAuthGrantRepository,
        token_repo: IOAuthTokenRepository,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        codes: IAuthorizationCodeStore,
        secrets: ISecretHasher,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._clients = client_repo
        self._grants = grant_repo
        self._tokens = token_repo
        self._users = user_repo
        self._settings = settings_repo
        self._codes = codes
        self._secrets = secrets
        self._audit = audit
        self._uow = uow

    # ── Grant types ───────────────────────────────────────────────────

    async def exchange_code(
        self,
        creds: ClientCredentials,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str | None,
        context: RequestContext,
    ) -> TokenPair:
        client = await self._authenticate(creds)
        agents = await self._settings.get_agents()
        assert_oauth_open(agents)
        code_hash = self._secrets.hash(code)
        stored = await self._codes.take(code_hash)
        if stored is None:
            leaked = await self._codes.redeemed_grant(code_hash)
            if leaked is not None:
                await self._end_after_reuse(leaked, "authorization_code", context)
            raise OAuthGrantError("The authorization code is unknown, expired or used.")
        if stored.client_id != client.id:
            raise OAuthGrantError("The authorization code was issued to another client.")
        if redirect_uri is not None and not redirect_matches(stored.redirect_uri, redirect_uri):
            raise OAuthGrantError("redirect_uri does not match the authorization request.")
        if not pkce_matches(code_verifier, stored.code_challenge):
            raise OAuthGrantError("The code_verifier does not match the code_challenge.")
        user = await self._users.get(stored.user_id)
        if user is None or not self._may_connect(user, stored.token_version):
            raise OAuthGrantError("The approving account can no longer connect apps.")

        now = now_utc()
        # A new approval replaces the app's earlier one, so the person sees
        # one entry per app.
        for earlier in await self._grants.list_active_for_user(user.id):
            if earlier.client_id == client.id:
                await end_grant(earlier, grants=self._grants, tokens=self._tokens, now=now)
        security = await self._settings.get_security()
        grant = await self._grants.save(
            OAuthGrant(
                user_id=user.id,
                client_id=client.id,
                permissions=list(stored.permissions),
                redirect_uri=stored.redirect_uri,
                token_version=stored.token_version,
                created=now,
                expires_at=grant_expiry(
                    now, agents.token_max_lifetime_days, security.token_max_lifetime_days
                ),
            )
        )
        client.last_grant_at = now
        await self._clients.save(client)
        pair = await self._issue(grant, now)
        await self._uow.commit()
        await self._codes.mark_redeemed(code_hash, grant.id, _REDEEMED_MEMORY_SECONDS)
        return pair

    async def refresh(
        self, creds: ClientCredentials, *, refresh_token: str, context: RequestContext
    ) -> TokenPair:
        client = await self._authenticate(creds)
        assert_oauth_open(await self._settings.get_agents())
        token = await self._tokens.get_by_token_hash(self._secrets.hash(refresh_token))
        if token is None or token.kind != TOKEN_KIND_REFRESH:
            raise OAuthGrantError("The refresh token is unknown.")
        grant = await self._grants.get(token.grant_id)
        if grant is None or grant.client_id != client.id:
            raise OAuthGrantError("The refresh token is unknown.")
        if token.used_at is not None and grant.revoked_at is None:
            await self._end_after_reuse(grant.id, "refresh_token", context)
            raise OAuthGrantError("The refresh token was already used; the connection ended.")
        if not token.is_usable:
            raise OAuthGrantError("The refresh token is expired or revoked.")
        user = await self._users.get(grant.user_id)
        if user is None or not grant.is_usable_for(user.token_version):
            raise OAuthGrantError("The connection ended; approve the app again.")
        if not self._may_connect(user, grant.token_version):
            raise OAuthGrantError("The account can no longer connect apps.")
        now = now_utc()
        token.used_at = now
        await self._tokens.save(token)
        pair = await self._issue(grant, now)
        await self._uow.commit()
        return pair

    async def revoke(
        self, creds: ClientCredentials, *, token: str, context: RequestContext
    ) -> None:
        """Revoking a refresh token ends the grant; revoking an access token
        ends that token only. An unknown token is no error (RFC 7009 2.2)."""
        client = await self._authenticate(creds)
        stored = await self._tokens.get_by_token_hash(self._secrets.hash(token))
        if stored is None:
            return
        grant = await self._grants.get(stored.grant_id)
        if grant is None or grant.client_id != client.id:
            return
        now = now_utc()
        if stored.kind == TOKEN_KIND_REFRESH:
            if grant.revoked_at is None:
                await end_grant(grant, grants=self._grants, tokens=self._tokens, now=now)
                user = await self._users.get(grant.user_id)
                await self._audit.record(
                    SecurityEventType.OAUTH_GRANT_REVOKED,
                    actor=None,
                    target=user,
                    context=context,
                    detail={"client": client.name, "reason": "revoked_by_app"},
                )
        elif stored.revoked_at is None:
            stored.revoked_at = now
            await self._tokens.save(stored)
        await self._uow.commit()

    # ── Helpers ───────────────────────────────────────────────────────

    async def _authenticate(self, creds: ClientCredentials) -> OAuthClient:
        client = await self._clients.get_by_client_id(creds.client_id) if creds.client_id else None
        if client is None:
            raise OAuthClientError("Unknown client.")
        if client.auth_method == AUTH_METHOD_NONE:
            return client
        given = self._secrets.hash(creds.client_secret) if creds.client_secret else ""
        if not client.secret_hash or not hmac.compare_digest(given, client.secret_hash):
            raise OAuthClientError("The client secret is wrong.")
        return client

    @staticmethod
    def _may_connect(user: User, token_version: int) -> bool:
        return (
            user.is_active
            and not user.is_systemuser
            and user.token_version == token_version
            and user.has_permission(Permission.USE_MCP)
            and user.consent_ai_agents_at is not None
        )

    async def _issue(self, grant: OAuthGrant, now: datetime) -> TokenPair:
        access = self._secrets.generate(OAUTH_ACCESS_PREFIX)
        refresh = self._secrets.generate(OAUTH_REFRESH_PREFIX)
        access_expires = access_token_expiry(now, grant.expires_at)
        await self._tokens.save(
            OAuthToken(
                grant_id=grant.id,
                kind=TOKEN_KIND_ACCESS,
                token_hash=self._secrets.hash(access),
                created=now,
                expires_at=access_expires,
            )
        )
        await self._tokens.save(
            OAuthToken(
                grant_id=grant.id,
                kind=TOKEN_KIND_REFRESH,
                token_hash=self._secrets.hash(refresh),
                created=now,
                expires_at=grant.expires_at,
            )
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=max(1, int((access_expires - now).total_seconds())),
            scope=scope_string(grant.permissions),
        )

    async def _end_after_reuse(self, grant_id: int, what: str, context: RequestContext) -> None:
        grant = await self._grants.get(grant_id)
        if grant is None or grant.revoked_at is not None:
            return
        await end_grant(grant, grants=self._grants, tokens=self._tokens, now=now_utc())
        user = await self._users.get(grant.user_id)
        await self._audit.record(
            SecurityEventType.OAUTH_TOKEN_REUSED,
            actor=None,
            target=user,
            context=context,
            outcome=SecurityEventOutcome.FAILURE,
            detail={"reused": what},
        )
        await self._uow.commit()
