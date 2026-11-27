from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class PeerChannelModel(Base):
    """One per peer, keyed by the peer: the sequence counters, the sender's
    cursor and retry state, the receiver's position, the timers and the
    leases that keep two workers from doing the same work."""

    __tablename__ = "peer_channels"

    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), primary_key=True
    )
    paired_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    out_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    send_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_send_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_delivery_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_delivery_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_delivery_error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    in_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_catch_up_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_reconcile_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_receive_error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    catch_up_due_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    reconcile_due_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    ping_due_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    send_lease_until: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    receive_lease_until: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class PeerChannelEventModel(PublicIdMixin, Base):
    """The channel log: the latest event per item and peer."""

    __tablename__ = "peer_channel_events"
    __table_args__ = (
        UniqueConstraint("peer_id", "kind", "item_id", name="uq_peer_channel_events_item"),
        Index("ix_peer_channel_events_peer_seq", "peer_id", "seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    revision: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class PeerInboxModel(PublicIdMixin, Base):
    """Events received from peers, waiting for the background worker."""

    __tablename__ = "peer_inbox"
    __table_args__ = (Index("ix_peer_inbox_peer_next", "peer_id", "next_attempt_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    item_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    revision: Mapped[str | None] = mapped_column(String(128), nullable=True)
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prev_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
