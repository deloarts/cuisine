"""
The OAuth discovery documents of Cuisine's MCP surface, built from the
public origin (`DOMAIN`): the Protected Resource Metadata of the MCP
endpoint (RFC 9728), which names Cuisine as its authorization server, and
the Authorization Server Metadata (RFC 8414), which names the endpoints. A
client finds the first through the `resource_metadata` parameter of the
MCP endpoint's 401 challenge.
"""

from typing import Any

from src.platform.const import API_MCP
from src.platform.const import API_OAUTH
from src.platform.domain.entities.oauth import AUTH_METHODS
from src.platform.domain.services.oauth_rules import OAUTH_SCOPES
from src.platform.infrastructure.config.settings import cfg

PROTECTED_RESOURCE_PATH = "/.well-known/oauth-protected-resource"
AUTHORIZATION_SERVER_PATH = "/.well-known/oauth-authorization-server"
# The consent page of the web app, which serves as the authorization
# endpoint.
AUTHORIZE_PAGE_PATH = "/oauth/authorize"


def issuer() -> str:
    return cfg.domain.rstrip("/")


def resource_url() -> str:
    return f"{issuer()}{API_MCP}"


def resource_metadata_url() -> str:
    return f"{issuer()}{PROTECTED_RESOURCE_PATH}{API_MCP}"


def bearer_challenge(*, error: str | None = None) -> str:
    """The `WWW-Authenticate` value of a refused MCP request."""
    parts = ['Bearer realm="cuisine"']
    if error:
        parts.append(f'error="{error}"')
    parts.append(f'resource_metadata="{resource_metadata_url()}"')
    return ", ".join(parts)


def protected_resource_metadata() -> dict[str, Any]:
    return {
        "resource": resource_url(),
        "authorization_servers": [issuer()],
        "scopes_supported": list(OAUTH_SCOPES),
        "bearer_methods_supported": ["header"],
        "resource_name": "Cuisine",
    }


def authorization_server_metadata() -> dict[str, Any]:
    base = issuer()
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}{AUTHORIZE_PAGE_PATH}",
        "token_endpoint": f"{base}{API_OAUTH}/token",
        "registration_endpoint": f"{base}{API_OAUTH}/register",
        "revocation_endpoint": f"{base}{API_OAUTH}/revoke",
        "scopes_supported": list(OAUTH_SCOPES),
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": list(AUTH_METHODS),
        "revocation_endpoint_auth_methods_supported": list(AUTH_METHODS),
        "authorization_response_iss_parameter_supported": True,
    }
