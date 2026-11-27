from datetime import datetime
from uuid import UUID

from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class StoredFileResponse(ResponseSchema):
    id: UUID
    file_name: str
    content_type: str
    size: int
    width: int | None
    height: int | None
    has_thumbnail: bool
    created: datetime
