"""The Alembic history builds exactly the schema the models declare, on a
throwaway SQLite file."""

from pathlib import Path

from sqlalchemy import create_engine

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from src.bootstrap.migrations import alembic_config
from src.bootstrap.models import Base


def test_migrations_match_the_models(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    engine = create_engine(url)
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []
