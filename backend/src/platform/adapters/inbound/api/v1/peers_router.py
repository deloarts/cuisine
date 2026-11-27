"""
/api/v1/web/admin/peers: the administrator's side of peering. This
instance's own identity, invitations, accepting another instance's
invitation, the paired instances with their switches and channel status,
refresh, sync now and revoke. Reading needs read:settings, changing
write:settings. Every route answers 404 while the peering feature switch
is off.
"""

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import get_manage_peer_invitations
from src.platform.adapters.inbound.api.deps import get_manage_peers
from src.platform.adapters.inbound.api.deps import get_pair_with_peer
from src.platform.adapters.inbound.api.deps import get_peer_channel_status
from src.platform.adapters.inbound.api.peer_auth import require_peering_enabled
from src.platform.adapters.inbound.api.schemas.peering_schema import AcceptPeerInvitationRequest
from src.platform.adapters.inbound.api.schemas.peering_schema import CreatedPeerInvitationResponse
from src.platform.adapters.inbound.api.schemas.peering_schema import OwnInstanceResponse
from src.platform.adapters.inbound.api.schemas.peering_schema import PeerChannelResponse
from src.platform.adapters.inbound.api.schemas.peering_schema import PeerInvitationResponse
from src.platform.adapters.inbound.api.schemas.peering_schema import PeerResponse
from src.platform.adapters.inbound.api.schemas.peering_schema import PeerRevokeResponse
from src.platform.adapters.inbound.api.schemas.peering_schema import PeerSwitchesRequest
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.peering.channel_jobs import ChannelStatus
from src.platform.application.use_cases.peering.channel_jobs import PeerChannelStatus
from src.platform.application.use_cases.peering.invitations import ManagePeerInvitations
from src.platform.application.use_cases.peering.pairing import PairWithPeer
from src.platform.application.use_cases.peering.peers import ManagePeers
from src.platform.application.use_cases.peering.peers import PeerSwitches
from src.platform.domain.entities.peer import MirrorVisibility
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer import PeerInvitation
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["peering"], dependencies=[Depends(require_peering_enabled)])

_read = require_permission(Permission.READ_SETTINGS)
_write = require_permission(Permission.WRITE_SETTINGS)


def _channel(status: ChannelStatus | None) -> PeerChannelResponse | None:
    if status is None:
        return None
    return PeerChannelResponse(
        last_sent_seq=status.delivered_seq,
        out_seq=status.out_seq,
        pending_outgoing=status.pending_outgoing,
        last_received_seq=status.in_seq,
        pending_incoming=status.pending_incoming,
        last_delivery_at=status.last_delivery_at,
        last_delivery_status=status.last_delivery_status,
        last_delivery_error=status.last_delivery_error,
        next_send_at=status.next_send_at,
        last_catch_up_at=status.last_catch_up_at,
        last_reconcile_at=status.last_reconcile_at,
        last_receive_error=status.last_receive_error,
    )


def _peer(peer: Peer, groups: dict[int, UUID], channels: dict[int, ChannelStatus]) -> PeerResponse:
    return PeerResponse(
        id=peer.public_id,
        instance_id=peer.instance_id,
        name=peer.name,
        base_url=peer.base_url,
        app_version=peer.app_version,
        status=peer.status.value,
        revoked_by=peer.revoked_by.value if peer.revoked_by else None,
        protocol_version=peer.protocol_version,
        format_versions=peer.format_versions,
        capabilities=peer.capabilities,
        users_may_share=peer.users_may_share,
        accept_incoming=peer.accept_incoming,
        mirror_visibility=peer.mirror_visibility.value,
        mirror_group=groups.get(peer.mirror_group_id) if peer.mirror_group_id else None,
        sync_all=peer.sync_all,
        created=peer.created,
        paired_at=peer.paired_at,
        revoked_at=peer.revoked_at,
        last_contact_at=peer.last_contact_at,
        channel=_channel(channels.get(peer.id)),
    )


async def _present(peer: Peer, use_case: ManagePeers, channels: PeerChannelStatus) -> PeerResponse:
    return _peer(peer, await use_case.group_public_ids([peer]), await channels.of([peer]))


def _invitation(invitation: PeerInvitation) -> PeerInvitationResponse:
    return PeerInvitationResponse(
        id=invitation.public_id, created=invitation.created, expires_at=invitation.expires_at
    )


