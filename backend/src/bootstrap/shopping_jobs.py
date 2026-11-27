"""
The shopping list purge on each backend worker's event loop, every 15
minutes: it forgets what continuous lists bought before the recently bought
window and deletes unused normal lists. Like the nightly jobs, a worker
claims a run by writing its time into the job state first, so the workers
together run it about once per interval; the purge is safe to run twice.
"""

import asyncio
from datetime import datetime
from datetime import timedelta

from src.bootstrap.worker_loop import run_forever
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_live
from src.cookbook.adapters.inbound.api.deps import shopping_purge
from src.cookbook.ports.outbound.live_publisher import ILivePublisher
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.infrastructure.logging.logger import log
from src.shared_kernel.domain.services.clock import now_utc

INTERVAL_SECONDS = 15 * 60.0
# A little under the interval, so a worker that slept a few seconds less
# than the one that claimed the last run still finds it due next time.
RUN_EVERY = timedelta(minutes=14)


async def run_shopping_purge_once(
    *, force: bool = False, live: ILivePublisher | None = None
) -> bool:
    """Runs the purge when it is due (or `force`) and says whether it did."""
    async with SessionLocal() as db:
        p = Platform(db)
        state = dict(await p.settings.get_job_state())
        last = state.get("shopping_purge_at")
        now = now_utc()
        if not force and isinstance(last, str) and now - datetime.fromisoformat(last) < RUN_EVERY:
            return False
        state["shopping_purge_at"] = now.isoformat()
        await p.settings.save_job_state(state)
        await p.uow.commit()
        result = await shopping_purge(Cookbook(p), live or get_live()).run(now)
        if result.bought_removed or result.lists_deleted:
            log.info(
                "Shopping purge removed %s bought items and %s unused lists.",
                result.bought_removed,
                result.lists_deleted,
            )
        return True


def start_shopping_jobs() -> asyncio.Task[None]:
    return asyncio.create_task(
        run_forever(
            run_shopping_purge_once,
            interval=INTERVAL_SECONDS,
            failure="The shopping list purge failed.",
        ),
        name="shopping-purge",
    )
