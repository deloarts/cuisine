from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.common_schema import EquipmentRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import PersonRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import RecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import SubRecipeRef
from src.cookbook.adapters.inbound.api.schemas.common_schema import UnitRef
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import OwnRating
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeDetailResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeEditResponse
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import VariationChangeKind
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema

# ── Writing ──────────────────────────────────────────────────────────


class VariationLineRequest(RequestSchema):
    ingredient_id: UUID
    # Null means "to taste".
    amount: float | None = Field(default=None, ge=0)
    unit_id: UUID | None = None
    note: str = Field(default="", max_length=255)


class VariationEquipmentRequest(RequestSchema):
    equipment_id: UUID
    count: int | None = Field(default=None, ge=1, le=100)
    note: str = Field(default="", max_length=255)


class VariationChangeRequest(RequestSchema):
    """One change; which fields count depends on `kind`:

    - `swap`: `ingredient_id` → `to_ingredient_id` in step `step`, or in every
      step with `step` null. `keep_amount` (default) keeps each line's amount,
      unit and note; otherwise `amount`, `unit_id` and `note` replace them.
    - `add_line`: `ingredient_id`, `amount`, `unit_id`, `note` in step `step`.
    - `remove_line`: the lines of step `step` naming `ingredient_id` or
      `sub_recipe_id`.
    - `step_text`: `text` instead of step `step`'s text.
    - `extra_step`: a new step after step `step` (0 puts it first) with
      `text`, `duration_minutes`, `lines` and `equipment`.

    Steps are numbered from 1 as the recipe is now. `id` keeps an existing
    change's id on an update; leave it out for a new change."""

    kind: VariationChangeKind
    id: str | None = Field(default=None, max_length=64)
    step: int | None = Field(default=None, ge=0, le=100)
    ingredient_id: UUID | None = None
    sub_recipe_id: UUID | None = None
    to_ingredient_id: UUID | None = None
    amount: float | None = Field(default=None, ge=0)
    unit_id: UUID | None = None
    keep_amount: bool = True
    note: str = Field(default="", max_length=255)
    text: str = Field(default="", max_length=10_000)
    duration_minutes: int | None = Field(default=None, ge=0, le=10_000)
    lines: list[VariationLineRequest] = Field(default_factory=list, max_length=50)
    equipment: list[VariationEquipmentRequest] = Field(default_factory=list, max_length=50)


class VariationRequest(RequestSchema):
    name: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=1000)
    # The language the name, note and texts are written in.
    locale: ContentLocale
    # Visible to its author only.
    private: bool = False
    changes: list[VariationChangeRequest] = Field(default_factory=list, max_length=100)


class AdoptVariationRequest(RequestSchema):
    # Null adopts every change.
    change_ids: list[str] | None = Field(default=None, max_length=100)
    # The note of the revision; the variation's name by default.
    revision_note: str | None = Field(default=None, max_length=255)


class CoEditorsRequest(RequestSchema):
    user_ids: list[UUID] = Field(default_factory=list, max_length=50)


# ── Reading ──────────────────────────────────────────────────────────


class VariationLineView(ResponseSchema):
    ingredient_id: UUID | None
    ingredient_name: str
    amount: float | None
    unit: UnitRef | None
    note: str


class VariationEquipmentView(ResponseSchema):
    equipment: EquipmentRef | None
    count: int | None
    note: str


class VariationChangeView(ResponseSchema):
    """A stored change with the names of what it refers to, in the viewer's
    language. `available` is false when a record it names no longer
    exists; `applies` is false when its step or line is no longer in the
    recipe. Either way it is left out of the applied recipe."""

    id: str
    kind: str
    step: int | None
    ingredient_id: UUID | None
    ingredient_name: str | None
    sub_recipe: SubRecipeRef | None
    to_ingredient_id: UUID | None
    to_ingredient_name: str | None
    amount: float | None
    unit: UnitRef | None
    keep_amount: bool
    note: str
    text: str
    duration_minutes: int | None
    lines: list[VariationLineView]
    equipment: list[VariationEquipmentView]
    available: bool
    applies: bool


class StaleStepView(ResponseSchema):
    """A step the variation names that changed (`changed`) or went
    (`deleted`) since the revision it is based on, with its text then."""

    step: int
    state: str
    old_text: str
    current_text: str | None


class VariationResponse(ResponseSchema):
    id: UUID
    recipe_id: UUID
    name: str
    note: str
    locale: str
    private: bool
    # Null once the author's account was deleted ("former member").
    author: PersonRef | None
    based_on_revision: int | None
    current_revision: int | None
    # A step the variation names changed or went since its base revision.
    is_stale: bool
    # False when the base revision is unknown or was purged; staleness
    # cannot be told then.
    base_revision_available: bool
    stale_steps: list[StaleStepView]
    changes: list[VariationChangeView]
    rating_average: float | None
    rating_count: int
    own_rating: OwnRating | None
    can_edit: bool
    can_delete: bool
    can_adopt: bool
    created: datetime
    changed: datetime
    # Came with a mirror from its source instance: read only here, with the
    # author's display name there (null when the author does not show it).
    mirrored: bool = False
    source_author_name: str | None = None
    # The avatar the source sent with that name, as a file here.
    source_author_avatar_id: UUID | None = None


class LineMarkerView(ResponseSchema):
    """A line of a step in the applied recipe that the variation swapped or
    added; `index` counts from 0 within the step's `ingredients`."""

    index: int
    kind: str
    change_id: str
    swapped_from_ingredient_id: UUID | None
    swapped_from_name: str | None


class RemovedLineView(ResponseSchema):
    change_id: str
    ingredient_id: UUID | None
    sub_recipe: SubRecipeRef | None
    name: str
    # Scaled to the servings of the view.
    amount: float | None
    unit: UnitRef | None


class StepMarkerView(ResponseSchema):
    """What differs in one step of the applied recipe; `position` matches
    `recipe.steps[].position`, `origin_step` is the original's number
    (null for a step the variation adds)."""

    position: int
    origin_step: int | None
    added: bool
    text_changed: bool
    changed: bool
    change_ids: list[str]
    lines: list[LineMarkerView]
    removed: list[RemovedLineView]


class VariationViewResponse(ResponseSchema):
    """The recipe with the variation applied, in the shape of the recipe
    detail: ingredient list, nutrition, allergens, diets, the viewer's
    warnings, the dinner-guest flag and the kitchen are derived from the
    applied recipe; the rating fields are the variation's."""

    recipe: RecipeDetailResponse
    variation: VariationResponse
    steps: list[StepMarkerView]


class AdoptVariationResponse(ResponseSchema):
    recipe: RecipeEditResponse
    variation: VariationResponse


class RecipeCopyResponse(ResponseSchema):
    recipe: RecipeRef
    owner: PersonRef | None
    created: datetime
