from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.common_schema import EquipmentRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import RecipeRef
from src.cookbook.adapters.inbound.api.schemas.resource_schema import NameTextSchema
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class EquipmentRequest(RequestSchema):
    kind: EquipmentKind
    translations: dict[ContentLocale, NameTextSchema]
    # Other names per locale; every name and alias must be free across the
    # catalogue's ingredient, family and equipment names (409 otherwise).
    aliases: dict[ContentLocale, list[str]] = Field(default_factory=dict)
    # An @mdi/font icon name without the "mdi-" prefix, such as "pot".
    icon: str | None = Field(default=None, max_length=64)
    # Pre-ticked when a kitchen is set up.
    basic: bool = False


class EquipmentResponse(ResponseSchema):
    id: UUID
    name: str
    # The locale the name is served in.
    locale: str
    available_locales: list[str]
    kind: str
    icon: str | None
    basic: bool
    status: str
    seeded: bool
    aliases: dict[str, list[str]]
    translations: dict[str, NameTextSchema]
    changed: datetime


class EquipmentDeletionImpact(ResponseSchema):
    seeded: bool
    recipe_count: int
    # The recipes the viewer can see among those naming the item.
    recipes: list[RecipeRef]
    can_merge: bool


class EquipmentDuplicate(ResponseSchema):
    id: UUID
    name: str
    matched: str
    exact: bool


class KitchenRequest(RequestSchema):
    equipment_ids: list[UUID]


class KitchenSetupRequest(RequestSchema):
    # Null ticks the catalogue's basic items.
    equipment_ids: list[UUID] | None = None


class KitchenResponse(ResponseSchema):
    """The viewer's kitchen. Before set-up `set_up` is false, the list is
    empty and no recipe is flagged."""

    set_up: bool
    # The kitchen is the household's, shared by every member.
    household: bool
    equipment: list[EquipmentRef]
    changed: datetime | None
