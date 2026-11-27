"""Which warnings the storage and backup state earns, adapted from glados's
backup rules."""

import ipaddress
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlparse

from src.platform.domain.value_objects.storage_warning import StorageWarning

# Host names that put an object store on the database's own machine: the
# bundled SeaweedFS by its service name, and the loopback names.
_ON_HOST_NAMES = frozenset({"seaweedfs", "localhost"})
# A nightly dump plus slack for a slow run.
STALE_AFTER = timedelta(hours=26)


def files_on_database_host(provider: str, endpoint_url: str | None) -> bool:
    if provider == "local":
        return True
    if provider == "seaweedfs" and endpoint_url:
        host = (urlparse(endpoint_url).hostname or "").lower()
        if host in _ON_HOST_NAMES:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False
    return False


def storage_warnings(
    *,
    provider: str,
    endpoint_url: str | None,
    backups_visible: bool,
    newest_backup: datetime | None,
    now: datetime,
) -> list[StorageWarning]:
    warnings: list[StorageWarning] = []
    if files_on_database_host(provider, endpoint_url):
        warnings.append(StorageWarning.FILES_ON_DATABASE_HOST)
    if provider != "postgres":
        warnings.append(StorageWarning.FILES_NOT_IN_BACKUP)
    if not backups_visible:
        warnings.append(StorageWarning.BACKUPS_NOT_VISIBLE)
        return warnings
    if newest_backup is None:
        warnings.append(StorageWarning.NO_BACKUP_YET)
    elif now - newest_backup > STALE_AFTER:
        warnings.append(StorageWarning.BACKUP_STALE)
    warnings.append(StorageWarning.BACKUPS_ON_DATABASE_HOST)
    return warnings
