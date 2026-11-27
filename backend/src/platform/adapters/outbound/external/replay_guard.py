"""IReplayGuard on Redis (`SET NX EX`), and an in-process one for tests."""

import time

from redis.asyncio import Redis

_PREFIX = "cuisine:once"


class RedisReplayGuard:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def consume_once(self, key: str, ttl_seconds: int) -> bool:
        return bool(await self._redis.set(f"{_PREFIX}:{key}", "1", nx=True, ex=ttl_seconds))


class InMemoryReplayGuard:
    def __init__(self) -> None:
        self._claimed: dict[str, float] = {}

    async def consume_once(self, key: str, ttl_seconds: int) -> bool:
        now = time.monotonic()
        if self._claimed.get(key, 0.0) > now:
            return False
        self._claimed[key] = now + ttl_seconds
        return True
