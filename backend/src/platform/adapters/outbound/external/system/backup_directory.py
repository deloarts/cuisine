"""
Reads the directory the backup sidecar writes its nightly dumps to
(`cuisine-<timestamp>.dump`), mounted read-only into the backend at
BACKUP__DIR. The backend never writes there.
"""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from anyio import to_thread

from src.platform.ports.outbound.system_readings import BackupFile
from src.platform.ports.outbound.system_readings import BackupReading

# The newest ones, enough for the tab and its staleness check.
LISTED = 30


class BackupDirectoryReader:
    def __init__(self, directory: str, *, keep_days: int, hour_utc: int) -> None:
        self._dir = Path(directory) if directory else None
        self._keep_days = keep_days
        self._hour = hour_utc

    async def read(self) -> BackupReading:
        directory = self._dir
        if directory is None:
            return BackupReading(visible=False, keep_days=self._keep_days, hour_utc=self._hour)

        def scan() -> list[BackupFile] | None:
            if not directory.is_dir():
                return None
            found: list[BackupFile] = []
            for path in directory.glob("cuisine-*.dump"):
                stat = path.stat()
                found.append(
                    BackupFile(
                        name=path.name,
                        size_bytes=stat.st_size,
                        created=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                    )
                )
            found.sort(key=lambda b: b.created, reverse=True)
            return found[:LISTED]

        try:
            files = await to_thread.run_sync(scan)
        except OSError:
            files = None
        return BackupReading(
            visible=files is not None,
            keep_days=self._keep_days,
            hour_utc=self._hour,
            files=files or [],
        )
