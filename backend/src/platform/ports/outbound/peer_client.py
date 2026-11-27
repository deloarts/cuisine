"""Sending one request to a paired, or soon paired, Cuisine instance."""

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PeerSigning:
    # This instance's id, sent in the `Cuisine-Peer` header.
    sender_instance_id: UUID
    # The secret the peer issued to this instance.
    secret: str


@dataclass(frozen=True)
class PeerRequest:
    # The peer's base URL, as stored or parsed from the invitation link.
    base_url: str
    method: str
    # The path below the protocol root, with its query string: `/hello`.
    target: str
    protocol_version: int
    body: dict[str, Any] | None = None
    # None only for the handshake, which the invitation code authenticates.
    signing: PeerSigning | None = None
    # Extra request headers, such as `If-None-Match`.
    headers: dict[str, str] = field(default_factory=dict)
    # A larger answer limit than the client's default, for item content.
    max_response_bytes: int | None = None


@dataclass(frozen=True)
class PeerReply:
    status: int
    # The JSON object the peer answered, or None for an empty or non-object
    # body.
    data: dict[str, Any] | None
    # The peer's `Cuisine-Peering-Version` header, if it sent one.
    protocol_version: str | None
    # The raw answer with its media type and etag, for item content.
    body: bytes = b""
    media_type: str | None = None
    etag: str | None = None


class IPeerClient(Protocol):
    async def send(self, request: PeerRequest, *, allow_private: bool) -> PeerReply:
        """Sends the request and returns any HTTP answer. Raises
        InvalidPeerConfigurationError when the target guard or the https
        rule refuses the URL, and PeerUnreachableError when the peer cannot
        be reached or answers with something that is no peering answer."""
        ...
