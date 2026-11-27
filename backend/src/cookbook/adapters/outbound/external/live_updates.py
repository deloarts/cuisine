"""
Live updates over Redis pub/sub: a change to a shared shopping list is
published on the list's channel, and every open stream of that list, in any
worker process, receives it. The in-memory variant serves the test suite
and a single process.
"""

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import Redis

from src.platform.infrastructure.logging.logger import log


class RedisLivePublisher:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        try:
            await self._redis.publish(channel, json.dumps(event))
        except Exception as exc:
            # A missed signal only delays the other screens until they
            # refetch; it must never fail the change itself.
            log.warning("Could not publish a live update: %s", type(exc).__name__)

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    await asyncio.sleep(0)
                    continue
                try:
                    yield json.loads(message["data"])
                except (TypeError, ValueError):
                    continue
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()  # type: ignore[no-untyped-call]


class InMemoryLivePublisher:
    """Delivers to subscribers of the same process and remembers every event,
    so tests can assert on what was published."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        self.published.append((channel, event))
        for queue in self._queues.get(channel, []):
            queue.put_nowait(event)

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues[channel].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues[channel].remove(queue)
