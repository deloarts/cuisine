"""
Dynamic Client Registration (RFC 7591). Hosted AI clients register
themselves before their first authorization request, so registration is
open; what makes it safe is that a client can do nothing until a person
approves it, that its redirect URIs are checked here and again at every
approval, and that a client nobody approves is pruned after a day.
"""

from dataclasses import dataclass
from urllib.parse import urlsplit

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.const import OAUTH_CLIENT_ID_PREFIX
from src.platform.const import OAUTH_CLIENT_SECRET_PREFIX
from src.platform.domain.entities.oauth import AUTH_METHOD_NONE
from src.platform.domain.entities.oauth import AUTH_METHOD_SECRET_BASIC
from src.platform.domain.entities.oauth import AUTH_METHODS
from src.platform.domain.entities.oauth import OAuthClient
from src.platform.domain.entities.settings import AgentSettings
from src.platform.domain.exceptions import AgentAccessDisabledError
from src.platform.domain.exceptions import OAuthDisabledError
from src.platform.domain.exceptions import OAuthRequestError
from src.platform.domain.services.oauth_rules import MAX_REDIRECT_URIS
from src.platform.domain.services.oauth_rules import host_allowed
from src.platform.domain.services.oauth_rules import redirect_host
from src.platform.domain.services.oauth_rules import validate_redirect_uri
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.oauth_repository import IOAuthClientRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.secret_hasher import ISecretHasher
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

GRANT_TYPES = ("authorization_code", "refresh_token")
RESPONSE_TYPES = ("code",)
_MAX_NAME = 128
_UNNAMED = "Unnamed app"


@dataclass(frozen=True)
class ClientRegistration:
    redirect_uris: list[str]
    client_name: str | None = None
    client_uri: str | None = None
    token_endpoint_auth_method: str | None = None
    grant_types: list[str] | None = None
    response_types: list[str] | None = None


@dataclass(frozen=True)
class RegisteredClient:
    client: OAuthClient
    # Returned once for a confidential client; only its hash is stored.
    secret: str | None


def assert_oauth_open(agents: AgentSettings) -> None:
    if not agents.enabled:
        raise AgentAccessDisabledError("Agent access is switched off on this instance.")
    if not agents.oauth_enabled:
        raise OAuthDisabledError("OAuth connections are switched off on this instance.")


def _client_uri(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value)
    return value if parts.scheme == "https" and parts.hostname and len(value) <= 2000 else None


class RegisterOAuthClient:
    def __init__(
        self,
        *,
        client_repo: IOAuthClientRepository,
        settings_repo: ISettingsRepository,
        secrets: ISecretHasher,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._clients = client_repo
        self._settings = settings_repo
        self._secrets = secrets
        self._audit = audit
        self._uow = uow

    async def execute(
        self, reg: ClientRegistration, *, context: RequestContext
    ) -> RegisteredClient:
        agents = await self._settings.get_agents()
        assert_oauth_open(agents)
        if not reg.redirect_uris:
            raise OAuthRequestError("invalid_redirect_uri", "redirect_uris is required.")
        if len(reg.redirect_uris) > MAX_REDIRECT_URIS:
            raise OAuthRequestError(
                "invalid_redirect_uri", f"At most {MAX_REDIRECT_URIS} redirect URIs."
            )
        uris = [validate_redirect_uri(uri) for uri in reg.redirect_uris]
        refused = [uri for uri in uris if not host_allowed(uri, agents.oauth_redirect_hosts)]
        if refused:
            raise OAuthRequestError(
                "invalid_redirect_uri",
                f"This Cuisine instance does not accept apps that redirect to "
                f"{redirect_host(refused[0])}.",
            )
        method = reg.token_endpoint_auth_method or AUTH_METHOD_SECRET_BASIC
        if method not in AUTH_METHODS:
            raise OAuthRequestError(
                "invalid_client_metadata",
                f"token_endpoint_auth_method must be one of {', '.join(AUTH_METHODS)}.",
            )
        if reg.grant_types is not None and not set(reg.grant_types) <= set(GRANT_TYPES):
            raise OAuthRequestError(
                "invalid_client_metadata", "Only authorization_code and refresh_token."
            )
        if reg.response_types is not None and not set(reg.response_types) <= set(RESPONSE_TYPES):
            raise OAuthRequestError("invalid_client_metadata", "Only the code response type.")

        secret = (
            None
            if method == AUTH_METHOD_NONE
            else self._secrets.generate(OAUTH_CLIENT_SECRET_PREFIX)
        )
        name = (reg.client_name or "").strip()[:_MAX_NAME] or _UNNAMED
        client = await self._clients.save(
            OAuthClient(
                client_id=self._secrets.generate(OAUTH_CLIENT_ID_PREFIX),
                secret_hash=self._secrets.hash(secret) if secret else None,
                name=name,
                client_uri=_client_uri(reg.client_uri),
                redirect_uris=uris,
                auth_method=method,
                created=now_utc(),
            )
        )
        await self._audit.record(
            SecurityEventType.OAUTH_CLIENT_REGISTERED,
            actor=None,
            context=context,
            detail={
                "client": name,
                "redirect_hosts": sorted({redirect_host(uri) for uri in uris}),
            },
        )
        await self._uow.commit()
        return RegisteredClient(client=client, secret=secret)
