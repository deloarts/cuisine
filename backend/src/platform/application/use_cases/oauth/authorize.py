"""
The authorization step of the OAuth code flow, behind the consent page of
the web app. The person is signed in with their normal session; the page
first inspects the request (who asks, for what) and then sends the
person's decision, which answers the URI the browser continues to.

Both calls validate the whole request again, so the page holds no state the
server trusts. An unknown client or a redirect URI the client did not
register is shown on the page and never redirected to. Any other broken
request is reported to the client through its redirect URI, as RFC 6749
section 4.1.2.1 asks.
"""

from dataclasses import dataclass

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.use_cases.oauth.register_client import assert_oauth_open
from src.platform.const import API_MCP
from src.platform.const import OAUTH_CODE_PREFIX
from src.platform.domain.entities.oauth import AuthorizationCode
from src.platform.domain.entities.oauth import OAuthClient
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import ConsentRequiredError
from src.platform.domain.exceptions import OAuthRedirectRejectedError
from src.platform.domain.exceptions import OAuthRequestError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.exceptions import SystemUserProtectedError
from src.platform.domain.services.oauth_rules import AUTHORIZATION_CODE_SECONDS
from src.platform.domain.services.oauth_rules import OAUTH_SCOPES
from src.platform.domain.services.oauth_rules import assert_code_challenge
from src.platform.domain.services.oauth_rules import host_allowed
from src.platform.domain.services.oauth_rules import redirect_host
from src.platform.domain.services.oauth_rules import requested_permissions
from src.platform.domain.services.oauth_rules import resolve_redirect
from src.platform.domain.services.oauth_rules import with_query
from src.platform.domain.value_objects.permission import Permission
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.authorization_codes import IAuthorizationCodeStore
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthClientRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.unit_of_work import IUnitOfWork


@dataclass(frozen=True)
class AuthorizationRequest:
    """The query of the authorization URL, as the client sent it."""

    client_id: str
    redirect_uri: str | None = None
    response_type: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    state: str | None = None
    scope: str | None = None
    resource: str | None = None


@dataclass(frozen=True)
class AuthorizationPrompt:
    """What the consent page shows. `error_redirect` is set when the request
    is broken in a way the client must hear about; the page then sends the
    browser there at once."""

    client: OAuthClient
    redirect_uri: str
    redirect_host: str
    # The permissions the person may grant, and those the client asked for
    # (pre-ticked on the page).
    offered: list[str]
    requested: list[str]
    error_redirect: str | None = None


