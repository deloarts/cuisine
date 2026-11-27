"""Which diets a set of ingredients fits, decided by their diet markers. An
ingredient without markers fits every diet, so an unmarked ingredient can
make a recipe look vegetarian when it is not; the markers are set in the
ingredient editor, by an agent and in the seed. A draft ingredient has
markers nobody has confirmed yet, so it fits no diet until a person
activates it."""

from collections.abc import Iterable

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import DietMarker as M
from src.cookbook.domain.value_objects.enums import IngredientStatus

_LAND_ANIMALS = frozenset({M.MEAT, M.POULTRY, M.PORK, M.BEEF})

# The markers each diet excludes.
EXCLUDED: dict[Diet, frozenset[M]] = {
    Diet.VEGETARIAN: _LAND_ANIMALS | {M.FISH, M.SEAFOOD, M.GELATIN},
    Diet.VEGAN: _LAND_ANIMALS | {M.FISH, M.SEAFOOD, M.GELATIN, M.DAIRY, M.EGGS, M.HONEY},
    Diet.PESCETARIAN: _LAND_ANIMALS | {M.GELATIN},
    Diet.HALAL: frozenset({M.PORK, M.GELATIN, M.ALCOHOL}),
    Diet.NO_PORK: frozenset({M.PORK, M.GELATIN}),
    Diet.NO_BEEF: frozenset({M.BEEF}),
    Diet.NO_ALCOHOL: frozenset({M.ALCOHOL}),
}


def breaks(diet: Diet, markers: Iterable[M]) -> bool:
    return bool(EXCLUDED[diet] & set(markers))


def fitting_diets(markers: Iterable[M]) -> list[Diet]:
    """The diets none of `markers` breaks, in their declared order."""
    present = set(markers)
    return [diet for diet in Diet if not EXCLUDED[diet] & present]


def unconfirmed(ingredient: Ingredient) -> bool:
    """Whether the ingredient's markers wait for a person to confirm them."""
    return ingredient.status == IngredientStatus.DRAFT


def breaks_ingredient(diet: Diet, ingredient: Ingredient) -> bool:
    """Whether the ingredient may break the diet: by its markers, or because
    it is a draft whose markers nobody has confirmed."""
    return unconfirmed(ingredient) or breaks(diet, ingredient.diet_markers)


def diets_of(ingredients: Iterable[Ingredient]) -> list[Diet]:
    """The diets a recipe using `ingredients` fits: none while any of them
    is a draft, otherwise those none of their markers breaks."""
    markers: list[M] = []
    for ingredient in ingredients:
        if unconfirmed(ingredient):
            return []
        markers.extend(ingredient.diet_markers)
    return fitting_diets(markers)
