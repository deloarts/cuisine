"""
The OAuth surface hosted AI clients call server to server, and the
discovery documents they read first.

`/.well-known/oauth-protected-resource` (RFC 9728) and
`/.well-known/oauth-authorization-server` (RFC 8414) are mounted at the
root, as the RFCs require. Client registration (RFC 7591), the token
endpoint and token revocation (RFC 7009) live under `/api/v1/oauth`. None
of them uses the session cookie, and their errors take the RFC shape
`{"error", "error_description"}` instead of Cuisine's `{detail, code}`,
since OAuth clients read that shape. The consent page, which needs the
session, is on the web surface (`oauth_web_router.py`).
"""

import base64
import binascii
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from pydantic import ValidationError

from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.deps import get_issue_oauth_tokens
from src.platform.adapters.inbound.api.deps import get_register_oauth_client
from src.platform.adapters.inbound.api.oauth_metadata import AUTHORIZATION_SERVER_PATH
from src.platform.adapters.inbound.api.oauth_metadata import PROTECTED_RESOURCE_PATH
from src.platform.adapters.inbound.api.oauth_metadata import authorization_server_metadata
from src.platform.adapters.inbound.api.oauth_metadata import protected_resource_metadata
from src.platform.adapters.inbound.api.rate_limit import limit_oauth_registrations
from src.platform.adapters.inbound.api.rate_limit import limit_oauth_requests
from src.platform.adapters.inbound.api.schemas.oauth_schema import ClientRegistrationRequest
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.oauth.register_client import GRANT_TYPES
from src.platform.application.use_cases.oauth.register_client import RESPONSE_TYPES
from src.platform.application.use_cases.oauth.register_client import ClientRegistration
from src.platform.application.use_cases.oauth.register_client import RegisterOAuthClient
from src.platform.application.use_cases.oauth.tokens import ClientCredentials
from src.platform.application.use_cases.oauth.tokens import IssueOAuthTokens
from src.platform.const import API_MCP
from src.platform.domain.exceptions import DomainError
from src.platform.domain.exceptions import ForbiddenError
from src.platform.domain.exceptions import OAuthClientError
from src.platform.domain.exceptions import OAuthRequestError
from src.platform.infrastructure.logging.logger import log

well_known_router = APIRouter(tags=["oauth"])
oauth_router = APIRouter(tags=["oauth"])

_NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
# The discovery documents are public and read by clients on any origin,
# browser-based developer tools included.
_PUBLIC_JSON = {"Cache-Control": "public, max-age=300", "Access-Control-Allow-Origin": "*"}


def _oauth_error(error: str, description: str, status: int, **headers: str) -> JSONResponse:
    return JSONResponse(
        {"error": error, "error_description": description},
        status_code=status,
        headers={**_NO_STORE, **headers},
    )


def _from_domain(e: DomainError, *, refused_error: str) -> JSONResponse:
    if isinstance(e, OAuthClientError):
        return _oauth_error(
            "invalid_client", str(e), 401, **{"WWW-Authenticate": 'Basic realm="cuisine"'}
        )
    if isinstance(e, OAuthRequestError):
        return _oauth_error(e.error, str(e), 400)
    if isinstance(e, ForbiddenError):
        return _oauth_error(refused_error, str(e), 403 if refused_error == "access_denied" else 400)
    log.error("OAuth endpoint failed: %r", e)
    return _oauth_error("server_error", "Cuisine could not answer this request.", 500)


# ── Discovery ────────────────────────────────────────────────────────


@well_known_router.get(PROTECTED_RESOURCE_PATH)
@well_known_router.get(f"{PROTECTED_RESOURCE_PATH}{API_MCP}")
async def protected_resource() -> JSONResponse:
    return JSONResponse(protected_resource_metadata(), headers=_PUBLIC_JSON)


@well_known_router.get(AUTHORIZATION_SERVER_PATH)
@well_known_router.get(f"{AUTHORIZATION_SERVER_PATH}{API_MCP}")
async def authorization_server() -> JSONResponse:
    return JSONResponse(authorization_server_metadata(), headers=_PUBLIC_JSON)


# ── Client registration ──────────────────────────────────────────────


