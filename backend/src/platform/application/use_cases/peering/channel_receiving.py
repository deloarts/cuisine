"""
The receiving side of a peer channel.

`POST /events` stores the event in the inbound queue and answers 202 at
once; only `peer.revoked` is handled on the spot, while its signature is
still valid. Every authenticated request proves contact, and a request
sent with another protocol version than the negotiated one queues a
renegotiation.

The background worker processes a peer's queue in arrival order, one
worker per peer at a time (the `receive` lease). For an event with sequence
`seq` and predecessor `prev_seq`, after processing up to `last`:

- `prev_seq <= last < seq`: the event follows; apply it.
- `prev_seq > last`: events were missed; catch up with
  `/changes?since=last` and continue.
- `seq <= last`: a duplicate, or the source was restored from a backup;
  the catch-up tells which. A source whose highest sequence is below
  `last` was restored, and the receiver reconciles fully: it reads
  `/changes?since=0`, applies every shared item and hands the full list to
  each consumer, which withdraws everything else from that peer.

Applying an item event fetches the item from `/items/{kind}/{id}` with the
etag of the copy held here; 304 keeps the copy, a 404 marked as withdrawn
withdraws it. A failed fetch leaves the event queued and retries it with
the sender's schedule, never giving up; the timer's catch-up covers the
same ground meanwhile.
"""

from collections.abc import Awaitable
from collections.abc import Callable

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.peer_calls import CONSUMER_FAILED
from src.platform.application.services.peer_calls import INVALID_ANSWER
from src.platform.application.services.peer_calls import REFUSED
from src.platform.application.services.peer_calls import UNREACHABLE
from src.platform.application.services.peer_calls import PeerCallFailed
from src.platform.application.services.peer_calls import PeerCalls
from src.platform.application.services.peering_messages import ChangesResponseV1
from src.platform.application.services.peering_messages import read_changes
from src.platform.application.services.peering_messages import read_event
from src.platform.application.use_cases.peering.authenticate_peer import AuthenticatedPeer
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer_channel import PeerChannelState
from src.platform.domain.entities.peer_channel import PeerInboxJob
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import PeeringVersionMismatchError
from src.platform.domain.exceptions import PeerRefusedError
from src.platform.domain.exceptions import PeerUnreachableError
from src.platform.domain.services.peer_channel_rules import ITEM_EVENTS
from src.platform.domain.services.peer_channel_rules import ITEM_MAX_BYTES
from src.platform.domain.services.peer_channel_rules import ITEM_WITHDRAWN
from src.platform.domain.services.peer_channel_rules import PEER_REVOKED
from src.platform.domain.services.peer_channel_rules import PEER_UPDATED
from src.platform.domain.services.peer_channel_rules import SequenceStep
from src.platform.domain.services.peer_channel_rules import retry_after
from src.platform.domain.services.peer_channel_rules import sequence_step
from src.platform.domain.services.peer_channel_rules import source_was_restored
from src.platform.ports.outbound.peer_content import IPeerContentConsumer
from src.platform.ports.outbound.peer_content import PeerItem
from src.platform.ports.outbound.repositories.peer_channel_repository import IPeerChannelRepository
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# How many queued events one run processes for one peer.
INBOX_BATCH = 100

Renegotiate = Callable[[Peer], Awaitable[Peer]]
RevokedByPeer = Callable[[Peer, RequestContext], Awaitable[None]]


class PeerContact:
    """Records that an authenticated peer request arrived."""

    def __init__(
        self, *, peers: IPeerRepository, channels: IPeerChannelRepository, uow: IUnitOfWork
    ) -> None:
        self._peers = peers
        self._channels = channels
        self._uow = uow

    async def seen(self, auth: AuthenticatedPeer) -> None:
        """Sets the peer's last contact and, when the request named another
        protocol version than the negotiated one, queues a renegotiation."""
        now = now_utc()
        peer = auth.peer
        await self._peers.touch_contact(peer.id, now)
        if auth.protocol_version != peer.protocol_version and not await self._channels.has_job(
            peer.id, PEER_UPDATED
        ):
            await self._channels.add_job(
                PeerInboxJob(peer_id=peer.id, type=PEER_UPDATED, next_attempt_at=now, created=now)
            )
        await self._uow.commit()


