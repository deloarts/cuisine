from datetime import date
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy import and_
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.cooking_models import CookEventModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import MealPlanEntryModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingItemModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingListMemberModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingListModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingListNoteModel
from src.cookbook.domain.entities.cooking import CookEvent
from src.cookbook.domain.entities.cooking import MealPlanEntry
from src.cookbook.domain.entities.cooking import ShoppingItem
from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.entities.cooking import ShoppingListNote
from src.cookbook.domain.services.meal_suggestions import CookHistory
from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.domain.value_objects.enums import ShoppingListMode
from src.platform.adapters.outbound.persistence.repositories._common import copy_entity_to_row
from src.platform.adapters.outbound.persistence.repositories._common import entity_from_row
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id


class SqlAlchemyCookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get_by_public_id(self, public_id: str) -> CookEvent | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(CookEventModel).where(CookEventModel.public_id == uid))
        return entity_from_row(CookEvent, row) if row is not None else None

    async def find(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        user_id: int | None = None,
        recipe_id: int | None = None,
        limit: int = 500,
    ) -> list[CookEvent]:
        stmt = select(CookEventModel)
        if date_from is not None:
            stmt = stmt.where(CookEventModel.cooked_on >= date_from)
        if date_to is not None:
            stmt = stmt.where(CookEventModel.cooked_on <= date_to)
        if user_id is not None:
            stmt = stmt.where(CookEventModel.user_id == user_id)
        if recipe_id is not None:
            stmt = stmt.where(CookEventModel.recipe_id == recipe_id)
        rows = await self._db.scalars(
            stmt.order_by(CookEventModel.cooked_on.desc(), CookEventModel.id.desc()).limit(limit)
        )
        return [entity_from_row(CookEvent, r) for r in rows.all()]

    async def last_cooked(
        self, recipe_ids: list[int], user_id: int | None = None
    ) -> dict[int, date]:
        if not recipe_ids:
            return {}
        stmt = (
            select(CookEventModel.recipe_id, func.max(CookEventModel.cooked_on))
            .where(CookEventModel.recipe_id.in_(recipe_ids))
            .group_by(CookEventModel.recipe_id)
        )
        if user_id is not None:
            stmt = stmt.where(CookEventModel.user_id == user_id)
        return {rid: day for rid, day in (await self._db.execute(stmt)).all()}

    async def history(
        self, user_ids: list[int], windows: list[tuple[date, date]]
    ) -> dict[int, CookHistory]:
        if not user_ids:
            return {}
        cooked_by = CookEventModel.user_id.in_(user_ids)
        totals = await self._db.execute(
            select(
                CookEventModel.recipe_id,
                func.count(),
                func.min(CookEventModel.cooked_on),
                func.max(CookEventModel.cooked_on),
            )
            .where(cooked_by)
            .group_by(CookEventModel.recipe_id)
        )
        around: dict[int, int] = {}
        if windows:
            in_window = or_(
                *(
                    and_(CookEventModel.cooked_on >= start, CookEventModel.cooked_on <= end)
                    for start, end in windows
                )
            )
            rows = await self._db.execute(
                select(CookEventModel.recipe_id, func.count())
                .where(cooked_by, in_window)
                .group_by(CookEventModel.recipe_id)
            )
            around = {recipe_id: count for recipe_id, count in rows.all()}
        return {
            recipe_id: CookHistory(
                times_cooked=count,
                first_cooked=first,
                last_cooked=last,
                around_this_time=around.get(recipe_id, 0),
            )
            for recipe_id, count, first, last in totals.all()
        }

    async def save(self, event: CookEvent) -> CookEvent:
        row = await self._db.get(CookEventModel, event.id) if event.id else None
        if row is None:
            row = CookEventModel(public_id=event.public_id)
            self._db.add(row)
        copy_entity_to_row(event, row, skip=frozenset())
        await self._db.flush()
        return entity_from_row(CookEvent, row)

    async def delete(self, event: CookEvent) -> None:
        await self._db.execute(delete(CookEventModel).where(CookEventModel.id == event.id))


