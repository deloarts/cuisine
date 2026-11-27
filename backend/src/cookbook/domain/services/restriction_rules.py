"""Matching food restrictions against what a recipe or a shopping list
contains. A user's own matches go to that user only; for dinner guests only
the fact that something matches leaves the use case."""

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.services.diet_rules import breaks_ingredient
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import RestrictionKind


@dataclass(frozen=True)
class RestrictionWarning:
    restriction_id: int
    kind: RestrictionKind
    allergen: Allergen | None
    ingredient_id: int | None
    diet: Diet | None
    family_id: int | None
    # The ingredients of the recipe or list that trigger the warning.
    matching_ingredient_ids: list[int]


def warnings_for(
    restrictions: Iterable[FoodRestriction],
    ingredient_ids: Iterable[int],
    ingredients: Mapping[int, Ingredient],
) -> list[RestrictionWarning]:
    present = sorted(set(ingredient_ids))
    result: list[RestrictionWarning] = []
    for restriction in restrictions:
        if restriction.ingredient_id is not None:
            matching = [i for i in present if i == restriction.ingredient_id]
        elif restriction.family_id is not None:
            family = restriction.family_id
            matching = [
                i for i in present if i in ingredients and ingredients[i].family_id == family
            ]
        elif restriction.diet is not None:
            diet = restriction.diet
            matching = [
                i for i in present if i in ingredients and breaks_ingredient(diet, ingredients[i])
            ]
        elif restriction.allergen is not None:
            matching = [
                i
                for i in present
                if i in ingredients and restriction.allergen in ingredients[i].allergens
            ]
        else:
            matching = []
        if matching:
            result.append(
                RestrictionWarning(
                    restriction_id=restriction.id,
                    kind=restriction.kind,
                    allergen=restriction.allergen,
                    ingredient_id=restriction.ingredient_id,
                    diet=restriction.diet,
                    family_id=restriction.family_id,
                    matching_ingredient_ids=matching,
                )
            )
    return result
