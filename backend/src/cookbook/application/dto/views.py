"""What the read use cases hand to the adapters: a record together with
what was derived or looked up for the viewer."""

from dataclasses import dataclass
from dataclasses import field
from datetime import date

from src.cookbook.application.services.mirror_facts import MirrorInfo
from src.cookbook.domain.entities.cooking import ShoppingItem
from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.personal import CookNote
from src.cookbook.domain.entities.personal import Rating
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.services.recipe_derivation import DerivedRecipe
from src.cookbook.domain.services.restriction_rules import RestrictionWarning
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet


@dataclass
class Lookups:
    """The resources and ingredients a set of records refers to, by
    internal id, so the adapters can name them."""

    units: dict[int, Unit] = field(default_factory=dict)
    ingredients: dict[int, Ingredient] = field(default_factory=dict)
    tags: dict[int, Tag] = field(default_factory=dict)
    categories: dict[int, IngredientCategory] = field(default_factory=dict)
    families: dict[int, IngredientFamily] = field(default_factory=dict)
    equipment: dict[int, Equipment] = field(default_factory=dict)
    # Every sub-recipe the records reach, whatever the viewer may see of
    # them; derivation needs them all, presentation hides what it must.
    recipes: dict[int, Recipe] = field(default_factory=dict)


@dataclass
class RecipeSummary:
    recipe: Recipe
    allergens: list[Allergen]
    rating_average: float | None
    rating_count: int
    is_favourite: bool
    # Whether one of the viewer's own food restrictions matches.
    has_warning: bool
    can_edit: bool
    last_cooked: date | None = None
    diets: list[Diet] = field(default_factory=list)
    # The recipe conflicts with a restriction of at least one chosen guest
    # who opted in. Never which guest or which restriction.
    unsuitable_for_guests: bool = False
    # The months in which every seasonal ingredient is in season; empty when
    # it uses none (`seasons.recipe_season`).
    season_months: list[int] = field(default_factory=list)
    in_season: bool = False
    # With the viewer's kitchen set up: the equipment of the tree it lacks.
    # None before set-up, so nothing is flagged.
    missing_equipment_ids: list[int] | None = None
    # The variations the viewer may see.
    variation_count: int = 0
    # The recipe itself conflicts with a chosen guest, but a variation the
    # viewer may see does not.
    variation_fits_guests: bool = False
    # The recipe itself misses one of the wanted diets, but a variation the
    # viewer may see fits them all.
    variation_fits_diets: bool = False
    # For a mirror: the source instance's name and the author's display
    # name there (None when the author does not show it).
    mirror_instance: str | None = None
    mirror_author: str | None = None
    mirror_author_avatar: str | None = None


@dataclass
class RecipeView:
    recipe: Recipe
    derived: DerivedRecipe
    lookups: Lookups
    rating_average: float | None
    rating_count: int
    is_favourite: bool
    own_rating: Rating | None
    own_note: CookNote | None
    warnings: list[RestrictionWarning]
    can_edit: bool
    last_cooked: date | None
    last_cooked_by_me: date | None
    unsuitable_for_guests: bool = False
    season_months: list[int] = field(default_factory=list)
    in_season: bool = False
    missing_equipment_ids: list[int] | None = None
    variation_count: int = 0
    # The copies of the recipe the viewer may see.
    based_on_count: int = 0
    # Over the recipe and all its variations together.
    rating_overall_average: float | None = None
    rating_overall_count: int = 0
    # For a mirror: where it comes from, its plain-text lines and what the
    # source added to the allergens and markers.
    mirror: MirrorInfo | None = None
    # Allergens only the source's data contributed.
    source_allergens_added: list[Allergen] = field(default_factory=list)
    # Allergens and diet markers of the source this release does not know.
    unknown_allergens: list[str] = field(default_factory=list)
    unknown_diet_markers: list[str] = field(default_factory=list)


@dataclass
class StepImage:
    """An image of the step image library: the stored file, the recipe and
    the step (0-based) that show it, and how many ingredients and equipment
    items that step shares with the step being edited."""

    file_id: int
    recipe: Recipe
    step_index: int
    matches: int


@dataclass
class ShoppingListView:
    shopping_list: ShoppingList
    items: list[ShoppingItem]
    lookups: Lookups
    # Item ids the viewer's own food restrictions flag.
    warning_item_ids: set[int] = field(default_factory=set)
