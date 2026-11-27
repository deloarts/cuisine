"""
The peering surface (/api/peering/v1) that other Cuisine instances call.
It is separate from the web, PAT and key surfaces and from the privacy
acknowledgement: no person signs in here. The handshake is authenticated by
its invitation code, every other route by the peer's request signature
(`application/use_cases/peering/authenticate_peer.py`). Every route is rate
limited per address and answers 404 while the peering feature switch is
off; every answer names the protocol version in `Cuisine-Peering-Version`
(set in `bootstrap/main.py`, so refusals carry it too).

The messages are the dicts of `application/services/peering_identity.py`
and `application/services/peering_messages.py`.
The surface is left out of the OpenAPI snapshot, since the web app never
calls it; `docs/reference/peering.md` describes it.
"""

from typing import Any

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import Header
from fastapi import Query
from fastapi import Response
from fastapi import status
from fastapi.responses import JSONResponse

from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.deps import get_answer_peer
from src.platform.adapters.inbound.api.deps import get_answer_peer_channel
from src.platform.adapters.inbound.api.deps import get_pair_with_peer
from src.platform.adapters.inbound.api.deps import get_receive_peer_events
from src.platform.adapters.inbound.api.peer_auth import get_authenticated_peer
from src.platform.adapters.inbound.api.peer_auth import get_contacted_peer
from src.platform.adapters.inbound.api.peer_auth import require_peering_enabled
from src.platform.adapters.inbound.api.rate_limit import limit_peering_requests
from src.platform.application.dto.context import RequestContext
from src.platform.application.services.peering_identity import identity_message
from src.platform.application.services.peering_identity import negotiated_message
from src.platform.application.services.peering_identity import read_identity
from src.platform.application.use_cases.peering.authenticate_peer import AuthenticatedPeer
from src.platform.application.use_cases.peering.channel_receiving import ReceivePeerEvents
from src.platform.application.use_cases.peering.channel_source import AnswerPeerChannel
from src.platform.application.use_cases.peering.pairing import HandshakeCommand
from src.platform.application.use_cases.peering.pairing import PairWithPeer
from src.platform.application.use_cases.peering.peers import AnswerPeer
from src.platform.domain.exceptions import InvalidPeerInvitationError
from src.platform.domain.services.peer_channel_rules import ITEM_ID_MAX
from src.platform.domain.services.peer_channel_rules import KIND_MAX
from src.platform.domain.services.peer_channel_rules import is_token
from src.platform.domain.services.peering_rules import Negotiated

router = APIRouter(
    tags=["peering-surface"],
    dependencies=[Depends(require_peering_enabled), Depends(limit_peering_requests)],
)


@router.post("/handshake")
async def handshake(
    body: dict[str, Any] = Body(...),
    context: RequestContext = Depends(get_request_context),
    use_case: PairWithPeer = Depends(get_pair_with_peer),
) -> dict[str, Any]:
    """Pairs the calling instance, authenticated by the invitation code."""
    code = body.get("code")
    if not isinstance(code, str) or not code or len(code) > 128:
        raise InvalidPeerInvitationError(
            "The invitation is unknown, already used or expired. Ask for a new one."
        )
    secret = body.get("secret")
    answer = await use_case.answer_handshake(
        HandshakeCommand(
            identity=read_identity(body),
            code=code,
            secret=secret if isinstance(secret, str) else "",
        ),
        context=context,
    )
    return {
        **identity_message(answer.identity),
        **negotiated_message(answer.negotiated),
        "secret": answer.secret,
    }


@router.get("/hello")
async def hello(
    auth: AuthenticatedPeer = Depends(get_contacted_peer),
    use_case: AnswerPeer = Depends(get_answer_peer),
) -> dict[str, Any]:
    """This instance's identity, supported versions and capabilities, and
    the versions negotiated with the caller."""
    own = await use_case.hello()
    negotiated = Negotiated(
        protocol_version=auth.peer.protocol_version, format_versions=auth.peer.format_versions
    )
    return {**identity_message(own), **negotiated_message(negotiated)}


@router.post("/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke(
    auth: AuthenticatedPeer = Depends(get_authenticated_peer),
    context: RequestContext = Depends(get_request_context),
    use_case: AnswerPeer = Depends(get_answer_peer),
) -> None:
    """The caller revoked the pairing; this side follows."""
    await use_case.revoked_by_peer(auth.peer, context=context)


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def receive_event(
    body: dict[str, Any] = Body(...),
    auth: AuthenticatedPeer = Depends(get_contacted_peer),
    context: RequestContext = Depends(get_request_context),
    use_case: ReceivePeerEvents = Depends(get_receive_peer_events),
) -> dict[str, Any]:
    """One event of the caller's channel, queued for the background worker
    and answered at once."""
    await use_case.accept(auth.peer, body, context=context)
    return {}


@router.get("/changes")
async def changes(
    since: int = Query(0, ge=0),
    auth: AuthenticatedPeer = Depends(get_contacted_peer),
    use_case: AnswerPeerChannel = Depends(get_answer_peer_channel),
) -> dict[str, Any]:
    """The latest state of every item shared with the caller whose sequence
    is above `since`, and the channel's highest sequence."""
    return await use_case.changes(auth.peer, since)


@router.get("/items/{kind}/{item_id}", response_model=None)
async def item(
    kind: str,
    item_id: str,
    if_none_match: str | None = Header(default=None),
    auth: AuthenticatedPeer = Depends(get_contacted_peer),
    use_case: AnswerPeerChannel = Depends(get_answer_peer_channel),
) -> Response:
    """The content of one item shared with the caller, with its ETag; 304
    when the caller's copy is current. An item that is not shared with the
    caller answers 404 marked `withdrawn`, which the caller takes as a
    withdrawal; any other 404 (the feature switch is off) does not."""
    answer = (
        await use_case.item(auth.peer, kind, item_id, if_none_match=if_none_match)
        if is_token(kind, KIND_MAX) and is_token(item_id, ITEM_ID_MAX)
        else None
    )
    if answer is None or answer.item is None:
        return JSONResponse(
            {"detail": "The item is not shared with this instance.", "withdrawn": True},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    headers = {"ETag": answer.item.etag} if answer.item.etag else {}
    if answer.not_modified:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(content=answer.item.content, media_type=answer.item.media_type, headers=headers)
