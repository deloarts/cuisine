"""
A file kept in the database: its metadata here, its bytes in a table of
their own, so listing files never reads the content. Images are stored as a
re-encoded WebP with a thumbnail; documents are stored as uploaded.
"""

from dataclasses import dataclass
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class StoredFile(Entity):
    file_name: str
    content_type: str
    size: int
    # SHA-256 of the stored bytes, used as the ETag.
    content_hash: str
    created: datetime
    creator_id: int | None = None
    width: int | None = None
    height: int | None = None
    # Present on images only.
    thumbnail_size: int | None = None
    thumbnail_hash: str | None = None