@oauth_router.post("/register", dependencies=[Depends(limit_oauth_registrations)])
async def register_client(
    request: Request,
    context: RequestContext = Depends(get_request_context),
    use_case: RegisterOAuthClient = Depends(get_register_oauth_client),
) -> Response:
    try:
        body = ClientRegistrationRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        return _oauth_error(
            "invalid_client_metadata", "The body is not valid client metadata.", 400
        )
    try:
        registered = await use_case.execute(
            ClientRegistration(
                redirect_uris=body.redirect_uris,
                client_name=body.client_name,
                client_uri=body.client_uri,
                token_endpoint_auth_method=body.token_endpoint_auth_method,
                grant_types=body.grant_types,
                response_types=body.response_types,
            ),
            context=context,
        )
    except DomainError as e:
        return _from_domain(e, refused_error="access_denied")
    client = registered.client
    answer: dict[str, Any] = {
        "client_id": client.client_id,
        "client_id_issued_at": int(client.created.timestamp()),
        "client_name": client.name,
        "redirect_uris": client.redirect_uris,
        "token_endpoint_auth_method": client.auth_method,
        "grant_types": list(GRANT_TYPES),
        "response_types": list(RESPONSE_TYPES),
    }
    if client.client_uri:
        answer["client_uri"] = client.client_uri
    if registered.secret is not None:
        answer["client_secret"] = registered.secret
        answer["client_secret_expires_at"] = 0
    return JSONResponse(answer, status_code=201, headers=_NO_STORE)


# ── Token and revocation ─────────────────────────────────────────────


def _credentials(request: Request, form: dict[str, str]) -> ClientCredentials | JSONResponse:
    """The client id and secret from HTTP Basic (RFC 6749 section 2.3.1,
    form-encoded parts) or from the form body."""
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "basic" and value:
        try:
            decoded = base64.b64decode(value.strip(), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return _oauth_error("invalid_client", "Malformed Basic credentials.", 401)
        client_id, sep, secret = decoded.partition(":")
        if not sep:
            return _oauth_error("invalid_client", "Malformed Basic credentials.", 401)
        return ClientCredentials(client_id=unquote(client_id), client_secret=unquote(secret))
    return ClientCredentials(
        client_id=form.get("client_id") or None, client_secret=form.get("client_secret") or None
    )


async def _form(request: Request) -> dict[str, str]:
    form = await request.form()
    return {key: value for key, value in form.items() if isinstance(value, str)}


@oauth_router.post("/token", dependencies=[Depends(limit_oauth_requests)])
async def token(
    request: Request,
    context: RequestContext = Depends(get_request_context),
    use_case: IssueOAuthTokens = Depends(get_issue_oauth_tokens),
) -> Response:
    form = await _form(request)
    creds = _credentials(request, form)
    if isinstance(creds, JSONResponse):
        return creds
    grant_type = form.get("grant_type", "")
    try:
        if grant_type == "authorization_code":
            if not form.get("code") or not form.get("code_verifier"):
                raise OAuthRequestError("invalid_request", "code and code_verifier are required.")
            pair = await use_case.exchange_code(
                creds,
                code=form["code"],
                code_verifier=form["code_verifier"],
                redirect_uri=form.get("redirect_uri") or None,
                context=context,
            )
        elif grant_type == "refresh_token":
            if not form.get("refresh_token"):
                raise OAuthRequestError("invalid_request", "refresh_token is required.")
            pair = await use_case.refresh(
                creds, refresh_token=form["refresh_token"], context=context
            )
        else:
            raise OAuthRequestError(
                "unsupported_grant_type", "Use authorization_code or refresh_token."
            )
    except DomainError as e:
        return _from_domain(e, refused_error="unauthorized_client")
    return JSONResponse(
        {
            "access_token": pair.access_token,
            "token_type": "Bearer",
            "expires_in": pair.expires_in,
            "refresh_token": pair.refresh_token,
            "scope": pair.scope,
        },
        headers=_NO_STORE,
    )


@oauth_router.post("/revoke", dependencies=[Depends(limit_oauth_requests)])
async def revoke(
    request: Request,
    context: RequestContext = Depends(get_request_context),
    use_case: IssueOAuthTokens = Depends(get_issue_oauth_tokens),
) -> Response:
    form = await _form(request)
    creds = _credentials(request, form)
    if isinstance(creds, JSONResponse):
        return creds
    if not form.get("token"):
        return _oauth_error("invalid_request", "token is required.", 400)
    try:
        await use_case.revoke(creds, token=form["token"], context=context)
    except DomainError as e:
        return _from_domain(e, refused_error="unauthorized_client")
    return Response(status_code=200, headers=_NO_STORE)
