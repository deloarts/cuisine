"""
The peer channel: how events flow between two paired instances.

Each side keeps one channel state per peer. As a source it numbers the
events it publishes to the peer with a sequence that only grows, and keeps
the latest event per item in its channel log, so many updates of one item
collapse into one entry and the log doubles as the answer to "what changed
since sequence n". A cursor says up to which sequence the peer has taken
the events, and the sender retries from there for as long as it takes. As
a receiver it remembers the last sequence it processed and queues the
events the peer sends for a background worker.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class PeerChannelState:
    """One per peer, keyed by the peer. Created on first use and started
    afresh when the peer is paired again."""

    peer_id: int
    # The pairing this state belongs to; a newer pairing starts it afresh.
    paired_at: datetime
    # Sending: the last sequence number given out, and the last one the
    # peer accepted.
    out_seq: int = 0
    delivered_seq: int = 0
    # Failed attempts since the last accepted event, and when to try next.
    send_attempts: int = 0
    next_send_at: datetime | None = None
    last_delivery_at: datetime | None = None
    last_delivery_status: int | None = None
    # A short category of the last failure, never the peer's text; None
    # after a success.
    last_delivery_error: str | None = None
    # Receiving: the last sequence number of the peer processed here.
    in_seq: int = 0
    last_catch_up_at: datetime | None = None
    last_reconcile_at: datetime | None = None
    # A short category of the last failure to fetch from the peer.
    last_receive_error: str | None = None
    # When the timers are due next.
    catch_up_due_at: datetime | None = None
    reconcile_due_at: datetime | None = None
    ping_due_at: datetime | None = None


@dataclass(kw_only=True)
class PeerChannelEvent(Entity):
    """The latest event of one item (or of one control type) in a peer's
    channel log."""

    peer_id: int
    seq: int
    type: str
    # The item's kind and id; for a control event (`peer.updated`, `ping`)
    # the kind is empty and the id is the event type.
    kind: str
    item_id: str
    revision: str | None = None
    # Extra fields of a control event, such as the versions of
    # `peer.updated`.
    data: dict[str, Any] = field(default_factory=dict)
    created: datetime


@dataclass(kw_only=True)
class PeerInboxJob(Entity):
    """An event a peer sent, waiting for the background worker."""

    peer_id: int
    type: str
    kind: str | None = None
    item_id: str | None = None
    revision: str | None = None
    # None for work this instance queued itself, such as a renegotiation
    # after the peer named another protocol version.
    seq: int | None = None
    prev_seq: int | None = None
    data: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    next_attempt_at: datetime
    error: str | None = None
    created: datetime
