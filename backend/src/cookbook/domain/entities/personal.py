"""
The personal layer: ratings, private cook notes and food restrictions.
Favourites are a plain link and have no entity. Food restrictions are
health data and strictly private to their user.
"""

from dataclasses import dataclass
from datetime import datetime

from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import RestrictionKind
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class Rating(Entity):
    user_id: int
    recipe_id: int
    stars: int
    created: datetime
    changed: datetime
    comment: str = ""
    # Set when the rating is for a variation of the recipe; one rating per
    # user for the recipe itself and one per variation.
    variation_id: int | None = None


@dataclass(kw_only=True)
class CookNote(Entity):
    """A user's own note on a recipe, visible to nobody else."""

    user_id: int
    recipe_id: int
    text: str
    changed: datetime


@dataclass(kw_only=True)
class FoodRestriction(Entity):
    """An allergy, intolerance or diet of one user. An allergy or
    intolerance names one of the declared allergens or one specific
    ingredient; a diet names one of the diets."""

    user_id: int
    kind: RestrictionKind
    created: datetime
    allergen: Allergen | None = None
    ingredient_id: int | None = None
    diet: Diet | None = None
    # Covers every ingredient of the family, also ones added later.
    family_id: int | None = None
    note: str = ""
