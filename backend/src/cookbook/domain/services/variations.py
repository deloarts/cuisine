"""
Recipe variations: who may see and change them, the rules a variation's
changes follow, and how they apply to the original.

A variation stores differences only. Each change has a stable `id` and a
`kind` (`VariationChangeKind`):

- `swap`: another ingredient instead of `ingredient_id`, in step `step` or,
  with no step, in every step of the original and in its declared
  ingredient list. `keep_amount` keeps each
  line's amount, unit and note; otherwise the line takes `amount`, `unit_id`
  and `note`.
- `add_line`: an extra line in step `step`.
- `remove_line`: leaves out the lines of step `step` that name
  `ingredient_id` or `sub_recipe_id`.
- `step_text`: `text` replaces the text of step `step`.
- `extra_step`: a new step after step `step` (0 puts it first) with `text`,
  `duration_minutes`, its own lines and its own equipment.

Steps are numbered from 1 as the recipe was at the variation's base revision.
A variation names steps by that number, not by their public ids;
`stale_steps` tells when a step it names has changed or
gone since, and a change whose step or line no longer exists is skipped, not
applied somewhere else.

Applying a variation gives a recipe in the ordinary shape, so everything
derived from a recipe (ingredient list, nutrition, allergens, diets,
warnings, dinner guests, kitchen) is derived from a variation the same way.
"""

import copy
import re
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Literal

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepEquipment
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.variation import RecipeVariation
from src.cookbook.domain.exceptions import InvalidVariationError
from src.cookbook.domain.services.recipe_rules import can_edit_recipe
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.value_objects.enums import VariationChangeKind
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.domain.value_objects.viewer import Viewer
from src.platform.domain.value_objects.permission import Permission

MAX_CHANGES = 100
MAX_NAME = 120
MAX_NOTE = 1000
MAX_TEXT = 10_000
MAX_LINES = 50
MAX_MINUTES = 10_000

# ── Permissions ──────────────────────────────────────────────────────


def can_view_variation(viewer: Viewer, recipe: Recipe, variation: RecipeVariation) -> bool:
    """Whoever sees the recipe sees its variations, never more; a private
    variation is its author's alone, also for administrators."""
    if not can_view_recipe(viewer, recipe):
        return False
    return not variation.private or variation.author_id == viewer.id


def can_create_variation(viewer: Viewer, recipe: Recipe) -> bool:
    return viewer.user.has_permission(Permission.WRITE_RECIPES) and can_view_recipe(viewer, recipe)


def can_edit_variation(viewer: Viewer, recipe: Recipe, variation: RecipeVariation) -> bool:
    return (
        not variation.mirrored
        and variation.author_id is not None
        and variation.author_id == viewer.id
        and can_create_variation(viewer, recipe)
    )


def can_delete_variation(viewer: Viewer, recipe: Recipe, variation: RecipeVariation) -> bool:
    """Its author, or manage:recipes on a variation the manager can see. A
    variation that came with a mirror goes only with its source."""
    if variation.mirrored or not can_view_variation(viewer, recipe, variation):
        return False
    return variation.author_id == viewer.id or viewer.user.has_permission(Permission.MANAGE_RECIPES)


def can_adopt_variation(viewer: Viewer, recipe: Recipe, variation: RecipeVariation) -> bool:
    """The recipe's editors (owner, co-editors, manage:recipes) take over
    changes of a variation they can see."""
    return can_view_variation(viewer, recipe, variation) and can_edit_recipe(viewer, recipe)


# ── Changes ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LineSpec:
    """A line of an added step or an added line: a catalogue ingredient."""

    ingredient_id: int
    amount: float | None = None
    unit_id: int | None = None
    note: str = ""


@dataclass(frozen=True)
class EquipmentSpec:
    equipment_id: int
    count: int | None = None
    note: str = ""


@dataclass(frozen=True)
class Mention:
    """How a swap rewrites mentions of the swapped ingredient in step text:
    public ids and the new ingredient's name."""

    from_public_id: str
    to_public_id: str
    to_name: str


