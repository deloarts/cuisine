from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.common_schema import CategoryRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import PersonRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import RecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import SubRecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import UnitRef
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeSummaryResponse
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import MealPlanScope
from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.domain.value_objects.enums import RestrictionKind
from src.cookbook.domain.value_objects.enums import ShoppingListMode
from src.cookbook.domain.value_objects.enums import SuggestionReason
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema

# ── Cook events ──────────────────────────────────────────────────────


class VariationRef(ResponseSchema):
    id: UUID
    name: str


class CookEventRequest(RequestSchema):
    recipe_id: UUID
    # The variation of the recipe that was cooked, if any.
    variation_id: UUID | None = None
    cooked_on: date
    servings: int = Field(ge=1, le=100)
    note: str = Field(default="", max_length=2000)


class CookEventUpdate(RequestSchema):
    cooked_on: date
    servings: int = Field(ge=1, le=100)
    note: str = Field(default="", max_length=2000)


class CookEventResponse(ResponseSchema):
    id: UUID
    cooked_on: date
    servings: int
    note: str
    user: PersonRef | None
    recipe: RecipeRef | None
    # The variation cooked; null for the recipe itself, or when the
    # variation was deleted or is hidden from the viewer.
    variation: VariationRef | None = None
    is_own: bool
    created: datetime


# ── Meal plan ────────────────────────────────────────────────────────


class MealPlanRequest(RequestSchema):
    plan_date: date
    slot: MealSlot
    recipe_id: UUID | None = None
    title: str = Field(default="", max_length=255)
    servings: int = Field(default=2, ge=1, le=100)
    # The plan a new entry goes to; without it a household member plans in
    # the household's plan. An update keeps the entry in its plan.
    scope: MealPlanScope | None = None


class MealPlanEntryResponse(ResponseSchema):
    id: UUID
    plan_date: date
    slot: str
    servings: int
    title: str
    recipe: RecipeRef | None
    scope: MealPlanScope


class MealPlanSuggestionResponse(ResponseSchema):
    recipe: RecipeSummaryResponse
    # The signal that weighed most in the ranking, for a small label.
    reason: SuggestionReason


class MealPlanToListRequest(RequestSchema):
    date_from: date
    date_to: date
    list_id: UUID
    # "I'll buy it": sub-recipes added as one item each instead of their
    # ingredients, for every planned recipe that uses them directly.
    bought_sub_recipe_ids: list[UUID] = Field(default_factory=list)
    # The plan the range is taken from, as for reading the plan.
    scope: MealPlanScope | None = None


class AddedResponse(ResponseSchema):
    # Lines added to the list or merged into existing ones.
    added: int


# ── Shopping lists ───────────────────────────────────────────────────


class ShoppingListRequest(RequestSchema):
    name: str = Field(min_length=1, max_length=128)
    member_ids: list[UUID] = Field(default_factory=list)


