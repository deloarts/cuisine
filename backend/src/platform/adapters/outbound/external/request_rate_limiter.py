"""
IRequestRateLimiter on Redis, and an in-process one for tests.

A fixed window: the first request of a key starts a counter that expires
after the window; every request increments it, and a key above the limit
waits for the counter to expire. Redis keeps the counters shared across
workers.
"""

import time

from redis.asyncio import Redis

_PREFIX = "cuisine:rate"


class RedisRequestRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> int:
        counter = f"{_PREFIX}:{key}"
        count = await self._redis.incr(counter)
        if count == 1:
            await self._redis.expire(counter, window_seconds)
        if count <= limit:
            return 0
        ttl = int(await self._redis.ttl(counter))
        if ttl < 0:
            # The expiry got lost (a crash between the two calls); set it
            # again so the key is never blocked for good.
            await self._redis.expire(counter, window_seconds)
            ttl = window_seconds
        return max(ttl, 1)


class InMemoryRequestRateLimiter:
    """Single-process stand-in with the same behaviour, for tests."""

    def __init__(self) -> None:
        self._windows: dict[str, tuple[float, int]] = {}

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> int:
        now = time.monotonic()
        started, count = self._windows.get(key, (now, 0))
        if now - started >= window_seconds:
            started, count = now, 0
        count += 1
        self._windows[key] = (started, count)
        if count <= limit:
            return 0
        return max(int(started + window_seconds - now), 1)
