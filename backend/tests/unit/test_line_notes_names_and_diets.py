"""How a recipe's ingredient list reads: the notes of merged lines, which
lines take the plural, the diets a recipe with a draft ingredient claims,
and the order ingredient search answers in."""

from datetime import UTC
from datetime import datetime

import pytest

from src.cookbook.adapters.inbound.api.presenters import name_amount
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.services.diet_rules import breaks_ingredient
from src.cookbook.domain.services.diet_rules import diets_of
from src.cookbook.domain.services.mentions import MentionTarget
from src.cookbook.domain.services.mentions import UnresolvedMentionError
from src.cookbook.domain.services.mentions import mentions
from src.cookbook.domain.services.mentions import resolve_named_mentions
from src.cookbook.domain.services.names import name_key
from src.cookbook.domain.services.names import search_rank
from src.cookbook.domain.services.recipe_derivation import derive
from src.cookbook.domain.services.recipe_derivation import merged_lines
from src.cookbook.domain.services.restriction_rules import warnings_for
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import RestrictionKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText

NOW = datetime(2026, 1, 1, tzinfo=UTC)

G = Unit(id=1, code="g", kind=UnitKind.MASS, to_base=1.0, created=NOW)
PIECE = Unit(id=2, code="piece", kind=UnitKind.COUNT, to_base=None, created=NOW)
CLOVE = Unit(id=3, code="clove", kind=UnitKind.COUNT, to_base=None, created=NOW)
UNITS = {u.id: u for u in (G, PIECE, CLOVE)}


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


BUTTER = _ingredient(10, "Butter", diet_markers=[DietMarker.DAIRY])
ONION = _ingredient(11, "Zwiebel")
FAT = _ingredient(12, "Fett", status=IngredientStatus.DRAFT)
INGREDIENTS = {i.id: i for i in (BUTTER, ONION, FAT)}


def _line(ingredient: Ingredient, amount: float | None, note: str = "") -> StepIngredient:
    return StepIngredient(
        ingredient_id=ingredient.id,
        amount=amount,
        unit_id=G.id,
        translations={"de-AT": NoteText(note)} if note else {},
    )


def _recipe(declared: list[StepIngredient], step: list[StepIngredient]) -> Recipe:
    return Recipe(
        id=1,
        owner_id=1,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        translations={"de-AT": RecipeText("Suppe")},
        steps=[RecipeStep(translations={"de-AT": StepText("Kochen.")}, ingredients=step)],
        ingredients=declared,
    )


def _notes(recipe: Recipe) -> dict[int | None, str]:
    return {
        line.ingredient_id: line.notes["de-AT"].note if line.notes else ""
        for line in merged_lines(recipe, INGREDIENTS, UNITS, {})
    }


def test_a_declared_note_reaches_the_merged_list() -> None:
    recipe = _recipe([_line(BUTTER, 150, "weich")], [])
    assert _notes(recipe) == {BUTTER.id: "weich"}
    (line,) = derive(recipe, INGREDIENTS, UNITS).lines
    assert line.notes["de-AT"].note == "weich"


def test_declared_notes_win_over_step_notes() -> None:
    recipe = _recipe([_line(BUTTER, 150, "weich")], [_line(BUTTER, 50, "geschmolzen")])
    assert _notes(recipe) == {BUTTER.id: "weich"}


def test_a_step_note_counts_when_every_step_line_shares_it() -> None:
    recipe = _recipe(
        [_line(ONION, 100)], [_line(ONION, 50, "gehackt"), _line(ONION, 50, "gehackt")]
    )
    assert _notes(recipe) == {ONION.id: "gehackt"}


def test_different_step_notes_stay_on_their_steps() -> None:
    recipe = _recipe([], [_line(BUTTER, None, "etwas"), _line(BUTTER, 150, "der Rest")])
    assert _notes(recipe) == {BUTTER.id: ""}


def test_the_same_note_is_named_once() -> None:
    recipe = _recipe([], [_line(ONION, 50, "gehackt"), _line(ONION, 50, "gehackt")])
    assert _notes(recipe) == {ONION.id: "gehackt"}


def test_counts_of_pieces_and_weights_take_the_plural() -> None:
    assert name_amount(6, PIECE) == 6
    assert name_amount(1, PIECE) == 1
    assert name_amount(450, G) == 2
    assert name_amount(3, None) == 3
    # Other count units keep the ingredient singular: "2 cloves garlic".
    assert name_amount(2, CLOVE) == 1
    assert name_amount(None, G) is None


