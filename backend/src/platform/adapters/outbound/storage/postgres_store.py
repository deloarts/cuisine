"""
The `postgres` provider: content in the `stored_file_contents` table (bytea
on Postgres), keyed by file row and variant, written in the request's own
transaction. Deleting a file row removes its content by cascade, so delete
here only matters for a single variant or the storage CLI.
"""

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.stored_file_models import (
    StoredFileContentModel,
)
from src.platform.ports.outbound.file_content_store import ContentRef
from src.platform.ports.outbound.file_content_store import ContentUrl


class PostgresContentStore:
    provider = "postgres"

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def put(self, ref: ContentRef, data: bytes, content_type: str) -> None:
        row = await self._db.get(StoredFileContentModel, (ref.file_id, ref.variant))
        if row is None:
            self._db.add(
                StoredFileContentModel(file_id=ref.file_id, variant=ref.variant, data=data)
            )
        else:
            row.data = data
        await self._db.flush()

    async def get(self, ref: ContentRef) -> bytes | None:
        data: bytes | None = await self._db.scalar(
            select(StoredFileContentModel.data).where(
                StoredFileContentModel.file_id == ref.file_id,
                StoredFileContentModel.variant == ref.variant,
            )
        )
        return data

    async def delete(self, ref: ContentRef) -> None:
        await self._db.execute(
            delete(StoredFileContentModel).where(
                StoredFileContentModel.file_id == ref.file_id,
                StoredFileContentModel.variant == ref.variant,
            )
        )
        await self._db.flush()

    async def exists(self, ref: ContentRef) -> bool:
        found = await self._db.scalar(
            select(StoredFileContentModel.file_id).where(
                StoredFileContentModel.file_id == ref.file_id,
                StoredFileContentModel.variant == ref.variant,
            )
        )
        return found is not None

    def url_for(
        self, ref: ContentRef, *, file_name: str, content_type: str, inline: bool
    ) -> ContentUrl | None:
        return None

    async def check(self) -> None:
        await self._db.execute(select(1))
