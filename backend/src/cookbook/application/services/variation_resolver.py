"""
Translates between a variation's stored changes, which name records by
public id (`domain/entities/variation.py`), and the domain's changes with
internal ids (`domain/services/variations.py`). Storing public ids lets a
variation outlive a merged or deleted ingredient: such a change is reported
as unavailable and left out instead of failing the whole variation.

One resolver serves one request and remembers every record it looked up.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from uuid import uuid4

from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.exceptions import EquipmentNotFoundError
from src.cookbook.domain.exceptions import IngredientNotFoundError
from src.cookbook.domain.exceptions import InvalidVariationError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.exceptions import UnitNotFoundError
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.services.variations import Change
from src.cookbook.domain.services.variations import EquipmentSpec
from src.cookbook.domain.services.variations import LineSpec
from src.cookbook.domain.services.variations import Mention
from src.cookbook.domain.value_objects.enums import VariationChangeKind
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository


@dataclass(frozen=True)
class VariationLineCommand:
    ingredient_id: str
    amount: float | None = None
    unit_id: str | None = None
    note: str = ""


@dataclass(frozen=True)
class VariationEquipmentCommand:
    equipment_id: str
    count: int | None = None
    note: str = ""


@dataclass(frozen=True)
class VariationChangeCommand:
    """One change as the editor sends it, records by public id. `id` keeps
    an existing change's id on an update; a new change gets one."""

    kind: VariationChangeKind
    id: str | None = None
    step: int | None = None
    ingredient_id: str | None = None
    sub_recipe_id: str | None = None
    to_ingredient_id: str | None = None
    amount: float | None = None
    unit_id: str | None = None
    keep_amount: bool = True
    note: str = ""
    text: str = ""
    duration_minutes: int | None = None
    lines: list[VariationLineCommand] = field(default_factory=list)
    equipment: list[VariationEquipmentCommand] = field(default_factory=list)


@dataclass
class Resolved:
    changes: list[Change]
    # Changes naming a record that no longer exists.
    unavailable_ids: list[str]


def _id(value: str | None) -> str | None:
    return value.strip().lower() if value else None


