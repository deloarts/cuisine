"""Facts about this instance's configuration that texts shown to users must
name exactly, such as how long backups keep deleted data."""

from datetime import date
from typing import Protocol

from src.platform.domain.services.backup_rules import BackupRetention


class IInstanceFacts(Protocol):
    def backup_retention(self, deleted_on: date | None = None) -> BackupRetention:
        """BACKUP__KEEP_DAYS and, for data deleted on `deleted_on` (today by
        default), the day it is gone from every backup."""
        ...

    def storage_provider(self) -> str: ...
    def backup_hour_utc(self) -> int: ...