class AuthorizeOAuthClient:
    def __init__(
        self,
        *,
        client_repo: IOAuthClientRepository,
        settings_repo: ISettingsRepository,
        codes: IAuthorizationCodeStore,
        secrets: ISecretHasher,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        issuer: str,
    ) -> None:
        self._clients = client_repo
        self._settings = settings_repo
        self._codes = codes
        self._secrets = secrets
        self._audit = audit
        self._uow = uow
        self._issuer = issuer.rstrip("/")

    async def inspect(self, user: User, req: AuthorizationRequest) -> AuthorizationPrompt:
        client, redirect_uri = await self._trusted_target(req)
        offered = self._offered(user)
        try:
            self._check_request(req)
        except OAuthRequestError as e:
            return self._prompt(
                client, redirect_uri, offered, [], self._error(redirect_uri, req, e)
            )
        self._check_user(user)
        requested = [p for p in requested_permissions(req.scope) if p in offered]
        return self._prompt(client, redirect_uri, offered, requested, None)

    async def decide(
        self,
        user: User,
        req: AuthorizationRequest,
        *,
        approve: bool,
        permissions: list[str],
        context: RequestContext,
    ) -> str:
        """The URI the browser continues to: the client's redirect URI with
        the code, or with the error."""
        client, redirect_uri = await self._trusted_target(req)
        try:
            self._check_request(req)
        except OAuthRequestError as e:
            return self._error(redirect_uri, req, e)
        self._check_user(user)
        if not approve:
            await self._audit.record(
                SecurityEventType.OAUTH_GRANT_DENIED,
                actor=user,
                target=user,
                context=context,
                outcome=SecurityEventOutcome.FAILURE,
                detail={"client": client.name, "redirect_host": redirect_host(redirect_uri)},
            )
            await self._uow.commit()
            return with_query(
                redirect_uri,
                {"error": "access_denied", "state": req.state, "iss": self._issuer},
            )

        offered = set(self._offered(user))
        chosen = (set(permissions) & offered) | {Permission.USE_MCP}
        granted = tuple(p for p in OAUTH_SCOPES if p in chosen)
        assert req.code_challenge is not None
        code = self._secrets.generate(OAUTH_CODE_PREFIX)
        await self._codes.put(
            self._secrets.hash(code),
            AuthorizationCode(
                client_id=client.id,
                user_id=user.id,
                redirect_uri=redirect_uri,
                code_challenge=req.code_challenge,
                permissions=granted,
                token_version=user.token_version,
            ),
            AUTHORIZATION_CODE_SECONDS,
        )
        await self._audit.record(
            SecurityEventType.OAUTH_GRANT_APPROVED,
            actor=user,
            target=user,
            context=context,
            detail={
                "client": client.name,
                "redirect_host": redirect_host(redirect_uri),
                "permissions": list(granted),
            },
        )
        await self._uow.commit()
        return with_query(redirect_uri, {"code": code, "state": req.state, "iss": self._issuer})

    # ── Checks ────────────────────────────────────────────────────────

    async def _trusted_target(self, req: AuthorizationRequest) -> tuple[OAuthClient, str]:
        """The client and the redirect URI, when both can be trusted with a
        redirect; anything else is shown on the page."""
        agents = await self._settings.get_agents()
        assert_oauth_open(agents)
        client = await self._clients.get_by_client_id(req.client_id) if req.client_id else None
        if client is None:
            raise OAuthRedirectRejectedError("This app is not registered with Cuisine.")
        redirect_uri = resolve_redirect(client.redirect_uris, req.redirect_uri)
        if redirect_uri is None:
            raise OAuthRedirectRejectedError(
                "The app asked to return to an address it did not register."
            )
        if not host_allowed(redirect_uri, agents.oauth_redirect_hosts):
            raise OAuthRedirectRejectedError(
                f"This Cuisine instance does not accept apps that redirect to "
                f"{redirect_host(redirect_uri)}."
            )
        return client, redirect_uri

    def _check_request(self, req: AuthorizationRequest) -> None:
        if req.response_type != "code":
            raise OAuthRequestError("unsupported_response_type", "response_type must be code.")
        assert_code_challenge(req.code_challenge, req.code_challenge_method)
        if req.resource is not None and req.resource.rstrip("/") not in {
            self._issuer,
            f"{self._issuer}{API_MCP}",
        }:
            raise OAuthRequestError(
                "invalid_target", "This server issues tokens for its MCP surface only."
            )

    @staticmethod
    def _check_user(user: User) -> None:
        if user.is_systemuser:
            raise SystemUserProtectedError(
                "The system account is for administration only and cannot connect apps."
            )
        if not user.has_permission(Permission.USE_MCP):
            raise PermissionDeniedError("Connecting an AI agent needs the use:mcp permission.")
        if user.consent_ai_agents_at is None:
            raise ConsentRequiredError("Connecting an AI agent needs your consent to AI agents.")

    @staticmethod
    def _offered(user: User) -> list[str]:
        return [p for p in OAUTH_SCOPES if user.has_permission(p)]

    def _error(self, redirect_uri: str, req: AuthorizationRequest, e: OAuthRequestError) -> str:
        return with_query(
            redirect_uri,
            {
                "error": e.error,
                "error_description": str(e),
                "state": req.state,
                "iss": self._issuer,
            },
        )

    @staticmethod
    def _prompt(
        client: OAuthClient,
        redirect_uri: str,
        offered: list[str],
        requested: list[str],
        error_redirect: str | None,
    ) -> AuthorizationPrompt:
        return AuthorizationPrompt(
            client=client,
            redirect_uri=redirect_uri,
            redirect_host=redirect_host(redirect_uri),
            offered=offered,
            requested=requested,
            error_redirect=error_redirect,
        )
