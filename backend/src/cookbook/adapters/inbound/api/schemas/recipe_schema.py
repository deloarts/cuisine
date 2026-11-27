from datetime import date
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.common_schema import EquipmentRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import NutritionSchema
from src.cookbook.adapters.inbound.api.schemas.common_schema import PersonRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import RecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import SubRecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import TagRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import UnitRef
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class BasedOnRef(ResponseSchema):
    """The recipe a copy was made from: with link, title and owner when the
    viewer may see it, as an anonymous placeholder otherwise."""

    recipe: SubRecipeRef
    owner: PersonRef | None


class PeerRef(ResponseSchema):
    """A paired instance, by its public id here."""

    id: UUID
    name: str


class MirrorSourceRef(ResponseSchema):
    """Where a mirror comes from, for cards: "by <author> · <instance>"."""

    instance_name: str
    # The author's display name there; null when the author does not show it.
    author_name: str | None
    # The avatar the source sent with the name, as a file here.
    author_avatar_id: UUID | None = None


class MirrorPlainLine(ResponseSchema):
    """An ingredient line of a mirror kept as text, with the source's
    allergens and diet markers. `step` is the index of its step (from 0) and
    `position` its place among that step's ingredient lines as the source
    has them."""

    step: int
    position: int
    name: str
    # Scaled to the servings of the response.
    amount: float | None
    unit: UnitRef | None
    note: str
    allergens: list[str]
    diet_markers: list[str]


class MirrorPlainEquipment(ResponseSchema):
    step: int
    name: str
    count: int | None
    note: str


class MirrorUnlinkedSubRecipe(ResponseSchema):
    """A sub-recipe line whose sub-recipe is not mirrored here (not shared
    with this instance, or not accepted yet); `title` only when the source
    shares that sub-recipe with this instance too."""

    step: int
    position: int
    title: str | None
    amount: float | None
    unit: UnitRef | None


class MirrorView(ResponseSchema):
    """A mirror of a recipe a paired instance shares with this one. It is
    read only; `source_url` opens it at its source."""

    peer: PeerRef
    instance_name: str
    author_name: str | None
    author_avatar_id: UUID | None = None
    source_url: str
    source_revision: str
    accepted_at: datetime
    updated_at: datetime
    plain_lines: list[MirrorPlainLine]
    plain_equipment: list[MirrorPlainEquipment]
    unlinked_sub_recipes: list[MirrorUnlinkedSubRecipe]


# ── Editing ──────────────────────────────────────────────────────────


class RecipeTextSchema(RequestSchema):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10_000)
    tips: str = Field(default="", max_length=10_000)


class StepTextSchema(RequestSchema):
    text: str = Field(min_length=1, max_length=10_000)


class NoteTextSchema(RequestSchema):
    note: str = Field(max_length=255)


class StepIngredientRequest(RequestSchema):
    """A catalogue ingredient or a sub-recipe, exactly one. A sub-recipe's
    amount is in its yield unit (scaled by amount / yield) or, without one,
    in servings of the sub-recipe."""

    # The line's own id from the editor response; a save keeps it when the
    # recipe has this line, and gives a new or unknown line a fresh one.
    id: UUID | None = None
    ingredient_id: UUID | None = None
    sub_recipe_id: UUID | None = None
    # Null means "to taste".
    amount: float | None = Field(default=None, ge=0)
    unit_id: UUID | None = None
    notes: dict[ContentLocale, NoteTextSchema] = Field(default_factory=dict)


class StepEquipmentRequest(RequestSchema):
    # Kept like the id of a step ingredient.
    id: UUID | None = None
    equipment_id: UUID
    # How many the step needs, such as 2 bowls; null for one or unspecified.
    count: int | None = Field(default=None, ge=1, le=100)
    # Such as "26 cm" or "200 °C fan".
    notes: dict[ContentLocale, NoteTextSchema] = Field(default_factory=dict)


class StepRequest(RequestSchema):
    # Kept like the id of a step ingredient.
    id: UUID | None = None
    translations: dict[ContentLocale, StepTextSchema]
    duration_minutes: int | None = Field(default=None, ge=0, le=10_000)
    image_id: UUID | None = None
    ingredients: list[StepIngredientRequest] = Field(default_factory=list)
    equipment: list[StepEquipmentRequest] = Field(default_factory=list)


