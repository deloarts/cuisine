"""
The shared async Redis client. Login throttling and the TOTP replay guard
use it today; the live shopping list will publish through it. Created
lazily, because a client is bound to the event loop it first ran on.
"""

from redis.asyncio import Redis

from src.platform.infrastructure.config.settings import cfg

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(
            cfg.redis.url,
            socket_timeout=cfg.redis.socket_timeout_seconds,
            socket_connect_timeout=cfg.redis.socket_connect_timeout_seconds,
            max_connections=cfg.redis.max_connections,
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
