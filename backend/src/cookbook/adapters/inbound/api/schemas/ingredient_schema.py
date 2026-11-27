from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.common_schema import CategoryRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import FamilyRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import NutritionSchema
from src.cookbook.adapters.inbound.api.schemas.common_schema import PersonRef
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import NutritionSource
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class IngredientTextSchema(RequestSchema):
    name: str = Field(min_length=1, max_length=128)
    # Defaults to the name when empty.
    plural_name: str = Field(default="", max_length=128)


class NutritionRequest(RequestSchema):
    kcal: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0)
    fat: float | None = Field(default=None, ge=0)
    saturated_fat: float | None = Field(default=None, ge=0)
    carbohydrates: float | None = Field(default=None, ge=0)
    sugar: float | None = Field(default=None, ge=0)
    fibre: float | None = Field(default=None, ge=0)
    salt: float | None = Field(default=None, ge=0)


class ConversionRequest(RequestSchema):
    unit_id: UUID
    grams: float = Field(gt=0)


class IngredientRequest(RequestSchema):
    original_locale: ContentLocale
    translations: dict[ContentLocale, IngredientTextSchema]
    category_id: UUID | None = None
    family_id: UUID | None = None
    # Other names per locale (search, pickers, matching); each must be free
    # across main names and aliases in its locale (409 otherwise).
    aliases: dict[ContentLocale, list[str]] = Field(default_factory=dict)
    nutrition: NutritionRequest = Field(default_factory=NutritionRequest)
    # Extended nutrients per 100 g by the keys of GET /nutrition/nutrients
    # (422 for any other key); null or absent means unknown.
    extended_nutrition: dict[str, Annotated[float, Field(ge=0)] | None] = Field(
        default_factory=dict
    )
    # The months when the ingredient is in season in Austria; empty means
    # not seasonal.
    season_months: list[Annotated[int, Field(ge=1, le=12)]] = Field(default_factory=list)
    density_g_per_ml: float | None = Field(default=None, gt=0)
    conversions: list[ConversionRequest] = Field(default_factory=list)
    allergens: list[Allergen] = Field(default_factory=list)
    diet_markers: list[DietMarker] = Field(default_factory=list)
    nutrition_source: NutritionSource = NutritionSource.MANUAL
    usda_fdc_id: int | None = None


class ConversionResponse(ResponseSchema):
    unit_id: UUID
    unit_code: str
    unit_name: str
    grams: float


class IngredientResponse(ResponseSchema):
    id: UUID
    name: str
    plural_name: str
    # The locale the name is served in, which falls back to the original.
    locale: str
    original_locale: str
    available_locales: list[str]
    category: CategoryRef | None
    family: FamilyRef | None
    aliases: dict[str, list[str]]
    nutrition: NutritionSchema
    # Extended nutrients per 100 g by catalogue key; a missing key is unknown.
    extended_nutrition: dict[str, float]
    season_months: list[int]
    density_g_per_ml: float | None
    conversions: list[ConversionResponse]
    allergens: list[str]
    diet_markers: list[str]
    status: str
    nutrition_source: str
    usda_fdc_id: int | None
    owner: PersonRef | None
    can_edit: bool
    changed: datetime
    # In a list with `search`: the alias that matched when no main name did.
    matched_alias: str | None = None


class IngredientListItem(IngredientResponse):
    # How many recipes the viewer may see use the ingredient, in a step or
    # in the declared list, each recipe once.
    usage_count: int


class IngredientDetailResponse(IngredientResponse):
    translations: dict[str, IngredientTextSchema]
    recipe_count: int


class FoodMatchResponse(ResponseSchema):
    fdc_id: int
    description: str
    data_type: str
    brand: str | None
    nutrition: NutritionSchema
    extended_nutrition: dict[str, float]


class ExtendedNutrientResponse(ResponseSchema):
    """One entry of the extended nutrient catalogue. The amount is per
    100 g in `unit` (mg, ug or g); `label_key` names the label in the
    frontend's locale files."""

    key: str
    unit: str
    label_key: str
    usda_nutrient_id: int


class DuplicateCandidate(ResponseSchema):
    id: UUID
    # The ingredient's main name.
    name: str
    # The name or alias that matched.
    matched: str
    # The same name or alias apart from case, diacritics and spacing.
    exact: bool
