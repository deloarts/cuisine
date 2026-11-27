"""
"Back up now" through the directory the backend and the backup sidecar
share (BACKUP__CONTROL_DIR). The backend writes `request`; the sidecar
checks for it every few seconds, runs the same dump as at night, removes
the request and writes `status.json` before and after the run. No socket
and no Docker access is needed, and the backend never runs pg_dump itself.
"""

import json
from datetime import datetime
from pathlib import Path

from anyio import to_thread

from src.platform.ports.outbound.backup_control import BackupRunStatus

REQUEST_FILE = "request"
STATUS_FILE = "status.json"


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class FileBackupControl:
    def __init__(self, directory: str) -> None:
        self._dir = Path(directory) if directory else None

    @property
    def available(self) -> bool:
        return self._dir is not None and self._dir.is_dir()

    async def request(self, at: datetime) -> None:
        directory = self._dir
        if directory is None:
            raise OSError("BACKUP__CONTROL_DIR is not set.")

        def write() -> None:
            partial = directory / f"{REQUEST_FILE}.partial"
            partial.write_text(json.dumps({"requested_at": at.isoformat()}))
            partial.replace(directory / REQUEST_FILE)

        await to_thread.run_sync(write)

    async def pending(self) -> bool:
        if self._dir is None:
            return False
        path = self._dir / REQUEST_FILE
        return await to_thread.run_sync(path.is_file)

    async def last_run(self) -> BackupRunStatus | None:
        if self._dir is None:
            return None
        path = self._dir / STATUS_FILE

        def read() -> dict[str, object] | None:
            try:
                data = json.loads(path.read_text())
            except (OSError, ValueError):
                return None
            return data if isinstance(data, dict) else None

        data = await to_thread.run_sync(read)
        started = _parse_time(data.get("started")) if data else None
        if data is None or started is None:
            return None
        ok = data.get("ok")
        return BackupRunStatus(
            trigger=str(data.get("trigger") or "scheduled"),
            started=started,
            finished=_parse_time(data.get("finished")),
            ok=ok if isinstance(ok, bool) else None,
            file=str(data["file"]) if data.get("file") else None,
        )
