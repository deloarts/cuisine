"""
The rules of pairing and of authenticating peering requests: secrets and
invitation codes, the invitation link, version negotiation, and the request
signature.

Every peering request but the handshake is signed the Standard Webhooks way,
extended to bind the method and the path, so a signed GET cannot be replayed
against another route:

    webhook-id:        <a fresh UUID per request>
    webhook-timestamp: <Unix seconds at sending>
    webhook-signature: v1,<base64 HMAC-SHA256 of
                       "{id}.{timestamp}.{METHOD} {target}.{body}">

`target` is the path below the protocol root (`/hello`, `/changes?since=4`)
with its query string, so a reverse proxy in front of either side does not
change what is signed. The HMAC key is the secret the receiver issued to the
sender, as UTF-8 bytes.
"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import PeeringVersionMismatchError

# The prefixes make a leaked value recognisable, and the log redaction
# blanks both (`ring_buffer.py`).
PEER_SECRET_PREFIX = "cuisine_ps_"
INVITATION_CODE_PREFIX = "cuisine_pi_"
INVITATION_LIFETIME = timedelta(hours=24)
# The path of the invitation link on the inviting instance's web app.
ACCEPT_PATH = "/peering/accept"
# How far a request's timestamp may be from this instance's clock.
SIGNATURE_WINDOW = timedelta(minutes=5)
SIGNATURE_VERSION = "v1"


def new_peer_secret() -> str:
    return PEER_SECRET_PREFIX + secrets.token_urlsafe(32)


def new_invitation_code() -> str:
    return INVITATION_CODE_PREFIX + secrets.token_urlsafe(32)


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def normalised_base_url(url: str, *, require_https: bool) -> str:
    """The base URL of an instance: scheme, host, port and an optional path
    prefix, without a trailing slash, query, fragment or credentials. Plain
    http is refused unless `require_https` is off (debug mode)."""
    text = url.strip()
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError as exc:
        raise InvalidPeerConfigurationError("The instance URL is not a valid URL.") from exc
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise InvalidPeerConfigurationError("The instance URL must start with https://.")
    if require_https and parts.scheme != "https":
        raise InvalidPeerConfigurationError(
            "Peering needs https; plain http is accepted only in debug mode."
        )
    if parts.username or parts.password:
        raise InvalidPeerConfigurationError("The instance URL must not carry a user name.")
    if parts.query or parts.fragment:
        raise InvalidPeerConfigurationError("The instance URL must not carry a query.")
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    netloc = f"{host}:{port}" if port is not None else host
    return f"{parts.scheme}://{netloc}{parts.path.rstrip('/')}"


def invitation_link(base_url: str, code: str) -> str:
    return f"{base_url.rstrip('/')}{ACCEPT_PATH}?code={code}"


@dataclass(frozen=True)
class ParsedInvitation:
    base_url: str
    code: str


def parse_invitation_link(link: str, *, require_https: bool) -> ParsedInvitation:
    """Splits an invitation link into the inviting instance's base URL and
    the one-time code."""
    text = link.strip()
    try:
        parts = urlsplit(text)
    except ValueError as exc:
        raise InvalidPeerConfigurationError("The invitation link is not a valid URL.") from exc
    path = parts.path.rstrip("/")
    if not path.endswith(ACCEPT_PATH):
        raise InvalidPeerConfigurationError(
            "This is not a Cuisine invitation link; it ends in /peering/accept?code=…"
        )
    codes = parse_qs(parts.query).get("code", [])
    code = codes[0].strip() if len(codes) == 1 else ""
    if not code.startswith(INVITATION_CODE_PREFIX) or len(code) > 128:
        raise InvalidPeerConfigurationError("The invitation link carries no valid code.")
    prefix = path[: -len(ACCEPT_PATH)]
    base = normalised_base_url(
        f"{parts.scheme}://{parts.netloc}{prefix}", require_https=require_https
    )
    return ParsedInvitation(base_url=base, code=code)


# ── Version negotiation ───────────────────────────────────────────────


@dataclass(frozen=True)
class Negotiated:
    protocol_version: int
    # The highest common version of every format both sides know.
    format_versions: dict[str, int]


def _versions(values: list[int] | tuple[int, ...]) -> str:
    return ", ".join(str(v) for v in sorted(values)) or "none"


def negotiate(
    *,
    own_protocols: tuple[int, ...],
    peer_protocols: list[int],
    own_formats: dict[str, tuple[int, ...]],
    peer_formats: dict[str, list[int]],
    required_formats: set[str],
) -> Negotiated:
    """The highest common protocol version and, per format both sides
    know, the highest common format version. Raises with a message naming
    both sides' versions when there is no common protocol version, or no
    common version of a required format."""
    common = set(own_protocols) & set(peer_protocols)
    if not common:
        raise PeeringVersionMismatchError(
            f"No common peering protocol version: this instance speaks "
            f"{_versions(own_protocols)}, the other one {_versions(peer_protocols)}. "
            "Update the older instance."
        )
    formats: dict[str, int] = {}
    for name, own in sorted(own_formats.items()):
        theirs = peer_formats.get(name)
        if theirs is None:
            if name in required_formats:
                raise PeeringVersionMismatchError(
                    f"The other instance does not know the format {name} "
                    f"(this instance reads versions {_versions(own)})."
                )
            continue
        shared = set(own) & set(theirs)
        if not shared:
            if name in required_formats:
                raise PeeringVersionMismatchError(
                    f"No common version of the format {name}: this instance reads "
                    f"{_versions(own)}, the other one {_versions(theirs)}. "
                    "Update the older instance."
                )
            continue
        formats[name] = max(shared)
    return Negotiated(protocol_version=max(common), format_versions=formats)


def negotiation_is_acceptable(
    negotiated: Negotiated,
    *,
    own_protocols: tuple[int, ...],
    own_formats: dict[str, tuple[int, ...]],
    required_formats: set[str],
) -> bool:
    """Whether versions another instance chose are ones this instance
    supports, for checking the answer to a handshake."""
    if negotiated.protocol_version not in own_protocols:
        return False
    for name in required_formats:
        if name not in negotiated.format_versions:
            return False
    return all(
        name in own_formats and version in own_formats[name]
        for name, version in negotiated.format_versions.items()
    )


# ── Request signatures ────────────────────────────────────────────────


def signed_content(message_id: str, timestamp: int, method: str, target: str, body: bytes) -> bytes:
    head = f"{message_id}.{timestamp}.{method.upper()} {target}.".encode()
    return head + body


def sign_request(
    secret: str, *, message_id: str, timestamp: int, method: str, target: str, body: bytes
) -> str:
    """The `webhook-signature` value of a peering request."""
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_content(message_id, timestamp, method, target, body),
        hashlib.sha256,
    ).digest()
    return f"{SIGNATURE_VERSION},{base64.b64encode(digest).decode()}"


def signature_matches(
    secret: str,
    header: str,
    *,
    message_id: str,
    timestamp: int,
    method: str,
    target: str,
    body: bytes,
) -> bool:
    """Whether one of the space-separated signatures in the header is the
    expected one. Compared in constant time."""
    if not secret:
        return False
    expected = sign_request(
        secret, message_id=message_id, timestamp=timestamp, method=method, target=target, body=body
    )
    return any(hmac.compare_digest(expected, candidate) for candidate in header.split())


def timestamp_is_fresh(timestamp: int, now: datetime) -> bool:
    return abs(now.timestamp() - timestamp) <= SIGNATURE_WINDOW.total_seconds()
