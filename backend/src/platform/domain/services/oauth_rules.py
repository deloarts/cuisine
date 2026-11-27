"""
The protocol rules of Cuisine's OAuth authorization server, kept free of
any framework so they can be tested on their own: PKCE, redirect URIs,
scopes, the redirect host allowlist and the lifetime of a grant.
"""

import base64
import hashlib
import hmac
import re
from collections.abc import Iterable
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from src.platform.domain.exceptions import OAuthRequestError
from src.platform.domain.value_objects.permission import Permission

# The permissions an OAuth client may ask for. use:mcp is always part of a
# grant; the other two let the agent create drafts.
OAUTH_SCOPES = (Permission.USE_MCP, Permission.WRITE_RECIPES, Permission.WRITE_INGREDIENTS)

ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
AUTHORIZATION_CODE_SECONDS = 60
# A registered client that never gets a grant within this time is pruned.
UNUSED_CLIENT_LIFETIME = timedelta(hours=24)
# Revoked or expired grants stay this long before they are pruned, so the
# security log's references still resolve for a while.
ENDED_GRANT_RETENTION = timedelta(days=7)

MAX_REDIRECT_URIS = 10
MAX_REDIRECT_URI_LENGTH = 2000

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# RFC 7636: 43 to 128 characters of the unreserved set.
_VERIFIER = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")
_CHALLENGE = re.compile(r"^[A-Za-z0-9\-_]{43}$")
_HOST = re.compile(
    r"^(?=.{1,253}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$"
)


# ── PKCE ──────────────────────────────────────────────────────────────


def assert_code_challenge(challenge: str | None, method: str | None) -> str:
    """Only S256 is accepted; plain would hand the verifier to anyone who
    sees the authorization request."""
    if not challenge:
        raise OAuthRequestError("invalid_request", "code_challenge is required (PKCE).")
    if (method or "plain") != "S256":
        raise OAuthRequestError("invalid_request", "code_challenge_method must be S256.")
    if not _CHALLENGE.match(challenge):
        raise OAuthRequestError("invalid_request", "code_challenge is malformed.")
    return challenge


def pkce_matches(verifier: str, challenge: str) -> bool:
    if not _VERIFIER.match(verifier):
        return False
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, challenge)


# ── Redirect URIs ────────────────────────────────────────────────────


def redirect_host(uri: str) -> str:
    return (urlsplit(uri).hostname or "").lower()


def _is_loopback(uri: str) -> bool:
    parts = urlsplit(uri)
    return parts.scheme == "http" and (parts.hostname or "").lower() in _LOOPBACK_HOSTS


def validate_redirect_uri(uri: str) -> str:
    """A redirect URI is https, or plain http on a loopback address for a
    native client. It carries no fragment, no user info and no wildcard."""
    if not isinstance(uri, str) or not uri or len(uri) > MAX_REDIRECT_URI_LENGTH:
        raise OAuthRequestError("invalid_redirect_uri", "A redirect URI is empty or too long.")
    parts = urlsplit(uri)
    host = (parts.hostname or "").lower()
    if not host or "*" in uri:
        raise OAuthRequestError("invalid_redirect_uri", f"{uri!r} is not an absolute URI.")
    if parts.fragment or "#" in uri:
        raise OAuthRequestError("invalid_redirect_uri", "A redirect URI must not have a fragment.")
    if parts.username or parts.password:
        raise OAuthRequestError("invalid_redirect_uri", "A redirect URI must not carry user info.")
    if parts.scheme == "https":
        return uri
    if _is_loopback(uri):
        return uri
    raise OAuthRequestError(
        "invalid_redirect_uri", "A redirect URI must use https, or http on localhost."
    )


def redirect_matches(registered: str, given: str) -> bool:
    """Exact match, except that a loopback URI may use any port (RFC 8252
    section 7.3), since a native client picks a free port at runtime."""
    if registered == given:
        return True
    if not (_is_loopback(registered) and _is_loopback(given)):
        return False
    a, b = urlsplit(registered), urlsplit(given)
    return (a.hostname, a.path, a.query) == (b.hostname, b.path, b.query)


def resolve_redirect(registered: Iterable[str], given: str | None) -> str | None:
    """The redirect URI an authorization request uses: the one it names, if
    registered, or the only registered one when it names none."""
    uris = list(registered)
    if not given:
        return uris[0] if len(uris) == 1 else None
    return given if any(redirect_matches(r, given) for r in uris) else None


def with_query(uri: str, params: dict[str, str | None]) -> str:
    """The redirect URI with the response parameters appended to its query."""
    parts = urlsplit(uri)
    extra = urlencode({k: v for k, v in params.items() if v is not None})
    query = f"{parts.query}&{extra}" if parts.query else extra
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


# ── The redirect host allowlist ──────────────────────────────────────


def normalise_hosts(hosts: Iterable[str]) -> list[str]:
    """Lower case, trimmed, unique host names. A scheme, a path, a port or a
    wildcard is refused, so an entry always means exactly one host."""
    cleaned: list[str] = []
    for raw in hosts:
        host = raw.strip().lower().rstrip(".")
        if not host:
            continue
        if host not in _LOOPBACK_HOSTS and not _HOST.match(host):
            raise ValueError(raw)
        if host not in cleaned:
            cleaned.append(host)
    return cleaned


def host_allowed(uri: str, allowlist: Iterable[str]) -> bool:
    allowed = list(allowlist)
    return not allowed or redirect_host(uri) in allowed


# ── Scopes ───────────────────────────────────────────────────────────


def requested_permissions(scope: str | None) -> list[str]:
    """The permissions a scope string asks for. Unknown scopes are dropped,
    since clients add their own (openid, offline_access); no scope at all
    asks for every OAuth scope. use:mcp is always included."""
    wanted = set((scope or "").split())
    chosen = {p for p in OAUTH_SCOPES if p in wanted} if wanted & set(OAUTH_SCOPES) else set()
    if not chosen:
        chosen = set(OAUTH_SCOPES)
    chosen.add(Permission.USE_MCP)
    return [p for p in OAUTH_SCOPES if p in chosen]


def scope_string(permissions: Iterable[str]) -> str:
    return " ".join(p for p in OAUTH_SCOPES if p in set(permissions))


# ── Lifetimes ────────────────────────────────────────────────────────


def grant_expiry(now: datetime, agent_cap_days: int, general_cap_days: int) -> datetime | None:
    """A grant lives as long as an agent token may: the agent cap, else the
    general token cap, counted from approval. Refreshing never extends it."""
    days = agent_cap_days or general_cap_days
    return now + timedelta(days=days) if days else None


def access_token_expiry(now: datetime, grant_expires_at: datetime | None) -> datetime:
    expiry = now + ACCESS_TOKEN_LIFETIME
    return min(expiry, grant_expires_at) if grant_expires_at is not None else expiry
