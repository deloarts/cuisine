"""
The `local` provider: one file per variant below LOCAL_STORAGE__BASE_DIR,
at `files/<public id>/<variant>`, a Docker volume in production. Writes go
to a temporary name and are renamed into place, so a reader never sees half
a file. The file system calls run in a worker thread.
"""

import contextlib
import os
from pathlib import Path

from anyio import to_thread

from src.platform.ports.outbound.file_content_store import ContentRef
from src.platform.ports.outbound.file_content_store import ContentUrl


class LocalContentStore:
    provider = "local"

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir).resolve()

    def _path(self, ref: ContentRef) -> Path:
        path = (self._base / ref.key).resolve()
        # The key is built from a UUID and a fixed variant, so this holds;
        # the check keeps a future caller from escaping the base directory.
        if not path.is_relative_to(self._base):
            raise ValueError("Content key escapes the storage directory.")
        return path

    async def put(self, ref: ContentRef, data: bytes, content_type: str) -> None:
        path = self._path(ref)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_name(path.name + ".partial")
            with partial.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            partial.replace(path)

        await to_thread.run_sync(write)

    async def get(self, ref: ContentRef) -> bytes | None:
        path = self._path(ref)

        def read() -> bytes | None:
            try:
                return path.read_bytes()
            except FileNotFoundError:
                return None

        return await to_thread.run_sync(read)

    async def delete(self, ref: ContentRef) -> None:
        path = self._path(ref)

        def remove() -> None:
            path.unlink(missing_ok=True)
            # The directory of the file goes too once it is empty.
            with contextlib.suppress(OSError):
                path.parent.rmdir()

        await to_thread.run_sync(remove)

    async def exists(self, ref: ContentRef) -> bool:
        path = self._path(ref)
        return await to_thread.run_sync(path.is_file)

    def url_for(
        self, ref: ContentRef, *, file_name: str, content_type: str, inline: bool
    ) -> ContentUrl | None:
        return None

    async def check(self) -> None:
        def probe() -> None:
            self._base.mkdir(parents=True, exist_ok=True)
            if not os.access(self._base, os.W_OK):
                raise OSError(f"{self._base} is not writable.")

        await to_thread.run_sync(probe)
