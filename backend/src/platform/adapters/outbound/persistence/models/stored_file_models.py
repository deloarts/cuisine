"""
The database-backed file storage. The bytes live in a table of their own,
keyed by file and variant, so the metadata table stays small and a listing
or an ETag check never reads content.
"""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class StoredFileModel(PublicIdMixin, Base):
    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(127), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creator_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class StoredFileContentModel(Base):
    __tablename__ = "stored_file_contents"

    file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stored_files.id", ondelete="CASCADE"), primary_key=True
    )
    # "original" or "thumbnail".
    variant: Mapped[str] = mapped_column(String(16), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
