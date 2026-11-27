"""Sizes of the database and counts of the stored files, for the Storage
and backup tab. Postgres reports table sizes; SQLite only its file size."""

from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.stored_file_models import StoredFileModel
from src.platform.ports.outbound.system_readings import DatabaseReading
from src.platform.ports.outbound.system_readings import FileKindCount
from src.platform.ports.outbound.system_readings import FileReading
from src.platform.ports.outbound.system_readings import TableSize

LARGEST_TABLES = 8


class SqlAlchemyStorageStatsReader:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def database(self) -> DatabaseReading:
        dialect = self._db.bind.dialect.name if self._db.bind else "unknown"
        if dialect == "postgresql":
            size = await self._db.scalar(text("SELECT pg_database_size(current_database())"))
            rows = await self._db.execute(
                text(
                    "SELECT relname, pg_total_relation_size(relid) AS bytes "
                    "FROM pg_catalog.pg_statio_user_tables ORDER BY bytes DESC LIMIT :n"
                ),
                {"n": LARGEST_TABLES},
            )
            tables = [TableSize(name=str(n), bytes=int(b)) for n, b in rows.all()]
            return DatabaseReading(
                dialect=dialect, size_bytes=int(size or 0), largest_tables=tables
            )
        if dialect == "sqlite":
            pages = await self._db.scalar(text("PRAGMA page_count"))
            page_size = await self._db.scalar(text("PRAGMA page_size"))
            return DatabaseReading(
                dialect=dialect, size_bytes=int(pages or 0) * int(page_size or 0)
            )
        return DatabaseReading(dialect=dialect, size_bytes=None)

    async def files(self) -> FileReading:
        kind = case(
            (StoredFileModel.content_type.like("image/%"), "image"),
            (StoredFileModel.content_type == "application/pdf", "pdf"),
            else_="other",
        )
        rows = await self._db.execute(
            select(
                kind,
                func.count(),
                func.coalesce(func.sum(StoredFileModel.size), 0),
                func.coalesce(func.sum(StoredFileModel.thumbnail_size), 0),
            ).group_by(kind)
        )
        by_kind: list[FileKindCount] = []
        count = original = thumbnails = 0
        for name, n, size, thumb in rows.all():
            by_kind.append(FileKindCount(kind=str(name), count=int(n), bytes=int(size)))
            count += int(n)
            original += int(size)
            thumbnails += int(thumb)
        by_kind.sort(key=lambda k: k.kind)
        return FileReading(
            count=count, original_bytes=original, thumbnail_bytes=thumbnails, by_kind=by_kind
        )
