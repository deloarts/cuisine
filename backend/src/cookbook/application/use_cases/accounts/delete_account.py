"""
What happens to the cookbook data of an account an administrator deletes.
It runs inside Platform's account deletion (ManageUsers.delete), in the same
transaction, before the user row goes.

- Drafts are deleted.
- Published recipes and the user's ingredients go to a new owner, any active
  person, or to nobody. Without a new owner the administrator chooses for the
  recipes: keep their visibility, make them visible to every signed-in user
  (instance; public recipes stay public), or delete them. Private and
  household recipes cannot keep their visibility without an owner (nobody
  could read them), so "keep" is refused while there are some. Ownerless
  recipes are editable with manage:recipes only.
- A household loses the member; their entries of its plan and its default
  list pass to another member, and the last member dissolves it.
- Shopping lists the user owns pass to the longest-standing member (the
  oldest account among them), or are deleted when nobody else is on them.
- Variations (`settle_variations`): a shared variation of a published
  recipe visible to every signed-in user (instance or public) stays online
  without an author, like such a recipe after a self-deletion; private
  variations and variations of any other recipe are deleted.
- Favourites, ratings (averages follow), notes, food restrictions, cook
  events and the personal plan go with the user row (ON DELETE CASCADE);
  pointers such as checked_by become empty.
"""

from dataclasses import dataclass
from typing import Literal

from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.application.services.recipe_deletion import RecipeDeletion
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import AccountDeletionChoiceError
from src.cookbook.domain.exceptions import RecipeInUseError
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.ports.outbound.repositories.cooking_repositories import IMealPlanRepository
from src.cookbook.ports.outbound.repositories.cooking_repositories import IShoppingListRepository
from src.cookbook.ports.outbound.repositories.household_repository import IHouseholdRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import UserNotFoundError
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.shared_kernel.domain.services.clock import now_utc

OwnerlessVisibility = Literal["keep", "instance", "delete"]
_EVERY_MEMBER = (RecipeVisibility.INSTANCE, RecipeVisibility.PEERS, RecipeVisibility.PUBLIC)
_UNREADABLE = (RecipeVisibility.PRIVATE, RecipeVisibility.HOUSEHOLD)


@dataclass(frozen=True)
class AccountImpact:
    # Published recipes per visibility value.
    recipes: dict[str, int]
    drafts: int
    ingredients: int
    lists_handed_over: int
    lists_deleted: int
    in_household: bool


