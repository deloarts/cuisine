"""The cookbook's domain rules, without a database: language fallback,
weighing amounts, deriving a recipe's ingredient list and nutrition, food
restriction warnings and merging shopping items."""

from datetime import UTC
from datetime import datetime

import pytest

from src.cookbook.domain.entities.cooking import ShoppingItem
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.ingredient import UnitConversion
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.exceptions import InvalidRecipeError
from src.cookbook.domain.services.quantity import to_grams
from src.cookbook.domain.services.recipe_derivation import derive
from src.cookbook.domain.services.recipe_rules import validate_publishable
from src.cookbook.domain.services.restriction_rules import warnings_for
from src.cookbook.domain.services.shopping_rules import find_mergeable
from src.cookbook.domain.services.translations import assert_translations
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import RestrictionKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.platform.domain.exceptions import InvalidInputError

NOW = datetime(2026, 1, 1, tzinfo=UTC)

G = Unit(id=1, code="g", kind=UnitKind.MASS, to_base=1.0, created=NOW)
KG = Unit(id=2, code="kg", kind=UnitKind.MASS, to_base=1000.0, created=NOW)
ML = Unit(id=3, code="ml", kind=UnitKind.VOLUME, to_base=1.0, created=NOW)
TBSP = Unit(id=4, code="tbsp", kind=UnitKind.VOLUME, to_base=15.0, created=NOW)
PIECE = Unit(id=5, code="piece", kind=UnitKind.COUNT, to_base=None, created=NOW)
UNITS = {u.id: u for u in (G, KG, ML, TBSP, PIECE)}


def _ingredient(id_: int, name: str, **kwargs: object) -> Ingredient:
    return Ingredient(
        id=id_,
        owner_id=1,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        translations={"de-AT": IngredientText(name, name)},
        **kwargs,  # type: ignore[arg-type]
    )


FLOUR = _ingredient(
    10, "Mehl", nutrition=Nutrition(kcal=350, protein=10), allergens=[Allergen.GLUTEN]
)
OIL = _ingredient(11, "Öl", nutrition=Nutrition(kcal=900, fat=100), density_g_per_ml=0.9)
EGG = _ingredient(
    12,
    "Ei",
    nutrition=Nutrition(kcal=143),
    conversions=[UnitConversion(PIECE.id, 50.0)],
    allergens=[Allergen.EGGS],
)
SALT = _ingredient(13, "Salz")
INGREDIENTS = {i.id: i for i in (FLOUR, OIL, EGG, SALT)}


def _recipe(*steps: list[StepIngredient], servings: int = 2) -> Recipe:
    return Recipe(
        id=1,
        owner_id=1,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        base_servings=servings,
        translations={"de-AT": RecipeText("Test")},
        steps=[RecipeStep(translations={"de-AT": StepText("x")}, ingredients=s) for s in steps],
    )


def test_resolve_prefers_wanted_then_original() -> None:
    texts = {"de-AT": "Hallo", "en-GB": "Hello"}
    assert resolve(texts, "en-GB", "de-AT") == ("en-GB", "Hello")
    assert resolve({"de-AT": "Hallo"}, "en-GB", "de-AT") == ("de-AT", "Hallo")


def test_translations_need_the_original_and_known_locales() -> None:
    with pytest.raises(InvalidInputError):
        assert_translations({"en-GB": 1}, "de-AT", "recipe")
    with pytest.raises(InvalidInputError):
        assert_translations({"de-AT": 1, "fr-FR": 2}, "de-AT", "recipe")
    assert ui_locale("enGB") == "en-GB"
    assert ui_locale("deAT") == "de-AT"


def test_to_grams_by_mass_density_and_conversion() -> None:
    assert to_grams(2, KG, FLOUR) == 2000
    assert to_grams(2, TBSP, OIL) == pytest.approx(27.0)
    assert to_grams(3, PIECE, EGG) == 150
    assert to_grams(2, TBSP, FLOUR) is None
    assert to_grams(None, G, FLOUR) is None