@dataclass(frozen=True)
class Change:
    """One change with internal ids, as the application resolved it."""

    id: str
    kind: VariationChangeKind
    step: int | None = None
    ingredient_id: int | None = None
    sub_recipe_id: int | None = None
    to_ingredient_id: int | None = None
    amount: float | None = None
    unit_id: int | None = None
    keep_amount: bool = True
    note: str = ""
    text: str = ""
    duration_minutes: int | None = None
    lines: tuple[LineSpec, ...] = ()
    equipment: tuple[EquipmentSpec, ...] = ()
    mention: Mention | None = None


def validate_header(name: str, note: str) -> None:
    if not name.strip():
        raise InvalidVariationError("A variation needs a name.")
    if len(name) > MAX_NAME:
        raise InvalidVariationError(f"The name of a variation has at most {MAX_NAME} characters.")
    if len(note) > MAX_NOTE:
        raise InvalidVariationError(f"The note of a variation has at most {MAX_NOTE} characters.")


def _lines_of(step: RecipeStep) -> tuple[set[int], set[int]]:
    return (
        {si.ingredient_id for si in step.ingredients if si.ingredient_id is not None},
        {si.sub_recipe_id for si in step.ingredients if si.sub_recipe_id is not None},
    )


def validate_changes(recipe: Recipe, changes: list[Change]) -> None:
    """The changes fit the recipe as it is now: every step they name exists
    and every line they swap or remove is there. Raised as
    `InvalidVariationError`, naming the change by its position from 1."""
    if len(changes) > MAX_CHANGES:
        raise InvalidVariationError(f"A variation has at most {MAX_CHANGES} changes.")
    count = len(recipe.steps)
    texts: set[int] = set()
    ids: set[str] = set()
    for number, change in enumerate(changes, start=1):
        where = f"Change {number}"
        if change.id in ids:
            raise InvalidVariationError(f"{where} repeats the id of another change.")
        ids.add(change.id)
        if change.amount is not None and change.amount < 0:
            raise InvalidVariationError(f"{where} has a negative amount.")
        if len(change.text) > MAX_TEXT or len(change.note) > 255:
            raise InvalidVariationError(f"{where} has a text that is too long.")
        if change.kind is VariationChangeKind.EXTRA_STEP:
            if change.step is None or not 0 <= change.step <= count:
                raise InvalidVariationError(f"{where} adds a step after a step the recipe lacks.")
            if not change.text.strip():
                raise InvalidVariationError(f"{where} adds a step without text.")
            if change.duration_minutes is not None and not (
                0 <= change.duration_minutes <= MAX_MINUTES
            ):
                raise InvalidVariationError(f"{where} has a duration out of range.")
            if len(change.lines) > MAX_LINES:
                raise InvalidVariationError(f"{where} has too many ingredients.")
            for line in change.lines:
                if line.amount is not None and line.amount < 0:
                    raise InvalidVariationError(f"{where} has a negative amount.")
            for item in change.equipment:
                if item.count is not None and not 1 <= item.count <= 100:
                    raise InvalidVariationError(f"{where} has an equipment count out of range.")
            continue
        if change.kind is VariationChangeKind.SWAP and change.step is None:
            if change.ingredient_id is None or change.to_ingredient_id is None:
                raise InvalidVariationError(f"{where} swaps without naming both ingredients.")
            if change.ingredient_id not in recipe.ingredient_ids:
                raise InvalidVariationError(f"{where} swaps an ingredient the recipe does not use.")
            continue
        if change.step is None or not 1 <= change.step <= count:
            raise InvalidVariationError(f"{where} names a step the recipe does not have.")
        ingredients, subs = _lines_of(recipe.steps[change.step - 1])
        match change.kind:
            case VariationChangeKind.SWAP:
                if change.ingredient_id is None or change.to_ingredient_id is None:
                    raise InvalidVariationError(f"{where} swaps without naming both ingredients.")
                if change.ingredient_id not in ingredients:
                    raise InvalidVariationError(
                        f"{where} swaps an ingredient step {change.step} does not use."
                    )
            case VariationChangeKind.ADD_LINE:
                if change.ingredient_id is None:
                    raise InvalidVariationError(f"{where} adds a line without an ingredient.")
            case VariationChangeKind.REMOVE_LINE:
                if (change.ingredient_id is None) == (change.sub_recipe_id is None):
                    raise InvalidVariationError(
                        f"{where} removes a line by naming exactly one ingredient or recipe."
                    )
                if (
                    change.ingredient_id is not None and change.ingredient_id not in ingredients
                ) or (change.sub_recipe_id is not None and change.sub_recipe_id not in subs):
                    raise InvalidVariationError(
                        f"{where} removes a line step {change.step} does not have."
                    )
            case VariationChangeKind.STEP_TEXT:
                if not change.text.strip():
                    raise InvalidVariationError(f"{where} gives a step an empty text.")
                if change.step in texts:
                    raise InvalidVariationError(f"Step {change.step} has more than one new text.")
                texts.add(change.step)