class VariationResolver:
    def __init__(
        self,
        *,
        ingredient_repo: IIngredientRepository,
        unit_repo: IUnitRepository,
        equipment_repo: IEquipmentRepository,
        recipe_repo: IRecipeRepository,
    ) -> None:
        self._ingredient_repo = ingredient_repo
        self._unit_repo = unit_repo
        self._equipment_repo = equipment_repo
        self._recipe_repo = recipe_repo
        self.ingredients: dict[str, Ingredient | None] = {}
        self.units: dict[str, Unit | None] = {}
        self.equipment: dict[str, Equipment | None] = {}
        self.recipes: dict[str, Recipe | None] = {}

    async def ingredient(self, public_id: str | None) -> Ingredient | None:
        key = _id(public_id)
        if key is None:
            return None
        if key not in self.ingredients:
            self.ingredients[key] = await self._ingredient_repo.get_by_public_id(key)
        return self.ingredients[key]

    async def unit(self, public_id: str | None) -> Unit | None:
        key = _id(public_id)
        if key is None:
            return None
        if key not in self.units:
            self.units[key] = await self._unit_repo.get_by_public_id(key)
        return self.units[key]

    async def equipment_item(self, public_id: str | None) -> Equipment | None:
        key = _id(public_id)
        if key is None:
            return None
        if key not in self.equipment:
            self.equipment[key] = await self._equipment_repo.get_by_public_id(key)
        return self.equipment[key]

    async def recipe(self, public_id: str | None) -> Recipe | None:
        key = _id(public_id)
        if key is None:
            return None
        if key not in self.recipes:
            self.recipes[key] = await self._recipe_repo.get_by_public_id(key)
        return self.recipes[key]

    def ingredient_by_id(self, internal: int) -> Ingredient | None:
        return next((i for i in self.ingredients.values() if i and i.id == internal), None)

    # ── Commands to stored changes ───────────────────────────────────

    async def stored(self, commands: list[VariationChangeCommand]) -> list[dict[str, Any]]:
        """The changes as they are stored. Every record they name must exist
        (404 otherwise); the shape rules are checked on the resolved changes."""

        async def need_ingredient(public_id: str | None) -> str | None:
            if public_id is None:
                return None
            if await self.ingredient(public_id) is None:
                raise IngredientNotFoundError("An ingredient of the variation does not exist.")
            return _id(public_id)

        async def need_unit(public_id: str | None) -> str | None:
            if public_id is None:
                return None
            if await self.unit(public_id) is None:
                raise UnitNotFoundError("A unit of the variation does not exist.")
            return _id(public_id)

        async def need_equipment(public_id: str) -> str:
            if await self.equipment_item(public_id) is None:
                raise EquipmentNotFoundError("An equipment item of the variation does not exist.")
            return str(_id(public_id))

        async def need_recipe(public_id: str | None) -> str | None:
            if public_id is None:
                return None
            if await self.recipe(public_id) is None:
                raise RecipeNotFoundError("A recipe the variation names does not exist.")
            return _id(public_id)

        result: list[dict[str, Any]] = []
        for cmd in commands:
            change: dict[str, Any] = {
                "id": (cmd.id or "").strip() or uuid4().hex,
                "kind": cmd.kind.value,
                "step": cmd.step,
            }
            match cmd.kind:
                case VariationChangeKind.SWAP:
                    change |= {
                        "ingredient_id": await need_ingredient(cmd.ingredient_id),
                        "to_ingredient_id": await need_ingredient(cmd.to_ingredient_id),
                        "keep_amount": cmd.keep_amount,
                        "amount": None if cmd.keep_amount else cmd.amount,
                        "unit_id": None if cmd.keep_amount else await need_unit(cmd.unit_id),
                        "note": "" if cmd.keep_amount else cmd.note.strip(),
                    }
                case VariationChangeKind.ADD_LINE:
                    change |= {
                        "ingredient_id": await need_ingredient(cmd.ingredient_id),
                        "amount": cmd.amount,
                        "unit_id": await need_unit(cmd.unit_id),
                        "note": cmd.note.strip(),
                    }
                case VariationChangeKind.REMOVE_LINE:
                    change |= {
                        "ingredient_id": await need_ingredient(cmd.ingredient_id),
                        "sub_recipe_id": await need_recipe(cmd.sub_recipe_id),
                    }
                case VariationChangeKind.STEP_TEXT:
                    change |= {"text": cmd.text.strip()}
                case VariationChangeKind.EXTRA_STEP:
                    change |= {
                        "text": cmd.text.strip(),
                        "duration_minutes": cmd.duration_minutes,
                        "lines": [
                            {
                                "ingredient_id": await need_ingredient(line.ingredient_id),
                                "amount": line.amount,
                                "unit_id": await need_unit(line.unit_id),
                                "note": line.note.strip(),
                            }
                            for line in cmd.lines
                        ],
                        "equipment": [
                            {
                                "equipment_id": await need_equipment(item.equipment_id),
                                "count": item.count,
                                "note": item.note.strip(),
                            }
                            for item in cmd.equipment
                        ],
                    }
            result.append(change)
        return result

    # ── Stored changes to domain changes ─────────────────────────────

    async def resolve(self, stored: list[dict[str, Any]], locale: str) -> Resolved:
        changes: list[Change] = []
        unavailable: list[str] = []
        for raw in stored:
            try:
                changes.append(await self._change(raw, locale))
            except LookupError:
                unavailable.append(str(raw.get("id", "")))
        return Resolved(changes=changes, unavailable_ids=unavailable)

    async def _must[T](self, value: T | None) -> T:
        if value is None:
            raise LookupError
        return value

    async def _change(self, raw: dict[str, Any], locale: str) -> Change:
        try:
            kind = VariationChangeKind(raw.get("kind"))
        except ValueError as exc:
            raise InvalidVariationError("A stored change has an unknown kind.") from exc
        ingredient = await self.ingredient(raw.get("ingredient_id"))
        if raw.get("ingredient_id") and ingredient is None:
            raise LookupError
        sub = await self.recipe(raw.get("sub_recipe_id"))
        if raw.get("sub_recipe_id") and sub is None:
            raise LookupError
        target = await self.ingredient(raw.get("to_ingredient_id"))
        if raw.get("to_ingredient_id") and target is None:
            raise LookupError
        unit = await self.unit(raw.get("unit_id"))
        if raw.get("unit_id") and unit is None:
            raise LookupError
        lines: list[LineSpec] = []
        for line in raw.get("lines", []):
            line_ingredient = await self._must(await self.ingredient(line.get("ingredient_id")))
            line_unit = await self.unit(line.get("unit_id"))
            if line.get("unit_id") and line_unit is None:
                raise LookupError
            lines.append(
                LineSpec(
                    ingredient_id=line_ingredient.id,
                    amount=line.get("amount"),
                    unit_id=line_unit.id if line_unit else None,
                    note=str(line.get("note") or ""),
                )
            )
        equipment: list[EquipmentSpec] = []
        for item in raw.get("equipment", []):
            found = await self._must(await self.equipment_item(item.get("equipment_id")))
            equipment.append(
                EquipmentSpec(
                    equipment_id=found.id,
                    count=item.get("count"),
                    note=str(item.get("note") or ""),
                )
            )
        mention = None
        if kind is VariationChangeKind.SWAP and ingredient is not None and target is not None:
            mention = Mention(
                from_public_id=str(ingredient.public_id).lower(),
                to_public_id=str(target.public_id).lower(),
                to_name=resolve(target.translations, locale, target.original_locale)[1].name,
            )
        step = raw.get("step")
        return Change(
            id=str(raw.get("id", "")),
            kind=kind,
            step=int(step) if isinstance(step, int) else None,
            ingredient_id=ingredient.id if ingredient else None,
            sub_recipe_id=sub.id if sub else None,
            to_ingredient_id=target.id if target else None,
            amount=raw.get("amount"),
            unit_id=unit.id if unit else None,
            keep_amount=bool(raw.get("keep_amount", True)),
            note=str(raw.get("note") or ""),
            text=str(raw.get("text") or ""),
            duration_minutes=raw.get("duration_minutes"),
            lines=tuple(lines),
            equipment=tuple(equipment),
            mention=mention,
        )
