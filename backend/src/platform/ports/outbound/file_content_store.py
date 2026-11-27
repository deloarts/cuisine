"""
The port for the bytes of stored files. The metadata of every file lives in
the database whatever the provider; a content store only keeps, returns and
removes the bytes of one variant of one file. The provider is chosen by
STORAGE__PROVIDER, and the storage CLI copies content between providers.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

ORIGINAL = "original"
THUMBNAIL = "thumbnail"
VARIANTS = (ORIGINAL, THUMBNAIL)


@dataclass(frozen=True)
class ContentRef:
    """One variant of one stored file. The database provider keys content by
    the file's row id, the object stores by `key`, which is built from the
    public id so it never reveals a sequential id."""

    file_id: int
    public_id: UUID
    variant: str = ORIGINAL

    @property
    def key(self) -> str:
        return f"files/{self.public_id}/{self.variant}"


@dataclass(frozen=True)
class ContentUrl:
    """A short-lived URL the browser loads the content from directly."""

    url: str


class IFileContentStore(Protocol):
    # The provider name, as STORAGE__PROVIDER spells it.
    provider: str

    async def put(self, ref: ContentRef, data: bytes, content_type: str) -> None:
        """Writes the content, replacing what the ref held before."""
        ...

    async def get(self, ref: ContentRef) -> bytes | None:
        """The content, or None when the provider holds none for the ref."""
        ...

    async def delete(self, ref: ContentRef) -> None:
        """Removes the content. A missing ref is no error."""
        ...

    async def exists(self, ref: ContentRef) -> bool: ...

    def url_for(
        self, ref: ContentRef, *, file_name: str, content_type: str, inline: bool
    ) -> ContentUrl | None:
        """A presigned URL when the provider serves content itself, None when
        the backend must stream it."""
        ...

    async def check(self) -> None:
        """Raises when the provider is unreachable or misconfigured."""
        ...
