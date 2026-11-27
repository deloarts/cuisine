"""Live readings of the machine, the services and the storage, for the
admin area. Nothing here is stored."""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Literal
from typing import Protocol

ServiceStatus = Literal["ok", "degraded", "down"]


@dataclass(frozen=True)
class HostReading:
    hostname: str
    platform: str
    python_version: str
    boot_time: datetime
    process_start_time: datetime
    cpu_count: int
    cpu_percent: float
    load_average: tuple[float, float, float] | None
    memory_total_bytes: int
    memory_used_bytes: int
    memory_percent: float
    disk_path: str
    disk_total_bytes: int
    disk_used_bytes: int
    disk_percent: float


@dataclass(frozen=True)
class ServiceReading:
    name: str
    status: ServiceStatus
    latency_ms: float | None
    version: str | None
    # A short category on failure, never the raw exception.
    detail: str | None = None


@dataclass(frozen=True)
class TableSize:
    name: str
    bytes: int


@dataclass(frozen=True)
class DatabaseReading:
    dialect: str
    size_bytes: int | None
    # The largest tables, biggest first; empty where the database cannot say.
    largest_tables: list[TableSize] = field(default_factory=list)


@dataclass(frozen=True)
class FileKindCount:
    # image, pdf or other
    kind: str
    count: int
    bytes: int


@dataclass(frozen=True)
class FileReading:
    count: int
    original_bytes: int
    thumbnail_bytes: int
    by_kind: list[FileKindCount] = field(default_factory=list)


@dataclass(frozen=True)
class BackupFile:
    name: str
    size_bytes: int
    created: datetime


@dataclass(frozen=True)
class BackupReading:
    # Whether the backend can see the backup directory at all.
    visible: bool
    keep_days: int
    hour_utc: int
    files: list[BackupFile] = field(default_factory=list)


class IHostReader(Protocol):
    def read(self) -> HostReading: ...


class IServiceProbe(Protocol):
    async def probe(self) -> list[ServiceReading]: ...


class IStorageStatsReader(Protocol):
    async def database(self) -> DatabaseReading: ...
    async def files(self) -> FileReading: ...


class IBackupReader(Protocol):
    async def read(self) -> BackupReading: ...
