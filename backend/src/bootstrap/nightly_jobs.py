"""
The nightly jobs on each backend worker's event loop: the retention purge,
the sweep of unused uploads and the checks that mail operational alerts.
Every worker checks hourly whether the last run is a day old and claims the
run by writing its time into the job state first, so the jobs run about
once a day. Every job is
safe to run twice, so a race between workers costs nothing.
"""

import asyncio
from datetime import datetime
from datetime import timedelta

from src.bootstrap.worker_loop import run_forever
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import nightly_checks
from src.platform.adapters.inbound.api.deps import purge_expired
from src.platform.adapters.inbound.api.deps import sweep_unused_files
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.infrastructure.logging.logger import log
from src.shared_kernel.domain.services.clock import now_utc

CHECK_EVERY_SECONDS = 3600.0
RUN_EVERY = timedelta(hours=23)


async def run_nightly_once(*, force: bool = False) -> bool:
    """Runs the jobs when they are due (or `force`) and says whether it did."""
    async with SessionLocal() as db:
        p = Platform(db)
        state = dict(await p.settings.get_job_state())
        last = state.get("nightly_at")
        now = now_utc()
        if not force and isinstance(last, str) and now - datetime.fromisoformat(last) < RUN_EVERY:
            return False
        state["nightly_at"] = now.isoformat()
        await p.settings.save_job_state(state)
        await p.uow.commit()
        removed = await purge_expired(p).run()
        log.info("Retention purge removed %s.", removed)
        swept = await sweep_unused_files(p).run()
        log.info(
            "Unused file sweep removed %d files (%d bytes).", swept.removed, swept.removed_bytes
        )
        if swept.content_failures:
            log.warning(
                "Unused file sweep could not delete the content of %d files from the storage "
                "provider.",
                swept.content_failures,
            )
        await nightly_checks(p).run()
        return True


def start_nightly_jobs() -> asyncio.Task[None]:
    return asyncio.create_task(
        run_forever(
            run_nightly_once, interval=CHECK_EVERY_SECONDS, failure="The nightly jobs failed."
        ),
        name="nightly-jobs",
    )