class DeleteAccountData:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        household_repo: IHouseholdRepository,
        list_repo: IShoppingListRepository,
        meal_plan_repo: IMealPlanRepository,
        user_repo: IUserRepository,
        deletion: RecipeDeletion,
        variation_repo: IRecipeVariationRepository,
        sharing: PeerRecipeSharing | None = None,
    ) -> None:
        self._sharing = sharing
        self._variations = variation_repo
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._households = household_repo
        self._lists = list_repo
        self._plan = meal_plan_repo
        self._users = user_repo
        self._deletion = deletion

    async def impact(self, user: User) -> AccountImpact:
        owned = await self._recipes.owned_by(user.id)
        published = [r for r in owned if r.status is RecipeStatus.PUBLISHED]
        counts = {v.value: 0 for v in RecipeVisibility}
        for recipe in published:
            counts[recipe.visibility.value] += 1
        handed, deleted = await self.list_fates(user)
        household = await self._households.of_user(user.id)
        return AccountImpact(
            recipes=counts,
            drafts=len(owned) - len(published),
            ingredients=len(await self._ingredients.ids_owned_by(user.id)),
            lists_handed_over=handed,
            lists_deleted=deleted,
            in_household=household is not None,
        )

    async def list_fates(self, user: User) -> tuple[int, int]:
        """How many of the user's own lists pass to another member and how
        many are deleted, since nobody else is on them."""
        handed, deleted = 0, 0
        for shopping_list in await self._lists.list_for_user(user.id, None):
            if shopping_list.owner_id != user.id or shopping_list.household_id is not None:
                continue
            if [m for m in shopping_list.member_ids if m != user.id]:
                handed += 1
            else:
                deleted += 1
        return handed, deleted

    async def _new_owner(self, public_id: str | None) -> User | None:
        if not public_id:
            return None
        owner = await self._users.get_by_public_id(public_id)
        if owner is None or not owner.is_active or owner.is_service_account:
            raise UserNotFoundError("The new owner must be an active person.")
        return owner

    async def stage(
        self,
        user: User,
        *,
        new_owner_id: str | None,
        ownerless_visibility: OwnerlessVisibility,
    ) -> None:
        owner = await self._new_owner(new_owner_id)
        if owner is not None and owner.id == user.id:
            raise AccountDeletionChoiceError("The new owner must be another person.")
        owned = await self._recipes.owned_by(user.id)
        owned_ids = [str(r.public_id) for r in owned]
        drafts = [r for r in owned if r.status is not RecipeStatus.PUBLISHED]
        published = [r for r in owned if r.status is RecipeStatus.PUBLISHED]
        if owner is None and ownerless_visibility == "keep":
            unreadable = [r for r in published if r.visibility in _UNREADABLE]
            if unreadable:
                raise AccountDeletionChoiceError(
                    f"{len(unreadable)} private or household recipes would be readable by "
                    "nobody without an owner; make them visible to every member or delete them."
                )
        for draft in drafts:
            await self._deletion.stage(draft, unlink_parents=True)
        if owner is None and ownerless_visibility == "delete":
            await self._delete_all(published)
        else:
            for recipe in published:
                recipe.pass_to(owner.id if owner else None)
                if (
                    owner is None
                    and ownerless_visibility == "instance"
                    and recipe.visibility not in (RecipeVisibility.PEERS, RecipeVisibility.PUBLIC)
                ):
                    recipe.visibility = RecipeVisibility.INSTANCE
                    recipe.shared_user_ids, recipe.shared_group_ids = [], []
                recipe.changed = now_utc()
                await self._recipes.save(recipe)
        await self._ingredients.reassign_owner(user.id, owner.id if owner else None)
        await self.settle_variations(user, delete_public=False)
        await self.tell_peers(owned_ids)
        await self.leave_household(user)
        await self.hand_over_lists(user)

    async def tell_peers(self, recipe_ids: list[str]) -> None:
        """The paired instances lose the recipes of a deleted account: those
        deleted, those left without an owner and, unless the new owner's
        recipe is public, those handed over."""
        if self._sharing is not None:
            await self._sharing.refresh(recipe_ids)

    async def _delete_all(self, recipes: list[Recipe]) -> None:
        """Deletes the recipes; one another person's recipe uses blocks all."""
        ids = {r.id for r in recipes}
        parents = await self._recipes.parent_ids(sorted(ids))
        if any(set(found) - ids for found in parents.values()):
            raise RecipeInUseError(
                "Another person's recipe uses one of these recipes as a sub-recipe; "
                "hand them over instead."
            )
        for recipe in recipes:
            await self._deletion.stage(recipe, unlink_parents=True)

    async def settle_variations(self, user: User, *, delete_public: bool) -> None:
        """Runs after the user's recipes were handed over, kept or deleted.
        A shared variation of a published recipe visible to every signed-in
        user (instance or public) stays online without an author, unless
        `delete_public` (the user chose to delete their public recipes too);
        every other one is deleted."""
        variations = await self._variations.by_author(user.id)
        recipes = {r.id: r for r in await self._recipes.get_many([v.recipe_id for v in variations])}
        for variation in variations:
            recipe = recipes.get(variation.recipe_id)
            stays = (
                not delete_public
                and not variation.private
                and recipe is not None
                and recipe.status is RecipeStatus.PUBLISHED
                and recipe.visibility in _EVERY_MEMBER
            )
            if stays:
                variation.author_id = None
                await self._variations.save(variation)
            else:
                await self._variations.delete(variation)

    async def leave_household(self, user: User) -> None:
        household = await self._households.of_user(user.id)
        if household is None:
            return
        others = [m for m in household.member_ids if m != user.id]
        if not others:
            await self._households.delete(household)
            return
        await self._plan.hand_over(household.id, user.id, others[0])
        default = await self._lists.of_household(household.id)
        if default is not None and default.owner_id == user.id:
            default.owner_id = others[0]
            await self._lists.save(default)
        household.member_ids = others
        await self._households.save(household)

    async def hand_over_lists(self, user: User) -> None:
        for shopping_list in await self._lists.list_for_user(user.id, None):
            if shopping_list.owner_id != user.id or shopping_list.household_id is not None:
                continue
            members = [m for m in shopping_list.member_ids if m != user.id]
            if not members:
                await self._lists.delete(shopping_list)
                continue
            accounts = [u for u in [await self._users.get(m) for m in members] if u is not None]
            heir = min(accounts, key=lambda u: (u.created, u.id))
            shopping_list.owner_id = heir.id
            shopping_list.member_ids = [m for m in members if m != heir.id]
            await self._lists.save(shopping_list)
