"""
The file storage port: the metadata in `stored_files`, the bytes in the
content store of the active provider (STORAGE__PROVIDER). With the default
`postgres` provider the bytes go to `stored_file_contents` in the same
transaction and a deleted row takes them along by cascade; the local and
S3 providers write outside the transaction, so a rolled-back upload can
leave content that no row names; it is never served, since every read goes
through a row.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.stored_file_models import StoredFileModel
from src.platform.adapters.outbound.persistence.repositories._common import copy_entity_to_row
from src.platform.adapters.outbound.persistence.repositories._common import entity_from_row
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.platform.adapters.outbound.storage.postgres_store import PostgresContentStore
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.ports.outbound.file_content_store import ORIGINAL
from src.platform.ports.outbound.file_content_store import THUMBNAIL
from src.platform.ports.outbound.file_content_store import ContentRef
from src.platform.ports.outbound.file_content_store import ContentUrl
from src.platform.ports.outbound.file_content_store import IFileContentStore


def content_ref(file: StoredFile, *, thumbnail: bool = False) -> ContentRef:
    return ContentRef(
        file_id=file.id, public_id=file.public_id, variant=THUMBNAIL if thumbnail else ORIGINAL
    )


class SqlAlchemyStoredFileRepository:
    def __init__(self, session: AsyncSession, content: IFileContentStore | None = None) -> None:
        self._db = session
        self._content = content or PostgresContentStore(session)

    async def get(self, file_id: int) -> StoredFile | None:
        row = await self._db.get(StoredFileModel, file_id)
        return entity_from_row(StoredFile, row) if row is not None else None

    async def get_by_public_id(self, public_id: str) -> StoredFile | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(StoredFileModel).where(StoredFileModel.public_id == uid))
        return entity_from_row(StoredFile, row) if row is not None else None

    async def public_ids(self, ids: list[int]) -> dict[int, UUID]:
        """The public ids of files by internal id, for responses that refer
        to images without loading them."""
        wanted = sorted({i for i in ids if i})
        if not wanted:
            return {}
        rows = await self._db.execute(
            select(StoredFileModel.id, StoredFileModel.public_id).where(
                StoredFileModel.id.in_(wanted)
            )
        )
        return {file_id: public_id for file_id, public_id in rows.all()}

    async def add(self, file: StoredFile, data: bytes, thumbnail: bytes | None) -> StoredFile:
        row = StoredFileModel(public_id=file.public_id)
        copy_entity_to_row(file, row, skip=frozenset())
        self._db.add(row)
        await self._db.flush()
        stored = entity_from_row(StoredFile, row)
        await self._content.put(content_ref(stored), data, stored.content_type)
        if thumbnail is not None:
            await self._content.put(
                content_ref(stored, thumbnail=True), thumbnail, stored.content_type
            )
        return stored

    async def read_content(self, file: StoredFile, *, thumbnail: bool = False) -> bytes | None:
        return await self._content.get(content_ref(file, thumbnail=thumbnail))

    def content_url(self, file: StoredFile, *, thumbnail: bool, inline: bool) -> ContentUrl | None:
        return self._content.url_for(
            content_ref(file, thumbnail=thumbnail),
            file_name=file.file_name,
            content_type=file.content_type,
            inline=inline,
        )

    async def list_all(self) -> list[StoredFile]:
        rows = await self._db.scalars(select(StoredFileModel).order_by(StoredFileModel.id))
        return [entity_from_row(StoredFile, r) for r in rows.all()]

    async def created_before(self, cutoff: datetime) -> list[StoredFile]:
        rows = await self._db.scalars(
            select(StoredFileModel)
            .where(StoredFileModel.created < cutoff)
            .order_by(StoredFileModel.id)
        )
        return [entity_from_row(StoredFile, r) for r in rows.all()]

    async def lock(self, file_id: int) -> StoredFile | None:
        # On Postgres a transaction that is writing a reference to the file
        # holds a key share lock on its row; SKIP LOCKED passes over it
        # instead of waiting. SQLite has one writer and ignores the clause.
        row = await self._db.scalar(
            select(StoredFileModel)
            .where(StoredFileModel.id == file_id)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        return entity_from_row(StoredFile, row) if row is not None else None

    async def delete(self, file: StoredFile, *, content: bool = True) -> None:
        row = await self._db.get(StoredFileModel, file.id)
        if row is None:
            return
        await self._db.delete(row)
        await self._db.flush()
        if content:
            await self.delete_content(file)

    async def delete_content(self, file: StoredFile) -> None:
        if self._content.provider != "postgres":
            await self._content.delete(content_ref(file))
            await self._content.delete(content_ref(file, thumbnail=True))
