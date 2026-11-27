from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingItemModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import (
    IngredientConversionModel,
)
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import StepIngredientModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientCategoryModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientCategoryTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import IngredientFamilyModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientFamilyTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import TagModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import TagTranslationModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import UnitModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import UnitTranslationModel
from src.cookbook.adapters.outbound.persistence.repositories._translations import load_translations
from src.cookbook.adapters.outbound.persistence.repositories._translations import (
    replace_translations,
)
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id

_TAG_KINDS = frozenset(k.value for k in TagKind)


def _unit_text(row: UnitTranslationModel) -> UnitText:
    return UnitText(name=row.name, plural_name=row.plural_name, abbreviation=row.abbreviation)


def _name_text(
    row: TagTranslationModel
    | IngredientCategoryTranslationModel
    | IngredientFamilyTranslationModel,
) -> NameText:
    return NameText(name=row.name)


class SqlAlchemyUnitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entities(self, rows: list[UnitModel]) -> list[Unit]:
        texts = await load_translations(
            self._db, UnitTranslationModel, "unit_id", [r.id for r in rows], _unit_text
        )
        return [
            Unit(
                id=r.id,
                public_id=r.public_id,
                code=r.code,
                kind=UnitKind(r.kind),
                to_base=r.to_base,
                sort_order=r.sort_order,
                created=r.created,
                translations=texts.get(r.id, {}),
                seed_key=r.seed_key,
            )
            for r in rows
        ]

    async def list_all(self) -> list[Unit]:
        rows = await self._db.scalars(
            select(UnitModel).order_by(UnitModel.sort_order, UnitModel.id)
        )
        return await self._entities(list(rows.all()))

    async def get_by_public_id(self, public_id: str) -> Unit | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(UnitModel).where(UnitModel.public_id == uid))
        return (await self._entities([row]))[0] if row is not None else None

    async def get_by_code(self, code: str) -> Unit | None:
        row = await self._db.scalar(select(UnitModel).where(UnitModel.code == code))
        return (await self._entities([row]))[0] if row is not None else None

    async def code_taken(self, code: str, exclude_id: int | None = None) -> bool:
        query = select(func.count()).select_from(UnitModel).where(UnitModel.code == code)
        if exclude_id is not None:
            query = query.where(UnitModel.id != exclude_id)
        return bool(await self._db.scalar(query))

    async def in_use(self, unit_id: int) -> bool:
        steps = await self._db.scalar(
            select(func.count())
            .select_from(StepIngredientModel)
            .where(StepIngredientModel.unit_id == unit_id)
        )
        declared = await self._db.scalar(
            select(func.count())
            .select_from(RecipeIngredientModel)
            .where(RecipeIngredientModel.unit_id == unit_id)
        )
        conversions = await self._db.scalar(
            select(func.count())
            .select_from(IngredientConversionModel)
            .where(IngredientConversionModel.unit_id == unit_id)
        )
        return bool(steps) or bool(declared) or bool(conversions)

    async def merge_into(self, source_id: int, target_id: int) -> None:
        """Moves every use of the source unit to the target; an ingredient
        that already converts the target keeps that conversion."""
        for model in (StepIngredientModel, RecipeIngredientModel):
            await self._db.execute(
                update(model).where(model.unit_id == source_id).values(unit_id=target_id)
            )
        await self._db.execute(
            update(ShoppingItemModel)
            .where(ShoppingItemModel.unit_id == source_id)
            .values(unit_id=target_id)
        )
        await self._db.execute(
            update(RecipeModel)
            .where(RecipeModel.yield_unit_id == source_id)
            .values(yield_unit_id=target_id)
        )
        taken = select(IngredientConversionModel.ingredient_id).where(
            IngredientConversionModel.unit_id == target_id
        )
        await self._db.execute(
            delete(IngredientConversionModel).where(
                IngredientConversionModel.unit_id == source_id,
                IngredientConversionModel.ingredient_id.in_(taken),
            )
        )
        await self._db.execute(
            update(IngredientConversionModel)
            .where(IngredientConversionModel.unit_id == source_id)
            .values(unit_id=target_id)
        )

    async def save(self, unit: Unit) -> Unit:
        row = await self._db.get(UnitModel, unit.id) if unit.id else None
        if row is None:
            row = UnitModel(public_id=unit.public_id, created=unit.created, seed_key=unit.seed_key)
            self._db.add(row)
        row.code = unit.code
        row.kind = unit.kind.value
        row.to_base = unit.to_base
        row.sort_order = unit.sort_order
        await self._db.flush()
        await replace_translations(
            self._db,
            UnitTranslationModel,
            "unit_id",
            row.id,
            unit.translations,
            lambda t: {
                "name": t.name,
                "plural_name": t.plural_name,
                "abbreviation": t.abbreviation,
            },
        )
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def delete(self, unit: Unit) -> None:
        row = await self._db.get(UnitModel, unit.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()


class SqlAlchemyIngredientCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entities(self, rows: list[IngredientCategoryModel]) -> list[IngredientCategory]:
        texts = await load_translations(
            self._db,
            IngredientCategoryTranslationModel,
            "category_id",
            [r.id for r in rows],
            _name_text,
        )
        return [
            IngredientCategory(
                id=r.id,
                public_id=r.public_id,
                sort_order=r.sort_order,
                created=r.created,
                translations=texts.get(r.id, {}),
                seed_key=r.seed_key,
            )
            for r in rows
        ]

    async def list_all(self) -> list[IngredientCategory]:
        rows = await self._db.scalars(
            select(IngredientCategoryModel).order_by(
                IngredientCategoryModel.sort_order, IngredientCategoryModel.id
            )
        )
        return await self._entities(list(rows.all()))

    async def get_by_public_id(self, public_id: str) -> IngredientCategory | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(IngredientCategoryModel).where(IngredientCategoryModel.public_id == uid)
        )
        return (await self._entities([row]))[0] if row is not None else None

    async def move_contents(
        self, source_id: int, target_id: int | None, items_to: int | None
    ) -> None:
        """Ingredients of the category move to `target_id`, shopping items
        to `items_to`, before the category is deleted."""
        await self._db.execute(
            update(IngredientModel)
            .where(IngredientModel.category_id == source_id)
            .values(category_id=target_id)
        )
        await self._db.execute(
            update(ShoppingItemModel)
            .where(ShoppingItemModel.category_id == source_id)
            .values(category_id=items_to)
        )

    async def save(self, category: IngredientCategory) -> IngredientCategory:
        row = await self._db.get(IngredientCategoryModel, category.id) if category.id else None
        if row is None:
            row = IngredientCategoryModel(
                public_id=category.public_id, created=category.created, seed_key=category.seed_key
            )
            self._db.add(row)
        row.sort_order = category.sort_order
        await self._db.flush()
        await replace_translations(
            self._db,
            IngredientCategoryTranslationModel,
            "category_id",
            row.id,
            category.translations,
            lambda t: {"name": t.name},
        )
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def delete(self, category: IngredientCategory) -> None:
        row = await self._db.get(IngredientCategoryModel, category.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()


class SqlAlchemyTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entities(self, rows: list[TagModel]) -> list[Tag]:
        texts = await load_translations(
            self._db, TagTranslationModel, "tag_id", [r.id for r in rows], _name_text
        )
        return [
            Tag(
                id=r.id,
                public_id=r.public_id,
                # A kind the code no longer knows, such as the former "diet",
                # reads as "other".
                kind=TagKind(r.kind) if r.kind in _TAG_KINDS else TagKind.OTHER,
                color=r.color,
                created=r.created,
                translations=texts.get(r.id, {}),
                seed_key=r.seed_key,
            )
            for r in rows
        ]

    async def list_all(self) -> list[Tag]:
        rows = await self._db.scalars(select(TagModel).order_by(TagModel.kind, TagModel.id))
        return await self._entities(list(rows.all()))

    async def get_by_public_id(self, public_id: str) -> Tag | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(TagModel).where(TagModel.public_id == uid))
        return (await self._entities([row]))[0] if row is not None else None

    async def save(self, tag: Tag) -> Tag:
        row = await self._db.get(TagModel, tag.id) if tag.id else None
        if row is None:
            row = TagModel(public_id=tag.public_id, created=tag.created, seed_key=tag.seed_key)
            self._db.add(row)
        row.kind = tag.kind.value
        row.color = tag.color
        await self._db.flush()
        await replace_translations(
            self._db,
            TagTranslationModel,
            "tag_id",
            row.id,
            tag.translations,
            lambda t: {"name": t.name},
        )
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def delete(self, tag: Tag) -> None:
        row = await self._db.get(TagModel, tag.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()


class SqlAlchemyIngredientFamilyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entities(self, rows: list[IngredientFamilyModel]) -> list[IngredientFamily]:
        texts = await load_translations(
            self._db,
            IngredientFamilyTranslationModel,
            "family_id",
            [r.id for r in rows],
            _name_text,
        )
        return [
            IngredientFamily(
                id=r.id,
                public_id=r.public_id,
                created=r.created,
                translations=texts.get(r.id, {}),
                seed_key=r.seed_key,
            )
            for r in rows
        ]

    async def list_all(self) -> list[IngredientFamily]:
        rows = await self._db.scalars(
            select(IngredientFamilyModel).order_by(IngredientFamilyModel.id)
        )
        return await self._entities(list(rows.all()))

    async def get_by_public_id(self, public_id: str) -> IngredientFamily | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(IngredientFamilyModel).where(IngredientFamilyModel.public_id == uid)
        )
        return (await self._entities([row]))[0] if row is not None else None

    async def save(self, family: IngredientFamily) -> IngredientFamily:
        row = await self._db.get(IngredientFamilyModel, family.id) if family.id else None
        if row is None:
            row = IngredientFamilyModel(
                public_id=family.public_id, created=family.created, seed_key=family.seed_key
            )
            self._db.add(row)
        await self._db.flush()
        await replace_translations(
            self._db,
            IngredientFamilyTranslationModel,
            "family_id",
            row.id,
            family.translations,
            lambda t: {"name": t.name},
        )
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def delete(self, family: IngredientFamily) -> None:
        row = await self._db.get(IngredientFamilyModel, family.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()
