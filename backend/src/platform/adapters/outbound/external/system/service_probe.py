"""Whether the database and Redis answer, how fast, and their versions."""

import time

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.ports.outbound.system_readings import ServiceReading


def _elapsed(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


class ServiceProbe:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self._db = session
        self._redis = redis

    async def probe(self) -> list[ServiceReading]:
        return [await self._database(), await self._redis_reading()]

    async def _database(self) -> ServiceReading:
        start = time.perf_counter()
        try:
            dialect = self._db.bind.dialect.name if self._db.bind else "unknown"
            query = "SHOW server_version" if dialect == "postgresql" else "SELECT sqlite_version()"
            version = await self._db.scalar(text(query))
            return ServiceReading(
                name="database",
                status="ok",
                latency_ms=_elapsed(start),
                version=f"{dialect} {version}",
            )
        except Exception as exc:
            return ServiceReading(
                name="database",
                status="down",
                latency_ms=None,
                version=None,
                detail=type(exc).__name__,
            )

    async def _redis_reading(self) -> ServiceReading:
        start = time.perf_counter()
        try:
            await self._redis.ping()
            latency = _elapsed(start)
            info = await self._redis.info("server")
            return ServiceReading(
                name="redis",
                status="ok",
                latency_ms=latency,
                version=str(info.get("redis_version")) if info else None,
            )
        except Exception as exc:
            return ServiceReading(
                name="redis",
                status="down",
                latency_ms=None,
                version=None,
                detail=type(exc).__name__,
            )
