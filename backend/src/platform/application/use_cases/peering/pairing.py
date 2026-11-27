"""
Pairing two instances. The administrator of instance A creates an
invitation; the administrator of instance B pastes the link into B, and B's
server calls A's handshake with the code, B's identity and the secret A
shall sign its requests to B with. A checks the code (one-time, unexpired),
negotiates the versions, stores the peer and answers its own identity, the
negotiated versions and the secret B shall sign its requests to A with.
B stores the peer too.

A pairing with an instance that is paired and active is refused; after a
revoke, pairing again reuses the record of that instance with fresh
secrets, versions and switches kept as they were.
"""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.peer_targets import checked_base_url
from src.platform.application.services.peer_targets import private_targets_allowed
from src.platform.application.services.peering_identity import InstanceIdentity
from src.platform.application.services.peering_identity import PeerIdentity
from src.platform.application.services.peering_identity import PeeringIdentity
from src.platform.application.services.peering_identity import identity_message
from src.platform.application.services.peering_identity import read_identity
from src.platform.application.services.peering_identity import read_negotiated
from src.platform.application.services.peering_identity import read_secret
from src.platform.application.services.peering_identity import required_formats
from src.platform.application.services.peering_identity import valid_secret
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer import PeerInvitation
from src.platform.domain.entities.peer import PeerStatus
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import DomainError
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import InvalidPeerInvitationError
from src.platform.domain.exceptions import PeerAlreadyPairedError
from src.platform.domain.exceptions import PeeringVersionMismatchError
from src.platform.domain.exceptions import PeerRefusedError
from src.platform.domain.services.peering_rules import Negotiated
from src.platform.domain.services.peering_rules import hash_code
from src.platform.domain.services.peering_rules import negotiate
from src.platform.domain.services.peering_rules import negotiation_is_acceptable
from src.platform.domain.services.peering_rules import new_peer_secret
from src.platform.domain.services.peering_rules import parse_invitation_link
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.peer_client import IPeerClient
from src.platform.ports.outbound.peer_client import PeerReply
from src.platform.ports.outbound.peer_client import PeerRequest
from src.platform.ports.outbound.repositories.peer_repository import IPeerInvitationRepository
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.platform.ports.outbound.webhook_sender import IWebhookTargetGuard
from src.shared_kernel.domain.services.clock import now_utc

# The longest part of a peer's refusal message shown to the administrator.
REFUSAL_MAX = 300


@dataclass(frozen=True)
class HandshakeCommand:
    """The handshake request: the caller's identity, the invitation code and
    the secret this instance shall sign its requests to the caller with."""

    identity: PeerIdentity
    code: str
    secret: str


@dataclass(frozen=True)
class HandshakeAnswer:
    identity: InstanceIdentity
    negotiated: Negotiated
    # The secret the caller shall sign its requests to this instance with.
    secret: str


def _refusal_reason(exc: DomainError) -> str:
    if isinstance(exc, PeeringVersionMismatchError):
        return "version_mismatch"
    if isinstance(exc, PeerAlreadyPairedError):
        return "already_paired"
    return "invalid_identity"


def _refusal_message(reply: PeerReply) -> str:
    detail = (reply.data or {}).get("detail")
    if isinstance(detail, str) and detail.strip():
        text = " ".join(detail.split())[:REFUSAL_MAX]
        return f"The other instance refused the pairing: {text}"
    return f"The other instance refused the pairing (HTTP {reply.status})."


# Called with the peer inside the transaction that paired it, on both sides
# and also when an instance pairs again after a revoke.
PeerPairedHook = Callable[[Peer], Awaitable[None]]


