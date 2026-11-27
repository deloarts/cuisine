"""
Auth resolution dependencies.

The web session travels in an httponly cookie JavaScript cannot read. A
bearer header is also accepted, for tests and the TOTP setup-token bridge.
A bearer token carries no CSRF risk, but the cookie does, so an unsafe
method authenticated by cookie must carry `X-Requested-With: cuisine`.
Forms and image tags cannot set a custom header, and a script that could
would have to run on an origin CORS already allows.

Personal access tokens and API keys travel in the `X-Api-Key` header, each
on its own surface (/api/v1/pat, /api/v1/key).

Every refusal here is a domain error, so its body carries a `code` like any
other: an InvalidTokenError answers 401 and the rest answer 403.
"""

from collections.abc import Awaitable
from collections.abc import Callable

from fastapi import Depends
from fastapi import Request
from fastapi import Security
from fastapi.security import APIKeyHeader
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.adapters.inbound.api.deps import secrets
from src.platform.adapters.inbound.api.deps import tokens
from src.platform.adapters.inbound.api.privacy_gate import enforce_privacy_acknowledgement
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.auth.validate_bearer import ValidateApiKey
from src.platform.application.use_cases.auth.validate_bearer import ValidatePat
from src.platform.application.use_cases.auth.validate_web_token import ValidateWebToken
from src.platform.application.use_cases.auth.validate_web_token import WebIdentity
from src.platform.const import CSRF_HEADER_NAME
from src.platform.const import CSRF_HEADER_VALUE
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import ApiKeyAuthDisabledError
from src.platform.domain.exceptions import CsrfHeaderMissingError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.exceptions import TotpSetupRequiredError
from src.platform.domain.services.login_rules import permission_needs_totp
from src.platform.domain.value_objects import token_scope
from src.platform.infrastructure.security.cookies import SESSION_COOKIE

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

_CSRF_PROTECTED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_request_context(request: Request) -> RequestContext:
    """The client address (resolved from X-Forwarded-For by the server for
    trusted proxies only) and the user agent."""
    return RequestContext(
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def require_csrf_header(request: Request) -> None:
    if request.method not in _CSRF_PROTECTED_METHODS:
        return
    if request.headers.get(CSRF_HEADER_NAME) != CSRF_HEADER_VALUE:
        raise CsrfHeaderMissingError("The request lacks the CSRF header.")


def _resolve_token(
    request: Request, bearer: HTTPAuthorizationCredentials | None
) -> tuple[str, bool]:
    """The token and whether it came from the cookie. The header wins."""
    if bearer is not None and bearer.credentials:
        return bearer.credentials, False
    return request.cookies.get(SESSION_COOKIE) or "", True


async def _identity(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None,
    p: Platform,
    allowed_scopes: frozenset[str],
) -> WebIdentity:
    token, from_cookie = _resolve_token(request, bearer)
    use_case = ValidateWebToken(
        user_repo=p.users,
        session_repo=p.sessions,
        settings_repo=p.settings,
        tokens=tokens(),
        uow=p.uow,
    )
    identity = await use_case.execute(token, allowed_scopes=allowed_scopes)
    if from_cookie:
        require_csrf_header(request)
    return identity


async def get_web_identity(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    p: Platform = Depends(get_platform),
) -> WebIdentity:
    identity = await _identity(request, bearer, p, frozenset({token_scope.SESSION}))
    await enforce_privacy_acknowledgement(request, identity.user)
    return identity


async def get_totp_enrolment_identity(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    p: Platform = Depends(get_platform),
) -> WebIdentity:
    """Accepts a session or, for enrolment forced at login, a setup token."""
    return await _identity(
        request, bearer, p, frozenset({token_scope.SESSION, token_scope.TOTP_SETUP})
    )


async def get_current_user(identity: WebIdentity = Depends(get_web_identity)) -> User:
    return identity.user


def require_permission(permission: str) -> Callable[..., Awaitable[User]]:
    """A dependency that resolves the signed-in user and refuses with 403
    unless they hold `permission`."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise PermissionDeniedError("You do not have the permission for this.")
        if permission_needs_totp(user, permission):
            raise TotpSetupRequiredError(
                "Set up two-factor authentication on your account to use the settings."
            )
        return user

    return dependency


async def get_pat_user(
    request: Request,
    token: str | None = Security(api_key_header),
    p: Platform = Depends(get_platform),
) -> User:
    user = await ValidatePat(
        pat_repo=p.pats, user_repo=p.users, secrets=secrets(), uow=p.uow
    ).execute(token or "")
    await enforce_privacy_acknowledgement(request, user)
    return user


async def get_api_key_user(
    token: str | None = Security(api_key_header), p: Platform = Depends(get_platform)
) -> User:
    if not (await p.settings.get_security()).enable_api_key_auth:
        raise ApiKeyAuthDisabledError("API key authentication is switched off.")
    return await ValidateApiKey(
        key_repo=p.api_keys, user_repo=p.users, secrets=secrets(), uow=p.uow
    ).execute(token or "")


def require_any_permission(*permissions: str) -> Callable[..., Awaitable[User]]:
    """Like require_permission, satisfied by any one of `permissions`."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_permission(p) for p in permissions):
            raise PermissionDeniedError("You do not have the permission for this.")
        return user

    return dependency