class RecipeRequest(RequestSchema):
    original_locale: ContentLocale
    translations: dict[ContentLocale, RecipeTextSchema]
    base_servings: int = Field(default=4, ge=1, le=100)
    prep_minutes: int | None = Field(default=None, ge=0, le=10_000)
    cook_minutes: int | None = Field(default=None, ge=0, le=10_000)
    rest_minutes: int | None = Field(default=None, ge=0, le=10_000)
    difficulty: Difficulty = Difficulty.EASY
    cover_image_id: UUID | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    source_name: str | None = Field(default=None, max_length=255)
    tag_ids: list[UUID] = Field(default_factory=list)
    steps: list[StepRequest] = Field(default_factory=list)
    # The ingredient list declared for the whole recipe, in its order. The
    # recipe's derived list takes the larger of it and what the steps use.
    ingredients: list[StepIngredientRequest] = Field(default_factory=list, max_length=200)
    # What one batch makes, such as 500 g: both or neither.
    yield_amount: float | None = Field(default=None, gt=0)
    yield_unit_id: UUID | None = None
    # Only the owner's values count, and only when the privacy settings let
    # users choose; null keeps the current visibility (the default on create).
    # "peers" needs peering on and "public" public recipes allowed (422
    # PeerRecipesNotAllowedError, PublicRecipesNotAllowedError), unless the
    # recipe has that value already; neither is possible on a copy of a
    # recipe from another instance (422 PeerShareNotAllowedError).
    visibility: RecipeVisibility | None = None
    shared_user_ids: list[UUID] | None = None
    shared_group_ids: list[UUID] | None = None
    # Paired instances the recipe goes to, inside "shared" (only the owner,
    # only while peering is on and the instance lets users share with them;
    # never for a copy of a mirror).
    shared_peer_ids: list[UUID] | None = None
    # A short note on the revision this save records ("less salt").
    revision_note: str | None = Field(default=None, max_length=255)


class StepIngredientEdit(ResponseSchema):
    id: UUID
    ingredient_id: UUID | None
    sub_recipe_id: UUID | None
    # The ingredient's or sub-recipe's name; empty for a sub-recipe the
    # viewer can no longer see.
    ingredient_name: str
    amount: float | None
    unit_id: UUID | None
    notes: dict[str, NoteTextSchema]


class StepEquipmentEdit(ResponseSchema):
    id: UUID
    equipment_id: UUID
    equipment_name: str
    count: int | None
    notes: dict[str, NoteTextSchema]


class StepEdit(ResponseSchema):
    id: UUID
    translations: dict[str, StepTextSchema]
    duration_minutes: int | None
    image_id: UUID | None
    ingredients: list[StepIngredientEdit]
    equipment: list[StepEquipmentEdit]


class RecipeEditResponse(ResponseSchema):
    """The recipe as the editor works on it: every language, every id."""

    id: UUID
    status: str
    original_locale: str
    translations: dict[str, RecipeTextSchema]
    base_servings: int
    prep_minutes: int | None
    cook_minutes: int | None
    rest_minutes: int | None
    difficulty: str
    cover_image_id: UUID | None
    source_url: str | None
    source_name: str | None
    tag_ids: list[UUID]
    steps: list[StepEdit]
    # The declared ingredient list, in its order.
    ingredients: list[StepIngredientEdit]
    yield_amount: float | None
    yield_unit_id: UUID | None
    # Direct sub-recipes some reader of this recipe may not see (drafts or
    # narrower visibility); publishing should warn about them.
    less_visible_sub_recipe_ids: list[UUID]
    # The stored visibility, as the owner chose it.
    visibility: str
    # The visibility that applies: "public" reads as "instance" while the
    # instance does not allow public recipes, "peers" while peering is off.
    effective_visibility: str
    shared_user_ids: list[UUID]
    shared_group_ids: list[UUID]
    shared_peers: list[PeerRef] = Field(default_factory=list)
    # A copy of a mirror (or of such a copy): never public, never shared
    # with a paired instance.
    peer_capped: bool = False
    # Direct sub-recipes that do not go to every paired instance this
    # recipe goes to; those instances show them without a title.
    peer_hidden_sub_recipe_ids: list[UUID] = Field(default_factory=list)
    # Whether the viewer may change the visibility (the owner, when the
    # privacy settings let users choose).
    can_change_visibility: bool
    created_via: str
    owner: PersonRef | None
    can_edit: bool
    # Owner or manage:recipes: delete, publish and unpublish. Co-editors
    # edit the content only.
    can_delete: bool
    # The people the owner lets edit the content; only the owner changes
    # them (`can_manage_co_editors`).
    co_editors: list[PersonRef]
    can_manage_co_editors: bool
    based_on: BasedOnRef | None
    created: datetime
    changed: datetime
    published_at: datetime | None


