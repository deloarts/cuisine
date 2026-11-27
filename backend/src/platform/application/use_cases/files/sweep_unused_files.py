"""
The nightly sweep of unused uploads. An image is uploaded as soon as it is
picked, before the form that uses it is saved, so a discarded draft leaves a
file nothing refers to. The sweep deletes every file that is older than the
grace period and that no avatar, branding image or feature record (a
recipe, a step, a revision snapshot, a mirror) refers to.

Each candidate is locked and checked again before its row is deleted, all
in one transaction, so a file that was attached after the first check stays.
The content of the `local` and `seaweedfs` providers is deleted only after
the commit, so a failed commit never leaves a row without its content.
"""

from dataclasses import dataclass
from datetime import timedelta

from src.platform.application.services.file_access import FileAccess
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# The recipe editor keeps an unsaved draft on the device without a time
# limit, so the images picked in it must outlive a draft the user comes back
# to weeks later; the editor removes the images of an older draft that are
# gone. Unused uploads are rare and small, so keeping them a month costs
# little.
UNUSED_FILE_GRACE = timedelta(days=30)


@dataclass(frozen=True)
class SweepResult:
    removed: int
    # The stored bytes of the removed files, originals and thumbnails.
    removed_bytes: int
    # Removed files whose content the provider failed to delete; the rows
    # are gone, so the leftover content is never served.
    content_failures: int


def _stored_bytes(file: StoredFile) -> int:
    return file.size + (file.thumbnail_size or 0)


class SweepUnusedFiles:
    def __init__(
        self,
        *,
        file_repo: IStoredFileRepository,
        access: FileAccess,
        uow: IUnitOfWork,
        grace: timedelta = UNUSED_FILE_GRACE,
    ) -> None:
        self._files = file_repo
        self._access = access
        self._uow = uow
        self._grace = grace

    async def run(self) -> SweepResult:
        old = await self._files.created_before(now_utc() - self._grace)
        referenced = await self._access.referenced(old, history=True) if old else set()
        locked: list[StoredFile] = []
        for candidate in (f for f in old if f.id not in referenced):
            row = await self._files.lock(candidate.id)
            if row is not None:
                locked.append(row)
        # The second check runs after every lock is held, so it sees each
        # reference committed before then; a later one waits for the commit
        # and then fails on the missing row instead of losing its image.
        attached = await self._access.referenced(locked, history=True) if locked else set()
        removed = [f for f in locked if f.id not in attached]
        for file in removed:
            await self._files.delete(file, content=False)
        if not removed:
            await self._uow.rollback()
            return SweepResult(removed=0, removed_bytes=0, content_failures=0)
        await self._uow.commit()
        failures = 0
        for file in removed:
            try:
                await self._files.delete_content(file)
            except Exception:
                failures += 1
        return SweepResult(
            removed=len(removed),
            removed_bytes=sum(_stored_bytes(f) for f in removed),
            content_failures=failures,
        )
