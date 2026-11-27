from uuid import UUID

from pydantic import Field

from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class NameTextSchema(RequestSchema):
    name: str = Field(min_length=1, max_length=64)


class UnitTextSchema(RequestSchema):
    name: str = Field(min_length=1, max_length=64)
    plural_name: str = Field(default="", max_length=64)
    abbreviation: str = Field(default="", max_length=16)


class UnitRequest(RequestSchema):
    code: str = Field(min_length=1, max_length=32)
    kind: UnitKind
    to_base: float | None = Field(default=None, gt=0)
    sort_order: int = 0
    translations: dict[ContentLocale, UnitTextSchema]


class UnitResponse(ResponseSchema):
    id: UUID
    # From the reference seed; seeded units are never deleted, and no
    # seeded row comes back once deleted.
    seeded: bool
    code: str
    kind: str
    to_base: float | None
    sort_order: int
    # Resolved for the viewer's language.
    name: str
    plural_name: str
    abbreviation: str
    translations: dict[str, UnitTextSchema]


class TagRequest(RequestSchema):
    kind: TagKind
    color: str | None = Field(default=None, max_length=16)
    translations: dict[ContentLocale, NameTextSchema]


class TagResponse(ResponseSchema):
    id: UUID
    # From the reference seed; seeded units are never deleted, and no
    # seeded row comes back once deleted.
    seeded: bool
    kind: str
    color: str | None
    name: str
    translations: dict[str, NameTextSchema]


class FamilyRequest(RequestSchema):
    translations: dict[ContentLocale, NameTextSchema]


class FamilyResponse(ResponseSchema):
    id: UUID
    # From the reference seed; seeded units are never deleted, and no
    # seeded row comes back once deleted.
    seeded: bool
    name: str
    translations: dict[str, NameTextSchema]


class CategoryRequest(RequestSchema):
    sort_order: int = 0
    translations: dict[ContentLocale, NameTextSchema]


class CategoryResponse(ResponseSchema):
    id: UUID
    # From the reference seed; seeded units are never deleted, and no
    # seeded row comes back once deleted.
    seeded: bool
    sort_order: int
    name: str
    translations: dict[str, NameTextSchema]


class UsageCount(ResponseSchema):
    id: UUID
    usage_count: int


class ResourceUsageResponse(ResponseSchema):
    """How often each resource is used. Tags, units and equipment count the
    recipes the viewer may see that use them, each recipe once; categories
    and families count the ingredients in them. Every item is listed, zero
    included."""

    tags: list[UsageCount]
    units: list[UsageCount]
    categories: list[UsageCount]
    families: list[UsageCount]
    equipment: list[UsageCount]
