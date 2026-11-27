"""Applying a variation, telling its staleness and renumbering what is left
after an adoption, without a database."""

from datetime import UTC
from datetime import datetime
from typing import Any

import pytest

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.variation import RecipeVariation
from src.cookbook.domain.exceptions import InvalidVariationError
from src.cookbook.domain.services.variations import Change
from src.cookbook.domain.services.variations import LineSpec
from src.cookbook.domain.services.variations import Mention
from src.cookbook.domain.services.variations import apply_variation
from src.cookbook.domain.services.variations import can_delete_variation
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.services.variations import renumber_after_adoption
from src.cookbook.domain.services.variations import stale_steps
from src.cookbook.domain.services.variations import validate_changes
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import VariationChangeKind as Kind
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.domain.value_objects.viewer import Viewer
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

NOW = datetime(2026, 11, 22, tzinfo=UTC)
FROM_ID = "00000000-0000-0000-0000-000000000001"
TO_ID = "00000000-0000-0000-0000-000000000002"


def _recipe() -> Recipe:
    def step(text: str, *lines: tuple[int, float]) -> RecipeStep:
        return RecipeStep(
            translations={"de-AT": StepText(text)},
            ingredients=[StepIngredient(ingredient_id=i, amount=a, unit_id=1) for i, a in lines],
        )

    return Recipe(
        id=1,
        owner_id=10,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        status=RecipeStatus.PUBLISHED,
        translations={"de-AT": RecipeText("Palatschinken")},
        steps=[
            step(f"Mit @[Milch](ingredient:{FROM_ID}) verrühren.", (1, 250), (2, 100)),
            step("Zucker dazu.", (3, 20)),
            step("Backen.", (1, 50)),
        ],
    )


def test_swaps_removals_additions_and_extra_steps() -> None:
    recipe = _recipe()
    applied = apply_variation(
        recipe,
        [
            Change(
                id="a",
                kind=Kind.SWAP,
                ingredient_id=1,
                to_ingredient_id=7,
                mention=Mention(FROM_ID, TO_ID, "Haferdrink"),
            ),
            Change(id="b", kind=Kind.REMOVE_LINE, step=2, ingredient_id=3),
            Change(id="c", kind=Kind.ADD_LINE, step=2, ingredient_id=8, amount=1),
            Change(
                id="d",
                kind=Kind.EXTRA_STEP,
                step=0,
                text="Vorbereiten.",
                lines=(LineSpec(ingredient_id=9, amount=5),),
            ),
            Change(id="e", kind=Kind.STEP_TEXT, step=3, text="In Öl backen."),
        ],
        "de-AT",
    )
    steps = applied.recipe.steps
    assert [s.translations["de-AT"].text for s in steps] == [
        "Vorbereiten.",
        f"Mit @[Haferdrink](ingredient:{TO_ID}) verrühren.",
        "Zucker dazu.",
        "In Öl backen.",
    ]
    # The swap is recipe-wide and keeps each line's amount.
    assert [(i.ingredient_id, i.amount) for i in steps[1].ingredients] == [(7, 250), (2, 100)]
    assert [(i.ingredient_id, i.amount) for i in steps[3].ingredients] == [(7, 50)]
    assert [i.ingredient_id for i in steps[2].ingredients] == [8]
    markers = applied.steps
    assert [m.origin_step for m in markers] == [None, 1, 2, 3]
    assert markers[0].added and markers[3].text_changed
    assert markers[2].removed[0].ingredient_id == 3
    assert [(line.index, line.kind) for line in markers[2].lines] == [(0, "added")]
    assert markers[1].lines[0].swapped_from_ingredient_id == 1
    assert applied.skipped_change_ids == []
    # The original is untouched.
    assert recipe.steps[0].ingredients[0].ingredient_id == 1


def test_changes_whose_step_or_line_is_gone_are_skipped() -> None:
    applied = apply_variation(
        _recipe(),
        [
            Change(id="a", kind=Kind.STEP_TEXT, step=9, text="x"),
            Change(id="b", kind=Kind.REMOVE_LINE, step=2, ingredient_id=1),
            Change(id="c", kind=Kind.SWAP, step=2, ingredient_id=1, to_ingredient_id=7),
            Change(id="d", kind=Kind.SWAP, ingredient_id=42, to_ingredient_id=7),
        ],
        "de-AT",
    )
    assert applied.skipped_change_ids == ["a", "b", "c", "d"]
    assert not any(m.changed for m in applied.steps)


def test_validation_names_the_broken_change() -> None:
    with pytest.raises(InvalidVariationError, match="Change 2"):
        validate_changes(
            _recipe(),
            [
                Change(id="a", kind=Kind.STEP_TEXT, step=1, text="ok"),
                Change(id="b", kind=Kind.SWAP, step=2, ingredient_id=1, to_ingredient_id=7),
            ],
        )
    with pytest.raises(InvalidVariationError, match="more than one new text"):
        validate_changes(
            _recipe(),
            [
                Change(id="a", kind=Kind.STEP_TEXT, step=1, text="ok"),
                Change(id="b", kind=Kind.STEP_TEXT, step=1, text="again"),
            ],
        )


def test_stale_steps_compare_snapshots() -> None:
    def snapshot(*texts: str) -> dict[str, object]:
        return {
            "original_locale": "de-AT",
            "steps": [{"translations": {"de-AT": {"text": t}}, "ingredients": []} for t in texts],
        }

    found = stale_steps(snapshot("a", "b", "c"), snapshot("a", "B"), [1, 2, 3], "de-AT")
    assert [(s.step, s.state, s.old_text, s.current_text) for s in found] == [
        (2, "changed", "b", "B"),
        (3, "deleted", "c", None),
    ]


def test_renumbering_after_adopting_added_steps() -> None:
    stored: list[dict[str, Any]] = [
        {"id": "x", "kind": "extra_step", "step": 1},
        {"id": "y", "kind": "step_text", "step": 2},
        {"id": "z", "kind": "extra_step", "step": 1},
        {"id": "w", "kind": "swap", "step": None},
    ]
    left = renumber_after_adoption(stored, {"x"})
    assert left == [
        {"id": "y", "kind": "step_text", "step": 3},
        {"id": "z", "kind": "extra_step", "step": 2},
        {"id": "w", "kind": "swap", "step": None},
    ]


def _user(user_id: int, permissions: list[str]) -> User:
    return User(
        id=user_id,
        full_name="",
        email="",
        created=NOW,
        hashed_password="",
        permissions=permissions,
    )


def test_private_variations_stay_private_for_managers() -> None:
    recipe = _recipe()
    variation = RecipeVariation(
        recipe_id=1, author_id=20, name="v", locale="de-AT", created=NOW, changed=NOW, private=True
    )
    manager = Viewer(user=_user(30, [Permission.MANAGE_RECIPES]))
    author = Viewer(user=_user(20, []))
    assert not can_view_variation(manager, recipe, variation)
    assert not can_delete_variation(manager, recipe, variation)
    assert can_view_variation(author, recipe, variation)
    variation.private = False
    assert can_delete_variation(manager, recipe, variation)