class ShoppingListUpdate(RequestSchema):
    """Only the fields sent change. Anyone on the list renames it and
    switches mode and keep; only the owner changes the members."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    member_ids: list[UUID] | None = None
    mode: ShoppingListMode | None = None
    keep: bool | None = None


class ShoppingListSummaryResponse(ResponseSchema):
    id: UUID
    name: str
    owner: PersonRef | None
    members: list[PersonRef]
    is_owner: bool
    open_count: int
    checked_count: int
    changed: datetime
    mode: ShoppingListMode
    # A member chose to keep this normal list from deleting itself.
    keep: bool
    # The last add, tick, edit or mode change.
    last_activity_at: datetime
    # The UTC day an unused normal list deletes itself on; null when it
    # never does (continuous, kept, the household's list, or switched off).
    deletes_on: date | None


class ShoppingItemResponse(ResponseSchema):
    id: UUID
    ingredient_id: UUID | None
    # The ingredient's name in the viewer's language, or the free text.
    name: str
    text: str
    amount: float | None
    unit: UnitRef | None
    category: CategoryRef | None
    # The ingredient's family, for placing variants next to each other.
    family_id: UUID | None
    checked: bool
    checked_by: PersonRef | None
    checked_at: datetime | None
    # The recipe the item was first added from; null when the viewer may
    # not see it or it was deleted.
    recipe: RecipeRef | None
    # Every recipe the item is for, the first one first: amounts of the same
    # ingredient from several recipes join one item. A recipe the viewer may
    # not see is a placeholder without id and title; a deleted one is left
    # out.
    recipes: list[SubRecipeRef]
    # The sub-recipes between `recipe` and the item, outermost first, for
    # "for Lasagna sheets, in Lasagna". An item without ingredient or text is
    # the last sub-recipe itself, bought as a whole.
    sub_recipe_path: list[SubRecipeRef]
    # One of the viewer's own food restrictions matches this item.
    has_warning: bool


class ShoppingListResponse(ShoppingListSummaryResponse):
    # On a continuous list the checked items are the recently bought ones;
    # each leaves this many hours after its `checked_at`.
    bought_window_hours: int
    items: list[ShoppingItemResponse]


class ShoppingListNoteResponse(ResponseSchema):
    """An idle list the viewer was on deleted itself."""

    id: UUID
    list_name: str
    idle_days: int
    created: datetime


class ShoppingItemRequest(RequestSchema):
    ingredient_id: UUID | None = None
    text: str = Field(default="", max_length=255)
    amount: float | None = Field(default=None, ge=0)
    unit_id: UUID | None = None


class ShoppingItemUpdate(RequestSchema):
    """Only the fields sent change; send amount or unit_id as null to clear."""

    checked: bool | None = None
    text: str | None = Field(default=None, max_length=255)
    amount: float | None = Field(default=None, ge=0)
    unit_id: UUID | None = None


class AddRecipeToListRequest(RequestSchema):
    recipe_id: UUID
    servings: int | None = Field(default=None, ge=1, le=100)
    # "I'll buy it": direct sub-recipes added as one item each instead of
    # their ingredients.
    bought_sub_recipe_ids: list[UUID] = Field(default_factory=list)


class RemovedResponse(ResponseSchema):
    removed: int


# ── Food restrictions ────────────────────────────────────────────────


class FoodRestrictionRequest(RequestSchema):
    """Exactly one of allergen, ingredient_id, ingredient_name and diet; a
    diet goes with kind "diet". An unknown ingredient_name creates a draft
    ingredient of that name."""

    kind: RestrictionKind
    allergen: Allergen | None = None
    ingredient_id: UUID | None = None
    ingredient_name: str | None = Field(default=None, min_length=1, max_length=128)
    diet: Diet | None = None
    # Covers every ingredient of the family.
    family_id: UUID | None = None
    note: str = Field(default="", max_length=255)


class FoodRestrictionResponse(ResponseSchema):
    id: UUID
    kind: str
    allergen: str | None
    ingredient_id: UUID | None
    ingredient_name: str | None
    diet: str | None
    family_id: UUID | None
    family_name: str | None
    note: str
    created: datetime


# ── Home ─────────────────────────────────────────────────────────────


class FoodFactResponse(ResponseSchema):
    """The food fact of the day, about one base ingredient."""

    key: str
    text: str
    # The content locale the text is in: the viewer's when it exists.
    locale: str
    ingredient_id: UUID
    ingredient_name: str
    # The Wikipedia article that backs the fact.
    source_title: str
    source_url: str


class HomeResponse(ResponseSchema):
    # Null when no fact's ingredient is in the catalogue.
    food_fact: FoodFactResponse | None
    on_this_day: list[CookEventResponse]
    recently_cooked: list[CookEventResponse]
    favourites: list[RecipeSummaryResponse]
    newest: list[RecipeSummaryResponse]
    # Published recipes in season this month, recently changed first.
    in_season: list[RecipeSummaryResponse]