# ── Applying ─────────────────────────────────────────────────────────


@dataclass
class LineMarker:
    """A line of the applied recipe that the variation swapped or added:
    its index (from 0) within its step."""

    index: int
    kind: Literal["swapped", "added"]
    change_id: str
    # On a swap: the ingredient the original names here.
    swapped_from_ingredient_id: int | None = None


@dataclass
class RemovedLine:
    change_id: str
    ingredient_id: int | None
    sub_recipe_id: int | None
    amount: float | None
    unit_id: int | None


@dataclass
class StepMarker:
    """What the variation did to one step of the applied recipe."""

    # From 1, in the applied recipe.
    position: int
    # From 1, in the original; None for a step the variation adds.
    origin_step: int | None
    added: bool = False
    text_changed: bool = False
    change_ids: list[str] = field(default_factory=list)
    lines: list[LineMarker] = field(default_factory=list)
    removed: list[RemovedLine] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.added or self.text_changed or bool(self.lines) or bool(self.removed)


@dataclass
class AppliedVariation:
    recipe: Recipe
    steps: list[StepMarker]
    # Changes whose step or line no longer exists in the recipe.
    skipped_change_ids: list[str]


def _texts(text: str, locale: str, original_locale: str) -> dict[str, StepText]:
    """A variation's text stands for the step in its own locale and, so the
    recipe stays readable in its original language, in that one too."""
    return {locale: StepText(text.strip()), original_locale: StepText(text.strip())}


def _rewrite_mentions(text: str, mention: Mention) -> str:
    pattern = re.compile(
        r"@\[([^\]\n]+)\]\(ingredient:" + re.escape(mention.from_public_id) + r"\)", re.IGNORECASE
    )
    name = mention.to_name.replace("]", "").replace("\n", " ") or "?"
    return pattern.sub(f"@[{name}](ingredient:{mention.to_public_id})", text)


def _swapped(line: StepIngredient, change: Change, locale: str) -> StepIngredient:
    assert change.to_ingredient_id is not None
    # A swap changes what the line holds, not which line it is.
    if change.keep_amount:
        return StepIngredient(
            public_id=line.public_id,
            ingredient_id=change.to_ingredient_id,
            amount=line.amount,
            unit_id=line.unit_id,
            translations=dict(line.translations),
        )
    return StepIngredient(
        public_id=line.public_id,
        ingredient_id=change.to_ingredient_id,
        amount=change.amount,
        unit_id=change.unit_id,
        translations={locale: NoteText(change.note.strip())} if change.note.strip() else {},
    )


