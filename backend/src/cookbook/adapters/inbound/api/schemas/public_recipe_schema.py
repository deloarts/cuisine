"""What the public recipe pages read without signing in. Each schema holds
exactly what the page shows: no internal ids, no ids of steps, lines,
ingredients, units or equipment, no owner id or e-mail address, no visibility
and nothing of the personal layer. The ids left are the recipe's public id
(its page), the public ids of images (served only in display size through
the public image route) and of tags (the tag filter)."""

from datetime import datetime
from uuid import UUID

from src.cookbook.adapters.inbound.api.schemas.common_schema import NutritionSchema
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import ExtendedNutrientAmount
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class PublicTag(ResponseSchema):
    id: UUID
    kind: str
    name: str
    color: str | None


class PublicUnit(ResponseSchema):
    kind: str
    name: str
    plural_name: str
    abbreviation: str


class PublicSubRecipe(ResponseSchema):
    """A recipe used inside another. One the visitor may not see comes
    without id and title, and still counts for allergens and nutrition."""

    id: UUID | None
    title: str | None
    accessible: bool
    cover_image_id: UUID | None


class PublicIngredientLine(ResponseSchema):
    name: str
    amount: float | None
    unit: PublicUnit | None
    note: str = ""
    # Set for a sub-recipe line instead of an ingredient.
    sub_recipe: PublicSubRecipe | None = None


class PublicStepEquipment(ResponseSchema):
    name: str
    count: int | None
    note: str = ""


class PublicStep(ResponseSchema):
    """A step. Mentions in `text` are rewritten for the visitor: an
    ingredient or equipment item carries its current name and the zero id, a
    public sub-recipe its title and public id, and a sub-recipe the visitor
    may not see the name `?` and the zero id, which the page shows as a
    placeholder."""

    position: int
    text: str
    duration_minutes: int | None
    image_id: UUID | None
    ingredients: list[PublicIngredientLine]
    equipment: list[PublicStepEquipment]


class PublicSubRecipeNeed(ResponseSchema):
    sub_recipe: PublicSubRecipe
    amount: float | None
    unit: PublicUnit | None
    batches: float


class PublicEquipmentNeed(ResponseSchema):
    name: str
    count: int | None


class PublicNutrition(ResponseSchema):
    total: NutritionSchema
    per_serving: NutritionSchema
    complete: bool
    extended: list[ExtendedNutrientAmount]


class PublicRecipeSummaryResponse(ResponseSchema):
    id: UUID
    title: str
    description_text: str
    locale: str
    available_locales: list[str]
    cover_image_id: UUID | None
    base_servings: int
    prep_minutes: int | None
    cook_minutes: int | None
    rest_minutes: int | None
    total_minutes: int | None
    difficulty: str
    tags: list[PublicTag]
    allergens: list[str]
    diets: list[str]
    season_months: list[int]
    in_season: bool
    # The owner's display name, only when the owner shows it on public
    # recipes; null otherwise.
    author: str | None
    # Whether GET /api/v1/public/recipes/{id}/author-avatar serves the
    # author's picture, under the same rule as the name.
    author_avatar: bool = False
    published_at: datetime | None


class PublicRecipeDetailResponse(PublicRecipeSummaryResponse):
    description: str
    tips: str
    yield_amount: float | None
    yield_unit: PublicUnit | None
    servings: int
    ingredients: list[PublicIngredientLine]
    needs: list[PublicSubRecipeNeed]
    equipment: list[PublicEquipmentNeed]
    steps: list[PublicStep]
    nutrition: PublicNutrition
    source_name: str | None
    source_url: str | None
