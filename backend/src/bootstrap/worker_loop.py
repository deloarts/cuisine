"""
The loop every background worker on a backend worker's event loop runs:
call one step, log a failure without ending the loop, sleep, repeat.
Cancelling the task ends it, which is how the app stops its workers.
"""

import asyncio
import contextlib
from collections.abc import Awaitable
from collections.abc import Callable

from src.platform.infrastructure.logging.logger import log


async def run_forever(
    step: Callable[[], Awaitable[object]], *, interval: float, failure: str
) -> None:
    """Runs `step` every `interval` seconds until cancelled. An exception
    from a step is logged with `failure` and the next tick retries, so a
    database hiccup or a failing consumer never ends the loop."""
    while True:
        try:
            await step()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception(failure)
        await asyncio.sleep(interval)


async def stop_worker(task: asyncio.Task[None]) -> None:
    """Cancels a worker task and waits until it has ended."""
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