def apply_variation(recipe: Recipe, changes: list[Change], locale: str) -> AppliedVariation:
    """The recipe with the changes applied, and a marker per step saying
    what differs. The recipe itself is left untouched."""
    applied = copy.deepcopy(recipe)
    original = recipe.original_locale
    skipped: list[str] = []
    count = len(recipe.steps)
    by_step: dict[int, list[Change]] = {}
    wide: list[Change] = []
    inserts: dict[int, list[Change]] = {}
    for change in changes:
        if change.kind is VariationChangeKind.EXTRA_STEP:
            if change.step is None or not 0 <= change.step <= count:
                skipped.append(change.id)
            else:
                inserts.setdefault(change.step, []).append(change)
        elif change.kind is VariationChangeKind.SWAP and change.step is None:
            wide.append(change)
        elif change.step is None or not 1 <= change.step <= count:
            skipped.append(change.id)
        else:
            by_step.setdefault(change.step, []).append(change)

    wide_hits: set[str] = set()
    steps: list[tuple[RecipeStep, StepMarker]] = []

    def add_inserts(after: int) -> None:
        for change in inserts.get(after, []):
            lines = [
                StepIngredient(
                    ingredient_id=line.ingredient_id,
                    amount=line.amount,
                    unit_id=line.unit_id,
                    translations={locale: NoteText(line.note.strip())} if line.note.strip() else {},
                )
                for line in change.lines
            ]
            step = RecipeStep(
                translations=_texts(change.text, locale, original),
                duration_minutes=change.duration_minutes,
                ingredients=lines,
                equipment=[
                    StepEquipment(
                        equipment_id=item.equipment_id,
                        count=item.count,
                        translations=(
                            {locale: NoteText(item.note.strip())} if item.note.strip() else {}
                        ),
                    )
                    for item in change.equipment
                ],
            )
            marker = StepMarker(
                position=0,
                origin_step=None,
                added=True,
                change_ids=[change.id],
                lines=[
                    LineMarker(index=i, kind="added", change_id=change.id)
                    for i in range(len(lines))
                ],
            )
            steps.append((step, marker))

    add_inserts(0)
    for number, step in enumerate(applied.steps, start=1):
        marker = StepMarker(position=0, origin_step=number)
        own = by_step.get(number, [])
        # Each line remembers the change that made it, if any.
        lines: list[tuple[StepIngredient, LineMarker | None]] = [
            (si, None) for si in step.ingredients
        ]
        for change in own:
            if change.kind is VariationChangeKind.STEP_TEXT:
                step.translations = _texts(change.text, locale, original)
                marker.text_changed = True
                marker.change_ids.append(change.id)
        for change in own:
            if change.kind is not VariationChangeKind.REMOVE_LINE:
                continue
            kept = []
            for si, made in lines:
                hit = made is None and (
                    (change.ingredient_id is not None and si.ingredient_id == change.ingredient_id)
                    or (
                        change.sub_recipe_id is not None
                        and si.sub_recipe_id == change.sub_recipe_id
                    )
                )
                if hit:
                    marker.removed.append(
                        RemovedLine(
                            change_id=change.id,
                            ingredient_id=si.ingredient_id,
                            sub_recipe_id=si.sub_recipe_id,
                            amount=si.amount,
                            unit_id=si.unit_id,
                        )
                    )
                else:
                    kept.append((si, made))
            if len(kept) == len(lines):
                skipped.append(change.id)
            else:
                marker.change_ids.append(change.id)
            lines = kept
        swaps = [c for c in own if c.kind is VariationChangeKind.SWAP]
        for change in [*swaps, *wide]:
            hit = False
            for index, (si, made) in enumerate(lines):
                if made is None and si.ingredient_id == change.ingredient_id:
                    lines[index] = (
                        _swapped(si, change, locale),
                        LineMarker(
                            index=0,
                            kind="swapped",
                            change_id=change.id,
                            swapped_from_ingredient_id=si.ingredient_id,
                        ),
                    )
                    hit = True
            if hit:
                if change.mention is not None:
                    step.translations = {
                        k: StepText(_rewrite_mentions(v.text, change.mention))
                        for k, v in step.translations.items()
                    }
                marker.change_ids.append(change.id)
                if change in wide:
                    wide_hits.add(change.id)
            elif change not in wide:
                skipped.append(change.id)
        for change in own:
            if change.kind is not VariationChangeKind.ADD_LINE:
                continue
            assert change.ingredient_id is not None
            lines.append(
                (
                    StepIngredient(
                        ingredient_id=change.ingredient_id,
                        amount=change.amount,
                        unit_id=change.unit_id,
                        translations=(
                            {locale: NoteText(change.note.strip())} if change.note.strip() else {}
                        ),
                    ),
                    LineMarker(index=0, kind="added", change_id=change.id),
                )
            )
            marker.change_ids.append(change.id)
        step.ingredients = [si for si, _ in lines]
        marker.lines = [
            LineMarker(
                index=index,
                kind=made.kind,
                change_id=made.change_id,
                swapped_from_ingredient_id=made.swapped_from_ingredient_id,
            )
            for index, (_, made) in enumerate(lines)
            if made is not None
        ]
        steps.append((step, marker))
        add_inserts(number)
    # A swap in every step covers the declared ingredient list too, so the
    # swapped ingredient does not come back through it.
    for change in wide:
        for index, line in enumerate(applied.ingredients):
            if line.ingredient_id == change.ingredient_id:
                applied.ingredients[index] = _swapped(line, change, locale)
                wide_hits.add(change.id)
    skipped.extend(c.id for c in wide if c.id not in wide_hits)
    applied.steps = [step for step, _ in steps]
    markers = [marker for _, marker in steps]
    for position, marker in enumerate(markers, start=1):
        marker.position = position
    order = {c.id: i for i, c in enumerate(changes)}
    return AppliedVariation(
        recipe=applied,
        steps=markers,
        skipped_change_ids=sorted(set(skipped), key=lambda i: order.get(i, 0)),
    )


