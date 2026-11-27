"""How long deleted data survives in the nightly dumps."""

from dataclasses import dataclass
from datetime import date
from datetime import timedelta


@dataclass(frozen=True)
class BackupRetention:
    keep_days: int
    # For data deleted today: the day the last dump still holding it is
    # removed. The sidecar deletes dumps older than keep_days on each run.
    gone_by: date


def backup_retention(keep_days: int, deleted_on: date) -> BackupRetention:
    return BackupRetention(keep_days=keep_days, gone_by=deleted_on + timedelta(days=keep_days + 1))
