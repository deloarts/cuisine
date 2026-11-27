"""The admin area's peering schemas. The peering surface itself speaks the
dict messages of `application/services/peering_identity.py`, whose readers
ignore unknown fields."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class OwnInstanceResponse(ResponseSchema):
    """This instance as its peers see it."""

    instance_id: UUID
    name: str
    base_url: str
    app_version: str
    protocol_versions: list[int]
    formats: dict[str, list[int]]
    capabilities: list[str]


class PeerChannelResponse(ResponseSchema):
    """The peer channel in both directions. Sequence numbers count the
    events of one direction; the last delivery fields describe the last
    attempt to send to the peer, the receive fields the last catch-up with
    it. Error fields hold a short category, never the peer's text."""

    last_sent_seq: int
    out_seq: int
    pending_outgoing: int
    last_received_seq: int
    pending_incoming: int
    last_delivery_at: datetime | None
    last_delivery_status: int | None
    last_delivery_error: str | None
    next_send_at: datetime | None
    last_catch_up_at: datetime | None
    last_reconcile_at: datetime | None
    last_receive_error: str | None


class PeerResponse(ResponseSchema):
    id: UUID
    instance_id: UUID
    name: str
    base_url: str
    app_version: str
    status: Literal["active", "revoked"]
    revoked_by: Literal["local", "remote"] | None
    protocol_version: int
    format_versions: dict[str, int]
    capabilities: list[str]
    users_may_share: bool
    accept_incoming: bool
    mirror_visibility: Literal["instance", "group"]
    mirror_group: UUID | None
    # Recipes from this peer become mirrors at once, with automatic
    # catalogue decisions, instead of waiting for an administrator.
    sync_all: bool
    created: datetime
    paired_at: datetime
    revoked_at: datetime | None
    last_contact_at: datetime | None
    # None for a revoked peer, or before the channel was first used.
    channel: PeerChannelResponse | None = None


class PeerSwitchesRequest(RequestSchema):
    users_may_share: bool
    accept_incoming: bool
    mirror_visibility: Literal["instance", "group"]
    # The group's id, for "group".
    mirror_group: str | None = Field(default=None, max_length=64)
    sync_all: bool


class PeerRevokeResponse(ResponseSchema):
    peer: PeerResponse
    # Whether the other instance confirmed the revoke. When it did not, it
    # learns of it the next time it calls.
    peer_notified: bool


class PeerInvitationResponse(ResponseSchema):
    id: UUID
    created: datetime
    expires_at: datetime


class CreatedPeerInvitationResponse(PeerInvitationResponse):
    """Answers creating an invitation: the only time the link is shown."""

    link: str


class AcceptPeerInvitationRequest(RequestSchema):
    invitation_url: str = Field(min_length=1, max_length=2048)