class PairWithPeer:
    def __init__(
        self,
        *,
        peers: IPeerRepository,
        invitations: IPeerInvitationRepository,
        identity: PeeringIdentity,
        client: IPeerClient,
        guard: IWebhookTargetGuard,
        settings_repo: ISettingsRepository,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        require_https: bool,
        on_paired: list[PeerPairedHook] | None = None,
    ) -> None:
        self._on_paired = on_paired or []
        self._peers = peers
        self._invitations = invitations
        self._identity = identity
        self._client = client
        self._guard = guard
        self._settings = settings_repo
        self._audit = audit
        self._uow = uow
        self._require_https = require_https

    # ── Instance B: accepting an invitation ──────────────────────────

    async def accept(self, actor: User, link: str, *, context: RequestContext) -> Peer:
        """Calls the inviting instance's handshake and stores the peer it
        answers."""
        parsed = parse_invitation_link(link, require_https=self._require_https)
        base = await self._checked(parsed.base_url)
        own = await self._identity.current()
        secret_for_them = new_peer_secret()
        reply = await self._client.send(
            PeerRequest(
                base_url=base,
                method="POST",
                target="/handshake",
                protocol_version=own.current_protocol,
                body={**identity_message(own), "code": parsed.code, "secret": secret_for_them},
            ),
            allow_private=await private_targets_allowed(self._settings),
        )
        if reply.status != 200:
            await self._record_refusal("refused_by_peer", actor=actor, context=context)
            await self._uow.commit()
            raise PeerRefusedError(_refusal_message(reply))
        data: dict[str, Any] = reply.data or {}
        identity = read_identity(data)
        negotiated = read_negotiated(data)
        secret_for_us = read_secret(data)
        if identity.instance_id == own.instance_id:
            raise InvalidPeerConfigurationError("An instance cannot pair with itself.")
        if not negotiation_is_acceptable(
            negotiated,
            own_protocols=own.protocol_versions,
            own_formats=own.formats,
            required_formats=required_formats(),
        ):
            raise PeeringVersionMismatchError(
                "The other instance chose versions this instance does not support; "
                "update the older instance."
            )
        peer_base = await self._checked(identity.base_url)
        existing = await self._peers.get_by_instance_id(identity.instance_id)
        peer = self._paired(
            existing,
            identity,
            peer_base,
            negotiated,
            inbound_secret=secret_for_them,
            outbound_secret=secret_for_us,
        )
        saved = await self._peers.save(peer)
        for hook in self._on_paired:
            await hook(saved)
        await self._audit.record(
            SecurityEventType.PEER_PAIRED,
            actor=actor,
            context=context,
            detail={"peer": str(saved.public_id), "role": "accepted"},
        )
        await self._uow.commit()
        return saved

    # ── Instance A: answering the handshake ──────────────────────────

    async def answer_handshake(
        self, command: HandshakeCommand, *, context: RequestContext
    ) -> HandshakeAnswer:
        now = now_utc()
        invitation = await self._invitations.get_by_code_hash(hash_code(command.code))
        reason = None
        if invitation is None:
            reason = "unknown_code"
        elif invitation.used_at is not None:
            reason = "used_code"
        elif invitation.expires_at <= now:
            reason = "expired_code"
        if invitation is None or reason is not None:
            await self._record_refusal(
                reason or "unknown_code", context=context, invitation=invitation
            )
            await self._uow.commit()
            raise InvalidPeerInvitationError(
                "The invitation is unknown, already used or expired. Ask for a new one."
            )
        own = await self._identity.current()
        try:
            negotiated, peer_base, existing = await self._validated(command, own)
        except (
            InvalidPeerConfigurationError,
            PeeringVersionMismatchError,
            PeerAlreadyPairedError,
        ) as exc:
            await self._record_refusal(_refusal_reason(exc), context=context, invitation=invitation)
            await self._uow.commit()
            raise
        peer = self._paired(
            existing,
            command.identity,
            peer_base,
            negotiated,
            inbound_secret=new_peer_secret(),
            outbound_secret=command.secret,
        )
        saved = await self._peers.save(peer)
        if not await self._invitations.claim(invitation, peer_id=saved.id, now=now):
            # Another handshake used the code a moment ago.
            await self._uow.rollback()
            await self._record_refusal("used_code", context=context, invitation=invitation)
            await self._uow.commit()
            raise InvalidPeerInvitationError(
                "The invitation is unknown, already used or expired. Ask for a new one."
            )
        for hook in self._on_paired:
            await hook(saved)
        await self._audit.record(
            SecurityEventType.PEER_PAIRED,
            actor=None,
            context=context,
            detail={
                "peer": str(saved.public_id),
                "role": "invited",
                "invitation": str(invitation.public_id),
            },
        )
        await self._uow.commit()
        return HandshakeAnswer(identity=own, negotiated=negotiated, secret=saved.inbound_secret)

    async def _validated(
        self, command: HandshakeCommand, own: InstanceIdentity
    ) -> tuple[Negotiated, str, Peer | None]:
        identity = command.identity
        if identity.instance_id == own.instance_id:
            raise InvalidPeerConfigurationError("An instance cannot pair with itself.")
        if not valid_secret(command.secret):
            raise InvalidPeerConfigurationError("The handshake carries no valid secret.")
        negotiated = negotiate(
            own_protocols=own.protocol_versions,
            peer_protocols=identity.protocol_versions,
            own_formats=own.formats,
            peer_formats=identity.formats,
            required_formats=required_formats(),
        )
        existing = await self._peers.get_by_instance_id(identity.instance_id)
        if existing is not None and existing.active:
            raise PeerAlreadyPairedError(
                f"This instance is already paired with {existing.name}. Revoke that pairing "
                "first to pair again."
            )
        peer_base = await self._checked(identity.base_url)
        return negotiated, peer_base, existing

    # ── Shared ───────────────────────────────────────────────────────

    async def _checked(self, url: str) -> str:
        return await checked_base_url(
            url, guard=self._guard, settings_repo=self._settings, require_https=self._require_https
        )

    @staticmethod
    def _paired(
        existing: Peer | None,
        identity: PeerIdentity,
        base_url: str,
        negotiated: Negotiated,
        *,
        inbound_secret: str,
        outbound_secret: str,
    ) -> Peer:
        now = now_utc()
        peer = existing or Peer(
            instance_id=identity.instance_id,
            name=identity.name,
            base_url=base_url,
            protocol_version=negotiated.protocol_version,
            created=now,
            paired_at=now,
            changed=now,
            # A first pairing takes the peer's recipes in at once; a pairing
            # again after a revoke keeps the stored switches.
            sync_all=True,
        )
        peer.name = identity.name
        peer.base_url = base_url
        peer.app_version = identity.app_version
        peer.protocol_version = negotiated.protocol_version
        peer.format_versions = dict(negotiated.format_versions)
        peer.capabilities = list(identity.capabilities)
        peer.status = PeerStatus.ACTIVE
        peer.revoked_by = None
        peer.revoked_at = None
        peer.inbound_secret = inbound_secret
        peer.outbound_secret = outbound_secret
        peer.paired_at = now
        peer.last_contact_at = now
        peer.changed = now
        return peer

    async def _record_refusal(
        self,
        reason: str,
        *,
        context: RequestContext,
        actor: User | None = None,
        invitation: PeerInvitation | None = None,
    ) -> None:
        detail: dict[str, object] = {"reason": reason}
        if invitation is not None:
            detail["invitation"] = str(invitation.public_id)
        await self._audit.record(
            SecurityEventType.PEER_PAIRING_REFUSED,
            actor=actor,
            context=context,
            outcome=SecurityEventOutcome.FAILURE,
            detail=detail,
        )