class TranslationRequest(RequestSchema):
    """One language of a recipe: its text, each step's text in order and,
    optionally, each step ingredient's note per step and each declared
    ingredient line's note in order."""

    locale: ContentLocale
    text: RecipeTextSchema
    steps: list[StepTextSchema] = Field(default_factory=list)
    notes: list[list[NoteTextSchema]] | None = None
    ingredient_notes: list[NoteTextSchema] | None = None


# ── Reading ──────────────────────────────────────────────────────────


class RecipeSummaryResponse(ResponseSchema):
    id: UUID
    title: str
    # The Markdown subset the editor writes (bold, italic, lists, breaks).
    description: str
    # The same without marks, on one line, for cards and snippets.
    description_text: str
    locale: str
    original_locale: str
    available_locales: list[str]
    status: str
    # The stored visibility, and the one that applies ("public" reads as
    # "instance" while the instance does not allow public recipes, "peers"
    # while peering is off).
    visibility: str
    effective_visibility: str
    cover_image_id: UUID | None
    base_servings: int
    prep_minutes: int | None
    cook_minutes: int | None
    rest_minutes: int | None
    total_minutes: int | None
    difficulty: str
    tags: list[TagRef]
    allergens: list[str]
    # The diets the recipe's ingredients fit, from their diet markers.
    diets: list[str]
    rating_average: float | None
    rating_count: int
    is_favourite: bool
    # One of the viewer's own food restrictions matches. Only the viewer
    # sees this; it never says which restriction.
    has_warning: bool
    # With `guests` given: the recipe conflicts with a restriction of at
    # least one guest. Never which guest or which restriction.
    unsuitable_for_guests: bool
    # The months in which every seasonal ingredient (sub-recipes included)
    # is in season; empty when the recipe uses no seasonal ingredient.
    season_months: list[int]
    # In season in the current month.
    in_season: bool
    # Only once the viewer's kitchen is set up (null before): the equipment
    # of the recipe and its sub-recipes the kitchen lacks, and whether it
    # lacks nothing.
    missing_equipment: list[EquipmentRef] | None
    kitchen_ready: bool | None
    # The variations of the recipe the viewer may see.
    variation_count: int
    # With `guests`: the recipe conflicts with a guest, but a variation the
    # viewer may see does not.
    variation_fits_guests: bool
    # With `diets`: the recipe misses a wanted diet, but a variation the
    # viewer may see fits them all.
    variation_fits_diets: bool
    can_edit: bool
    owner: PersonRef | None
    created_via: str
    last_cooked: date | None
    created: datetime
    changed: datetime
    # Set for a mirror of a recipe a paired instance shares with this one.
    mirror: MirrorSourceRef | None = None
    # Never public and never shared with a paired instance: a mirror or a
    # copy of one.
    peer_capped: bool = False


class IngredientAmount(ResponseSchema):
    """A catalogue ingredient (`ingredient_id`) or a sub-recipe
    (`sub_recipe`)."""

    ingredient_id: UUID | None
    sub_recipe: SubRecipeRef | None = None
    # Singular or plural, whichever the amount needs; the sub-recipe's title,
    # or empty when the viewer may not see it.
    name: str
    amount: float | None
    unit: UnitRef | None
    note: str
    category_id: UUID | None = None
    # The step line's own id; null in the recipe's summed ingredient list.
    line_id: UUID | None = None


class StepEquipmentView(ResponseSchema):
    id: UUID
    equipment: EquipmentRef
    count: int | None
    note: str


class StepView(ResponseSchema):
    id: UUID
    position: int
    text: str
    duration_minutes: int | None
    image_id: UUID | None
    ingredients: list[IngredientAmount]
    equipment: list[StepEquipmentView]


class EquipmentNeed(ResponseSchema):
    """One line of "You'll need": the highest count a single step names,
    and the sub-recipe whose steps need it (null for the recipe's own)."""

    equipment: EquipmentRef
    count: int | None
    sub_recipe: SubRecipeRef | None
    # Null before the viewer's kitchen is set up.
    missing: bool | None


class ExtendedNutrientAmount(ResponseSchema):
    """An extended nutrient summed over the recipe (`total` for the
    servings asked for). `complete` is false when an amount could not be
    weighed or a counted ingredient does not state this nutrient."""

    key: str
    unit: str
    total: float
    per_serving: float
    complete: bool


