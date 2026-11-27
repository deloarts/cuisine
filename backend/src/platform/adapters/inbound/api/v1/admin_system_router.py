"""/api/v1/web/admin/host and /admin/storage: live readings for the admin
area's Host and Storage and backup tabs. Nothing here is stored."""

from fastapi import APIRouter
from fastapi import Depends

from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import get_read_host_status
from src.platform.adapters.inbound.api.deps import get_read_storage_status
from src.platform.adapters.inbound.api.schemas.admin_system_schema import BackupFileResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import BackupReadingResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import BackupRunStatusResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import DatabaseReadingResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import FileKindCountResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import FileReadingResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import HostStatusResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import ServiceReadingResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import StorageStatusResponse
from src.platform.adapters.inbound.api.schemas.admin_system_schema import TableSizeResponse
from src.platform.application.use_cases.admin.system import ReadHostStatus
from src.platform.application.use_cases.admin.system import ReadStorageStatus
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(prefix="/admin", tags=["admin-system"])

_read = require_permission(Permission.READ_SETTINGS)


@router.get("/host", response_model=HostStatusResponse)
async def read_host(
    _user: User = Depends(_read), use_case: ReadHostStatus = Depends(get_read_host_status)
) -> HostStatusResponse:
    status = await use_case.run()
    h = status.host
    return HostStatusResponse(
        app_version=status.app_version,
        instance_id=status.instance_id,
        hostname=h.hostname,
        platform=h.platform,
        python_version=h.python_version,
        boot_time=h.boot_time,
        process_start_time=h.process_start_time,
        cpu_count=h.cpu_count,
        cpu_percent=h.cpu_percent,
        load_average=list(h.load_average) if h.load_average else None,
        memory_total_bytes=h.memory_total_bytes,
        memory_used_bytes=h.memory_used_bytes,
        memory_percent=h.memory_percent,
        disk_path=h.disk_path,
        disk_total_bytes=h.disk_total_bytes,
        disk_used_bytes=h.disk_used_bytes,
        disk_percent=h.disk_percent,
        services=[
            ServiceReadingResponse(
                name=s.name,
                status=s.status,
                latency_ms=s.latency_ms,
                version=s.version,
                detail=s.detail,
            )
            for s in status.services
        ],
    )


@router.get("/storage", response_model=StorageStatusResponse)
async def read_storage(
    _user: User = Depends(_read), use_case: ReadStorageStatus = Depends(get_read_storage_status)
) -> StorageStatusResponse:
    status = await use_case.run()
    backups = status.backups
    return StorageStatusResponse(
        provider=status.provider,
        provider_reachable=status.provider_reachable,
        database=DatabaseReadingResponse(
            dialect=status.database.dialect,
            size_bytes=status.database.size_bytes,
            largest_tables=[
                TableSizeResponse(name=t.name, bytes=t.bytes)
                for t in status.database.largest_tables
            ],
        ),
        files=FileReadingResponse(
            count=status.files.count,
            original_bytes=status.files.original_bytes,
            thumbnail_bytes=status.files.thumbnail_bytes,
            by_kind=[
                FileKindCountResponse(kind=k.kind, count=k.count, bytes=k.bytes)
                for k in status.files.by_kind
            ],
        ),
        backups=BackupReadingResponse(
            visible=backups.visible,
            keep_days=backups.keep_days,
            hour_utc=backups.hour_utc,
            newest=max((b.created for b in backups.files), default=None),
            files=[
                BackupFileResponse(name=b.name, size_bytes=b.size_bytes, created=b.created)
                for b in backups.files
            ],
        ),
        warnings=[w.value for w in status.warnings],
        backup_now_available=status.backup_now_available,
        backup_requested=status.backup_requested,
        last_run=(
            BackupRunStatusResponse(
                trigger=status.last_run.trigger,
                started=status.last_run.started,
                finished=status.last_run.finished,
                ok=status.last_run.ok,
                file=status.last_run.file,
            )
            if status.last_run
            else None
        ),
    )
