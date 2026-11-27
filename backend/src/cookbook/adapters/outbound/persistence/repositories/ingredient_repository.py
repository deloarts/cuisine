from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import CompoundSelect

from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingItemModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import EquipmentAliasModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import EquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import (
    EquipmentTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientAliasModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import (
    IngredientConversionModel,
)
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import (
    IngredientTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.personal_models import FoodRestrictionModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeStepModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import StepIngredientModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import IngredientFamilyModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientFamilyTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.repositories._like import contains_pattern
from src.cookbook.adapters.outbound.persistence.repositories._like import lower_contains
from src.cookbook.adapters.outbound.persistence.repositories._translations import load_translations
from src.cookbook.adapters.outbound.persistence.repositories._translations import (
    replace_translations,
)
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.ingredient import UnitConversion
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import NutritionSource
from src.cookbook.domain.value_objects.nutrition import NUTRIENTS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.ports.outbound.repositories.ingredient_repository import IngredientQuery
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id


def _text(row: IngredientTranslationModel) -> IngredientText:
    return IngredientText(name=row.name, plural_name=row.plural_name)


def _allergens(values: list[str] | None) -> list[Allergen]:
    known = {a.value for a in Allergen}
    return [Allergen(v) for v in (values or []) if v in known]


def _markers(values: list[str] | None) -> list[DietMarker]:
    known = {m.value for m in DietMarker}
    return [DietMarker(v) for v in (values or []) if v in known]


def name_matches(search: str) -> CompoundSelect[tuple[int]]:
    """The ids of ingredients with a name or alias containing `search` in
    any locale, as a subquery."""
    pattern = contains_pattern(search)
    by_name = select(IngredientTranslationModel.ingredient_id).where(
        lower_contains(IngredientTranslationModel.name, pattern)
        | lower_contains(IngredientTranslationModel.plural_name, pattern)
    )
    by_alias = select(IngredientAliasModel.ingredient_id).where(
        lower_contains(IngredientAliasModel.alias, pattern)
    )
    return by_name.union(by_alias)


@dataclass(frozen=True)
class CatalogueName:
    """One name of the shared namespace: whose it is and the entry's main
    name to show in a conflict."""

    kind: str
    id: int
    public_id: str
    name: str
    main_name: str
    # The family an ingredient's name belongs to; a family may share a name
    # with its own members.
    family_id: int | None = None


@dataclass(frozen=True)
class SeedIndex:
    """The seed keys and the casefolded names already in the catalogue."""

    keys: set[str]
    names: set[str]


class SqlAlchemyIngredientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entities(self, rows: list[IngredientModel]) -> list[Ingredient]:
        ids = [r.id for r in rows]
        texts = await load_translations(
            self._db, IngredientTranslationModel, "ingredient_id", ids, _text
        )
        aliases: dict[int, dict[str, list[str]]] = {i: {} for i in ids}
        if ids:
            for row in (
                await self._db.scalars(
                    select(IngredientAliasModel)
                    .where(IngredientAliasModel.ingredient_id.in_(ids))
                    .order_by(IngredientAliasModel.alias)
                )
            ).all():
                aliases[row.ingredient_id].setdefault(row.locale, []).append(row.alias)
        conversions: dict[int, list[UnitConversion]] = {i: [] for i in ids}
        if ids:
            result = await self._db.scalars(
                select(IngredientConversionModel)
                .where(IngredientConversionModel.ingredient_id.in_(ids))
                .order_by(IngredientConversionModel.unit_id)
            )
            for c in result.all():
                conversions[c.ingredient_id].append(UnitConversion(c.unit_id, c.grams))
        return [
            Ingredient(
                id=r.id,
                public_id=r.public_id,
                owner_id=r.owner_id,
                original_locale=r.original_locale,
                created=r.created,
                changed=r.changed,
                translations=texts.get(r.id, {}),
                category_id=r.category_id,
                family_id=r.family_id,
                aliases=aliases.get(r.id, {}),
                nutrition=Nutrition(**{n: getattr(r, n) for n in NUTRIENTS}),
                extended_nutrition={
                    k: float(v)
                    for k, v in (r.extended_nutrition or {}).items()
                    if isinstance(v, int | float)
                },
                season_months=sorted(int(m) for m in (r.season_months or [])),
                density_g_per_ml=r.density_g_per_ml,
                conversions=conversions.get(r.id, []),
                allergens=_allergens(r.allergens),
                diet_markers=_markers(r.diet_markers),
                status=IngredientStatus(r.status),
                nutrition_source=NutritionSource(r.nutrition_source),
                usda_fdc_id=r.usda_fdc_id,
                seed_key=r.seed_key,
            )
            for r in rows
        ]

    async def get(self, ingredient_id: int) -> Ingredient | None:
        row = await self._db.get(IngredientModel, ingredient_id)
        return (await self._entities([row]))[0] if row is not None else None

    async def get_by_public_id(self, public_id: str) -> Ingredient | None:
        """An ingredient of the catalogue; an archived one counts as gone."""
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(IngredientModel).where(
                IngredientModel.public_id == uid,
                IngredientModel.status != IngredientStatus.ARCHIVED.value,
            )
        )
        return (await self._entities([row]))[0] if row is not None else None

    async def get_many(self, ids: list[int]) -> list[Ingredient]:
        if not ids:
            return []
        rows = await self._db.scalars(
            select(IngredientModel).where(IngredientModel.id.in_(sorted(set(ids))))
        )
        return await self._entities(list(rows.all()))

    async def find(self, query: IngredientQuery) -> list[Ingredient]:
        """Every match, sorted by name in its original locale. The catalogue
        of a household stays small enough to page in memory."""
        stmt = select(IngredientModel).where(
            IngredientModel.status != IngredientStatus.ARCHIVED.value
        )
        if query.search and query.search.strip():
            stmt = stmt.where(IngredientModel.id.in_(name_matches(query.search)))
        if query.category_id is not None:
            stmt = stmt.where(IngredientModel.category_id == query.category_id)
        if query.family_id is not None:
            stmt = stmt.where(IngredientModel.family_id == query.family_id)
        if query.status is not None:
            stmt = stmt.where(IngredientModel.status == query.status.value)
        if query.owner_id is not None:
            stmt = stmt.where(IngredientModel.owner_id == query.owner_id)
        found = await self._entities(list((await self._db.scalars(stmt)).all()))
        return sorted(
            found,
            key=lambda i: (
                resolve(i.translations, None, i.original_locale)[1].name.lower()
                if i.translations
                else ""
            ),
        )

    async def find_by_name(self, name: str) -> Ingredient | None:
        """An ingredient whose singular or plural name equals `name` in any
        locale, ignoring case."""
        wanted = name.strip().lower()
        alias_id = await self._db.scalar(
            select(IngredientAliasModel.ingredient_id)
            .join(IngredientModel, IngredientModel.id == IngredientAliasModel.ingredient_id)
            .where(
                func.lower(IngredientAliasModel.alias) == wanted,
                IngredientModel.status != IngredientStatus.ARCHIVED.value,
            )
            .order_by(IngredientAliasModel.ingredient_id)
            .limit(1)
        )
        row_id = await self._db.scalar(
            select(IngredientTranslationModel.ingredient_id)
            .join(IngredientModel, IngredientModel.id == IngredientTranslationModel.ingredient_id)
            .where(
                (func.lower(IngredientTranslationModel.name) == wanted)
                | (func.lower(IngredientTranslationModel.plural_name) == wanted),
                IngredientModel.status != IngredientStatus.ARCHIVED.value,
            )
            .order_by(IngredientTranslationModel.ingredient_id)
            .limit(1)
        )
        found = row_id if row_id is not None else alias_id
        return await self.get(found) if found is not None else None

    async def find_by_names(self, names: list[str]) -> Ingredient | None:
        """The ingredient `find_by_name` gives for the first of `names` that
        matches, looked up in two queries rather than two per name."""
        wanted = list(dict.fromkeys(n.strip().lower() for n in names if n.strip()))
        if not wanted:
            return None
        active = IngredientModel.status != IngredientStatus.ARCHIVED.value
        by_text = await self._db.execute(
            select(
                IngredientTranslationModel.ingredient_id,
                func.lower(IngredientTranslationModel.name),
                func.lower(IngredientTranslationModel.plural_name),
            )
            .join(IngredientModel, IngredientModel.id == IngredientTranslationModel.ingredient_id)
            .where(
                func.lower(IngredientTranslationModel.name).in_(wanted)
                | func.lower(IngredientTranslationModel.plural_name).in_(wanted),
                active,
            )
        )
        by_alias = await self._db.execute(
            select(IngredientAliasModel.ingredient_id, func.lower(IngredientAliasModel.alias))
            .join(IngredientModel, IngredientModel.id == IngredientAliasModel.ingredient_id)
            .where(func.lower(IngredientAliasModel.alias).in_(wanted), active)
        )
        text_ids: dict[str, int] = {}
        for ingredient_id, name, plural in by_text.all():
            for key in (name, plural):
                if key in wanted:
                    text_ids[key] = min(text_ids.get(key, ingredient_id), ingredient_id)
        alias_ids: dict[str, int] = {}
        for ingredient_id, alias in by_alias.all():
            alias_ids[alias] = min(alias_ids.get(alias, ingredient_id), ingredient_id)
        for name in wanted:
            found = text_ids.get(name, alias_ids.get(name))
            if found is not None:
                return await self.get(found)
        return None

    async def catalogue_names(self, locale: str) -> list[CatalogueName]:
        """Every ingredient main name and alias, every family name and every
        equipment name and alias in `locale`; archived ingredients keep
        theirs out of the namespace."""
        names: list[CatalogueName] = []
        for ingredient_id, public_id, family_id, name in (
            await self._db.execute(
                select(
                    IngredientModel.id,
                    IngredientModel.public_id,
                    IngredientModel.family_id,
                    IngredientTranslationModel.name,
                )
                .join(
                    IngredientModel, IngredientModel.id == IngredientTranslationModel.ingredient_id
                )
                .where(
                    IngredientTranslationModel.locale == locale,
                    IngredientModel.status != IngredientStatus.ARCHIVED.value,
                )
            )
        ).all():
            names.append(
                CatalogueName("ingredient", ingredient_id, str(public_id), name, name, family_id)
            )
        for ingredient_id, public_id, family_id, alias, main in (
            await self._db.execute(
                select(
                    IngredientModel.id,
                    IngredientModel.public_id,
                    IngredientModel.family_id,
                    IngredientAliasModel.alias,
                    IngredientTranslationModel.name,
                )
                .join(IngredientModel, IngredientModel.id == IngredientAliasModel.ingredient_id)
                .outerjoin(
                    IngredientTranslationModel,
                    (IngredientTranslationModel.ingredient_id == IngredientModel.id)
                    & (IngredientTranslationModel.locale == IngredientModel.original_locale),
                )
                .where(
                    IngredientAliasModel.locale == locale,
                    IngredientModel.status != IngredientStatus.ARCHIVED.value,
                )
            )
        ).all():
            names.append(
                CatalogueName(
                    "ingredient", ingredient_id, str(public_id), alias, main or alias, family_id
                )
            )
        for family_id, public_id, name in (
            await self._db.execute(
                select(
                    IngredientFamilyModel.id,
                    IngredientFamilyModel.public_id,
                    IngredientFamilyTranslationModel.name,
                )
                .join(
                    IngredientFamilyModel,
                    IngredientFamilyModel.id == IngredientFamilyTranslationModel.family_id,
                )
                .where(IngredientFamilyTranslationModel.locale == locale)
            )
        ).all():
            names.append(CatalogueName("family", family_id, str(public_id), name, name))
        # Equipment shares the namespace, so a name means one thing only.
        equipment_main = dict(
            (
                await self._db.execute(
                    select(EquipmentTranslationModel.equipment_id, EquipmentTranslationModel.name)
                    .join(
                        EquipmentModel, EquipmentModel.id == EquipmentTranslationModel.equipment_id
                    )
                    .where(EquipmentTranslationModel.locale == locale)
                )
            )
            .tuples()
            .all()
        )
        equipment_ids = dict(
            (await self._db.execute(select(EquipmentModel.id, EquipmentModel.public_id)))
            .tuples()
            .all()
        )
        for equipment_id, name in equipment_main.items():
            names.append(
                CatalogueName(
                    "equipment", equipment_id, str(equipment_ids[equipment_id]), name, name
                )
            )
        for equipment_id, alias in (
            await self._db.execute(
                select(EquipmentAliasModel.equipment_id, EquipmentAliasModel.alias).where(
                    EquipmentAliasModel.locale == locale
                )
            )
        ).all():
            names.append(
                CatalogueName(
                    "equipment",
                    equipment_id,
                    str(equipment_ids[equipment_id]),
                    alias,
                    equipment_main.get(equipment_id, alias),
                )
            )
        return names

    async def name_owners(self, locale: str, names: list[str]) -> dict[str, int]:
        """Which ingredient already uses each of `names` (casefolded) as main
        name or alias in `locale`, for the alias rule and the duplicate
        warning."""
        wanted = {n.strip().lower() for n in names if n.strip()}
        if not wanted:
            return {}
        owners: dict[str, int] = {}
        for ingredient_id, name in (
            await self._db.execute(
                select(IngredientTranslationModel.ingredient_id, IngredientTranslationModel.name)
                .join(
                    IngredientModel, IngredientModel.id == IngredientTranslationModel.ingredient_id
                )
                .where(
                    IngredientTranslationModel.locale == locale,
                    func.lower(IngredientTranslationModel.name).in_(wanted),
                    IngredientModel.status != IngredientStatus.ARCHIVED.value,
                )
            )
        ).all():
            owners.setdefault(name.lower(), ingredient_id)
        for ingredient_id, alias in (
            await self._db.execute(
                select(IngredientAliasModel.ingredient_id, IngredientAliasModel.alias).where(
                    IngredientAliasModel.locale == locale,
                    func.lower(IngredientAliasModel.alias).in_(wanted),
                )
            )
        ).all():
            owners.setdefault(alias.lower(), ingredient_id)
        return owners

    async def by_seed_keys(self, keys: list[str]) -> dict[str, Ingredient]:
        """The seeded ingredients with these reference keys, by key."""
        if not keys:
            return {}
        rows = await self._db.scalars(
            select(IngredientModel).where(IngredientModel.seed_key.in_(keys))
        )
        return {i.seed_key: i for i in await self._entities(list(rows.all())) if i.seed_key}

    async def find_seeded_or_named(self) -> SeedIndex:
        keys = set(
            (
                await self._db.scalars(
                    select(IngredientModel.seed_key).where(IngredientModel.seed_key.is_not(None))
                )
            ).all()
        )
        names: set[str] = set()
        for name, plural in (
            await self._db.execute(
                select(IngredientTranslationModel.name, IngredientTranslationModel.plural_name)
            )
        ).all():
            names.update(n.strip().casefold() for n in (name, plural) if n)
        return SeedIndex(keys={k for k in keys if k}, names=names)

    async def recipe_count(self, ingredient_id: int) -> int:
        return len(await self.recipe_ids_using(ingredient_id))

    async def save(self, ingredient: Ingredient) -> Ingredient:
        row = await self._db.get(IngredientModel, ingredient.id) if ingredient.id else None
        if row is None:
            row = IngredientModel(
                public_id=ingredient.public_id,
                created=ingredient.created,
                seed_key=ingredient.seed_key,
            )
            self._db.add(row)
        row.owner_id = ingredient.owner_id
        row.original_locale = ingredient.original_locale
        row.category_id = ingredient.category_id
        row.family_id = ingredient.family_id
        for name in NUTRIENTS:
            setattr(row, name, getattr(ingredient.nutrition, name))
        row.extended_nutrition = dict(ingredient.extended_nutrition)
        row.season_months = sorted(set(ingredient.season_months))
        row.density_g_per_ml = ingredient.density_g_per_ml
        row.allergens = sorted({a.value for a in ingredient.allergens})
        row.diet_markers = sorted({m.value for m in ingredient.diet_markers})
        row.status = ingredient.status.value
        row.nutrition_source = ingredient.nutrition_source.value
        row.usda_fdc_id = ingredient.usda_fdc_id
        row.changed = ingredient.changed
        await self._db.flush()
        await replace_translations(
            self._db,
            IngredientTranslationModel,
            "ingredient_id",
            row.id,
            ingredient.translations,
            lambda t: {"name": t.name, "plural_name": t.plural_name},
        )
        await self._db.execute(
            delete(IngredientAliasModel).where(IngredientAliasModel.ingredient_id == row.id)
        )
        for locale, names in sorted(ingredient.aliases.items()):
            for alias in sorted({n.strip() for n in names if n.strip()}):
                self._db.add(IngredientAliasModel(ingredient_id=row.id, locale=locale, alias=alias))
        await self._db.execute(
            delete(IngredientConversionModel).where(
                IngredientConversionModel.ingredient_id == row.id
            )
        )
        for conversion in {c.unit_id: c for c in ingredient.conversions}.values():
            self._db.add(
                IngredientConversionModel(
                    ingredient_id=row.id, unit_id=conversion.unit_id, grams=conversion.grams
                )
            )
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def recipe_ids_using(self, ingredient_id: int) -> list[int]:
        """The recipes whose steps or declared list name the ingredient."""
        in_steps = await self._db.scalars(
            select(func.distinct(RecipeStepModel.recipe_id))
            .select_from(StepIngredientModel)
            .join(RecipeStepModel, RecipeStepModel.id == StepIngredientModel.step_id)
            .where(StepIngredientModel.ingredient_id == ingredient_id)
        )
        declared = await self._db.scalars(
            select(func.distinct(RecipeIngredientModel.recipe_id)).where(
                RecipeIngredientModel.ingredient_id == ingredient_id
            )
        )
        return sorted({*in_steps.all(), *declared.all()})

    async def restriction_count(self, ingredient_id: int) -> int:
        """How many food restrictions name the ingredient. Only the
        deletion rule reads it; no response ever carries it."""
        return int(
            await self._db.scalar(
                select(func.count())
                .select_from(FoodRestrictionModel)
                .where(FoodRestrictionModel.ingredient_id == ingredient_id)
            )
            or 0
        )

    async def items_to_text(self, ingredient_id: int, text: str) -> None:
        """Shopping items of the ingredient keep its name as free text."""
        await self._db.execute(
            update(ShoppingItemModel)
            .where(ShoppingItemModel.ingredient_id == ingredient_id)
            .values(ingredient_id=None, text=text)
        )

    async def repoint(self, source_id: int, target_id: int) -> None:
        """Moves recipe lines, shopping items and food restrictions from the
        source ingredient to the target, for a merge."""
        for model in (StepIngredientModel, RecipeIngredientModel):
            await self._db.execute(
                update(model)
                .where(model.ingredient_id == source_id)
                .values(ingredient_id=target_id)
            )
        await self._db.execute(
            update(ShoppingItemModel)
            .where(ShoppingItemModel.ingredient_id == source_id)
            .values(ingredient_id=target_id)
        )
        await self._db.execute(
            update(FoodRestrictionModel)
            .where(FoodRestrictionModel.ingredient_id == source_id)
            .values(ingredient_id=target_id)
        )

    async def ids_owned_by(self, owner_id: int) -> list[int]:
        rows = await self._db.scalars(
            select(IngredientModel.id).where(IngredientModel.owner_id == owner_id)
        )
        return list(rows.all())

    async def reassign_owner(self, owner_id: int, new_owner_id: int | None) -> None:
        await self._db.execute(
            update(IngredientModel)
            .where(IngredientModel.owner_id == owner_id)
            .values(owner_id=new_owner_id)
        )

    async def delete(self, ingredient: Ingredient) -> None:
        row = await self._db.get(IngredientModel, ingredient.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()