class NutritionView(ResponseSchema):
    total: NutritionSchema
    per_serving: NutritionSchema
    complete: bool
    missing_ingredient_ids: list[UUID]
    # The extended nutrients at least one ingredient states, in catalogue
    # order.
    extended: list[ExtendedNutrientAmount]


class WarningView(ResponseSchema):
    restriction_id: UUID
    kind: str
    allergen: str | None
    ingredient_id: UUID | None
    diet: str | None
    family_id: UUID | None
    ingredient_names: list[str]


class OwnRating(ResponseSchema):
    stars: int
    comment: str


class SubRecipeNeed(ResponseSchema):
    """A sub-recipe the recipe needs: the line's amount scaled to the
    servings, and how many batches of the sub-recipe that is."""

    sub_recipe: SubRecipeRef
    amount: float | None
    unit: UnitRef | None
    batches: float


class RecipeDetailResponse(RecipeSummaryResponse):
    tips: str
    yield_amount: float | None
    yield_unit: UnitRef | None
    needs: list[SubRecipeNeed]
    # "You'll need": the recipe's equipment first, then each sub-recipe's.
    equipment: list[EquipmentNeed]
    source_url: str | None
    source_name: str | None
    # The servings the amounts below are scaled to.
    servings: int
    ingredients: list[IngredientAmount]
    steps: list[StepView]
    nutrition: NutritionView
    warnings: list[WarningView]
    own_rating: OwnRating | None
    own_note: str | None
    last_cooked_by_me: date | None
    # Owner or manage:recipes; co-editors may edit but not delete.
    can_delete: bool
    # The recipe this one was copied from, if any.
    based_on: BasedOnRef | None
    # The copies of this recipe the viewer may see.
    based_on_count: int
    # The ratings of the recipe and all its variations together;
    # `rating_average` is the recipe's own.
    rating_overall_average: float | None
    rating_overall_count: int
    # For a mirror: its source, plain-text lines and sub-recipes not
    # mirrored here.
    mirror_details: MirrorView | None = None
    # Allergens that only the source's data added (the local catalogue does
    # not name them); the page says so.
    source_allergens_added: list[str] = Field(default_factory=list)
    # Allergens and diet markers from the source this release does not
    # know: "contains <value> (unknown)". The recipe then claims no diet.
    unknown_allergens: list[str] = Field(default_factory=list)
    unknown_diet_markers: list[str] = Field(default_factory=list)
    # Draft ingredients the recipe uses, through its sub-recipes too. Their
    # markers wait for a person to confirm them, so the recipe claims no
    # diet until every one is activated.
    unconfirmed_ingredient_ids: list[UUID] = Field(default_factory=list)


# ── Step image library ───────────────────────────────────────────────


class StepImageResponse(ResponseSchema):
    """An image a step of a visible recipe shows, offered for another step.
    `step_number` counts from 1 and `step_text` is that step's text in the
    viewer's language without marks or mentions. `matches` counts the
    ingredients and equipment items the step shares with the step being
    edited."""

    image_id: UUID
    recipe: RecipeRef
    step_number: int
    step_text: str
    matches: int


# ── Revisions ────────────────────────────────────────────────────────


class RecipeRevisionSummary(ResponseSchema):
    number: int
    # created, updated, translated, image_attached, restored or adopted.
    kind: str
    created: datetime
    created_via: str
    # Null once the author's account was deleted.
    author: PersonRef | None
    note: str | None
    restored_from: int | None
    # On an `adopted` revision: the author of the adopted variation.
    credited_author: PersonRef | None = None


class RecipeRevisionResponse(RecipeRevisionSummary):
    """The revision with its snapshot: the editable recipe in the shape of
    `RecipeEditResponse` (by public id, without status, visibility and
    shares) plus `schema_version` and `names`, the display names per locale
    of every referenced ingredient, unit, tag, equipment item and
    sub-recipe at that moment, by kind and public id."""

    snapshot: dict[str, Any]


# ── Personal ─────────────────────────────────────────────────────────


class FavouriteRequest(RequestSchema):
    favourite: bool


class RatingRequest(RequestSchema):
    stars: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)
    # Rates this variation of the recipe instead of the recipe itself.
    variation_id: UUID | None = None


class RatingResponse(ResponseSchema):
    stars: int
    comment: str
    rating_average: float | None
    rating_count: int


class RatingStatsResponse(ResponseSchema):
    rating_average: float | None
    rating_count: int


class NoteRequest(RequestSchema):
    # An empty text deletes the note.
    text: str = Field(max_length=10_000)


class NoteResponse(ResponseSchema):
    text: str | None
    changed: datetime | None
