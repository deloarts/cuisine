"""
Authenticates a signed peering request (`peering_rules` describes the
signature). A request passes when it names an active peer, its timestamp is
within five minutes of this instance's clock, one of its signatures matches
the secret this instance issued to that peer, and its message id was not
seen before. Every refusal is recorded in the security log with its reason
and answers the same 401.

The same check serves every signed route of the peering surface, and the
event deliveries a peer sends later use the same headers.
"""

from dataclasses import dataclass
from uuid import UUID

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.peer import Peer
from src.platform.domain.exceptions import PeerAuthenticationError
from src.platform.domain.exceptions import PeeringVersionMismatchError
from src.platform.domain.services.peering_rules import SIGNATURE_WINDOW
from src.platform.domain.services.peering_rules import signature_matches
from src.platform.domain.services.peering_rules import timestamp_is_fresh
from src.platform.domain.value_objects.peering import SUPPORTED_PROTOCOL_VERSIONS
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.replay_guard import IReplayGuard
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# A message id is remembered longer than the window in both directions, so a
# replay is refused for as long as its timestamp could pass.
REPLAY_MEMORY_SECONDS = int(SIGNATURE_WINDOW.total_seconds() * 2) + 60


@dataclass(frozen=True)
class SignedPeerRequest:
    """The parts of an HTTP request the signature covers, and its headers."""

    peer_instance_id: str | None
    message_id: str | None
    timestamp: str | None
    signature: str | None
    protocol_version: str | None
    method: str
    # The path below the protocol root with its query string.
    target: str
    body: bytes


@dataclass(frozen=True)
class AuthenticatedPeer:
    peer: Peer
    # The protocol version the request was sent with. A version other than
    # the negotiated one means the peer was upgraded.
    protocol_version: int


def protocol_version_of(header: str | None) -> int:
    """The protocol version a request names, refused when it is missing or
    outside this instance's support window."""
    supported = ", ".join(str(v) for v in SUPPORTED_PROTOCOL_VERSIONS)
    try:
        version = int(header or "")
    except ValueError as exc:
        raise PeeringVersionMismatchError(
            f"The request names no peering protocol version; this instance speaks {supported}."
        ) from exc
    if version not in SUPPORTED_PROTOCOL_VERSIONS:
        raise PeeringVersionMismatchError(
            f"The request uses peering protocol version {version}; this instance speaks "
            f"{supported}."
        )
    return version


class AuthenticatePeer:
    def __init__(
        self,
        *,
        peers: IPeerRepository,
        replay: IReplayGuard,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._peers = peers
        self._replay = replay
        self._audit = audit
        self._uow = uow

    async def authenticate(
        self, request: SignedPeerRequest, *, context: RequestContext
    ) -> AuthenticatedPeer:
        version = protocol_version_of(request.protocol_version)
        peer: Peer | None = None
        try:
            instance_id = UUID(request.peer_instance_id or "")
            timestamp = int(request.timestamp or "")
        except ValueError:
            return await self._refuse("malformed", None, context)
        if not request.message_id or not request.signature or len(request.message_id) > 128:
            return await self._refuse("malformed", None, context)
        peer = await self._peers.get_by_instance_id(instance_id)
        if peer is None:
            return await self._refuse("unknown_peer", None, context)
        if not peer.active:
            return await self._refuse("revoked", peer, context)
        if not timestamp_is_fresh(timestamp, now_utc()):
            return await self._refuse("stale_timestamp", peer, context)
        if not signature_matches(
            peer.inbound_secret,
            request.signature,
            message_id=request.message_id,
            timestamp=timestamp,
            method=request.method,
            target=request.target,
            body=request.body,
        ):
            return await self._refuse("bad_signature", peer, context)
        key = f"peering:{peer.public_id}:{request.message_id}"
        if not await self._replay.consume_once(key, REPLAY_MEMORY_SECONDS):
            return await self._refuse("replayed", peer, context)
        return AuthenticatedPeer(peer=peer, protocol_version=version)

    async def _refuse(
        self, reason: str, peer: Peer | None, context: RequestContext
    ) -> AuthenticatedPeer:
        detail: dict[str, object] = {"reason": reason}
        if peer is not None:
            detail["peer"] = str(peer.public_id)
        await self._audit.record(
            SecurityEventType.PEER_AUTH_FAILED,
            actor=None,
            context=context,
            outcome=SecurityEventOutcome.FAILURE,
            detail=detail,
        )
        await self._uow.commit()
        raise PeerAuthenticationError("The request is not signed by an active peer.")
