"""
The peer channel worker: a task on each backend worker's event loop that
runs the peer channels every few seconds. One run sends due events,
processes the inbound queues and runs the timers (catch-up every 15
minutes, full comparison and ping once a day); every piece of work is
claimed in the database first, so several workers never do it twice. While
the peering feature switch is off a run does nothing.

On startup the worker first tells every active peer when this instance's
app version, protocol versions, formats or capabilities changed since the
last run.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bootstrap.worker_loop import run_forever
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import announce_peer_changes
from src.platform.adapters.inbound.api.deps import get_own_base_url
from src.platform.adapters.inbound.api.deps import get_peer_client
from src.platform.adapters.inbound.api.deps import peer_channel_jobs
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.application.use_cases.peering.channel_jobs import ChannelRun
from src.platform.infrastructure.logging.logger import log
from src.platform.ports.outbound.peer_client import IPeerClient
from src.platform.ports.outbound.webhook_sender import IWebhookTargetGuard

INTERVAL_SECONDS = 5.0


async def run_peer_channels_once(
    *,
    sessions: async_sessionmaker[AsyncSession] = SessionLocal,
    client: IPeerClient | None = None,
    base_url: str | None = None,
    guard: IWebhookTargetGuard | None = None,
) -> ChannelRun:
    """One run of the channel jobs. The keywords let tests drive two
    instances by hand."""
    async with sessions() as db:
        jobs = peer_channel_jobs(
            Platform(db), client or get_peer_client(), base_url or get_own_base_url(), guard
        )
        return await jobs.run_once()


async def announce_peer_changes_once(
    *, sessions: async_sessionmaker[AsyncSession] = SessionLocal, base_url: str | None = None
) -> int:
    async with sessions() as db:
        return await announce_peer_changes(Platform(db), base_url or get_own_base_url()).run()


async def _loop() -> None:
    try:
        await announce_peer_changes_once()
    except asyncio.CancelledError:
        raise
    except Exception:
        log.exception("Announcing this instance's changes to its peers failed.")
    # A failed run leaves its work queued for the next tick.
    await run_forever(
        run_peer_channels_once,
        interval=INTERVAL_SECONDS,
        failure="The peer channel worker run failed.",
    )


def start_peer_channel_worker() -> asyncio.Task[None]:
    return asyncio.create_task(_loop(), name="peer-channel-worker")
