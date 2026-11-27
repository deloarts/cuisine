"""
Database engine and session factory. This is the only file allowed to
construct a SQLAlchemy engine.

Pool and timeout options are Postgres only. The test suite's SQLite file
runs on aiosqlite with NullPool instead, so no connection is ever reused
across the separate event loops pytest gives each test. Every Postgres
connection starts with statement, lock and idle-in-transaction timeouts, so
a runaway query or an abandoned transaction cannot hold locks indefinitely.
"""

from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from src.platform.infrastructure.config.settings import DatabaseSettings
from src.platform.infrastructure.config.settings import cfg


def postgres_connect_args(settings: DatabaseSettings) -> dict[str, str]:
    options = " ".join(
        f"-c {name}={seconds}s"
        for name, seconds in (
            ("statement_timeout", settings.statement_timeout_seconds),
            ("lock_timeout", settings.lock_timeout_seconds),
            ("idle_in_transaction_session_timeout", settings.idle_in_transaction_timeout_seconds),
        )
    )
    return {"options": options, "application_name": "cuisine"}


def build_engine(settings: DatabaseSettings) -> AsyncEngine:
    if settings.url.startswith("postgresql"):
        return create_async_engine(
            settings.async_url,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_timeout=settings.pool_timeout_seconds,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args=postgres_connect_args(settings),
        )
    sqlite_engine = create_async_engine(settings.async_url, poolclass=NullPool)
    event.listen(sqlite_engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
    return sqlite_engine


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    """SQLite ignores foreign keys, and so their ON DELETE rules, unless
    each connection switches them on."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine: AsyncEngine = build_engine(cfg.database)

# expire_on_commit=False: objects keep their loaded state after a commit,
# since an AsyncSession cannot lazily reload attributes anyway.
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)
