"""
The shared resources recipes and ingredients refer to: units, ingredient
categories and tags. Each is seeded in both content locales and can be
extended by holders of write:resources.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class Unit(Entity):
    # A stable key, such as "g" or "tbsp", which seeds and agents refer to.
    code: str
    kind: UnitKind
    # Grams per unit for mass, millilitres per unit for volume; None for
    # count and other units.
    to_base: float | None
    created: datetime
    translations: dict[str, UnitText] = field(default_factory=dict)
    sort_order: int = 0
    # The reference data key the record was seeded from, if any.
    seed_key: str | None = None


@dataclass(kw_only=True)
class IngredientCategory(Entity):
    created: datetime
    translations: dict[str, NameText] = field(default_factory=dict)
    # The aisle order the shopping list groups items by.
    sort_order: int = 0
    # The reference data key the record was seeded from, if any.
    seed_key: str | None = None


@dataclass(kw_only=True)
class IngredientFamily(Entity):
    """Variants of one food, such as tomatoes: fresh, canned, passata,
    cherry tomatoes. Each member keeps its own nutrition and allergens; a
    food restriction on the family covers every member, also future ones."""

    created: datetime
    translations: dict[str, NameText] = field(default_factory=dict)
    seed_key: str | None = None


@dataclass(kw_only=True)
class Tag(Entity):
    kind: TagKind
    created: datetime
    translations: dict[str, NameText] = field(default_factory=dict)
    # A hex colour such as "#d97706", or None for the default chip colour.
    color: str | None = None
    # The reference data key the record was seeded from, if any.
    seed_key: str | None = None
