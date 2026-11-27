"""
A paired Cuisine instance and the invitations that start a pairing.

Pairing is pairwise and done once by the administrators of both instances.
Each side keeps its own record of the other, with two secrets: the one this
instance issued, which the peer signs its requests to us with, and the one
the peer issued, which we sign our requests to the peer with. Both are
stored encrypted and never shown.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import UUID

from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class PeerStatus(StrValueEnum):
    ACTIVE = "active"
    # Either side revoked the pairing; the secrets are gone and every
    # peering request of this peer is refused.
    REVOKED = "revoked"


class PeerRevokedBy(StrValueEnum):
    # An administrator of this instance revoked it.
    LOCAL = "local"
    # The peer told us it revoked the pairing.
    REMOTE = "remote"


class MirrorVisibility(StrValueEnum):
    """Who on this instance sees the recipes a peer shares with us. A
    mirror has no owner here, so there is no household to scope it to; the
    choice is every signed-in user or the members of one group."""

    INSTANCE = "instance"
    GROUP = "group"


@dataclass(kw_only=True)
class Peer(Entity):
    instance_id: UUID
    name: str
    # Where the peer's web app and API live, without a trailing slash.
    base_url: str
    # Informative only, shown on the peer page; never decides anything.
    app_version: str = ""
    # The negotiated protocol version and, per format, the negotiated
    # format version.
    protocol_version: int
    format_versions: dict[str, int] = field(default_factory=dict)
    # What the peer announced it can show, such as `variations`.
    capabilities: list[str] = field(default_factory=list)
    status: PeerStatus = PeerStatus.ACTIVE
    revoked_by: PeerRevokedBy | None = None
    # The secret this instance issued: the peer signs its requests to us
    # with it. Empty once revoked.
    inbound_secret: str = ""
    # The secret the peer issued: we sign our requests to the peer with it.
    # Empty once revoked.
    outbound_secret: str = ""
    # Outgoing: whether this peer receives anything: the recipes users share
    # with it, and every recipe set to peers or public.
    users_may_share: bool = True
    # Incoming: whether recipes from this peer are accepted at all, who sees
    # them once accepted, and whether they are accepted at once with
    # automatic catalogue decisions instead of waiting for an administrator
    # (`sync_all`).
    accept_incoming: bool = True
    sync_all: bool = False
    mirror_visibility: MirrorVisibility = MirrorVisibility.INSTANCE
    # The group for MirrorVisibility.GROUP. A deleted group leaves this
    # empty, and mirrors are then shown to nobody until another is picked.
    mirror_group_id: int | None = None
    created: datetime
    paired_at: datetime
    revoked_at: datetime | None = None
    # The last time the peer answered or reached us.
    last_contact_at: datetime | None = None
    changed: datetime

    @property
    def active(self) -> bool:
        return self.status == PeerStatus.ACTIVE


@dataclass(kw_only=True)
class PeerInvitation(Entity):
    # SHA-256 of the one-time code; the code itself is shown once.
    code_hash: str
    created_by_id: int | None = None
    created: datetime
    expires_at: datetime
    used_at: datetime | None = None
    # The peer the invitation paired, once used.
    peer_id: int | None = None
