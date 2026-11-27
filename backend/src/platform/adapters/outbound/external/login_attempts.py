"""
ILoginAttemptTracker on Redis, and an in-process one for tests.

A failure increments a counter that expires with the lockout window; once
the counter reaches the limit the key is locked for the lockout duration.
Redis keeps the counters shared across workers and restarts.
"""

import time

from redis.asyncio import Redis

_PREFIX = "cuisine:login"


class RedisLoginAttemptTracker:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def lock_ttl(self, key: str) -> int:
        ttl = await self._redis.ttl(f"{_PREFIX}:lock:{key}")
        return max(int(ttl), 0)

    async def record_failure(self, key: str, *, limit: int, lockout_seconds: int) -> bool:
        if limit <= 0:
            return False
        counter = f"{_PREFIX}:fail:{key}"
        count = await self._redis.incr(counter)
        if count == 1:
            await self._redis.expire(counter, lockout_seconds)
        if count >= limit:
            await self._redis.set(f"{_PREFIX}:lock:{key}", "1", ex=lockout_seconds)
            await self._redis.delete(counter)
            return True
        return False

    async def reset(self, key: str) -> None:
        await self._redis.delete(f"{_PREFIX}:fail:{key}")


class InMemoryLoginAttemptTracker:
    """Single-process stand-in with the same behaviour, for tests."""

    def __init__(self) -> None:
        self._failures: dict[str, int] = {}
        self._locks: dict[str, float] = {}

    async def lock_ttl(self, key: str) -> int:
        until = self._locks.get(key, 0.0)
        return max(int(until - time.monotonic()), 0)

    async def record_failure(self, key: str, *, limit: int, lockout_seconds: int) -> bool:
        if limit <= 0:
            return False
        self._failures[key] = self._failures.get(key, 0) + 1
        if self._failures[key] >= limit:
            self._locks[key] = time.monotonic() + lockout_seconds
            self._failures.pop(key, None)
            return True
        return False

    async def reset(self, key: str) -> None:
        self._failures.pop(key, None)
