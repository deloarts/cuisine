"""The Host and the Storage and backup readings of the admin area."""

from dataclasses import dataclass
from uuid import UUID

from src.platform.domain.services.storage_rules import storage_warnings
from src.platform.domain.value_objects.storage_warning import StorageWarning
from src.platform.ports.outbound.backup_control import BackupRunStatus
from src.platform.ports.outbound.backup_control import IBackupControl
from src.platform.ports.outbound.file_content_store import IFileContentStore
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.system_readings import BackupReading
from src.platform.ports.outbound.system_readings import DatabaseReading
from src.platform.ports.outbound.system_readings import FileReading
from src.platform.ports.outbound.system_readings import HostReading
from src.platform.ports.outbound.system_readings import IBackupReader
from src.platform.ports.outbound.system_readings import IHostReader
from src.platform.ports.outbound.system_readings import IServiceProbe
from src.platform.ports.outbound.system_readings import IStorageStatsReader
from src.platform.ports.outbound.system_readings import ServiceReading
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class HostStatus:
    app_version: str
    # The instance's own id, which other instances know it by.
    instance_id: UUID
    host: HostReading
    services: list[ServiceReading]


@dataclass(frozen=True)
class StorageStatus:
    provider: str
    # Whether the active provider answered its check.
    provider_reachable: bool
    database: DatabaseReading
    files: FileReading
    backups: BackupReading
    warnings: list[StorageWarning]
    # "Back up now": whether it can reach the sidecar, whether a request is
    # waiting, and the sidecar's last run.
    backup_now_available: bool = False
    backup_requested: bool = False
    last_run: BackupRunStatus | None = None


class ReadHostStatus:
    def __init__(
        self,
        *,
        host: IHostReader,
        probe: IServiceProbe,
        app_version: str,
        settings_repo: ISettingsRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._host = host
        self._probe = probe
        self._version = app_version
        self._settings = settings_repo
        self._uow = uow

    async def run(self) -> HostStatus:
        instance_id = await self._settings.instance_id()
        # The startup seed creates the id; should it be missing, the one
        # just created must be kept.
        await self._uow.commit()
        return HostStatus(
            app_version=self._version,
            instance_id=instance_id,
            host=self._host.read(),
            services=await self._probe.probe(),
        )


class ReadStorageStatus:
    def __init__(
        self,
        *,
        stats: IStorageStatsReader,
        backups: IBackupReader,
        content: IFileContentStore,
        endpoint_url: str | None,
        control: IBackupControl | None = None,
    ) -> None:
        self._stats = stats
        self._backups = backups
        self._content = content
        self._endpoint = endpoint_url
        self._control = control

    async def run(self) -> StorageStatus:
        try:
            await self._content.check()
            reachable = True
        except Exception:
            reachable = False
        backups = await self._backups.read()
        newest = max((b.created for b in backups.files), default=None)
        return StorageStatus(
            provider=self._content.provider,
            provider_reachable=reachable,
            database=await self._stats.database(),
            files=await self._stats.files(),
            backups=backups,
            warnings=storage_warnings(
                provider=self._content.provider,
                endpoint_url=self._endpoint,
                backups_visible=backups.visible,
                newest_backup=newest,
                now=now_utc(),
            ),
            backup_now_available=self._control is not None and self._control.available,
            backup_requested=await self._control.pending() if self._control else False,
            last_run=await self._control.last_run() if self._control else None,
        )