def test_derive_sums_steps_and_scales() -> None:
    recipe = _recipe(
        [StepIngredient(ingredient_id=FLOUR.id, amount=200, unit_id=G.id)],
        [
            StepIngredient(ingredient_id=FLOUR.id, amount=100, unit_id=G.id),
            StepIngredient(ingredient_id=SALT.id, amount=None),
        ],
    )
    derived = derive(recipe, INGREDIENTS, UNITS, servings=4)
    flour = next(line for line in derived.lines if line.ingredient_id == FLOUR.id)
    assert flour.amount == 600 and flour.unit_id == G.id
    salt = next(line for line in derived.lines if line.ingredient_id == SALT.id)
    assert salt.amount is None
    # 300 g flour for two servings: 1050 kcal total, 525 per serving.
    assert derived.nutrition_per_serving.kcal == 525
    assert derived.nutrition_total.kcal == 2100
    assert derived.nutrition_complete is True
    assert derived.allergens == [Allergen.GLUTEN]


def test_derive_merges_units_in_grams_when_all_can_be_weighed() -> None:
    recipe = _recipe(
        [StepIngredient(ingredient_id=FLOUR.id, amount=1, unit_id=KG.id)],
        [StepIngredient(ingredient_id=FLOUR.id, amount=50, unit_id=G.id)],
    )
    lines = derive(recipe, INGREDIENTS, UNITS).lines
    assert len(lines) == 1
    assert lines[0].amount == 1050 and lines[0].unit_id == G.id


def test_derive_keeps_units_apart_and_flags_incomplete_nutrition() -> None:
    recipe = _recipe(
        [StepIngredient(ingredient_id=FLOUR.id, amount=2, unit_id=TBSP.id)],
        [StepIngredient(ingredient_id=FLOUR.id, amount=100, unit_id=G.id)],
    )
    derived = derive(recipe, INGREDIENTS, UNITS)
    assert len(derived.lines) == 2
    assert derived.nutrition_complete is False


def test_derive_reports_ingredients_without_nutrition() -> None:
    recipe = _recipe([StepIngredient(ingredient_id=SALT.id, amount=5, unit_id=G.id)])
    derived = derive(recipe, INGREDIENTS, UNITS)
    assert derived.nutrition_complete is False
    assert derived.missing_nutrition_ingredient_ids == [SALT.id]


def test_restriction_warnings_match_allergens_and_ingredients() -> None:
    restrictions = [
        FoodRestriction(
            id=1, user_id=1, kind=RestrictionKind.ALLERGY, created=NOW, allergen=Allergen.EGGS
        ),
        FoodRestriction(
            id=2, user_id=1, kind=RestrictionKind.INTOLERANCE, created=NOW, ingredient_id=OIL.id
        ),
        FoodRestriction(
            id=3, user_id=1, kind=RestrictionKind.ALLERGY, created=NOW, allergen=Allergen.FISH
        ),
    ]
    warnings = warnings_for(restrictions, [EGG.id, OIL.id, FLOUR.id], INGREDIENTS)
    assert {w.restriction_id for w in warnings} == {1, 2}
    assert next(w for w in warnings if w.restriction_id == 1).matching_ingredient_ids == [EGG.id]


def test_publishing_needs_a_step() -> None:
    recipe = _recipe()
    with pytest.raises(InvalidRecipeError):
        validate_publishable(recipe)


def test_shopping_items_merge_only_open_items_of_the_same_unit() -> None:
    open_item = ShoppingItem(
        id=1,
        list_id=1,
        created=NOW,
        created_by_id=1,
        ingredient_id=FLOUR.id,
        amount=100,
        unit_id=G.id,
    )
    checked = ShoppingItem(
        id=2,
        list_id=1,
        created=NOW,
        created_by_id=1,
        ingredient_id=OIL.id,
        amount=1,
        unit_id=ML.id,
        checked=True,
    )
    assert find_mergeable([open_item, checked], FLOUR.id, G.id) is open_item
    assert find_mergeable([open_item, checked], FLOUR.id, KG.id) is None
    assert find_mergeable([open_item, checked], OIL.id, ML.id) is None
    assert find_mergeable([open_item], None, None) is None


