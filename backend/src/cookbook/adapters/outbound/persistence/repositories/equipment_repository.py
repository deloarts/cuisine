from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import CompoundSelect

from src.cookbook.adapters.outbound.persistence.models.equipment_models import EquipmentAliasModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import EquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import (
    EquipmentTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.equipment_models import KitchenEquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import KitchenModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import StepEquipmentModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeStepModel
from src.cookbook.adapters.outbound.persistence.repositories._like import contains_pattern
from src.cookbook.adapters.outbound.persistence.repositories._like import lower_contains
from src.cookbook.adapters.outbound.persistence.repositories._translations import load_translations
from src.cookbook.adapters.outbound.persistence.repositories._translations import (
    replace_translations,
)
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.equipment import Kitchen
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import EquipmentStatus
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.ports.outbound.repositories.equipment_repository import EquipmentQuery
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id


def equipment_name_matches(search: str) -> CompoundSelect[tuple[int]]:
    """The ids of equipment whose name or alias contains `search` in any
    locale, ignoring case."""
    pattern = contains_pattern(search)
    by_name = select(EquipmentTranslationModel.equipment_id).where(
        lower_contains(EquipmentTranslationModel.name, pattern)
    )
    by_alias = select(EquipmentAliasModel.equipment_id).where(
        lower_contains(EquipmentAliasModel.alias, pattern)
    )
    return by_name.union(by_alias)


class SqlAlchemyEquipmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entities(self, rows: list[EquipmentModel]) -> list[Equipment]:
        ids = [r.id for r in rows]
        texts = await load_translations(
            self._db, EquipmentTranslationModel, "equipment_id", ids, lambda t: NameText(t.name)
        )
        aliases: dict[int, dict[str, list[str]]] = {i: {} for i in ids}
        if ids:
            for row in (
                await self._db.scalars(
                    select(EquipmentAliasModel)
                    .where(EquipmentAliasModel.equipment_id.in_(ids))
                    .order_by(EquipmentAliasModel.alias)
                )
            ).all():
                aliases[row.equipment_id].setdefault(row.locale, []).append(row.alias)
        return [
            Equipment(
                id=r.id,
                public_id=r.public_id,
                kind=EquipmentKind(r.kind),
                created=r.created,
                changed=r.changed,
                translations=texts.get(r.id, {}),
                aliases=aliases.get(r.id, {}),
                icon=r.icon,
                basic=r.basic,
                status=EquipmentStatus(r.status),
                seed_key=r.seed_key,
            )
            for r in rows
        ]

    async def get(self, equipment_id: int) -> Equipment | None:
        row = await self._db.get(EquipmentModel, equipment_id)
        return (await self._entities([row]))[0] if row is not None else None

    async def get_by_public_id(self, public_id: str) -> Equipment | None:
        parsed = parse_public_id(public_id)
        if parsed is None:
            return None
        row = await self._db.scalar(
            select(EquipmentModel).where(EquipmentModel.public_id == parsed)
        )
        return (await self._entities([row]))[0] if row is not None else None

    async def get_many(self, ids: list[int]) -> list[Equipment]:
        if not ids:
            return []
        rows = await self._db.scalars(
            select(EquipmentModel).where(EquipmentModel.id.in_(sorted(set(ids))))
        )
        return await self._entities(list(rows.all()))

    async def find(self, query: EquipmentQuery) -> list[Equipment]:
        stmt = select(EquipmentModel)
        if query.search and query.search.strip():
            stmt = stmt.where(EquipmentModel.id.in_(equipment_name_matches(query.search)))
        if query.kind is not None:
            stmt = stmt.where(EquipmentModel.kind == query.kind.value)
        if query.status is not None:
            stmt = stmt.where(EquipmentModel.status == query.status.value)
        return await self._entities(
            list((await self._db.scalars(stmt.order_by(EquipmentModel.id))).all())
        )

    async def find_by_name(self, name: str) -> Equipment | None:
        """An item whose name or alias equals `name` in any locale, ignoring
        case; main names win over aliases."""
        wanted = name.strip().lower()
        found = await self._db.scalar(
            select(EquipmentTranslationModel.equipment_id)
            .where(func.lower(EquipmentTranslationModel.name) == wanted)
            .order_by(EquipmentTranslationModel.equipment_id)
            .limit(1)
        )
        if found is None:
            found = await self._db.scalar(
                select(EquipmentAliasModel.equipment_id)
                .where(func.lower(EquipmentAliasModel.alias) == wanted)
                .order_by(EquipmentAliasModel.equipment_id)
                .limit(1)
            )
        return await self.get(found) if found is not None else None

    async def find_by_names(self, names: list[str]) -> Equipment | None:
        """The item `find_by_name` gives for the first of `names` that
        matches, looked up in two queries rather than two per name."""
        wanted = list(dict.fromkeys(n.strip().lower() for n in names if n.strip()))
        if not wanted:
            return None
        by_name = await self._db.execute(
            select(
                EquipmentTranslationModel.equipment_id, func.lower(EquipmentTranslationModel.name)
            ).where(func.lower(EquipmentTranslationModel.name).in_(wanted))
        )
        by_alias = await self._db.execute(
            select(EquipmentAliasModel.equipment_id, func.lower(EquipmentAliasModel.alias)).where(
                func.lower(EquipmentAliasModel.alias).in_(wanted)
            )
        )
        name_ids: dict[str, int] = {}
        for equipment_id, name in by_name.all():
            name_ids[name] = min(name_ids.get(name, equipment_id), equipment_id)
        alias_ids: dict[str, int] = {}
        for equipment_id, alias in by_alias.all():
            alias_ids[alias] = min(alias_ids.get(alias, equipment_id), equipment_id)
        for name in wanted:
            found = name_ids.get(name, alias_ids.get(name))
            if found is not None:
                return await self.get(found)
        return None

    async def by_seed_keys(self, keys: list[str]) -> dict[str, Equipment]:
        if not keys:
            return {}
        rows = await self._db.scalars(
            select(EquipmentModel).where(EquipmentModel.seed_key.in_(keys))
        )
        return {e.seed_key: e for e in await self._entities(list(rows.all())) if e.seed_key}

    async def recipe_ids_using(self, equipment_id: int) -> list[int]:
        rows = await self._db.scalars(
            select(RecipeStepModel.recipe_id)
            .distinct()
            .join(StepEquipmentModel, StepEquipmentModel.step_id == RecipeStepModel.id)
            .where(StepEquipmentModel.equipment_id == equipment_id)
        )
        return sorted(rows.all())

    async def repoint(self, source_id: int, target_id: int) -> None:
        """Moves step equipment and kitchens from the source item to the
        target, for a merge; a kitchen holding both keeps one."""
        await self._db.execute(
            update(StepEquipmentModel)
            .where(StepEquipmentModel.equipment_id == source_id)
            .values(equipment_id=target_id)
        )
        with_target = select(KitchenEquipmentModel.kitchen_id).where(
            KitchenEquipmentModel.equipment_id == target_id
        )
        await self._db.execute(
            delete(KitchenEquipmentModel).where(
                KitchenEquipmentModel.equipment_id == source_id,
                KitchenEquipmentModel.kitchen_id.in_(with_target),
            )
        )
        await self._db.execute(
            update(KitchenEquipmentModel)
            .where(KitchenEquipmentModel.equipment_id == source_id)
            .values(equipment_id=target_id)
        )

    async def save(self, equipment: Equipment) -> Equipment:
        row = await self._db.get(EquipmentModel, equipment.id) if equipment.id else None
        if row is None:
            row = EquipmentModel(
                public_id=equipment.public_id,
                created=equipment.created,
                seed_key=equipment.seed_key,
            )
            self._db.add(row)
        row.kind = equipment.kind.value
        row.icon = equipment.icon
        row.basic = equipment.basic
        row.status = equipment.status.value
        row.changed = equipment.changed
        await self._db.flush()
        await replace_translations(
            self._db,
            EquipmentTranslationModel,
            "equipment_id",
            row.id,
            equipment.translations,
            lambda t: {"name": t.name},
        )
        await self._db.execute(
            delete(EquipmentAliasModel).where(EquipmentAliasModel.equipment_id == row.id)
        )
        for locale, names in sorted(equipment.aliases.items()):
            for alias in sorted({n.strip() for n in names if n.strip()}):
                self._db.add(EquipmentAliasModel(equipment_id=row.id, locale=locale, alias=alias))
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def delete(self, equipment: Equipment) -> None:
        row = await self._db.get(EquipmentModel, equipment.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()


class SqlAlchemyKitchenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _entity(self, row: KitchenModel | None) -> Kitchen | None:
        if row is None:
            return None
        ids = await self._db.scalars(
            select(KitchenEquipmentModel.equipment_id)
            .where(KitchenEquipmentModel.kitchen_id == row.id)
            .order_by(KitchenEquipmentModel.equipment_id)
        )
        return Kitchen(
            id=row.id,
            public_id=row.public_id,
            household_id=row.household_id,
            user_id=row.user_id,
            equipment_ids=list(ids.all()),
            set_up_at=row.set_up_at,
            changed=row.changed,
        )

    async def of_household(self, household_id: int) -> Kitchen | None:
        return await self._entity(
            await self._db.scalar(
                select(KitchenModel).where(KitchenModel.household_id == household_id)
            )
        )

    async def of_user(self, user_id: int) -> Kitchen | None:
        return await self._entity(
            await self._db.scalar(select(KitchenModel).where(KitchenModel.user_id == user_id))
        )

    async def save(self, kitchen: Kitchen) -> Kitchen:
        row = await self._db.get(KitchenModel, kitchen.id) if kitchen.id else None
        if row is None:
            row = KitchenModel(
                public_id=kitchen.public_id,
                household_id=kitchen.household_id,
                user_id=kitchen.user_id,
                set_up_at=kitchen.set_up_at,
            )
            self._db.add(row)
        row.changed = kitchen.changed
        await self._db.flush()
        await self._db.execute(
            delete(KitchenEquipmentModel).where(KitchenEquipmentModel.kitchen_id == row.id)
        )
        for equipment_id in sorted(set(kitchen.equipment_ids)):
            self._db.add(KitchenEquipmentModel(kitchen_id=row.id, equipment_id=equipment_id))
        await self._db.flush()
        found = await self._entity(row)
        assert found is not None
        return found

    async def delete(self, kitchen: Kitchen) -> None:
        row = await self._db.get(KitchenModel, kitchen.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()
