"""
Moving stored file content between storage providers, for the storage CLI.

The move is three steps with a restart in between, so no step can lose a
file:

1. `copy` reads every variant of every file from the source provider,
   checks it against the content hash in the metadata, writes it to the
   target and reads it back to check again.
2. The operator sets STORAGE__PROVIDER to the target and restarts. Files
   uploaded between the copy and the restart are still only on the source,
   so `copy` runs again after the restart (it skips what is already there).
3. `remove-source` deletes the content from the old provider, and only
   after `verify` found every file intact on the active one. It refuses to
   touch the active provider.
"""

import hashlib
from dataclasses import dataclass
from dataclasses import field

from src.platform.domain.entities.stored_file import StoredFile
from src.platform.ports.outbound.file_content_store import ORIGINAL
from src.platform.ports.outbound.file_content_store import THUMBNAIL
from src.platform.ports.outbound.file_content_store import ContentRef
from src.platform.ports.outbound.file_content_store import IFileContentStore
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork


@dataclass
class MoveReport:
    files: int = 0
    copied: int = 0
    skipped: int = 0
    removed: int = 0
    # One line per variant that is missing or does not match its hash.
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _variants(file: StoredFile) -> list[tuple[ContentRef, str]]:
    """Each variant of the file with the hash its bytes must have."""
    refs = [(ContentRef(file.id, file.public_id, ORIGINAL), file.content_hash)]
    if file.thumbnail_hash:
        refs.append((ContentRef(file.id, file.public_id, THUMBNAIL), file.thumbnail_hash))
    return refs


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class MoveStorage:
    def __init__(self, *, files: IStoredFileRepository, uow: IUnitOfWork) -> None:
        self._files = files
        self._uow = uow

    async def copy(self, source: IFileContentStore, target: IFileContentStore) -> MoveReport:
        if source.provider == target.provider:
            raise ValueError("Source and target are the same provider.")
        await target.check()
        report = MoveReport()
        for file in await self._files.list_all():
            report.files += 1
            for ref, expected in _variants(file):
                existing = await target.get(ref)
                if existing is not None and _sha256(existing) == expected:
                    report.skipped += 1
                    continue
                data = await source.get(ref)
                if data is None:
                    report.problems.append(f"{ref.key}: missing on {source.provider}")
                    continue
                if _sha256(data) != expected:
                    report.problems.append(f"{ref.key}: hash mismatch on {source.provider}")
                    continue
                await target.put(ref, data, file.content_type)
                written = await target.get(ref)
                if written is None or _sha256(written) != expected:
                    report.problems.append(f"{ref.key}: read-back failed on {target.provider}")
                    continue
                report.copied += 1
        # The database provider writes in the session's transaction.
        await self._uow.commit()
        return report

    async def verify(self, store: IFileContentStore) -> MoveReport:
        report = MoveReport()
        for file in await self._files.list_all():
            report.files += 1
            for ref, expected in _variants(file):
                data = await store.get(ref)
                if data is None:
                    report.problems.append(f"{ref.key}: missing on {store.provider}")
                elif _sha256(data) != expected:
                    report.problems.append(f"{ref.key}: hash mismatch on {store.provider}")
        return report

    async def remove_source(
        self, source: IFileContentStore, active: IFileContentStore
    ) -> MoveReport:
        if source.provider == active.provider:
            raise ValueError("Refusing to remove content from the active provider.")
        report = await self.verify(active)
        if not report.ok:
            return report
        for file in await self._files.list_all():
            for ref, _expected in _variants(file):
                if await source.exists(ref):
                    await source.delete(ref)
                    report.removed += 1
        await self._uow.commit()
        return report
