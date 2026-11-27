"""
Kitchen equipment: the shared catalogue of cookware, bakeware, appliances
and utensils that recipe steps name, and a kitchen, the equipment a cook
owns. A kitchen belongs to the household when the cook is in one, so every
member shares and edits it, and to the cook alone otherwise.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import EquipmentStatus
from src.cookbook.domain.value_objects.texts import NameText
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class Equipment(Entity):
    kind: EquipmentKind
    created: datetime
    changed: datetime
    translations: dict[str, NameText] = field(default_factory=dict)
    # Other names per locale; names and aliases share the namespace of
    # ingredient and family names.
    aliases: dict[str, list[str]] = field(default_factory=dict)
    # An icon name of @mdi/font without the "mdi-" prefix, such as "pot".
    icon: str | None = None
    # An everyday item most kitchens have, pre-ticked when a kitchen is set up.
    basic: bool = False
    status: EquipmentStatus = EquipmentStatus.ACTIVE
    seed_key: str | None = None


@dataclass(kw_only=True)
class Kitchen(Entity):
    """Exactly one of `household_id` and `user_id` is set."""

    household_id: int | None = None
    user_id: int | None = None
    equipment_ids: list[int] = field(default_factory=list)
    set_up_at: datetime
    changed: datetime
