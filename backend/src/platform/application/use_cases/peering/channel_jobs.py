"""
The background work of the peer channels, run by the channel worker on
every backend worker's event loop, and the channel status on the peer page.

One run queues the daily `ping` where it is due, sends due events,
processes due inbound queues, and runs the timers of every active peer: a
catch-up every 15 minutes and a full comparison once a day (the source
side repairs its channel log from the providers, the receiving side
reconciles with `/changes?since=0`).
The timers also serve an instance that cannot receive events at all, for
example one behind NAT at home: it learns everything through its own
catch-up, so there is no separate polling mode.

Each timer is claimed by moving it on with a conditional update, and the
receiving work of a peer runs under its `receive` lease, so several workers
never do the same work twice. Nothing runs while the peering feature switch
is off.
"""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any

from src.platform.application.services.peer_calls import PeerCallFailed
from src.platform.application.services.peer_channel import PeerChannel
from src.platform.application.services.peering_identity import PeeringIdentity
from src.platform.application.use_cases.peering.channel_receiving import SyncFromPeer
from src.platform.application.use_cases.peering.channel_sending import DeliverPeerEvents
from src.platform.application.use_cases.peering.channel_source import RepairPeerChannel
from src.platform.domain.entities.peer import Peer
from src.platform.domain.exceptions import PeerNotFoundError
from src.platform.domain.services.peer_channel_rules import CATCH_UP_EVERY
from src.platform.domain.services.peer_channel_rules import LEASE
from src.platform.domain.services.peer_channel_rules import PEER_UPDATED
from src.platform.domain.services.peer_channel_rules import PING
from src.platform.domain.services.peer_channel_rules import PING_EVERY
from src.platform.domain.services.peer_channel_rules import RECONCILE_EVERY
from src.platform.ports.outbound.feature_switches import IFeatureSwitches
from src.platform.ports.outbound.repositories.peer_channel_repository import IPeerChannelRepository
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

PeerWork = Callable[[Peer], Awaitable[int]]

# The job state key of what this instance last announced to its peers.
ANNOUNCED_KEY = "peering_announced"


@dataclass(frozen=True)
class ChannelRun:
    sent: int = 0
    processed: int = 0
    pings: int = 0
    catch_ups: int = 0
    reconciles: int = 0


class RunPeerChannelJobs:
    def __init__(
        self,
        *,
        peers: IPeerRepository,
        channels: IPeerChannelRepository,
        channel: PeerChannel,
        features: IFeatureSwitches,
        deliver: DeliverPeerEvents,
        sync: SyncFromPeer,
        repair: RepairPeerChannel,
        uow: IUnitOfWork,
    ) -> None:
        self._peers = peers
        self._channels = channels
        self._channel = channel
        self._features = features
        self._deliver = deliver
        self._sync = sync
        self._repair = repair
        self._uow = uow

    async def run_once(self) -> ChannelRun:
        if not (await self._features.get_features()).peering:
            return ChannelRun()
        active = await self._peers.list_active()
        for peer in active:
            await self._channels.state(peer)
        await self._uow.commit()
        pings = await self._pings()
        sent = await self._deliver.run()
        processed = 0
        for peer_id in await self._channels.due_jobs(now_utc()):
            processed += max(0, await self._receiving(peer_id, self._sync.process_inbox))
        reconciles = await self._timer("reconcile", RECONCILE_EVERY, self._reconcile)
        catch_ups = await self._timer("catch_up", CATCH_UP_EVERY, self._catch_up)
        return ChannelRun(
            sent=sent,
            processed=processed,
            pings=pings,
            catch_ups=catch_ups,
            reconciles=reconciles,
        )

    async def _pings(self) -> int:
        now = now_utc()
        made = 0
        for peer_id in await self._channels.due_timers("ping", now):
            if not await self._channels.claim_timer(peer_id, "ping", now, now + PING_EVERY):
                continue
            peer = await self._peers.get(peer_id)
            if peer is not None:
                await self._channel.publish_control(peer, PING, {})
                made += 1
            await self._uow.commit()
        return made

    async def _timer(self, timer: str, every: timedelta, work: PeerWork) -> int:
        now = now_utc()
        done = 0
        for peer_id in await self._channels.due_timers(timer, now):
            if not await self._channels.claim_timer(peer_id, timer, now, now + every):
                continue
            await self._uow.commit()
            done += int(await self._receiving(peer_id, work) >= 0)
        return done

    async def _receiving(self, peer_id: int, work: PeerWork) -> int:
        """Runs receiving work for one peer under its lease; -1 when another
        worker holds the lease or the work failed."""
        now = now_utc()
        if not await self._channels.claim(peer_id, "receive", now, now + LEASE):
            return -1
        await self._uow.commit()
        try:
            peer = await self._peers.get(peer_id)
            if peer is None or not peer.active:
                return -1
            result: int = await work(peer)
            return result
        except PeerCallFailed as exc:
            await self._uow.rollback()
            await self._channels.update_state(peer_id, {"last_receive_error": exc.category})
            await self._uow.commit()
            return -1
        finally:
            await self._uow.rollback()
            await self._channels.release(peer_id, "receive")
            await self._uow.commit()

    async def _catch_up(self, peer: Peer) -> int:
        await self._sync.catch_up(peer)
        return 1

    async def _reconcile(self, peer: Peer) -> int:
        await self._repair.repair(peer)
        await self._sync.reconcile(peer)
        # A full comparison is a catch-up too.
        await self._channels.update_state(peer.id, {"catch_up_due_at": now_utc() + CATCH_UP_EVERY})
        await self._uow.commit()
        return 1


