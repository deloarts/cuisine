"""The cooking history, the meal plan and the shopping lists."""

from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime

from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.domain.value_objects.enums import ShoppingListMode
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class CookEvent(Entity):
    """Someone cooked a recipe on a day. Everyone sees the cooking calendar."""

    user_id: int
    recipe_id: int
    cooked_on: date
    servings: int
    created: datetime
    note: str = ""
    # The variation that was cooked, if any; None once it was deleted.
    variation_id: int | None = None


@dataclass(kw_only=True)
class MealPlanEntry(Entity):
    """One planned meal of one user: a recipe or a free text such as
    "leftovers"."""

    user_id: int
    plan_date: date
    slot: MealSlot
    servings: int
    created: datetime
    recipe_id: int | None = None
    title: str = ""
    # Set while the creator belongs to a household: the entry then belongs
    # to the household's plan and stays with it when the creator leaves.
    household_id: int | None = None


@dataclass(kw_only=True)
class ShoppingItem(Entity):
    list_id: int
    created: datetime
    created_by_id: int | None
    # An item is an ingredient from the catalogue or a free text.
    ingredient_id: int | None = None
    text: str = ""
    amount: float | None = None
    unit_id: int | None = None
    # The aisle the item is grouped under; taken from the ingredient.
    category_id: int | None = None
    checked: bool = False
    checked_by_id: int | None = None
    checked_at: datetime | None = None
    # The recipe the item was first added from, if any.
    recipe_id: int | None = None
    # The other recipes whose amounts joined this item later, in the order
    # they came; plain ids, so a deleted recipe only drops out of the label.
    extra_recipe_ids: list[int] = field(default_factory=list)
    # The sub-recipes between that recipe and the item, outermost first:
    # ["Lasagna sheets"] for flour that the lasagna's sheets need. An item
    # bought as a whole ("I'll buy it") is the last recipe of its path.
    sub_recipe_path: list[int] = field(default_factory=list)

    def recipe_ids(self) -> list[int]:
        """Every recipe the item is for, the first one first."""
        first = [self.recipe_id] if self.recipe_id is not None else []
        return first + [i for i in self.extra_recipe_ids if i != self.recipe_id]

    def add_recipe(self, recipe_id: int) -> None:
        """Records that a recipe's amount joined this item."""
        if self.recipe_id is None:
            self.recipe_id = recipe_id
        elif recipe_id not in self.recipe_ids():
            self.extra_recipe_ids = [*self.extra_recipe_ids, recipe_id]


@dataclass(kw_only=True)
class ShoppingList(Entity):
    owner_id: int
    name: str
    created: datetime
    changed: datetime
    # The last add, tick, edit or mode change; a normal list idle for the
    # configured days deletes itself.
    last_activity_at: datetime
    mode: ShoppingListMode = ShoppingListMode.NORMAL
    # Set by a member so a normal list never deletes itself.
    keep: bool = False
    # The users the owner shares the list with.
    member_ids: list[int] = field(default_factory=list)
    # Set on a household's default list, which every member is on.
    household_id: int | None = None

    def can_access(self, user_id: int, household_id: int | None = None) -> bool:
        if self.household_id is not None:
            return self.household_id == household_id or user_id in self.member_ids
        return user_id == self.owner_id or user_id in self.member_ids


@dataclass(kw_only=True)
class ShoppingListNote(Entity):
    """Tells a former member that an idle list deleted itself. The user
    dismisses it; it goes with their account."""

    user_id: int
    list_name: str
    # The idle days the list was deleted after, as configured then.
    idle_days: int
    created: datetime
