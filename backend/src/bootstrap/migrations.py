"""Applies the Alembic migrations programmatically. Used by the dev server
when MIGRATE_ON_STARTUP is set and by the container entrypoint."""

from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def upgrade_to_head() -> None:
    command.upgrade(alembic_config(), "head")
