"""The Host and the Storage and backup readings of the admin area."""

from datetime import datetime
from uuid import UUID

from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class ServiceReadingResponse(ResponseSchema):
    name: str
    # ok, degraded or down
    status: str
    latency_ms: float | None
    version: str | None
    detail: str | None


class HostStatusResponse(ResponseSchema):
    app_version: str
    # The instance's own id, created at first start and never changed.
    instance_id: UUID
    hostname: str
    platform: str
    python_version: str
    boot_time: datetime
    process_start_time: datetime
    cpu_count: int
    cpu_percent: float
    load_average: list[float] | None
    memory_total_bytes: int
    memory_used_bytes: int
    memory_percent: float
    disk_path: str
    disk_total_bytes: int
    disk_used_bytes: int
    disk_percent: float
    services: list[ServiceReadingResponse]


class TableSizeResponse(ResponseSchema):
    name: str
    bytes: int


class DatabaseReadingResponse(ResponseSchema):
    dialect: str
    size_bytes: int | None
    largest_tables: list[TableSizeResponse]


class FileKindCountResponse(ResponseSchema):
    kind: str
    count: int
    bytes: int


class FileReadingResponse(ResponseSchema):
    count: int
    original_bytes: int
    thumbnail_bytes: int
    by_kind: list[FileKindCountResponse]


class BackupFileResponse(ResponseSchema):
    name: str
    size_bytes: int
    created: datetime


class BackupReadingResponse(ResponseSchema):
    visible: bool
    keep_days: int
    hour_utc: int
    newest: datetime | None
    files: list[BackupFileResponse]


class StorageStatusResponse(ResponseSchema):
    # postgres, local or seaweedfs
    provider: str
    provider_reachable: bool
    database: DatabaseReadingResponse
    files: FileReadingResponse
    backups: BackupReadingResponse
    # files_on_database_host, files_not_in_backup, backups_not_visible,
    # no_backup_yet, backup_stale, backups_on_database_host
    warnings: list[str]
    # "Back up now": whether the sidecar is reachable, whether a request is
    # waiting, and the sidecar's last run (scheduled or manual).
    backup_now_available: bool
    backup_requested: bool
    last_run: "BackupRunStatusResponse | None"


class BackupRunStatusResponse(ResponseSchema):
    trigger: str
    started: datetime
    finished: datetime | None
    ok: bool | None
    file: str | None


StorageStatusResponse.model_rebuild()
