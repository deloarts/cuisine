"""
Declarative base for all ORM models, with a naming convention so every
constraint has a stable name across Postgres and SQLite.
"""

import uuid

from sqlalchemy import MetaData
from sqlalchemy import Uuid
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class PublicIdMixin:
    # Globally unique, opaque row identifier, safe to expose in the API
    # without leaking the sequential id. The domain entity generates it, so
    # it exists before the first save; never put it in an update payload.
    public_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), nullable=False, unique=True, index=True, default=uuid.uuid4
    )
