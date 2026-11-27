"""
The paired instances: the administrator's list with the per-peer switches,
refreshing a peer's versions and capabilities, and revoking a pairing from
either side.

Revoking marks the peer revoked and clears both secrets in one transaction,
runs the registered revocation hooks in that transaction (the cookbook
removes the peer's mirrors there) and then tells the peer, best effort: a
peer that cannot be reached stays paired on its side until its own
requests are refused.
"""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.peer_targets import checked_base_url
from src.platform.application.services.peer_targets import private_targets_allowed
from src.platform.application.services.peering_identity import InstanceIdentity
from src.platform.application.services.peering_identity import PeeringIdentity
from src.platform.application.services.peering_identity import read_identity
from src.platform.application.services.peering_identity import required_formats
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.peer import MirrorVisibility
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer import PeerRevokedBy
from src.platform.domain.entities.peer import PeerStatus
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import PeerNotFoundError
from src.platform.domain.exceptions import PeerRefusedError
from src.platform.domain.exceptions import PeerUnreachableError
from src.platform.domain.services.peering_rules import negotiate
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.peer_client import IPeerClient
from src.platform.ports.outbound.peer_client import PeerRequest
from src.platform.ports.outbound.peer_client import PeerSigning
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_group_repository import IUserGroupRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.platform.ports.outbound.webhook_sender import IWebhookTargetGuard
from src.shared_kernel.domain.services.clock import now_utc

# Called with the revoked peer inside the revoking transaction, whichever
# side revoked.
PeerRevokedHook = Callable[[Peer], Awaitable[None]]
# Called with the peer, the names of the changed fields and the
# capabilities the peer gained, inside the transaction that changed its
# switches or took over a renegotiation.
PeerChangedHook = Callable[[Peer, frozenset[str], frozenset[str]], Awaitable[None]]


@dataclass(frozen=True)
class PeerSwitches:
    users_may_share: bool
    accept_incoming: bool
    mirror_visibility: MirrorVisibility
    # The group's public id, for MirrorVisibility.GROUP.
    mirror_group: str | None = None
    sync_all: bool = False


@dataclass(frozen=True)
class RevokeResult:
    peer: Peer
    # Whether the peer confirmed that it took note.
    peer_notified: bool


async def revoke_peer(
    peer: Peer,
    *,
    by: PeerRevokedBy,
    peers: IPeerRepository,
    hooks: list[PeerRevokedHook],
) -> Peer:
    """Marks the peer revoked, clears its secrets and runs the hooks. The
    caller records the security log entry and commits."""
    now = now_utc()
    peer.status = PeerStatus.REVOKED
    peer.revoked_by = by
    peer.revoked_at = now
    peer.inbound_secret = ""
    peer.outbound_secret = ""
    peer.changed = now
    saved = await peers.save(peer)
    for hook in hooks:
        await hook(saved)
    return saved