def test_a_draft_ingredient_fits_no_diet() -> None:
    assert Diet.VEGAN in diets_of([ONION])
    assert diets_of([ONION, FAT]) == []
    assert breaks_ingredient(Diet.VEGAN, FAT)
    assert not breaks_ingredient(Diet.VEGETARIAN, BUTTER)


def test_a_recipe_with_a_draft_ingredient_claims_no_diet() -> None:
    recipe = _recipe([_line(ONION, 100), _line(FAT, 80)], [])
    assert derive(recipe, INGREDIENTS, UNITS).diets == []
    activated = {**INGREDIENTS, FAT.id: _ingredient(12, "Fett")}
    assert Diet.VEGAN in derive(recipe, activated, UNITS).diets


def test_a_draft_ingredient_warns_a_guest_with_a_diet() -> None:
    vegan = FoodRestriction(
        id=1, user_id=1, kind=RestrictionKind.DIET, diet=Diet.VEGAN, created=NOW
    )
    (warning,) = warnings_for([vegan], [ONION.id, FAT.id], INGREDIENTS)
    assert warning.matching_ingredient_ids == [FAT.id]


def test_search_ranks_exact_names_and_whole_words_first() -> None:
    names = {
        "Hirschhornsalz": ["Hirschhornsalz", "hartshorn salt"],
        "Kräutersalz": ["Kräutersalz", "herb salt"],
        "Salz": ["Salz", "salt"],
        "Pfefferoni": ["Pfefferoni"],
        "schwarzer Pfeffer": ["schwarzer Pfeffer"],
        "Piment": ["Piment", "Nelkenpfeffer"],
        "Kristallzucker": ["Kristallzucker", "Zucker"],
        "brauner Zucker": ["brauner Zucker"],
    }

    def order(search: str) -> list[str]:
        found = [
            n
            for n, all_names in names.items()
            if any(search.lower() in a.lower() for a in all_names)
        ]
        return sorted(found, key=lambda n: search_rank(names[n], search))

    assert order("Salz")[0] == "Salz"
    assert order("Pfeffer")[:2] == ["schwarzer Pfeffer", "Pfefferoni"]
    assert order("Pfeffer")[-1] == "Piment"
    # An alias counts as a name: "Zucker" is Kristallzucker in Austria.
    assert order("Zucker")[0] == "Kristallzucker"


def test_a_named_mention_finds_its_line_by_any_of_its_names() -> None:
    targets = [
        MentionTarget(
            "ingredient", "a" * 8 + "-0000-0000-0000-" + "0" * 12, ("Zwiebel", "Zwiebeln")
        ),
        MentionTarget("equipment", "b" * 8 + "-0000-0000-0000-" + "0" * 12, ("Topf",)),
    ]
    text = resolve_named_mentions(
        "@[Zwiebeln](ingredient) im @[topf](equipment) anschwitzen.", targets, name_key
    )
    assert mentions(text)[0].public_id == targets[0].public_id
    assert mentions(text)[1].kind == "equipment"
    # Mentions by id stay as they are.
    assert resolve_named_mentions(text, targets, name_key) == text


def test_a_named_mention_without_a_line_is_refused() -> None:
    with pytest.raises(UnresolvedMentionError):
        resolve_named_mentions("@[Butter](ingredient) schmelzen.", [], name_key)


def test_a_step_note_does_not_speak_for_unnoted_lines_of_other_steps() -> None:
    recipe = _recipe([], [_line(ONION, 400), _line(ONION, None, "zum Wälzen")])
    assert _notes(recipe) == {ONION.id: ""}


def test_a_named_mention_may_use_the_short_name() -> None:
    flour = MentionTarget("ingredient", "cccccccc-0000-0000-0000-000000000000", ("plain flour",))
    sugar = MentionTarget("ingredient", "dddddddd-0000-0000-0000-000000000000", ("Kristallzucker",))
    text = resolve_named_mentions(
        "@[flour](ingredient), @[Zucker](ingredient)", [flour, sugar], name_key
    )
    assert [m.public_id for m in mentions(text)] == [flour.public_id, sugar.public_id]


def test_a_short_name_matching_two_lines_is_refused() -> None:
    lines = [
        MentionTarget("ingredient", "eeeeeeee-0000-0000-0000-000000000000", ("plain flour",)),
        MentionTarget("ingredient", "ffffffff-0000-0000-0000-000000000000", ("coarse flour",)),
    ]
    with pytest.raises(UnresolvedMentionError):
        resolve_named_mentions("@[flour](ingredient)", lines, name_key)
