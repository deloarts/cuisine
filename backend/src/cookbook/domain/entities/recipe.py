"""
A recipe: its text in each content locale, the steps in order, in each step
the ingredients that step uses, and the ingredient list the cook declared
for the whole recipe. The ingredient list a reader sees, the nutrition and
the allergens are derived on read from the declared list merged with what
the steps use (services/recipe_derivation.py).
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from uuid import UUID
from uuid import uuid4

from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class StepIngredient:
    """A catalogue ingredient or another recipe (a sub-recipe), exactly one.
    The same shape serves a step's lines and the recipe's declared list."""

    # Kept across saves while a save names it, so a link can point at one
    # line of one step.
    public_id: UUID = field(default_factory=uuid4)
    ingredient_id: int | None = None
    sub_recipe_id: int | None = None
    # None means "to taste" or "as needed".
    amount: float | None = None
    unit_id: int | None = None
    translations: dict[str, NoteText] = field(default_factory=dict)


@dataclass(kw_only=True)
class StepEquipment:
    """An item of the equipment catalogue a step needs, with an optional
    count ("2 bowls") and a translatable note ("26 cm", "200 °C fan")."""

    public_id: UUID = field(default_factory=uuid4)
    equipment_id: int
    count: int | None = None
    translations: dict[str, NoteText] = field(default_factory=dict)


@dataclass(kw_only=True)
class RecipeStep:
    # Kept across saves while a save names it, like the ids of its lines.
    public_id: UUID = field(default_factory=uuid4)
    translations: dict[str, StepText] = field(default_factory=dict)
    # Offers a timer in cook mode.
    duration_minutes: int | None = None
    image_file_id: int | None = None
    ingredients: list[StepIngredient] = field(default_factory=list)
    equipment: list[StepEquipment] = field(default_factory=list)


@dataclass(kw_only=True)
class Recipe(Entity):
    # None once the creating account was deleted.
    owner_id: int | None
    original_locale: str
    created: datetime
    changed: datetime
    translations: dict[str, RecipeText] = field(default_factory=dict)
    status: RecipeStatus = RecipeStatus.DRAFT
    visibility: RecipeVisibility = RecipeVisibility.INSTANCE
    # With visibility "shared": the users and groups who may read it.
    shared_user_ids: list[int] = field(default_factory=list)
    shared_group_ids: list[int] = field(default_factory=list)
    # With visibility "shared": the paired instances the owner sends it to.
    shared_peer_ids: list[int] = field(default_factory=list)
    # People the owner lets edit the content (not the visibility, the
    # co-editors or the deletion); they must be able to see the recipe.
    co_editor_ids: list[int] = field(default_factory=list)
    # The recipe this one was copied from ("Copy as my recipe"); None for an
    # original or once the source was deleted.
    based_on_recipe_id: int | None = None
    # Where an imported or mirrored recipe came from: the source instance's
    # `instance_id` and the recipe's public id there. Both or neither; the
    # recipe's own public id is always its own.
    origin_instance_id: UUID | None = None
    origin_public_id: UUID | None = None
    # Set on a mirror, the read-only copy of a recipe a paired instance
    # shares with this one: the peer it came from. A mirror has no owner.
    mirror_peer_id: int | None = None
    # Never sent to a paired instance and never public: mirrors and every
    # copy made from a mirror or from such a copy.
    peer_capped: bool = False
    base_servings: int = 4
    prep_minutes: int | None = None
    cook_minutes: int | None = None
    rest_minutes: int | None = None
    difficulty: Difficulty = Difficulty.EASY
    cover_file_id: int | None = None
    source_url: str | None = None
    source_name: str | None = None
    tag_ids: list[int] = field(default_factory=list)
    created_via: CreatedVia = CreatedVia.WEB
    published_at: datetime | None = None
    # What one batch makes, such as 500 g or 12 pieces. A sub-recipe line in
    # the yield's unit scales the sub-recipe by amount / yield.
    yield_amount: float | None = None
    yield_unit_id: int | None = None
    steps: list[RecipeStep] = field(default_factory=list)
    # The ingredient list the cook declared for the whole recipe, in their
    # order. It may name what no step uses yet; the derived list takes the
    # larger of it and the steps' usage (`recipe_derivation.merged_lines`).
    ingredients: list[StepIngredient] = field(default_factory=list)

    def pass_to(self, owner_id: int | None) -> None:
        """Gives the recipe another owner, or none. The origin of an import
        belongs to the cook who imported it ("update the earlier import"
        finds only their own recipes), so it does not pass on; the new owner
        may already hold an import of the same source recipe. Neither do
        the paired instances it was shared with."""
        if owner_id != self.owner_id:
            self.origin_instance_id = None
            self.origin_public_id = None
            # Sharing with a paired instance was the previous owner's
            # choice, so it ends with the ownership.
            self.shared_peer_ids = []
        self.owner_id = owner_id

    @property
    def is_mirror(self) -> bool:
        return self.mirror_peer_id is not None

    @property
    def total_minutes(self) -> int | None:
        parts = [m for m in (self.prep_minutes, self.cook_minutes, self.rest_minutes) if m]
        return sum(parts) if parts else None

    @property
    def all_lines(self) -> list[StepIngredient]:
        """Every ingredient line of the recipe: the steps' lines in order,
        then the declared list. Only for which records the recipe names; the
        amounts of the two overlap (`recipe_derivation.merged_lines`)."""
        return [*(si for s in self.steps for si in s.ingredients), *self.ingredients]

    @property
    def ingredient_ids(self) -> list[int]:
        """The catalogue ingredients the recipe's steps or declared list name."""
        return sorted({si.ingredient_id for si in self.all_lines if si.ingredient_id})

    @property
    def equipment_ids(self) -> list[int]:
        """The equipment the recipe's own steps name."""
        return sorted({e.equipment_id for s in self.steps for e in s.equipment})

    @property
    def sub_recipe_ids(self) -> list[int]:
        return sorted({si.sub_recipe_id for si in self.all_lines if si.sub_recipe_id})
