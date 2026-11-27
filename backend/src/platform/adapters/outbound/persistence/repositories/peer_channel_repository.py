"""
The peer channel tables. Every write to a channel state names the columns
it changes and goes out as one UPDATE, because the sender, the receiver and
the timers of one channel may run on different workers at once and must
not overwrite each other's columns with values read earlier.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import and_
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.peer_channel_models import (
    PeerChannelEventModel,
)
from src.platform.adapters.outbound.persistence.models.peer_channel_models import PeerChannelModel
from src.platform.adapters.outbound.persistence.models.peer_channel_models import PeerInboxModel
from src.platform.adapters.outbound.persistence.models.peer_models import PeerModel
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer import PeerStatus
from src.platform.domain.entities.peer_channel import PeerChannelEvent
from src.platform.domain.entities.peer_channel import PeerChannelState
from src.platform.domain.entities.peer_channel import PeerInboxJob
from src.platform.domain.services.peer_channel_rules import CONTROL_KIND
from src.platform.domain.services.peer_channel_rules import PING_EVERY
from src.platform.domain.services.peer_channel_rules import RECONCILE_EVERY
from src.shared_kernel.domain.services.clock import now_utc

_LEASES = {
    "send": PeerChannelModel.send_lease_until,
    "receive": PeerChannelModel.receive_lease_until,
}
_TIMERS = {
    "catch_up": PeerChannelModel.catch_up_due_at,
    "reconcile": PeerChannelModel.reconcile_due_at,
    "ping": PeerChannelModel.ping_due_at,
}
# The columns a caller may change through `update_state`; the counters
# have their own methods.
_STATE_COLUMNS = frozenset(
    {
        "delivered_seq",
        "send_attempts",
        "next_send_at",
        "last_delivery_at",
        "last_delivery_status",
        "last_delivery_error",
        "in_seq",
        "last_catch_up_at",
        "last_reconcile_at",
        "last_receive_error",
        "catch_up_due_at",
        "reconcile_due_at",
        "ping_due_at",
    }
)


def _state(row: PeerChannelModel) -> PeerChannelState:
    return PeerChannelState(
        peer_id=row.peer_id,
        paired_at=row.paired_at,
        out_seq=row.out_seq,
        delivered_seq=row.delivered_seq,
        send_attempts=row.send_attempts,
        next_send_at=row.next_send_at,
        last_delivery_at=row.last_delivery_at,
        last_delivery_status=row.last_delivery_status,
        last_delivery_error=row.last_delivery_error,
        in_seq=row.in_seq,
        last_catch_up_at=row.last_catch_up_at,
        last_reconcile_at=row.last_reconcile_at,
        last_receive_error=row.last_receive_error,
        catch_up_due_at=row.catch_up_due_at,
        reconcile_due_at=row.reconcile_due_at,
        ping_due_at=row.ping_due_at,
    )


def _fresh_values(paired_at: datetime, now: datetime) -> dict[str, Any]:
    """A channel that starts: catch up at once, compare and ping a day
    later."""
    return {
        "paired_at": paired_at,
        "out_seq": 0,
        "delivered_seq": 0,
        "send_attempts": 0,
        "next_send_at": None,
        "last_delivery_at": None,
        "last_delivery_status": None,
        "last_delivery_error": None,
        "in_seq": 0,
        "last_catch_up_at": None,
        "last_reconcile_at": None,
        "last_receive_error": None,
        "catch_up_due_at": now,
        "reconcile_due_at": now + RECONCILE_EVERY,
        "ping_due_at": now + PING_EVERY,
        "send_lease_until": None,
        "receive_lease_until": None,
    }


def _event(row: PeerChannelEventModel) -> PeerChannelEvent:
    return PeerChannelEvent(
        id=row.id,
        public_id=row.public_id,
        peer_id=row.peer_id,
        seq=row.seq,
        type=row.type,
        kind=row.kind,
        item_id=row.item_id,
        revision=row.revision,
        data=dict(row.data or {}),
        created=row.created,
    )


def _job(row: PeerInboxModel) -> PeerInboxJob:
    return PeerInboxJob(
        id=row.id,
        public_id=row.public_id,
        peer_id=row.peer_id,
        type=row.type,
        kind=row.kind,
        item_id=row.item_id,
        revision=row.revision,
        seq=row.seq,
        prev_seq=row.prev_seq,
        data=dict(row.data or {}),
        attempts=row.attempts,
        next_attempt_at=row.next_attempt_at,
        error=row.error,
        created=row.created,
    )


def _rowcount(result: Any) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


class SqlAlchemyPeerChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _row(self, peer_id: int) -> PeerChannelModel | None:
        return await self._db.get(PeerChannelModel, peer_id, populate_existing=True)

    async def state(self, peer: Peer) -> PeerChannelState:
        row = await self._row(peer.id)
        now = now_utc()
        if row is None:
            try:
                async with self._db.begin_nested():
                    self._db.add(
                        PeerChannelModel(peer_id=peer.id, **_fresh_values(peer.paired_at, now))
                    )
            except IntegrityError:
                # Another worker created it at the same moment.
                pass
            row = await self._row(peer.id)
            assert row is not None
        elif row.paired_at != peer.paired_at:
            # A new pairing with the same instance: nothing of the earlier
            # one carries over.
            await self._drop_log_and_queue(peer.id)
            await self._db.execute(
                update(PeerChannelModel)
                .where(PeerChannelModel.peer_id == peer.id)
                .values(**_fresh_values(peer.paired_at, now))
                .execution_options(synchronize_session=False)
            )
            row = await self._row(peer.id)
            assert row is not None
        return _state(row)

    async def states(self, peer_ids: list[int]) -> dict[int, PeerChannelState]:
        if not peer_ids:
            return {}
        rows = await self._db.scalars(
            select(PeerChannelModel)
            .where(PeerChannelModel.peer_id.in_(peer_ids))
            .execution_options(populate_existing=True)
        )
        return {r.peer_id: _state(r) for r in rows.all()}

    async def update_state(self, peer_id: int, values: dict[str, Any]) -> None:
        unknown = set(values) - _STATE_COLUMNS
        if unknown:
            raise ValueError(f"Not a channel state column: {sorted(unknown)}.")
        await self._db.execute(
            update(PeerChannelModel)
            .where(PeerChannelModel.peer_id == peer_id)
            .values(**values)
            .execution_options(synchronize_session=False)
        )

    async def next_seq(self, peer: Peer) -> int:
        await self.state(peer)
        await self._db.execute(
            update(PeerChannelModel)
            .where(PeerChannelModel.peer_id == peer.id)
            .values(out_seq=PeerChannelModel.out_seq + 1)
            .execution_options(synchronize_session=False)
        )
        # The update holds the row until commit, so this reads our number.
        seq = await self._db.scalar(
            select(PeerChannelModel.out_seq).where(PeerChannelModel.peer_id == peer.id)
        )
        return int(seq or 0)

    async def record(self, event: PeerChannelEvent) -> None:
        await self._db.execute(
            delete(PeerChannelEventModel)
            .where(
                PeerChannelEventModel.peer_id == event.peer_id,
                PeerChannelEventModel.kind == event.kind,
                PeerChannelEventModel.item_id == event.item_id,
            )
            .execution_options(synchronize_session=False)
        )
        self._db.add(
            PeerChannelEventModel(
                public_id=event.public_id,
                peer_id=event.peer_id,
                seq=event.seq,
                type=event.type,
                kind=event.kind,
                item_id=event.item_id,
                revision=event.revision,
                data=dict(event.data),
                created=event.created,
            )
        )
        await self._db.flush()

    async def events_after(self, peer_id: int, seq: int, *, limit: int) -> list[PeerChannelEvent]:
        rows = await self._db.scalars(
            select(PeerChannelEventModel)
            .where(PeerChannelEventModel.peer_id == peer_id, PeerChannelEventModel.seq > seq)
            .order_by(PeerChannelEventModel.seq)
            .limit(limit)
        )
        return [_event(r) for r in rows.all()]

    async def item_events_after(
        self, peer_id: int, seq: int, *, limit: int
    ) -> list[PeerChannelEvent]:
        rows = await self._db.scalars(
            select(PeerChannelEventModel)
            .where(
                PeerChannelEventModel.peer_id == peer_id,
                PeerChannelEventModel.seq > seq,
                PeerChannelEventModel.kind != CONTROL_KIND,
            )
            .order_by(PeerChannelEventModel.seq)
            .limit(limit)
        )
        return [_event(r) for r in rows.all()]

    async def item_events(self, peer_id: int, kind: str) -> list[PeerChannelEvent]:
        rows = await self._db.scalars(
            select(PeerChannelEventModel)
            .where(PeerChannelEventModel.peer_id == peer_id, PeerChannelEventModel.kind == kind)
            .order_by(PeerChannelEventModel.seq)
        )
        return [_event(r) for r in rows.all()]

    async def item_states(self, kind: str, item_id: str) -> dict[int, PeerChannelEvent]:
        rows = await self._db.scalars(
            select(PeerChannelEventModel).where(
                PeerChannelEventModel.kind == kind, PeerChannelEventModel.item_id == item_id
            )
        )
        return {r.peer_id: _event(r) for r in rows.all()}

    async def count_after(self, peer_id: int, seq: int) -> int:
        total = await self._db.scalar(
            select(func.count())
            .select_from(PeerChannelEventModel)
            .where(PeerChannelEventModel.peer_id == peer_id, PeerChannelEventModel.seq > seq)
        )
        return int(total or 0)

    async def due_to_send(self, now: datetime) -> list[int]:
        waiting = (
            select(PeerChannelEventModel.id)
            .where(
                PeerChannelEventModel.peer_id == PeerChannelModel.peer_id,
                PeerChannelEventModel.seq > PeerChannelModel.delivered_seq,
            )
            .exists()
        )
        rows = await self._db.scalars(
            select(PeerChannelModel.peer_id)
            .join(PeerModel, PeerModel.id == PeerChannelModel.peer_id)
            .where(
                PeerModel.status == PeerStatus.ACTIVE.value,
                or_(PeerChannelModel.next_send_at.is_(None), PeerChannelModel.next_send_at <= now),
                waiting,
            )
            .order_by(PeerChannelModel.peer_id)
        )
        return list(rows.all())

    async def claim(self, peer_id: int, lease: str, now: datetime, until: datetime) -> bool:
        column = _LEASES[lease]
        result = await self._db.execute(
            update(PeerChannelModel)
            .where(
                PeerChannelModel.peer_id == peer_id,
                or_(column.is_(None), column < now),
            )
            .values({column.key: until})
            .execution_options(synchronize_session=False)
        )
        return _rowcount(result) == 1

    async def release(self, peer_id: int, lease: str) -> None:
        column = _LEASES[lease]
        await self._db.execute(
            update(PeerChannelModel)
            .where(PeerChannelModel.peer_id == peer_id)
            .values({column.key: None})
            .execution_options(synchronize_session=False)
        )

    async def claim_timer(self, peer_id: int, timer: str, now: datetime, next_at: datetime) -> bool:
        column = _TIMERS[timer]
        result = await self._db.execute(
            update(PeerChannelModel)
            .where(
                PeerChannelModel.peer_id == peer_id,
                or_(column.is_(None), column <= now),
            )
            .values({column.key: next_at})
            .execution_options(synchronize_session=False)
        )
        return _rowcount(result) == 1

    async def due_timers(self, timer: str, now: datetime) -> list[int]:
        column = _TIMERS[timer]
        rows = await self._db.scalars(
            select(PeerChannelModel.peer_id)
            .join(PeerModel, PeerModel.id == PeerChannelModel.peer_id)
            .where(
                PeerModel.status == PeerStatus.ACTIVE.value,
                PeerModel.paired_at == PeerChannelModel.paired_at,
                or_(column.is_(None), column <= now),
            )
            .order_by(PeerChannelModel.peer_id)
        )
        return list(rows.all())

    async def add_job(self, job: PeerInboxJob) -> None:
        self._db.add(
            PeerInboxModel(
                public_id=job.public_id,
                peer_id=job.peer_id,
                type=job.type,
                kind=job.kind,
                item_id=job.item_id,
                revision=job.revision,
                seq=job.seq,
                prev_seq=job.prev_seq,
                data=dict(job.data),
                attempts=job.attempts,
                next_attempt_at=job.next_attempt_at,
                error=job.error,
                created=job.created,
            )
        )
        await self._db.flush()

    async def due_jobs(self, now: datetime) -> list[int]:
        oldest = (
            select(PeerInboxModel.peer_id, func.min(PeerInboxModel.id).label("first"))
            .group_by(PeerInboxModel.peer_id)
            .subquery()
        )
        rows = await self._db.scalars(
            select(PeerInboxModel.peer_id)
            .join(
                oldest,
                and_(
                    oldest.c.peer_id == PeerInboxModel.peer_id, oldest.c.first == PeerInboxModel.id
                ),
            )
            .join(PeerModel, PeerModel.id == PeerInboxModel.peer_id)
            .where(
                PeerInboxModel.next_attempt_at <= now,
                PeerModel.status == PeerStatus.ACTIVE.value,
            )
            .order_by(PeerInboxModel.peer_id)
        )
        return list(rows.all())

    async def jobs(self, peer_id: int, *, limit: int) -> list[PeerInboxJob]:
        rows = await self._db.scalars(
            select(PeerInboxModel)
            .where(PeerInboxModel.peer_id == peer_id)
            .order_by(PeerInboxModel.id)
            .limit(limit)
        )
        return [_job(r) for r in rows.all()]

    async def save_job(self, job: PeerInboxJob) -> None:
        await self._db.execute(
            update(PeerInboxModel)
            .where(PeerInboxModel.id == job.id)
            .values(attempts=job.attempts, next_attempt_at=job.next_attempt_at, error=job.error)
            .execution_options(synchronize_session=False)
        )

    async def delete_job(self, job: PeerInboxJob) -> None:
        await self._db.execute(
            delete(PeerInboxModel)
            .where(PeerInboxModel.id == job.id)
            .execution_options(synchronize_session=False)
        )

    async def count_jobs(self, peer_id: int) -> int:
        total = await self._db.scalar(
            select(func.count())
            .select_from(PeerInboxModel)
            .where(PeerInboxModel.peer_id == peer_id)
        )
        return int(total or 0)

    async def has_job(self, peer_id: int, type: str) -> bool:
        found = await self._db.scalar(
            select(PeerInboxModel.id)
            .where(
                PeerInboxModel.peer_id == peer_id,
                PeerInboxModel.type == type,
                PeerInboxModel.seq.is_(None),
            )
            .limit(1)
        )
        return found is not None

    async def _drop_log_and_queue(self, peer_id: int) -> None:
        await self._db.execute(
            delete(PeerChannelEventModel)
            .where(PeerChannelEventModel.peer_id == peer_id)
            .execution_options(synchronize_session=False)
        )
        await self._db.execute(
            delete(PeerInboxModel)
            .where(PeerInboxModel.peer_id == peer_id)
            .execution_options(synchronize_session=False)
        )

    async def purge(self, peer_id: int) -> None:
        await self._drop_log_and_queue(peer_id)
        await self._db.execute(
            delete(PeerChannelModel)
            .where(PeerChannelModel.peer_id == peer_id)
            .execution_options(synchronize_session=False)
        )
