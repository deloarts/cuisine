"""
The dependencies of everything peering: the feature switch, which makes
every peering route answer 404 while it is off, the signature check of the
signed peering routes, and the contact record every signed request leaves.
"""

from fastapi import Depends
from fastapi import Request

from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_authenticate_peer
from src.platform.adapters.inbound.api.deps import get_peer_contact
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.peering.authenticate_peer import AuthenticatedPeer
from src.platform.application.use_cases.peering.authenticate_peer import AuthenticatePeer
from src.platform.application.use_cases.peering.authenticate_peer import SignedPeerRequest
from src.platform.application.use_cases.peering.channel_receiving import PeerContact
from src.platform.const import API_PEERING
from src.platform.domain.exceptions import PeeringDisabledError
from src.platform.domain.value_objects.peering import MESSAGE_ID_HEADER
from src.platform.domain.value_objects.peering import PEER_HEADER
from src.platform.domain.value_objects.peering import SIGNATURE_HEADER
from src.platform.domain.value_objects.peering import TIMESTAMP_HEADER
from src.platform.domain.value_objects.peering import VERSION_HEADER


async def require_peering_enabled(p: Platform = Depends(get_platform)) -> None:
    if not (await p.settings.get_features()).peering:
        raise PeeringDisabledError("Not Found")


def signed_target(request: Request) -> str:
    """The path below the protocol root with its query string, as the
    sender signed it."""
    path = request.url.path
    target = path[len(API_PEERING) :] if path.startswith(API_PEERING) else path
    query = request.url.query
    return f"{target}?{query}" if query else target


async def get_authenticated_peer(
    request: Request,
    context: RequestContext = Depends(get_request_context),
    use_case: AuthenticatePeer = Depends(get_authenticate_peer),
) -> AuthenticatedPeer:
    headers = request.headers
    return await use_case.authenticate(
        SignedPeerRequest(
            peer_instance_id=headers.get(PEER_HEADER),
            message_id=headers.get(MESSAGE_ID_HEADER),
            timestamp=headers.get(TIMESTAMP_HEADER),
            signature=headers.get(SIGNATURE_HEADER),
            protocol_version=headers.get(VERSION_HEADER),
            method=request.method,
            target=signed_target(request),
            body=await request.body(),
        ),
        context=context,
    )


async def get_contacted_peer(
    auth: AuthenticatedPeer = Depends(get_authenticated_peer),
    contact: PeerContact = Depends(get_peer_contact),
) -> AuthenticatedPeer:
    """`get_authenticated_peer`, and records the contact: the peer's last
    contact time, and a renegotiation when the request named another
    protocol version than the negotiated one."""
    await contact.seen(auth)
    return auth