# ── Staleness ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StaleStep:
    """A step a variation names that changed or went since its base
    revision, with the text it had then."""

    step: int
    state: Literal["changed", "deleted"]
    old_text: str
    current_text: str | None


def referenced_steps(stored: Iterable[dict[str, Any]]) -> list[int]:
    """The original steps the stored changes name (an added step names the
    step it follows)."""
    found: set[int] = set()
    for change in stored:
        step = change.get("step")
        if isinstance(step, int) and step >= 1:
            found.add(step)
    return sorted(found)


def _step_text(step: dict[str, Any], locale: str, original_locale: str) -> str:
    texts: dict[str, dict[str, str]] = step.get("translations", {})
    chosen = texts.get(locale) or texts.get(original_locale) or next(iter(texts.values()), {})
    return str(chosen.get("text", ""))


def _content(step: dict[str, Any]) -> tuple[Any, Any]:
    # A line's own id is not content: snapshots from before lines had ids
    # compare equal to newer ones with the same lines.
    lines = [{k: v for k, v in line.items() if k != "id"} for line in step.get("ingredients", [])]
    return step.get("translations", {}), lines


def stale_steps(
    base: dict[str, Any], current: dict[str, Any], steps: Iterable[int], locale: str
) -> list[StaleStep]:
    """Compares two revision snapshots for the named steps: a step whose
    text or lines differ is `changed`, a step the current recipe no longer
    has is `deleted`."""
    base_steps: list[dict[str, Any]] = base.get("steps", [])
    now_steps: list[dict[str, Any]] = current.get("steps", [])
    base_locale = str(base.get("original_locale", locale))
    now_locale = str(current.get("original_locale", locale))
    found: list[StaleStep] = []
    for number in steps:
        if number > len(base_steps):
            continue
        old = base_steps[number - 1]
        old_text = _step_text(old, locale, base_locale)
        if number > len(now_steps):
            found.append(StaleStep(number, "deleted", old_text, None))
        elif _content(old) != _content(now_steps[number - 1]):
            found.append(
                StaleStep(
                    number,
                    "changed",
                    old_text,
                    _step_text(now_steps[number - 1], locale, now_locale),
                )
            )
    return found


# ── Adopting ─────────────────────────────────────────────────────────


def renumber_after_adoption(
    stored: list[dict[str, Any]], adopted_ids: set[str]
) -> list[dict[str, Any]]:
    """The changes left after `adopted_ids` went into the original, with
    their step numbers moved past the steps the adopted changes added. A
    remaining added step after the same step follows the adopted ones."""
    inserted = [
        int(c.get("step") or 0)
        for c in stored
        if c.get("id") in adopted_ids and c.get("kind") == VariationChangeKind.EXTRA_STEP.value
    ]

    def moved(number: int) -> int:
        return number + sum(1 for after in inserted if after < number)

    remaining: list[dict[str, Any]] = []
    for change in stored:
        if change.get("id") in adopted_ids:
            continue
        kept = dict(change)
        step = kept.get("step")
        if isinstance(step, int):
            if kept.get("kind") == VariationChangeKind.EXTRA_STEP.value:
                kept["step"] = moved(step) + sum(1 for after in inserted if after == step)
            else:
                kept["step"] = moved(step)
        remaining.append(kept)
    return remaining
