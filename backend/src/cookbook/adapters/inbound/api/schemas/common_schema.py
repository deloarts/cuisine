"""Pieces several cookbook schemas share: references to related records and
the nutrition block."""

from uuid import UUID

from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class PersonRef(ResponseSchema):
    id: UUID
    # The nickname when the person chose to go by it, otherwise the full name.
    display_name: str
    # The person's avatar, shown wherever their name is; its thumbnail is
    # served by /api/v1/web/files/{id}/content. Null shows the initials.
    avatar_id: UUID | None = None


class UnitRef(ResponseSchema):
    id: UUID
    code: str
    kind: str
    name: str
    plural_name: str
    abbreviation: str


class TagRef(ResponseSchema):
    id: UUID
    kind: str
    name: str
    color: str | None


class CategoryRef(ResponseSchema):
    id: UUID
    name: str
    sort_order: int


class FamilyRef(ResponseSchema):
    id: UUID
    name: str


class EquipmentRef(ResponseSchema):
    id: UUID
    name: str
    kind: str
    icon: str | None


class RecipeRef(ResponseSchema):
    id: UUID
    title: str
    cover_image_id: UUID | None
    status: str


class SubRecipeRef(ResponseSchema):
    """A recipe used inside another. A sub-recipe the viewer may not see
    comes without id and title ("a recipe you don't have access to"), and
    still counts for allergens and nutrition."""

    id: UUID | None
    title: str | None
    accessible: bool
    total_minutes: int | None
    cover_image_id: UUID | None


class NutritionSchema(ResponseSchema):
    """Energy in kcal, everything else in grams. Null means unknown."""

    kcal: float | None = None
    protein: float | None = None
    fat: float | None = None
    saturated_fat: float | None = None
    carbohydrates: float | None = None
    sugar: float | None = None
    fibre: float | None = None
    salt: float | None = None
