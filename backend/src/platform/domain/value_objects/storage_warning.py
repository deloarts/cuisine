"""The warnings the Storage and backup tab shows, in the order it shows them."""

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class StorageWarning(StrValueEnum):
    # The file content lives on the machine that runs the database (the
    # local provider, or the bundled SeaweedFS), so losing that machine
    # loses both.
    FILES_ON_DATABASE_HOST = "files_on_database_host"
    # The nightly dump covers the database only; with the local or
    # SeaweedFS provider the file content needs a backup of its own.
    FILES_NOT_IN_BACKUP = "files_not_in_backup"
    # The backend cannot see the backup directory, so it cannot tell
    # whether backups run.
    BACKUPS_NOT_VISIBLE = "backups_not_visible"
    NO_BACKUP_YET = "no_backup_yet"
    # The newest dump is older than a day and a bit.
    BACKUP_STALE = "backup_stale"
    # The dumps sit on the same machine as the database; copy them off it.
    BACKUPS_ON_DATABASE_HOST = "backups_on_database_host"