class ReceivePeerEvents:
    def __init__(
        self,
        *,
        channels: IPeerChannelRepository,
        uow: IUnitOfWork,
        revoked_by_peer: RevokedByPeer,
    ) -> None:
        self._channels = channels
        self._uow = uow
        self._revoked_by_peer = revoked_by_peer

    async def accept(self, peer: Peer, data: object, *, context: RequestContext) -> None:
        """Queues the event for the worker. Raises
        InvalidPeerConfigurationError for a malformed event."""
        event = read_event(data)
        if event.type == PEER_REVOKED:
            await self._revoked_by_peer(peer, context)
            return
        now = now_utc()
        await self._channels.add_job(
            PeerInboxJob(
                peer_id=peer.id,
                type=event.type,
                kind=event.kind,
                item_id=event.id,
                revision=event.revision,
                seq=event.seq,
                prev_seq=event.prev_seq,
                next_attempt_at=now,
                created=now,
            )
        )
        await self._uow.commit()


class SyncFromPeer:
    def __init__(
        self,
        *,
        peers: IPeerRepository,
        channels: IPeerChannelRepository,
        calls: PeerCalls,
        consumers: dict[str, IPeerContentConsumer],
        renegotiate: Renegotiate,
        uow: IUnitOfWork,
    ) -> None:
        self._peers = peers
        self._channels = channels
        self._calls = calls
        self._consumers = consumers
        self._renegotiate = renegotiate
        self._uow = uow

    # ── The inbound queue ────────────────────────────────────────────

    async def process_inbox(self, peer: Peer) -> int:
        """Processes the peer's due events in order; stops at the first that
        fails, which waits for its next attempt. Returns how many it
        processed."""
        done = 0
        caught_up = False
        for job in await self._channels.jobs(peer.id, limit=INBOX_BATCH):
            if job.next_attempt_at > now_utc():
                break
            try:
                caught_up = await self._handle(peer, job, caught_up=caught_up)
            except PeerCallFailed as exc:
                await self._uow.rollback()
                await self._failed(job, exc.category)
                break
            except Exception:
                # A consumer that cannot take the item in: retry on the
                # same schedule, and let the worker log what went wrong.
                await self._uow.rollback()
                await self._failed(job, CONSUMER_FAILED)
                raise
            await self._channels.delete_job(job)
            await self._uow.commit()
            done += 1
        return done

    async def _handle(self, peer: Peer, job: PeerInboxJob, *, caught_up: bool) -> bool:
        """Processes one queued event and says whether this run has caught
        up with the source by now."""
        if job.seq is None:
            # Queued here, not sent by the peer: a renegotiation.
            if job.type == PEER_UPDATED:
                await self._renegotiate_now(peer)
            return caught_up
        state = await self._channels.state(peer)
        step = sequence_step(state.in_seq, job.seq, job.prev_seq or 0)
        if step == SequenceStep.CATCH_UP:
            stale = job.seq <= state.in_seq
            if stale and caught_up:
                # Already checked with the source in this run.
                return caught_up
            await self.catch_up(peer)
            if not stale and job.type == PEER_UPDATED:
                await self._renegotiate_now(peer)
            return True
        if job.type in ITEM_EVENTS and job.kind and job.item_id:
            await self._apply(peer, job.type, job.kind, job.item_id)
        elif job.type == PEER_UPDATED:
            await self._renegotiate_now(peer)
        await self._channels.update_state(peer.id, {"in_seq": job.seq})
        return caught_up

    async def _failed(self, job: PeerInboxJob, category: str) -> None:
        now = now_utc()
        job.attempts += 1
        job.next_attempt_at = retry_after(job.attempts, now)
        job.error = category
        await self._channels.save_job(job)
        await self._channels.update_state(job.peer_id, {"last_receive_error": category})
        await self._uow.commit()

    async def _renegotiate_now(self, peer: Peer) -> None:
        try:
            await self._renegotiate(peer)
        except PeerUnreachableError as exc:
            raise PeerCallFailed(UNREACHABLE) from exc
        except (PeerRefusedError, PeeringVersionMismatchError) as exc:
            raise PeerCallFailed(REFUSED) from exc
        except InvalidPeerConfigurationError as exc:
            raise PeerCallFailed(INVALID_ANSWER) from exc

    # ── Catching up and reconciling ──────────────────────────────────

    async def catch_up(self, peer: Peer) -> None:
        """Applies what changed at the source since the last processed
        sequence, or reconciles fully when the source was restored. Raises
        PeerCallFailed and keeps the progress made so far."""
        state = await self._channels.state(peer)
        page = await self._changes(peer, state.in_seq)
        if source_was_restored(state.in_seq, page.max_seq):
            await self.reconcile(peer)
            return
        while True:
            for change in page.changes:
                if change.seq <= state.in_seq:
                    continue
                await self._apply(peer, change.type, change.kind, change.id)
                await self._channels.update_state(peer.id, {"in_seq": change.seq})
                await self._uow.commit()
            if not page.more or not page.changes:
                break
            page = await self._changes(peer, page.changes[-1].seq)
        await self._finish(peer, state, page.max_seq, reconciled=False)

    async def reconcile(self, peer: Peer) -> None:
        """Reads everything the source shares, applies it, and lets every
        consumer withdraw what the source no longer lists."""
        state = await self._channels.state(peer)
        shared: dict[str, set[str]] = {}
        since = 0
        while True:
            page = await self._changes(peer, since)
            for change in page.changes:
                await self._apply(peer, change.type, change.kind, change.id)
                if change.type != ITEM_WITHDRAWN:
                    shared.setdefault(change.kind, set()).add(change.id)
                await self._uow.commit()
            if not page.more or not page.changes:
                break
            since = page.changes[-1].seq
        for kind, consumer in sorted(self._consumers.items()):
            await consumer.reconcile(peer, shared.get(kind, set()))
        await self._finish(peer, state, page.max_seq, reconciled=True)

    async def _finish(
        self, peer: Peer, state: PeerChannelState, max_seq: int, *, reconciled: bool
    ) -> None:
        now = now_utc()
        current = (await self._channels.state(peer)).in_seq
        values: dict[str, object] = {
            # A reconcile follows the source back down; a catch-up only
            # moves forward.
            "in_seq": max_seq if reconciled else max(current, max_seq),
            "last_catch_up_at": now,
            "last_receive_error": None,
        }
        if reconciled:
            values["last_reconcile_at"] = now
        await self._channels.update_state(peer.id, values)
        await self._peers.touch_contact(peer.id, now)
        await self._uow.commit()

    async def _changes(self, peer: Peer, since: int) -> ChangesResponseV1:
        reply = await self._calls.send(peer, "GET", f"/changes?since={since}")
        if reply.status != 200:
            raise PeerCallFailed(REFUSED, reply.status)
        try:
            return read_changes(reply.data)
        except InvalidPeerConfigurationError as exc:
            raise PeerCallFailed(INVALID_ANSWER, reply.status) from exc

    async def _apply(self, peer: Peer, type: str, kind: str, item_id: str) -> None:
        """Brings the copy of one item in line with the source. A kind no
        consumer is registered for is ignored."""
        consumer = self._consumers.get(kind)
        if consumer is None:
            return
        if type == ITEM_WITHDRAWN:
            await consumer.withdraw(peer, item_id)
            return
        etag = await consumer.current_etag(peer, item_id)
        reply = await self._calls.send(
            peer,
            "GET",
            f"/items/{kind}/{item_id}",
            headers={"If-None-Match": etag} if etag else None,
            max_response_bytes=ITEM_MAX_BYTES,
        )
        if reply.status == 304:
            return
        if reply.status == 404 and (reply.data or {}).get("withdrawn") is True:
            await consumer.withdraw(peer, item_id)
            return
        if reply.status != 200:
            raise PeerCallFailed(REFUSED, reply.status)
        await consumer.apply(
            peer,
            PeerItem(
                item_id=item_id,
                content=reply.body,
                media_type=reply.media_type or "application/octet-stream",
                etag=reply.etag or "",
            ),
        )