class AnnouncePeerChanges:
    """On startup: when this instance's app version, protocol versions,
    formats or capabilities changed since the last run, sends `peer.updated`
    to every active peer, which then reads `/hello` again."""

    def __init__(
        self,
        *,
        peers: IPeerRepository,
        channel: PeerChannel,
        identity: PeeringIdentity,
        settings_repo: ISettingsRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._peers = peers
        self._channel = channel
        self._identity = identity
        self._settings = settings_repo
        self._uow = uow

    async def run(self) -> int:
        own = await self._identity.current()
        announced: dict[str, Any] = {
            "app_version": own.app_version,
            "protocol_versions": list(own.protocol_versions),
            "formats": {name: list(v) for name, v in sorted(own.formats.items())},
            "capabilities": list(own.capabilities),
        }
        state = dict(await self._settings.get_job_state())
        if state.get(ANNOUNCED_KEY) == announced:
            return 0
        made = 0
        for peer in await self._peers.list_active():
            await self._channel.publish_control(peer, PEER_UPDATED, announced)
            made += 1
        state[ANNOUNCED_KEY] = announced
        await self._settings.save_job_state(state)
        await self._uow.commit()
        return made


@dataclass(frozen=True)
class ChannelStatus:
    out_seq: int
    delivered_seq: int
    pending_outgoing: int
    in_seq: int
    pending_incoming: int
    last_delivery_at: datetime | None
    last_delivery_status: int | None
    last_delivery_error: str | None
    next_send_at: datetime | None
    last_catch_up_at: datetime | None
    last_reconcile_at: datetime | None
    last_receive_error: str | None


class PeerChannelStatus:
    """The channel figures on the peer page, and "sync now"."""

    def __init__(
        self, *, peers: IPeerRepository, channels: IPeerChannelRepository, uow: IUnitOfWork
    ) -> None:
        self._peers = peers
        self._channels = channels
        self._uow = uow

    async def of(self, peers: list[Peer]) -> dict[int, ChannelStatus]:
        states = await self._channels.states([p.id for p in peers if p.active])
        result: dict[int, ChannelStatus] = {}
        for peer in peers:
            state = states.get(peer.id)
            if state is None or state.paired_at != peer.paired_at:
                continue
            result[peer.id] = ChannelStatus(
                out_seq=state.out_seq,
                delivered_seq=state.delivered_seq,
                pending_outgoing=await self._channels.count_after(peer.id, state.delivered_seq),
                in_seq=state.in_seq,
                pending_incoming=await self._channels.count_jobs(peer.id),
                last_delivery_at=state.last_delivery_at,
                last_delivery_status=state.last_delivery_status,
                last_delivery_error=state.last_delivery_error,
                next_send_at=state.next_send_at,
                last_catch_up_at=state.last_catch_up_at,
                last_reconcile_at=state.last_reconcile_at,
                last_receive_error=state.last_receive_error,
            )
        return result

    async def sync_now(self, public_id: str) -> Peer:
        """Makes the catch-up due and the next delivery attempt due now; the
        channel worker picks both up within seconds."""
        peer = await self._peers.get_by_public_id(public_id)
        if peer is None:
            raise PeerNotFoundError("No such paired instance.")
        if peer.active:
            await self._channels.state(peer)
            now = now_utc()
            await self._channels.update_state(
                peer.id, {"catch_up_due_at": now, "next_send_at": now}
            )
            await self._uow.commit()
        return peer
