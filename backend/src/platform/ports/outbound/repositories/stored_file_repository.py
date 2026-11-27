from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.platform.domain.entities.stored_file import StoredFile
from src.platform.ports.outbound.file_content_store import ContentUrl


class IStoredFileRepository(Protocol):
    """The file storage port. Metadata and content are separate, so listing
    or checking an ETag never reads the bytes; the content goes to the
    active provider's content store."""

    async def get(self, file_id: int) -> StoredFile | None: ...
    async def get_by_public_id(self, public_id: str) -> StoredFile | None: ...
    async def public_ids(self, ids: list[int]) -> dict[int, UUID]: ...
    async def add(self, file: StoredFile, data: bytes, thumbnail: bytes | None) -> StoredFile: ...
    async def read_content(self, file: StoredFile, *, thumbnail: bool = False) -> bytes | None: ...
    def content_url(self, file: StoredFile, *, thumbnail: bool, inline: bool) -> ContentUrl | None:
        """A presigned URL when the provider serves content itself."""
        ...

    async def list_all(self) -> list[StoredFile]: ...
    async def created_before(self, cutoff: datetime) -> list[StoredFile]: ...
    async def lock(self, file_id: int) -> StoredFile | None:
        """Reads the file again and locks its row until the commit, so no
        other transaction can refer to it meanwhile. None when the file is
        gone or another transaction holds the row, which means it is being
        referenced right now."""
        ...

    async def delete(self, file: StoredFile, *, content: bool = True) -> None:
        """Deletes the row and, unless `content` is false, the content. The
        `postgres` provider's content always goes with the row, by cascade."""
        ...

    async def delete_content(self, file: StoredFile) -> None:
        """Deletes the content of a file whose row was deleted with
        `content=False` and committed; nothing to do for `postgres`."""
        ...
