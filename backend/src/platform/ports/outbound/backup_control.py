"""Asking the backup sidecar for a dump now, and reading how its last run
went."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class BackupRunStatus:
    # scheduled or manual
    trigger: str
    started: datetime
    finished: datetime | None
    ok: bool | None
    file: str | None


class IBackupControl(Protocol):
    @property
    def available(self) -> bool:
        """Whether the sidecar's control directory is configured and seen."""
        ...

    async def request(self, at: datetime) -> None: ...
    async def pending(self) -> bool: ...
    async def last_run(self) -> BackupRunStatus | None: ...
