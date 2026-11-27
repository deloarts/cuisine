"""IInstanceFacts from the environment configuration."""

from datetime import date

from src.platform.domain.services.backup_rules import BackupRetention
from src.platform.domain.services.backup_rules import backup_retention
from src.platform.infrastructure.config.settings import cfg
from src.shared_kernel.domain.services.clock import now_utc


class ConfiguredInstanceFacts:
    def backup_retention(self, deleted_on: date | None = None) -> BackupRetention:
        return backup_retention(cfg.backup.keep_days, deleted_on or now_utc().date())

    def storage_provider(self) -> str:
        return cfg.storage.provider

    def backup_hour_utc(self) -> int:
        return cfg.backup.hour