@router.get("/admin/peers/self", response_model=OwnInstanceResponse)
async def read_own_instance(
    _user: User = Depends(_read), use_case: ManagePeers = Depends(get_manage_peers)
) -> OwnInstanceResponse:
    own = await use_case.own_identity()
    return OwnInstanceResponse(
        instance_id=own.instance_id,
        name=own.name,
        base_url=own.base_url,
        app_version=own.app_version,
        protocol_versions=list(own.protocol_versions),
        formats={name: list(versions) for name, versions in own.formats.items()},
        capabilities=list(own.capabilities),
    )


@router.get("/admin/peers/invitations", response_model=list[PeerInvitationResponse])
async def list_peer_invitations(
    _user: User = Depends(_read),
    use_case: ManagePeerInvitations = Depends(get_manage_peer_invitations),
) -> list[PeerInvitationResponse]:
    return [_invitation(i) for i in await use_case.list_open()]


@router.post(
    "/admin/peers/invitations",
    response_model=CreatedPeerInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_peer_invitation(
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManagePeerInvitations = Depends(get_manage_peer_invitations),
) -> CreatedPeerInvitationResponse:
    created = await use_case.create(actor, context=context)
    return CreatedPeerInvitationResponse(
        **_invitation(created.invitation).model_dump(), link=created.link
    )


@router.delete("/admin/peers/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_peer_invitation(
    invitation_id: str,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManagePeerInvitations = Depends(get_manage_peer_invitations),
) -> None:
    await use_case.revoke(actor, invitation_id, context=context)


@router.post("/admin/peers/accept", response_model=PeerResponse)
async def accept_peer_invitation(
    body: AcceptPeerInvitationRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    pairing: PairWithPeer = Depends(get_pair_with_peer),
    peers: ManagePeers = Depends(get_manage_peers),
    channels: PeerChannelStatus = Depends(get_peer_channel_status),
) -> PeerResponse:
    peer = await pairing.accept(actor, body.invitation_url, context=context)
    return await _present(peer, peers, channels)


@router.get("/admin/peers", response_model=list[PeerResponse])
async def list_peers(
    _user: User = Depends(_read),
    use_case: ManagePeers = Depends(get_manage_peers),
    channels: PeerChannelStatus = Depends(get_peer_channel_status),
) -> list[PeerResponse]:
    peers = await use_case.list_all()
    groups = await use_case.group_public_ids(peers)
    statuses = await channels.of(peers)
    return [_peer(p, groups, statuses) for p in peers]


@router.put("/admin/peers/{peer_id}/switches", response_model=PeerResponse)
async def update_peer_switches(
    peer_id: str,
    body: PeerSwitchesRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManagePeers = Depends(get_manage_peers),
    channels: PeerChannelStatus = Depends(get_peer_channel_status),
) -> PeerResponse:
    peer = await use_case.update_switches(
        actor,
        peer_id,
        PeerSwitches(
            users_may_share=body.users_may_share,
            accept_incoming=body.accept_incoming,
            mirror_visibility=MirrorVisibility(body.mirror_visibility),
            mirror_group=body.mirror_group,
            sync_all=body.sync_all,
        ),
        context=context,
    )
    return await _present(peer, use_case, channels)


@router.post("/admin/peers/{peer_id}/refresh", response_model=PeerResponse)
async def refresh_peer(
    peer_id: str,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManagePeers = Depends(get_manage_peers),
    channels: PeerChannelStatus = Depends(get_peer_channel_status),
) -> PeerResponse:
    peer = await use_case.refresh(actor, peer_id, context=context)
    return await _present(peer, use_case, channels)


@router.post("/admin/peers/{peer_id}/revoke", response_model=PeerRevokeResponse)
async def revoke_peer(
    peer_id: str,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManagePeers = Depends(get_manage_peers),
    channels: PeerChannelStatus = Depends(get_peer_channel_status),
) -> PeerRevokeResponse:
    result = await use_case.revoke(actor, peer_id, context=context)
    return PeerRevokeResponse(
        peer=await _present(result.peer, use_case, channels), peer_notified=result.peer_notified
    )


@router.post("/admin/peers/{peer_id}/sync", response_model=PeerResponse)
async def sync_peer(
    peer_id: str,
    _actor: User = Depends(_write),
    use_case: ManagePeers = Depends(get_manage_peers),
    channels: PeerChannelStatus = Depends(get_peer_channel_status),
) -> PeerResponse:
    """Sync now: the channel worker catches up with the peer and retries
    pending deliveries within seconds instead of at their scheduled time."""
    peer = await channels.sync_now(peer_id)
    return await _present(peer, use_case, channels)
