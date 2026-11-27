"""
Pydantic settings classes that load configuration from environment
variables, grouped by concern and composed into the top-level `Settings`
object read via `cfg`. Nested values use `__`, e.g. DATABASE__URL.
"""

import os
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class SecuritySettings(BaseModel):
    # Signs the web tokens. Rotating it signs everybody out.
    secret_key: str
    # Encrypts the secrets the app must read back, such as TOTP secrets and
    # the SMTP password (secret_box.py). Rotating it without keeping the old
    # value as encryption_key_previous makes them unreadable.
    encryption_key: str
    encryption_key_previous: str | None = None
    algorithm: str = "HS256"


class DatabaseSettings(BaseModel):
    # A SQLAlchemy URL. Postgres URLs name the psycopg (v3) driver,
    # postgresql+psycopg://, the only Postgres driver installed.
    url: str
    pool_size: int = 5
    max_overflow: int = 5
    pool_timeout_seconds: int = 10
    statement_timeout_seconds: int = 30
    lock_timeout_seconds: int = 5
    idle_in_transaction_timeout_seconds: int = 60

    @property
    def async_url(self) -> str:
        """`url` in the form the async engine needs. psycopg 3 serves sync and
        async under one dialect name, so only SQLite (the test suite) swaps
        its driver for aiosqlite."""
        if self.url.startswith("sqlite://"):
            return "sqlite+aiosqlite://" + self.url.removeprefix("sqlite://")
        return self.url


class RedisSettings(BaseModel):
    url: str
    socket_timeout_seconds: float = 3.0
    socket_connect_timeout_seconds: float = 2.0
    max_connections: int = 50


class InitSettings(BaseModel):
    """The system user, who signs in as `system` or with `mail`. Created from
    these values at the first start and synced back to them on every later
    start, so they stay the source of truth for its name, address and
    password."""

    full_name: str
    mail: str
    password: str


class StorageSettings(BaseModel):
    """Where stored file content goes. The metadata always lives in the
    database; only the bytes move. `postgres` keeps them in the database
    (the default), `local` writes them below LOCAL_STORAGE__BASE_DIR, and
    `seaweedfs` talks to an S3 API such as the bundled SeaweedFS. Changing the
    provider moves no file; the storage CLI does that."""

    provider: Literal["postgres", "local", "seaweedfs"] = "postgres"
    # The S3 endpoint the backend talks to, over the internal network.
    endpoint_url: str | None = None
    # The origin the browser loads presigned URLs from: the deployment's own
    # address, whose nginx forwards /objects/ to SeaweedFS.
    public_endpoint_url: str | None = None
    bucket_name: str = "objects"
    access_key: str | None = None
    secret_key: str | None = None
    region: str = "us-east-1"
    use_ssl: bool = False
    # Lifetime of a presigned URL.
    presigned_url_seconds: int = 3600


class LocalStorageSettings(BaseModel):
    # The directory the `local` provider writes to; a volume in the image.
    base_dir: str = "./files"


class BackupSettings(BaseModel):
    """What the backend knows about the backup sidecar, so the admin area can
    show its state. The sidecar does the work; the backend only reads the
    directory it writes to, mounted read-only. An empty dir means the
    backend cannot see the backups."""

    dir: str = ""
    keep_days: int = 14
    # The UTC hour of the nightly dump.
    hour: int = 3
    # A small directory the backend and the sidecar share, read-write: the
    # backend drops a request file there for "back up now", the sidecar
    # writes the status of its last run. Empty switches "back up now" off.
    control_dir: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    debug: bool = False
    # The public URL the frontend is served from. CORS allows it, passkeys
    # are bound to its host name, and mail links point at it.
    domain: str = "http://localhost:5173"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["text", "json"] = "text"
    # Applies pending migrations at startup. Meant for the dev server only;
    # the container entrypoint migrates before the workers start.
    migrate_on_startup: bool = False

    security: SecuritySettings
    database: DatabaseSettings
    redis: RedisSettings
    init: InitSettings
    storage: StorageSettings = StorageSettings()
    local_storage: LocalStorageSettings = LocalStorageSettings()
    backup: BackupSettings = BackupSettings()


cfg = Settings()
