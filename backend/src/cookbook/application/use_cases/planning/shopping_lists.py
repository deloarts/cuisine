"""
Shopping lists: each has an owner and the members the owner shares it with,
who all read and change its items. A household's default list belongs to the
household: every member is on it, nobody shares or deletes it, and it goes
when the household dissolves. Adding a recipe adds its derived
ingredients for the wanted servings and merges them into open items of the
same ingredient and unit. Every change is published on the list's live
channel, so every open screen of the list refetches.

Anyone on a list switches its mode and its "keep" flag. Every add, tick,
edit and mode change counts as activity, which pushes back the day an idle
normal list deletes itself (`shopping_modes`). Switching to continuous
drops the items ticked before the recently bought window.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.cookbook.application.dto.views import ShoppingListView
from src.cookbook.application.services.lookups import LookupLoader
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.entities.cooking import ShoppingItem
from src.cookbook.domain.entities.cooking import ShoppingList
from src.cookbook.domain.entities.cooking import ShoppingListNote
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import IngredientNotFoundError
from src.cookbook.domain.exceptions import InvalidPlanError
from src.cookbook.domain.exceptions import NotOwnerError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.exceptions import ShoppingItemNotFoundError
from src.cookbook.domain.exceptions import ShoppingListNoteNotFoundError
from src.cookbook.domain.exceptions import ShoppingListNotFoundError
from src.cookbook.domain.exceptions import UnitNotFoundError
from src.cookbook.domain.services.recipe_derivation import derive
from src.cookbook.domain.services.recipe_derivation import merged_lines_of
from src.cookbook.domain.services.recipe_derivation import scale_factor
from src.cookbook.domain.services.recipe_derivation import shopping_lines
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.restriction_rules import warnings_for
from src.cookbook.domain.services.shopping_modes import bought_cutoff
from src.cookbook.domain.services.shopping_rules import find_mergeable
from src.cookbook.domain.services.sub_recipes import batches
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.value_objects.enums import ShoppingListMode
from src.cookbook.ports.outbound.live_publisher import ILivePublisher
from src.cookbook.ports.outbound.live_publisher import shopping_list_channel
from src.cookbook.ports.outbound.repositories.cooking_repositories import (
    IShoppingListNoteRepository,
)
from src.cookbook.ports.outbound.repositories.cooking_repositories import IShoppingListRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import (
    IFoodRestrictionRepository,
)
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import UserNotFoundError
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

MAX_ITEMS = 500


@dataclass(frozen=True)
class ItemCommand:
    ingredient_id: str | None = None
    text: str = ""
    amount: float | None = None
    unit_id: str | None = None


@dataclass(frozen=True)
class ItemUpdate:
    checked: bool | None = None
    text: str | None = None
    amount: float | None = None
    # Whether `amount` was sent, so None can clear it.
    amount_set: bool = False
    unit_id: str | None = None
    unit_set: bool = False


class ManageShoppingLists:
    def __init__(
        self,
        *,
        list_repo: IShoppingListRepository,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        unit_repo: IUnitRepository,
        user_repo: IUserRepository,
        restriction_repo: IFoodRestrictionRepository,
        note_repo: IShoppingListNoteRepository,
        settings_repo: ISettingsRepository,
        lookups: LookupLoader,
        live: ILivePublisher,
        viewers: ViewerResolver,
        uow: IUnitOfWork,
        mirror_repo: IMirrorRepository | None = None,
    ) -> None:
        self._lists = list_repo
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._units = unit_repo
        self._users = user_repo
        self._restrictions = restriction_repo
        self._notes = note_repo
        self._settings = settings_repo
        self._lookups = lookups
        self._live = live
        self._viewers = viewers
        self._uow = uow
        self._mirrors = mirror_repo

    async def _publish(self, shopping_list: ShoppingList, event: str, actor: User) -> None:
        payload: dict[str, Any] = {
            "type": event,
            "list_id": str(shopping_list.public_id),
            "by": str(actor.public_id),
        }
        await self._live.publish(shopping_list_channel(str(shopping_list.public_id)), payload)

    async def accessible(self, actor: User, public_id: str) -> ShoppingList:
        shopping_list = await self._lists.get_by_public_id(public_id)
        viewer = await self._viewers.of(actor)
        if shopping_list is None or not shopping_list.can_access(actor.id, viewer.household_id):
            raise ShoppingListNotFoundError("No such shopping list.")
        return shopping_list

    async def lists(self, actor: User) -> tuple[list[ShoppingList], dict[int, tuple[int, int]]]:
        viewer = await self._viewers.of(actor)
        lists = await self._lists.list_for_user(actor.id, viewer.household_id)
        return lists, await self._lists.item_counts([s.id for s in lists])

    async def view(self, actor: User, public_id: str) -> ShoppingListView:
        shopping_list = await self.accessible(actor, public_id)
        return await self._view(actor, shopping_list)

    async def _view(self, actor: User, shopping_list: ShoppingList) -> ShoppingListView:
        items = await self._lists.items(shopping_list.id)
        ingredient_ids = [i.ingredient_id for i in items if i.ingredient_id is not None]
        lookups = await self._lookups.load(ingredient_ids)
        warnings = warnings_for(
            await self._restrictions.list_for_user(actor.id), ingredient_ids, lookups.ingredients
        )
        flagged = {i for w in warnings for i in w.matching_ingredient_ids}
        return ShoppingListView(
            shopping_list=shopping_list,
            items=items,
            lookups=lookups,
            warning_item_ids={i.id for i in items if i.ingredient_id in flagged},
        )

    async def _member_ids(self, public_ids: list[str]) -> list[int]:
        ids: list[int] = []
        for public_id in dict.fromkeys(public_ids):
            user = await self._users.get_by_public_id(public_id)
            if user is None or user.is_service_account or not user.is_active:
                raise UserNotFoundError("One of the people does not exist.")
            ids.append(user.id)
        return ids

    @staticmethod
    def _name(name: str) -> str:
        cleaned = name.strip()
        if not cleaned or len(cleaned) > 128:
            raise InvalidPlanError("The list name must have 1 to 128 characters.")
        return cleaned

    async def create(self, actor: User, name: str, member_ids: list[str]) -> ShoppingList:
        """A new list starts normal; only a household's default list starts
        continuous."""
        now = now_utc()
        saved = await self._lists.save(
            ShoppingList(
                owner_id=actor.id,
                name=self._name(name),
                created=now,
                changed=now,
                last_activity_at=now,
                mode=ShoppingListMode.NORMAL,
                member_ids=await self._member_ids(member_ids),
            )
        )
        await self._uow.commit()
        return saved

    async def update(
        self,
        actor: User,
        public_id: str,
        *,
        name: str | None,
        member_ids: list[str] | None,
        mode: ShoppingListMode | None = None,
        keep: bool | None = None,
    ) -> ShoppingList:
        """Anyone on the list renames it, switches its mode and its keep
        flag; only the owner shares it. Every change counts as activity, so
        switching keep off never lets a long unused list vanish at once."""
        shopping_list = await self.accessible(actor, public_id)
        items_changed = False
        if member_ids is not None:
            if shopping_list.household_id is not None:
                raise InvalidPlanError("The household list is shared with the household.")
            if shopping_list.owner_id != actor.id:
                raise NotOwnerError("Only the owner shares the list.")
            shopping_list.member_ids = await self._member_ids(member_ids)
        if name is not None:
            shopping_list.name = self._name(name)
        if keep is not None:
            shopping_list.keep = keep
        if mode is not None and mode is not shopping_list.mode:
            shopping_list.mode = mode
            if mode is ShoppingListMode.CONTINUOUS:
                window = (await self._settings.get_shopping()).bought_window_hours
                removed = await self._lists.delete_checked_before(
                    shopping_list.id, bought_cutoff(now_utc(), window)
                )
                items_changed = removed > 0
        now = now_utc()
        shopping_list.changed = now
        shopping_list.last_activity_at = now
        saved = await self._lists.save(shopping_list)
        await self._uow.commit()
        await self._publish(saved, "list_changed", actor)
        if items_changed:
            await self._publish(saved, "items_changed", actor)
        return saved

    async def delete(self, actor: User, public_id: str) -> None:
        shopping_list = await self.accessible(actor, public_id)
        if shopping_list.household_id is not None:
            raise InvalidPlanError("The household list goes only with the household.")
        if shopping_list.owner_id != actor.id:
            raise NotOwnerError("Only the owner deletes the list.")
        await self._lists.delete(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "list_deleted", actor)

    async def leave(self, actor: User, public_id: str) -> None:
        shopping_list = await self.accessible(actor, public_id)
        if shopping_list.household_id is not None and actor.id not in shopping_list.member_ids:
            raise InvalidPlanError("Leave the household to leave its list.")
        if shopping_list.owner_id == actor.id and shopping_list.household_id is None:
            raise InvalidPlanError("The owner cannot leave the list; delete it instead.")
        shopping_list.member_ids = [m for m in shopping_list.member_ids if m != actor.id]
        await self._lists.save(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "list_changed", actor)

    async def _touch(self, shopping_list: ShoppingList) -> None:
        """Records a change of the items, which is also activity."""
        now = now_utc()
        shopping_list.changed = now
        shopping_list.last_activity_at = now
        await self._lists.save(shopping_list)

    async def _check_room(self, shopping_list: ShoppingList, adding: int) -> list[ShoppingItem]:
        items = await self._lists.items(shopping_list.id)
        if len(items) + adding > MAX_ITEMS:
            raise InvalidPlanError(f"A list holds at most {MAX_ITEMS} items.")
        return items

    async def add_item(self, actor: User, public_id: str, cmd: ItemCommand) -> ShoppingItem:
        shopping_list = await self.accessible(actor, public_id)
        items = await self._check_room(shopping_list, 1)
        ingredient_id: int | None = None
        category_id: int | None = None
        if cmd.ingredient_id:
            ingredient = await self._ingredients.get_by_public_id(cmd.ingredient_id)
            if ingredient is None:
                raise IngredientNotFoundError("No such ingredient.")
            ingredient_id, category_id = ingredient.id, ingredient.category_id
        elif not cmd.text.strip():
            raise InvalidPlanError("An item needs an ingredient or a text.")
        if len(cmd.text) > 255:
            raise InvalidPlanError("The item text is too long.")
        if cmd.amount is not None and cmd.amount < 0:
            raise InvalidPlanError("The amount must not be negative.")
        unit_id: int | None = None
        if cmd.unit_id:
            unit = await self._units.get_by_public_id(cmd.unit_id)
            if unit is None:
                raise UnitNotFoundError("No such unit.")
            unit_id = unit.id
        existing = find_mergeable(items, ingredient_id, unit_id) if cmd.amount is not None else None
        if existing is not None:
            existing.amount = (existing.amount or 0.0) + (cmd.amount or 0.0)
            item = await self._lists.save_item(existing)
        else:
            item = await self._lists.save_item(
                ShoppingItem(
                    list_id=shopping_list.id,
                    created=now_utc(),
                    created_by_id=actor.id,
                    ingredient_id=ingredient_id,
                    text=cmd.text.strip(),
                    amount=cmd.amount,
                    unit_id=unit_id,
                    category_id=category_id,
                )
            )
        await self._touch(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "items_changed", actor)
        return item

    async def update_item(
        self, actor: User, public_id: str, item_id: str, cmd: ItemUpdate
    ) -> ShoppingItem:
        shopping_list = await self.accessible(actor, public_id)
        item = await self._lists.get_item(shopping_list.id, item_id)
        if item is None:
            raise ShoppingItemNotFoundError("No such item on the list.")
        if cmd.checked is not None and cmd.checked != item.checked:
            item.checked = cmd.checked
            item.checked_by_id = actor.id if cmd.checked else None
            item.checked_at = now_utc() if cmd.checked else None
        if cmd.text is not None:
            if item.ingredient_id is None and not cmd.text.strip():
                raise InvalidPlanError("A free text item needs a text.")
            item.text = cmd.text.strip()[:255]
        if cmd.amount_set:
            if cmd.amount is not None and cmd.amount < 0:
                raise InvalidPlanError("The amount must not be negative.")
            item.amount = cmd.amount
        if cmd.unit_set:
            item.unit_id = None
            if cmd.unit_id:
                unit = await self._units.get_by_public_id(cmd.unit_id)
                if unit is None:
                    raise UnitNotFoundError("No such unit.")
                item.unit_id = unit.id
        saved = await self._lists.save_item(item)
        await self._touch(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "items_changed", actor)
        return saved

    async def delete_item(self, actor: User, public_id: str, item_id: str) -> None:
        shopping_list = await self.accessible(actor, public_id)
        item = await self._lists.get_item(shopping_list.id, item_id)
        if item is None:
            raise ShoppingItemNotFoundError("No such item on the list.")
        await self._lists.delete_item(item)
        await self._touch(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "items_changed", actor)

    async def clear_checked(self, actor: User, public_id: str) -> int:
        shopping_list = await self.accessible(actor, public_id)
        removed = await self._lists.delete_checked(shopping_list.id)
        await self._touch(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "items_changed", actor)
        return removed

    async def bought_window_hours(self) -> int:
        return (await self._settings.get_shopping()).bought_window_hours

    async def idle_list_days(self) -> int:
        return (await self._settings.get_shopping()).idle_list_days

    async def notes(self, actor: User) -> list[ShoppingListNote]:
        """The viewer's notes about idle lists that deleted themselves."""
        return await self._notes.list_for_user(actor.id)

    async def dismiss_note(self, actor: User, public_id: str) -> None:
        if not await self._notes.delete_for_user(actor.id, public_id):
            raise ShoppingListNoteNotFoundError("No such note.")
        await self._uow.commit()

    async def _add_recipe_items(
        self,
        actor: User,
        shopping_list: ShoppingList,
        recipe: Recipe,
        servings: int | None,
        bought: frozenset[int] = frozenset(),
    ) -> int:
        """Stages what the recipe and its sub-recipes need on the list
        without committing; returns how many lines it added or merged. A
        direct sub-recipe in `bought` goes on the list as one item instead
        of its ingredients."""
        lookups = await self._lookups.load_for([recipe])
        _, factor = scale_factor(recipe, servings)
        bought = bought & set(recipe.sub_recipe_ids)
        lines = shopping_lines(
            recipe, lookups.ingredients, lookups.units, lookups.recipes, factor, bought
        )
        needs = [
            n
            for n in derive(
                recipe, lookups.ingredients, lookups.units, servings, lookups.recipes
            ).needs
            if n.recipe_id in bought
        ]
        plain = await self._plain_lines(actor, recipe, lookups.recipes, factor, bought)
        items = await self._check_room(shopping_list, len(lines) + len(needs) + len(plain))
        touched = 0
        for line, path in lines:
            ingredient = lookups.ingredients.get(line.ingredient_id)
            existing = (
                find_mergeable(items, line.ingredient_id, line.unit_id, list(path))
                if line.amount is not None
                else None
            )
            if existing is not None:
                existing.amount = round((existing.amount or 0.0) + (line.amount or 0.0), 3)
                existing.add_recipe(recipe.id)
                await self._lists.save_item(existing)
            elif line.amount is None and any(
                i.ingredient_id == line.ingredient_id and not i.checked for i in items
            ):
                # Salt "to taste" is on the list already; an open item of the
                # same path still learns that this recipe wants it too.
                same = next(
                    (
                        i
                        for i in items
                        if i.ingredient_id == line.ingredient_id
                        and not i.checked
                        and i.sub_recipe_path == list(path)
                    ),
                    None,
                )
                if same is not None and recipe.id not in same.recipe_ids():
                    same.add_recipe(recipe.id)
                    await self._lists.save_item(same)
                continue
            else:
                item = await self._lists.save_item(
                    ShoppingItem(
                        list_id=shopping_list.id,
                        created=now_utc(),
                        created_by_id=actor.id,
                        ingredient_id=line.ingredient_id,
                        amount=round(line.amount, 3) if line.amount is not None else None,
                        unit_id=line.unit_id,
                        category_id=ingredient.category_id if ingredient else None,
                        recipe_id=recipe.id,
                        sub_recipe_path=list(path),
                    )
                )
                items.append(item)
            touched += 1
        for need in needs:
            # "I'll buy it": the sub-recipe itself, named from its path when
            # shown, so a reader who may not see it gets no title.
            items.append(
                await self._lists.save_item(
                    ShoppingItem(
                        list_id=shopping_list.id,
                        created=now_utc(),
                        created_by_id=actor.id,
                        amount=round(need.amount, 3) if need.amount is not None else None,
                        unit_id=need.unit_id,
                        recipe_id=recipe.id,
                        sub_recipe_path=[need.recipe_id],
                    )
                )
            )
            touched += 1
        for text, amount, unit_id, path in plain:
            existing = next(
                (
                    i
                    for i in items
                    if not i.checked
                    and i.ingredient_id is None
                    and i.text.casefold() == text.casefold()
                    and i.unit_id == unit_id
                    and i.sub_recipe_path == list(path)
                    and i.amount is not None
                ),
                None,
            )
            if existing is not None and amount is not None:
                existing.amount = round((existing.amount or 0.0) + amount, 3)
                existing.add_recipe(recipe.id)
                await self._lists.save_item(existing)
            else:
                items.append(
                    await self._lists.save_item(
                        ShoppingItem(
                            list_id=shopping_list.id,
                            created=now_utc(),
                            created_by_id=actor.id,
                            text=text,
                            amount=round(amount, 3) if amount is not None else None,
                            unit_id=unit_id,
                            recipe_id=recipe.id,
                            sub_recipe_path=list(path),
                        )
                    )
                )
            touched += 1
        return touched

    async def _plain_lines(
        self,
        actor: User,
        recipe: Recipe,
        tree: Mapping[int, Recipe],
        factor: float,
        bought: frozenset[int],
    ) -> list[tuple[str, float | None, int | None, tuple[int, ...]]]:
        """The plain-text lines of every mirror in the recipe's tree (the
        source's ingredients this instance keeps as text), scaled like the
        catalogue lines and named in the actor's language, as free-text
        items: text, amount, unit id and sub-recipe path."""
        if self._mirrors is None:
            return []
        # Only the sub-recipe lines count here, and their merge needs no units.
        lines_of = merged_lines_of({}, {}, tree)
        found = [
            (r, f, p)
            for r, f, p in batches(recipe, tree, lines_of, factor, skip=bought)
            if r.is_mirror
        ]
        if not found:
            return []
        mirrors = await self._mirrors.for_recipes(sorted({r.id for r, _, _ in found}))
        locale = ui_locale(str(actor.language))
        units: dict[str, int | None] = {}
        result: list[tuple[str, float | None, int | None, tuple[int, ...]]] = []
        for mirror_recipe, batch, path in found:
            mirror = mirrors.get(mirror_recipe.id)
            for line in (mirror.extras if mirror else {}).get("plain_lines") or []:
                names = {str(k): str(v) for k, v in (line.get("names") or {}).items() if v}
                text = names.get(locale) or next(iter(names.values()), "")
                if not text.strip():
                    continue
                unit_ref = line.get("unit_id")
                if unit_ref and unit_ref not in units:
                    unit = await self._units.get_by_public_id(str(unit_ref))
                    units[unit_ref] = unit.id if unit is not None else None
                amount = line.get("amount")
                result.append(
                    (
                        text.strip()[:255],
                        float(amount) * batch if isinstance(amount, int | float) else None,
                        units.get(unit_ref) if unit_ref else None,
                        path,
                    )
                )
        return result

    async def add_recipe(
        self,
        actor: User,
        public_id: str,
        recipe_public_id: str,
        servings: int | None,
        bought_sub_recipe_ids: list[str] | None = None,
    ) -> int:
        shopping_list = await self.accessible(actor, public_id)
        recipe = await self._recipes.get_by_public_id(recipe_public_id)
        if recipe is None or not can_view_recipe(await self._viewers.of(actor), recipe):
            raise RecipeNotFoundError("No such recipe.")
        if servings is not None and not 1 <= servings <= 100:
            raise InvalidPlanError("The servings must be between 1 and 100.")
        bought: set[int] = set()
        for sub_public_id in bought_sub_recipe_ids or []:
            sub = await self._recipes.get_by_public_id(sub_public_id)
            if sub is None or sub.id not in recipe.sub_recipe_ids:
                raise RecipeNotFoundError("The recipe has no such sub-recipe.")
            bought.add(sub.id)
        touched = await self._add_recipe_items(
            actor, shopping_list, recipe, servings, frozenset(bought)
        )
        await self._touch(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "items_changed", actor)
        return touched

    async def add_recipes(
        self,
        actor: User,
        public_id: str,
        wanted: list[tuple[Recipe, int]],
        bought_sub_recipe_ids: list[str] | None = None,
    ) -> int:
        """Adds several recipes at once, as the meal plan does for a week.
        A bought sub-recipe ("I'll buy it") applies to every recipe that
        uses it directly, and must be a direct sub-recipe of at least one."""
        shopping_list = await self.accessible(actor, public_id)
        direct = {s for recipe, _ in wanted for s in recipe.sub_recipe_ids}
        bought: set[int] = set()
        for sub_public_id in bought_sub_recipe_ids or []:
            sub = await self._recipes.get_by_public_id(sub_public_id)
            if sub is None or sub.id not in direct:
                raise RecipeNotFoundError("No planned recipe has such a sub-recipe.")
            bought.add(sub.id)
        touched = 0
        for recipe, servings in wanted:
            own = frozenset(bought & set(recipe.sub_recipe_ids))
            touched += await self._add_recipe_items(actor, shopping_list, recipe, servings, own)
        await self._touch(shopping_list)
        await self._uow.commit()
        await self._publish(shopping_list, "items_changed", actor)
        return touched
