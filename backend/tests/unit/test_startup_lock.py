"""The startup lock: a no-op on SQLite, and on Postgres a polled advisory
lock that waits for another worker, commits after every attempt, releases
itself after the block and gives up after its wait."""

from types import TracebackType
from typing import Any
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine

from src.bootstrap.startup_lock import STARTUP_LOCK_KEY
from src.bootstrap.startup_lock import startup_lock


class _Connection:
    """Answers pg_try_advisory_lock from a script of results and records
    every statement and commit."""

    def __init__(self, attempts: list[bool]) -> None:
        self.attempts = attempts
        self.calls: list[str] = []

    async def __aenter__(self) -> "_Connection":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def scalar(self, statement: Any, params: dict[str, int]) -> bool:
        assert params == {"key": STARTUP_LOCK_KEY}
        self.calls.append(str(statement))
        return self.attempts.pop(0)

    async def execute(self, statement: Any, params: dict[str, int]) -> None:
        assert params == {"key": STARTUP_LOCK_KEY}
        self.calls.append(str(statement))

    async def commit(self) -> None:
        self.calls.append("COMMIT")


class _Dialect:
    name = "postgresql"


class _Engine:
    dialect = _Dialect()

    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    def connect(self) -> _Connection:
        return self.connection


def _postgres(attempts: list[bool]) -> tuple[AsyncEngine, _Connection]:
    connection = _Connection(attempts)
    return cast(AsyncEngine, _Engine(connection)), connection


async def test_sqlite_runs_the_block_without_a_lock() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    ran = False
    async with startup_lock(engine):
        ran = True
    await engine.dispose()
    assert ran


async def test_waits_for_the_lock_then_releases_it() -> None:
    engine, connection = _postgres([False, False, True])
    async with startup_lock(engine, poll_seconds=0):
        connection.calls.append("block")
    assert connection.calls == [
        "SELECT pg_try_advisory_lock(:key)",
        "COMMIT",
        "SELECT pg_try_advisory_lock(:key)",
        "COMMIT",
        "SELECT pg_try_advisory_lock(:key)",
        "COMMIT",
        "block",
        "SELECT pg_advisory_unlock(:key)",
        "COMMIT",
    ]


async def test_releases_the_lock_when_the_block_fails() -> None:
    engine, connection = _postgres([True])
    with pytest.raises(RuntimeError):
        async with startup_lock(engine, poll_seconds=0):
            raise RuntimeError("setup failed")
    assert connection.calls[-2:] == ["SELECT pg_advisory_unlock(:key)", "COMMIT"]


async def test_gives_up_after_its_wait() -> None:
    engine, connection = _postgres([False] * 5)
    with pytest.raises(TimeoutError):
        async with startup_lock(engine, poll_seconds=0, wait_seconds=0):
            pytest.fail("the block ran without the lock")
    assert "SELECT pg_advisory_unlock(:key)" not in connection.calls
