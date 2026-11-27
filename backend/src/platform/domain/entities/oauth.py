"""
The records behind OAuth connections of hosted AI clients to the MCP surface.

A client registers itself (Dynamic Client Registration), a person approves
it on the consent page, and the approval becomes a grant once the client
redeems its authorization code. The grant is the connected app the person
sees and revokes; it plays the part a personal access token plays for an
agent configured by hand. Access and refresh tokens belong to a grant and
are stored as their SHA-256 only.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.services.clock import as_utc
from src.shared_kernel.domain.services.clock import now_utc

# How a client proves itself at the token endpoint (RFC 7591 names).
AUTH_METHOD_NONE = "none"
AUTH_METHOD_SECRET_POST = "client_secret_post"
AUTH_METHOD_SECRET_BASIC = "client_secret_basic"
AUTH_METHODS = (AUTH_METHOD_NONE, AUTH_METHOD_SECRET_POST, AUTH_METHOD_SECRET_BASIC)

TOKEN_KIND_ACCESS = "access"
TOKEN_KIND_REFRESH = "refresh"


@dataclass(kw_only=True)
class OAuthClient(Entity):
    # The public identifier the client sends; unique.
    client_id: str
    # The SHA-256 of the client secret, None for a public client.
    secret_hash: str | None = None
    # Self-declared by the client, so untrusted text.
    name: str
    client_uri: str | None = None
    redirect_uris: list[str] = field(default_factory=list)
    auth_method: str = AUTH_METHOD_NONE
    created: datetime
    # The last time a grant was made for this client; a client that never
    # gets one is pruned.
    last_grant_at: datetime | None = None


@dataclass(kw_only=True)
class OAuthGrant(Entity):
    user_id: int
    client_id: int
    # The permissions the person approved; at use they are capped again by
    # what the person still holds.
    permissions: list[str] = field(default_factory=list)
    # The redirect URI the approval used, kept so the person sees where the
    # app lives.
    redirect_uri: str
    # The user's token version at approval. Signing out everywhere, a
    # password reset by an administrator or a deactivation raises it, which
    # ends the grant.
    token_version: int = 0
    created: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    def is_usable_for(self, token_version: int) -> bool:
        if self.revoked_at is not None or self.token_version != token_version:
            return False
        return self.expires_at is None or as_utc(self.expires_at) > now_utc()


@dataclass(kw_only=True)
class OAuthToken(Entity):
    grant_id: int
    # TOKEN_KIND_ACCESS or TOKEN_KIND_REFRESH.
    kind: str
    token_hash: str
    created: datetime
    expires_at: datetime | None = None
    # When a refresh token was exchanged for a new pair. A second exchange
    # of the same token means it leaked, and ends the grant.
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    @property
    def is_usable(self) -> bool:
        if self.revoked_at is not None or self.used_at is not None:
            return False
        return self.expires_at is None or as_utc(self.expires_at) > now_utc()


@dataclass(frozen=True, kw_only=True)
class AuthorizationCode:
    """What an approval hands to the token endpoint. It lives for a minute in
    the code store and is redeemed once."""

    client_id: int
    user_id: int
    redirect_uri: str
    code_challenge: str
    permissions: tuple[str, ...]
    token_version: int
