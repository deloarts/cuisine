"""
Shared identity fields for domain entities backed by a database row.
No SQLAlchemy, no Pydantic, no FastAPI, kept dependency-free like every
other file in this package.
"""

from dataclasses import dataclass
from dataclasses import field
from uuid import UUID
from uuid import uuid4


@dataclass(kw_only=True)
class Entity:
    # 0 until the repository has saved the entity and loaded the database id.
    id: int = 0
    # The opaque identifier the API exposes instead of the sequential id. It
    # is generated here, so an entity has it before its first save, and a
    # repository never rewrites it on update.
    public_id: UUID = field(default_factory=uuid4)