class ManagePeers:
    def __init__(
        self,
        *,
        peers: IPeerRepository,
        groups: IUserGroupRepository,
        identity: PeeringIdentity,
        client: IPeerClient,
        guard: IWebhookTargetGuard,
        settings_repo: ISettingsRepository,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        require_https: bool,
        on_revoked: list[PeerRevokedHook] | None = None,
        on_changed: list[PeerChangedHook] | None = None,
    ) -> None:
        self._on_changed = on_changed or []
        self._peers = peers
        self._groups = groups
        self._identity = identity
        self._client = client
        self._guard = guard
        self._settings = settings_repo
        self._audit = audit
        self._uow = uow
        self._require_https = require_https
        self._on_revoked = on_revoked or []

    async def own_identity(self) -> InstanceIdentity:
        return await self._identity.current()

    async def list_all(self) -> list[Peer]:
        return await self._peers.list_all()

    async def get(self, public_id: str) -> Peer:
        found = await self._peers.get_by_public_id(public_id)
        if found is None:
            raise PeerNotFoundError("No such paired instance.")
        return found

    async def group_public_ids(self, peers: list[Peer]) -> dict[int, UUID]:
        ids = sorted({p.mirror_group_id for p in peers if p.mirror_group_id is not None})
        return {g.id: g.public_id for g in await self._groups.get_many(ids)} if ids else {}

    async def update_switches(
        self, actor: User, public_id: str, switches: PeerSwitches, *, context: RequestContext
    ) -> Peer:
        peer = await self.get(public_id)
        group_id: int | None = None
        if switches.mirror_visibility == MirrorVisibility.GROUP:
            group = (
                await self._groups.get_by_public_id(switches.mirror_group)
                if switches.mirror_group
                else None
            )
            if group is None:
                raise InvalidPeerConfigurationError(
                    "Pick the group that sees the recipes from this instance."
                )
            group_id = group.id
        before = (
            peer.users_may_share,
            peer.sync_all,
            peer.accept_incoming,
            peer.mirror_visibility,
            peer.mirror_group_id,
        )
        after = (
            switches.users_may_share,
            switches.sync_all,
            switches.accept_incoming,
            switches.mirror_visibility,
            group_id,
        )
        names = (
            "users_may_share",
            "sync_all",
            "accept_incoming",
            "mirror_visibility",
            "mirror_group",
        )
        changed = [name for name, old, new in zip(names, before, after, strict=True) if old != new]
        if not changed:
            return peer
        (
            peer.users_may_share,
            peer.sync_all,
            peer.accept_incoming,
            peer.mirror_visibility,
            peer.mirror_group_id,
        ) = after
        peer.changed = now_utc()
        saved = await self._peers.save(peer)
        for hook in self._on_changed:
            await hook(saved, frozenset(changed), frozenset())
        await self._audit.record(
            SecurityEventType.PEER_CHANGED,
            actor=actor,
            context=context,
            detail={"peer": str(saved.public_id), "action": "switches", "fields": changed},
        )
        await self._uow.commit()
        return saved

    async def refresh(self, actor: User, public_id: str, *, context: RequestContext) -> Peer:
        """Reads the peer's `/hello` again and takes over its name, URL,
        app version, capabilities and the newly negotiated versions."""
        peer = await self.get(public_id)
        return await self.renegotiate(peer, actor=actor, context=context)

    async def renegotiate(
        self, peer: Peer, *, actor: User | None = None, context: RequestContext | None = None
    ) -> Peer:
        """The refresh without an administrator, for a peer that announced
        a change. Leaves the record as it was when the peer cannot be
        reached or the versions no longer overlap, and raises."""
        if not peer.active:
            raise InvalidPeerConfigurationError("The pairing with this instance is revoked.")
        own = await self._identity.current()
        reply = await self._client.send(
            PeerRequest(
                base_url=peer.base_url,
                method="GET",
                target="/hello",
                protocol_version=peer.protocol_version,
                signing=PeerSigning(
                    sender_instance_id=own.instance_id, secret=peer.outbound_secret
                ),
            ),
            allow_private=await private_targets_allowed(self._settings),
        )
        if reply.status != 200:
            raise PeerRefusedError(
                f"The other instance refused the request (HTTP {reply.status}). It may have "
                "revoked the pairing."
            )
        identity = read_identity(reply.data)
        if identity.instance_id != peer.instance_id:
            raise InvalidPeerConfigurationError(
                "The instance at this address is not the paired instance any more."
            )
        negotiated = negotiate(
            own_protocols=own.protocol_versions,
            peer_protocols=identity.protocol_versions,
            own_formats=own.formats,
            peer_formats=identity.formats,
            required_formats=required_formats(),
        )
        base = await checked_base_url(
            identity.base_url,
            guard=self._guard,
            settings_repo=self._settings,
            require_https=self._require_https,
        )
        before = {
            "name": peer.name,
            "base_url": peer.base_url,
            "app_version": peer.app_version,
            "protocol_version": peer.protocol_version,
            "format_versions": peer.format_versions,
            "capabilities": peer.capabilities,
        }
        after = {
            "name": identity.name,
            "base_url": base,
            "app_version": identity.app_version,
            "protocol_version": negotiated.protocol_version,
            "format_versions": dict(negotiated.format_versions),
            "capabilities": list(identity.capabilities),
        }
        changed = sorted(k for k in after if before[k] != after[k])
        gained = frozenset(identity.capabilities) - frozenset(peer.capabilities)
        peer.name = identity.name
        peer.base_url = base
        peer.app_version = identity.app_version
        peer.protocol_version = negotiated.protocol_version
        peer.format_versions = dict(negotiated.format_versions)
        peer.capabilities = list(identity.capabilities)
        now = now_utc()
        peer.last_contact_at = now
        peer.changed = now
        saved = await self._peers.save(peer)
        if changed:
            for hook in self._on_changed:
                await hook(saved, frozenset(changed), gained)
            await self._audit.record(
                SecurityEventType.PEER_CHANGED,
                actor=actor,
                context=context,
                detail={"peer": str(saved.public_id), "action": "refreshed", "fields": changed},
            )
        await self._uow.commit()
        return saved

    async def revoke(self, actor: User, public_id: str, *, context: RequestContext) -> RevokeResult:
        peer = await self.get(public_id)
        if not peer.active:
            return RevokeResult(peer=peer, peer_notified=False)
        secret = peer.outbound_secret
        own = await self._identity.current()
        saved = await revoke_peer(
            peer, by=PeerRevokedBy.LOCAL, peers=self._peers, hooks=self._on_revoked
        )
        await self._audit.record(
            SecurityEventType.PEER_REVOKED,
            actor=actor,
            context=context,
            detail={"peer": str(saved.public_id), "by": PeerRevokedBy.LOCAL.value},
        )
        await self._uow.commit()
        return RevokeResult(peer=saved, peer_notified=await self._notify(saved, own, secret))

    async def _notify(self, peer: Peer, own: InstanceIdentity, secret: str) -> bool:
        """Tells the peer about the revoke. Failure is expected (the peer
        may be offline) and only reported back."""
        try:
            reply = await self._client.send(
                PeerRequest(
                    base_url=peer.base_url,
                    method="POST",
                    target="/revoke",
                    protocol_version=peer.protocol_version,
                    body={},
                    signing=PeerSigning(sender_instance_id=own.instance_id, secret=secret),
                ),
                allow_private=await private_targets_allowed(self._settings),
            )
        except (PeerUnreachableError, InvalidPeerConfigurationError):
            return False
        return 200 <= reply.status < 300


class AnswerPeer:
    """What the peering surface answers an authenticated peer: `/hello` and
    `/revoke`."""

    def __init__(
        self,
        *,
        peers: IPeerRepository,
        identity: PeeringIdentity,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        on_revoked: list[PeerRevokedHook] | None = None,
    ) -> None:
        self._peers = peers
        self._identity = identity
        self._audit = audit
        self._uow = uow
        self._on_revoked = on_revoked or []

    async def hello(self) -> InstanceIdentity:
        return await self._identity.current()

    async def revoked_by_peer(self, peer: Peer, *, context: RequestContext) -> None:
        saved = await revoke_peer(
            peer, by=PeerRevokedBy.REMOTE, peers=self._peers, hooks=self._on_revoked
        )
        await self._audit.record(
            SecurityEventType.PEER_REVOKED,
            actor=None,
            context=context,
            detail={"peer": str(saved.public_id), "by": PeerRevokedBy.REMOTE.value},
        )
        await self._uow.commit()