def test_fitting_diets_follow_the_markers() -> None:
    from src.cookbook.domain.services.diet_rules import fitting_diets
    from src.cookbook.domain.value_objects.enums import Diet
    from src.cookbook.domain.value_objects.enums import DietMarker

    assert fitting_diets([]) == list(Diet)
    assert set(fitting_diets([DietMarker.DAIRY, DietMarker.EGGS])) == set(Diet) - {Diet.VEGAN}
    fish = set(fitting_diets([DietMarker.FISH]))
    assert Diet.PESCETARIAN in fish and Diet.VEGETARIAN not in fish
    gelatin = set(fitting_diets([DietMarker.GELATIN]))
    assert not gelatin & {Diet.VEGETARIAN, Diet.PESCETARIAN, Diet.HALAL, Diet.NO_PORK}
    assert Diet.NO_BEEF in gelatin
    assert Diet.HALAL not in fitting_diets([DietMarker.ALCOHOL])


def test_diet_restrictions_warn_on_breaking_ingredients() -> None:
    from src.cookbook.domain.value_objects.enums import Diet
    from src.cookbook.domain.value_objects.enums import DietMarker

    bacon = _ingredient(20, "Speck", diet_markers=[DietMarker.MEAT, DietMarker.PORK])
    vegetarian = FoodRestriction(
        id=9, user_id=1, kind=RestrictionKind.DIET, created=NOW, diet=Diet.VEGETARIAN
    )
    found = warnings_for([vegetarian], [bacon.id, FLOUR.id], {**INGREDIENTS, bacon.id: bacon})
    assert [w.matching_ingredient_ids for w in found] == [[bacon.id]]
    assert found[0].diet is Diet.VEGETARIAN


def test_plain_text_strips_the_markdown_subset() -> None:
    from src.cookbook.domain.services.markdown import plain_text

    text = "Den **Teig** gut *rühren*:\n- Mehl\n- 2 Eier\n1. kneten\\\nfertig"
    assert plain_text(text) == "Den Teig gut rühren: Mehl 2 Eier kneten fertig"
    assert plain_text("3 * 4 = 12") == "3 * 4 = 12"


def test_a_handed_over_recipe_widens_only_to_the_using_recipes_readers() -> None:
    from src.cookbook.domain.services.recipe_handover import Readers
    from src.cookbook.domain.services.recipe_handover import handed_over_visibility
    from src.cookbook.domain.value_objects.enums import RecipeVisibility as V

    def readers(
        owner: int | None,
        visibility: V,
        users: set[int] | None = None,
        house: set[int] | None = None,
    ) -> Readers:
        return Readers(
            owner_id=owner,
            visibility=visibility,
            user_ids=frozenset(users or ()),
            group_ids=frozenset(),
            household_ids=frozenset(house or ()),
        )

    leaving = 1
    shared_with_new_owner = readers(leaving, V.SHARED, {2, 5})

    def hand_over(*using: Readers, house: set[int] | None = None) -> tuple[V, set[int]]:
        result = handed_over_visibility(
            shared_with_new_owner,
            using,
            new_owner_id=2,
            new_owner_household=house or set(),
            leaving_id=leaving,
        )
        return result.visibility, set(result.user_ids)

    # The recipe keeps its other reader and gains the using recipe's shares.
    assert hand_over(readers(2, V.SHARED, {3})) == (V.SHARED, {3, 5})
    assert hand_over(readers(2, V.INSTANCE)) == (V.INSTANCE, set())
    # Another using recipe's owner and that owner's household become shares.
    assert hand_over(readers(4, V.HOUSEHOLD, house={4, 6})) == (V.SHARED, {4, 5, 6})
    # The new owner's own household covers a household recipe of its own.
    private = readers(leaving, V.PRIVATE)
    result = handed_over_visibility(
        private,
        [readers(2, V.HOUSEHOLD, house={2, 3})],
        new_owner_id=2,
        new_owner_household={2, 3},
        leaving_id=leaving,
    )
    assert result.visibility is V.HOUSEHOLD and not result.user_ids
    alone = handed_over_visibility(
        private, [readers(2, V.PRIVATE)], new_owner_id=2, new_owner_household=set(), leaving_id=1
    )
    assert alone.visibility is V.PRIVATE
