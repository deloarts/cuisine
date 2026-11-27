"""
Alembic migration environment. It reads the database URL from Settings and
imports every ORM model through src/bootstrap/models.py.

Every online run on Postgres takes a transaction-scoped advisory lock before
it reads the current revision and holds it until the migration transaction
commits, so two containers that start at once never migrate together: the
second waits, then finds nothing left to do. SQLite has no advisory locks
and runs single-process, so there the lock is skipped.
"""

from logging.config import fileConfig
from typing import Any
from typing import Literal

from sqlalchemy import JSON
from sqlalchemy import Connection
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import text
from sqlalchemy.types import TypeDecorator

from alembic import context
from alembic.autogenerate.api import AutogenContext
from src.bootstrap.models import Base
from src.platform.infrastructure.config.settings import cfg

# An arbitrary constant shared by every process that migrates.
MIGRATION_LOCK_KEY = 0x6375_6973

config = context.config
config.set_main_option("sqlalchemy.url", cfg.database.url)

if config.config_file_name is not None:
    # disable_existing_loggers=False keeps the cuisine logger alive when
    # the app runs the migrations itself.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | Literal[False]:
    """Renders the app's TypeDecorators as their plain SQL type, so a
    migration never imports application code and stays valid when that
    code changes. Everything else renders the default way."""
    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"
    # Alembic renders the JSONB variant's astext_type as a bare Text(), which
    # the migration has not imported, so the JSON column type is spelled out.
    if type_ == "type" and isinstance(obj, JSON) and "postgresql" in obj._variant_mapping:
        autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
        return 'sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")'
    return False


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a connection: `alembic upgrade head --sql`."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_locked(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, render_item=render_item
    )
    with context.begin_transaction():
        if connection.dialect.name == "postgresql":
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK_KEY}
            )
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect and apply. A caller that drives Alembic programmatically, a
    test notably, can hand in an open connection through
    `config.attributes["connection"]`."""
    attributes_connection = config.attributes.get("connection")
    if attributes_connection is not None:
        _run_locked(attributes_connection)
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _run_locked(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
