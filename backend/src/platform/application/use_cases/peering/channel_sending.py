"""
Sends the events of every peer channel that has something the peer has not
taken yet. Events go out one by one in sequence order to the peer's
`POST /events`, signed like every peering request. A 2xx answer moves the
channel's cursor on; any other answer or a failed request stops the run
for that peer and schedules the next attempt after 1, 5, 30 and 120
minutes, then every hour, for as long as it takes. A channel never gives
up and is never switched off; revoking the pairing is the only way to end
it.

A channel is sent by one worker at a time: the `send` lease is taken with a
conditional update before the first request.
"""

from src.platform.application.services.peer_calls import REFUSED
from src.platform.application.services.peer_calls import PeerCallFailed
from src.platform.application.services.peer_calls import PeerCalls
from src.platform.application.services.peering_messages import event_message
from src.platform.domain.services.peer_channel_rules import LEASE
from src.platform.domain.services.peer_channel_rules import SEND_BATCH
from src.platform.domain.services.peer_channel_rules import retry_after
from src.platform.ports.outbound.repositories.peer_channel_repository import IPeerChannelRepository
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


class DeliverPeerEvents:
    def __init__(
        self,
        *,
        peers: IPeerRepository,
        channels: IPeerChannelRepository,
        calls: PeerCalls,
        uow: IUnitOfWork,
    ) -> None:
        self._peers = peers
        self._channels = channels
        self._calls = calls
        self._uow = uow

    async def run(self) -> int:
        """Sends what is due and returns how many events peers accepted."""
        now = now_utc()
        sent = 0
        for peer_id in await self._channels.due_to_send(now):
            if not await self._channels.claim(peer_id, "send", now, now + LEASE):
                continue
            await self._uow.commit()
            try:
                sent += await self._send(peer_id)
            finally:
                await self._uow.rollback()
                await self._channels.release(peer_id, "send")
                await self._uow.commit()
        return sent

    async def _send(self, peer_id: int) -> int:
        peer = await self._peers.get(peer_id)
        if peer is None or not peer.active:
            return 0
        state = await self._channels.state(peer)
        events = await self._channels.events_after(peer.id, state.delivered_seq, limit=SEND_BATCH)
        prev = state.delivered_seq
        attempts = state.send_attempts
        sent = 0
        for event in events:
            status: int | None = None
            error: str | None = None
            try:
                reply = await self._calls.send(
                    peer, "POST", "/events", body=event_message(event, prev)
                )
                status = reply.status
                if not 200 <= status < 300:
                    error = REFUSED
            except PeerCallFailed as exc:
                error = exc.category
            now = now_utc()
            if error is None:
                await self._channels.update_state(
                    peer.id,
                    {
                        "delivered_seq": event.seq,
                        "send_attempts": 0,
                        "next_send_at": None,
                        "last_delivery_at": now,
                        "last_delivery_status": status,
                        "last_delivery_error": None,
                    },
                )
                await self._peers.touch_contact(peer.id, now)
                await self._uow.commit()
                prev = event.seq
                attempts = 0
                sent += 1
                continue
            attempts += 1
            await self._channels.update_state(
                peer.id,
                {
                    "send_attempts": attempts,
                    "next_send_at": retry_after(attempts, now),
                    "last_delivery_at": now,
                    "last_delivery_status": status,
                    "last_delivery_error": error,
                },
            )
            await self._uow.commit()
            break
        return sent