def _entry(row: MealPlanEntryModel) -> MealPlanEntry:
    return MealPlanEntry(
        id=row.id,
        public_id=row.public_id,
        user_id=row.user_id,
        plan_date=row.plan_date,
        slot=MealSlot(row.slot),
        servings=row.servings,
        created=row.created,
        recipe_id=row.recipe_id,
        title=row.title,
        household_id=row.household_id,
    )


def _personal(user_id: int) -> ColumnElement[bool]:
    return (MealPlanEntryModel.user_id == user_id) & MealPlanEntryModel.household_id.is_(None)


def _plan_scope(user_id: int, household_id: int | None) -> ColumnElement[bool]:
    """The household's plan when a household is given, the personal plan
    otherwise."""
    if household_id is not None:
        return MealPlanEntryModel.household_id == household_id
    return _personal(user_id)


class SqlAlchemyMealPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get_accessible(
        self, user_id: int, household_id: int | None, public_id: str
    ) -> MealPlanEntry | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        # Either plan the user may reach: their household's or their own.
        scopes = [_personal(user_id)]
        if household_id is not None:
            scopes.append(MealPlanEntryModel.household_id == household_id)
        row = await self._db.scalar(
            select(MealPlanEntryModel).where(MealPlanEntryModel.public_id == uid, or_(*scopes))
        )
        return _entry(row) if row is not None else None

    async def between(
        self, user_id: int, household_id: int | None, date_from: date, date_to: date
    ) -> list[MealPlanEntry]:
        rows = await self._db.scalars(
            select(MealPlanEntryModel)
            .where(
                _plan_scope(user_id, household_id),
                MealPlanEntryModel.plan_date >= date_from,
                MealPlanEntryModel.plan_date <= date_to,
            )
            .order_by(MealPlanEntryModel.plan_date, MealPlanEntryModel.id)
        )
        return [_entry(r) for r in rows.all()]

    async def save(self, entry: MealPlanEntry) -> MealPlanEntry:
        row = await self._db.get(MealPlanEntryModel, entry.id) if entry.id else None
        if row is None:
            row = MealPlanEntryModel(public_id=entry.public_id, created=entry.created)
            self._db.add(row)
        row.user_id = entry.user_id
        row.plan_date = entry.plan_date
        row.slot = entry.slot.value
        row.recipe_id = entry.recipe_id
        row.title = entry.title
        row.servings = entry.servings
        row.household_id = entry.household_id
        await self._db.flush()
        return _entry(row)

    async def delete(self, entry: MealPlanEntry) -> None:
        await self._db.execute(delete(MealPlanEntryModel).where(MealPlanEntryModel.id == entry.id))

    async def hand_over(self, household_id: int, user_id: int, new_user_id: int) -> None:
        """A household's entries created by a leaving account are kept in
        another member's name."""
        await self._db.execute(
            update(MealPlanEntryModel)
            .where(
                MealPlanEntryModel.household_id == household_id,
                MealPlanEntryModel.user_id == user_id,
            )
            .values(user_id=new_user_id)
        )


class SqlAlchemyShoppingListRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _lists(self, rows: list[ShoppingListModel]) -> list[ShoppingList]:
        ids = [r.id for r in rows]
        members: dict[int, list[int]] = {i: [] for i in ids}
        if ids:
            for list_id, user_id in (
                await self._db.execute(
                    select(ShoppingListMemberModel.list_id, ShoppingListMemberModel.user_id).where(
                        ShoppingListMemberModel.list_id.in_(ids)
                    )
                )
            ).all():
                members[list_id].append(user_id)
        return [
            ShoppingList(
                id=r.id,
                public_id=r.public_id,
                owner_id=r.owner_id,
                name=r.name,
                created=r.created,
                changed=r.changed,
                last_activity_at=r.last_activity_at,
                mode=ShoppingListMode(r.mode),
                keep=r.keep,
                member_ids=sorted(members.get(r.id, [])),
                household_id=r.household_id,
            )
            for r in rows
        ]

    async def get_by_public_id(self, public_id: str) -> ShoppingList | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(ShoppingListModel).where(ShoppingListModel.public_id == uid)
        )
        return (await self._lists([row]))[0] if row is not None else None

    async def list_for_user(self, user_id: int, household_id: int | None) -> list[ShoppingList]:
        shared = select(ShoppingListMemberModel.list_id).where(
            ShoppingListMemberModel.user_id == user_id
        )
        own = (ShoppingListModel.owner_id == user_id) & ShoppingListModel.household_id.is_(None)
        scopes: list[Any] = [own, ShoppingListModel.id.in_(shared)]
        if household_id is not None:
            # The creator of a household list may have left the household.
            scopes.append(ShoppingListModel.household_id == household_id)
        rows = await self._db.scalars(
            select(ShoppingListModel)
            .where(or_(*scopes))
            .order_by(ShoppingListModel.changed.desc(), ShoppingListModel.id.desc())
        )
        return await self._lists(list(rows.all()))

    async def of_household(self, household_id: int) -> ShoppingList | None:
        row = await self._db.scalar(
            select(ShoppingListModel).where(ShoppingListModel.household_id == household_id)
        )
        return (await self._lists([row]))[0] if row is not None else None

    async def save(self, shopping_list: ShoppingList) -> ShoppingList:
        row = await self._db.get(ShoppingListModel, shopping_list.id) if shopping_list.id else None
        if row is None:
            row = ShoppingListModel(
                public_id=shopping_list.public_id, created=shopping_list.created
            )
            self._db.add(row)
        row.owner_id = shopping_list.owner_id
        row.name = shopping_list.name
        row.household_id = shopping_list.household_id
        row.changed = shopping_list.changed
        row.last_activity_at = shopping_list.last_activity_at
        row.mode = shopping_list.mode.value
        row.keep = shopping_list.keep
        await self._db.flush()
        await self._db.execute(
            delete(ShoppingListMemberModel).where(ShoppingListMemberModel.list_id == row.id)
        )
        for user_id in sorted(set(shopping_list.member_ids) - {shopping_list.owner_id}):
            self._db.add(ShoppingListMemberModel(list_id=row.id, user_id=user_id))
        await self._db.flush()
        return (await self._lists([row]))[0]

    async def delete(self, shopping_list: ShoppingList) -> None:
        await self._db.execute(
            delete(ShoppingListModel).where(ShoppingListModel.id == shopping_list.id)
        )

    async def items(self, list_id: int) -> list[ShoppingItem]:
        rows = await self._db.scalars(
            select(ShoppingItemModel)
            .where(ShoppingItemModel.list_id == list_id)
            .order_by(ShoppingItemModel.created, ShoppingItemModel.id)
        )
        return [entity_from_row(ShoppingItem, r) for r in rows.all()]

    async def item_counts(self, list_ids: list[int]) -> dict[int, tuple[int, int]]:
        """Per list: (open items, checked items)."""
        if not list_ids:
            return {}
        rows = await self._db.execute(
            select(ShoppingItemModel.list_id, ShoppingItemModel.checked, func.count())
            .where(ShoppingItemModel.list_id.in_(list_ids))
            .group_by(ShoppingItemModel.list_id, ShoppingItemModel.checked)
        )
        counts: dict[int, tuple[int, int]] = {i: (0, 0) for i in list_ids}
        for list_id, checked, count in rows.all():
            open_, done = counts[list_id]
            counts[list_id] = (open_, done + count) if checked else (open_ + count, done)
        return counts

    async def get_item(self, list_id: int, public_id: str) -> ShoppingItem | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(ShoppingItemModel).where(
                ShoppingItemModel.public_id == uid, ShoppingItemModel.list_id == list_id
            )
        )
        return entity_from_row(ShoppingItem, row) if row is not None else None

    async def save_item(self, item: ShoppingItem) -> ShoppingItem:
        row = await self._db.get(ShoppingItemModel, item.id) if item.id else None
        if row is None:
            row = ShoppingItemModel(public_id=item.public_id)
            self._db.add(row)
        copy_entity_to_row(item, row, skip=frozenset())
        await self._db.flush()
        return entity_from_row(ShoppingItem, row)

    async def delete_item(self, item: ShoppingItem) -> None:
        await self._db.execute(delete(ShoppingItemModel).where(ShoppingItemModel.id == item.id))

    async def delete_checked(self, list_id: int) -> int:
        result = await self._db.execute(
            delete(ShoppingItemModel).where(
                ShoppingItemModel.list_id == list_id, ShoppingItemModel.checked.is_(True)
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_checked_before(self, list_id: int, cutoff: datetime) -> int:
        """Deletes the items ticked before the cutoff, and ticked items
        without a tick time."""
        result = await self._db.execute(
            delete(ShoppingItemModel).where(
                ShoppingItemModel.list_id == list_id,
                ShoppingItemModel.checked.is_(True),
                or_(
                    ShoppingItemModel.checked_at.is_(None),
                    ShoppingItemModel.checked_at < cutoff,
                ),
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def continuous_with_checked_before(self, cutoff: datetime) -> list[ShoppingList]:
        """The continuous lists that hold items ticked before the cutoff."""
        stale = select(ShoppingItemModel.list_id).where(
            ShoppingItemModel.checked.is_(True),
            or_(ShoppingItemModel.checked_at.is_(None), ShoppingItemModel.checked_at < cutoff),
        )
        rows = await self._db.scalars(
            select(ShoppingListModel)
            .where(
                ShoppingListModel.mode == ShoppingListMode.CONTINUOUS.value,
                ShoppingListModel.id.in_(stale),
            )
            .order_by(ShoppingListModel.id)
        )
        return await self._lists(list(rows.all()))

    async def idle_since(self, cutoff: datetime) -> list[ShoppingList]:
        """The normal lists without keep, outside a household, last used
        before the cutoff."""
        rows = await self._db.scalars(
            select(ShoppingListModel)
            .where(
                ShoppingListModel.mode == ShoppingListMode.NORMAL.value,
                ShoppingListModel.keep.is_(False),
                ShoppingListModel.household_id.is_(None),
                ShoppingListModel.last_activity_at < cutoff,
            )
            .order_by(ShoppingListModel.id)
        )
        return await self._lists(list(rows.all()))


class SqlAlchemyShoppingListNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, note: ShoppingListNote) -> ShoppingListNote:
        row = ShoppingListNoteModel(public_id=note.public_id)
        copy_entity_to_row(note, row, skip=frozenset())
        self._db.add(row)
        await self._db.flush()
        return entity_from_row(ShoppingListNote, row)

    async def list_for_user(self, user_id: int) -> list[ShoppingListNote]:
        rows = await self._db.scalars(
            select(ShoppingListNoteModel)
            .where(ShoppingListNoteModel.user_id == user_id)
            .order_by(ShoppingListNoteModel.created.desc(), ShoppingListNoteModel.id.desc())
        )
        return [entity_from_row(ShoppingListNote, r) for r in rows.all()]

    async def delete_for_user(self, user_id: int, public_id: str) -> bool:
        uid = parse_public_id(public_id)
        if uid is None:
            return False
        result = await self._db.execute(
            delete(ShoppingListNoteModel).where(
                ShoppingListNoteModel.public_id == uid, ShoppingListNoteModel.user_id == user_id
            )
        )
        return bool(getattr(result, "rowcount", 0))
