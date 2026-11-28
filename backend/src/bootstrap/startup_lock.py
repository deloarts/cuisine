"""
A lock that lets one worker at a time run the setup of a start.

Gunicorn starts several workers at once, and each one runs the lifespan's
setup: the system user, the default groups, the instance id and the
reference data seed. On an empty database two workers insert the same rows,
and the slower one waits on the other's uncommitted rows until the
connection's lock timeout cancels it, which makes gunicorn stop the whole
server. Holding a session-level Postgres advisory lock around the setup
lets the second worker wait until the first has committed, after which it
finds nothing left to do.

The lock is taken with `pg_try_advisory_lock` in a loop rather than with the
blocking `pg_advisory_lock`, because the connection's lock timeout would
cancel a blocking wait just as it cancelled the insert. The connection
commits after each attempt, so it never sits idle in a transaction while the
setup runs on other connections. SQLite, which the test suite uses, has no
advisory locks and runs in one process, so there the lock does nothing.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic

import anyio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.platform.infrastructure.logging.logger import log

# Distinct from the migration lock in alembic/env.py, so a worker that
# migrates and one that runs the setup never wait on each other by mistake.
STARTUP_LOCK_KEY = 0x6375_6973_7375
POLL_SECONDS = 0.5
WAIT_SECONDS = 600.0


@asynccontextmanager
async def startup_lock(
    engine: AsyncEngine,
    *,
    poll_seconds: float = POLL_SECONDS,
    wait_seconds: float = WAIT_SECONDS,
) -> AsyncIterator[None]:
    """Holds the startup lock while the block runs. Waits for another worker
    that holds it, and raises TimeoutError after `wait_seconds`."""
    if engine.dialect.name != "postgresql":
        yield
        return
    async with engine.connect() as connection:
        deadline = monotonic() + wait_seconds
        waiting = False
        while True:
            acquired = await connection.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": STARTUP_LOCK_KEY}
            )
            await connection.commit()
            if acquired:
                break
            if not waiting:
                log.info("Waiting for another worker to finish the startup setup.")
                waiting = True
            if monotonic() >= deadline:
                raise TimeoutError(
                    f"Another worker held the startup lock for more than {wait_seconds:.0f} s."
                )
            await anyio.sleep(poll_seconds)
        try:
            yield
        finally:
            await connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": STARTUP_LOCK_KEY}
            )
            await connection.commit()
