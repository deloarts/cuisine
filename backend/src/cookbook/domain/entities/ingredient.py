"""
An ingredient of the shared catalogue: its name in each content locale, its
nutrition per 100 g, the conversions that turn its units into grams and its
allergens. Recipes refer to it from their steps.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import NutritionSource
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.shared_kernel.domain.entities.base import Entity


@dataclass(frozen=True)
class UnitConversion:
    """How many grams one of `unit_id` weighs, such as one egg = 55 g."""

    unit_id: int
    grams: float


@dataclass(kw_only=True)
class Ingredient(Entity):
    # None once the creating account was deleted.
    owner_id: int | None
    original_locale: str
    created: datetime
    changed: datetime
    translations: dict[str, IngredientText] = field(default_factory=dict)
    category_id: int | None = None
    family_id: int | None = None
    # Other names per locale next to the main name, such as "Tomaten" for
    # "Paradeiser". Search, pickers and name matching use them; display
    # uses the main name.
    aliases: dict[str, list[str]] = field(default_factory=dict)
    nutrition: Nutrition = field(default_factory=Nutrition)
    # Extended nutrients per 100 g by catalogue key (`nutrients.py`), such
    # as {"vitamin_c_mg": 19.7}; a missing key is unknown.
    extended_nutrition: dict[str, float] = field(default_factory=dict)
    # The months (1 to 12) when it is in season in Austria; empty means not
    # seasonal.
    season_months: list[int] = field(default_factory=list)
    # Grams per millilitre, for volume units; water is 1.0.
    density_g_per_ml: float | None = None
    conversions: list[UnitConversion] = field(default_factory=list)
    allergens: list[Allergen] = field(default_factory=list)
    diet_markers: list[DietMarker] = field(default_factory=list)
    status: IngredientStatus = IngredientStatus.ACTIVE
    nutrition_source: NutritionSource = NutritionSource.MANUAL
    # The FoodData Central id the nutrition was taken from.
    usda_fdc_id: int | None = None
    # The reference data key the record was seeded from, if any.
    seed_key: str | None = None

    def grams_per_unit(self, unit_id: int) -> float | None:
        for conversion in self.conversions:
            if conversion.unit_id == unit_id:
                return conversion.grams
        return None
