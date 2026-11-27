"""
A user deleting their own account. Platform's account deletion refuses
self-deletion, so this use case works over Platform's ports directly and
applies the self-deletion rules in one transaction:

- Published recipes visible to every signed-in user (instance or public)
  stay online without an owner, keeping their visibility,
  editable with manage:recipes. When the instance lets users choose a
  recipe's visibility, the user may delete them instead.
- Household recipes pass to the remaining household member with the oldest
  account; without one they are deleted. Private and shared recipes and all
  drafts are deleted.
- A recipe that would be deleted but that another user's recipe uses as a
  sub-recipe is handed over to that recipe's owner instead, the owner with
  the oldest account when several use it, and nothing in the using recipe
  changes. Its visibility widens just enough that the using recipes'
  readers keep reading it (`recipe_handover`). Recipes passing to the
  household, and recipes handed over themselves, count as using recipes of
  their new owner, so a handed-over recipe's own sub-recipes follow it.
  A recipe that would be deleted but that only recipes staying online
  without an owner use stays as well, without an owner, its visibility
  widened by the same rule, so nothing in those recipes changes either.
  Only a recipe nobody else's recipe uses, directly or through the tree,
  is deleted.
- Ingredients the user created stay in the catalogue without an owner.
- The household loses the member and the user's own shopping lists pass on
  or go, as in an administrator's deletion (DeleteAccountData).
- Credentials, sessions, devices, tokens, the API keys the user created
  with their service accounts, restrictions, consents, favourites, ratings,
  notes, cook events, the personal plan and the agent call log go with the
  user row, and every security event involving the user is removed. One
  anonymous `user_deleted` event remains, without actor, address or detail
  that could name the person.

The user proves it is them with the password or a passkey assertion and
types their e-mail address. The system user and the last remaining administrator
cannot delete themselves.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any
from typing import Literal
from uuid import UUID

from src.cookbook.application.services.recipe_deletion import RecipeDeletion
from src.cookbook.application.use_cases.accounts.delete_account import DeleteAccountData
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import LastAdministratorError
from src.cookbook.domain.exceptions import SelfDeletionConfirmationError
from src.cookbook.domain.services.recipe_handover import Readers
from src.cookbook.domain.services.recipe_handover import handed_over_visibility
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.ports.outbound.event_publisher import IEventPublisher
from src.cookbook.ports.outbound.repositories.household_repository import IHouseholdRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.platform.application.use_cases.account.avatar import delete_avatar_of
from src.platform.domain.entities.security_event import SecurityEvent
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PasswordConfirmationError
from src.platform.domain.exceptions import SystemUserProtectedError
from src.platform.domain.value_objects import token_scope
from src.platform.domain.value_objects.permission import Permission
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.instance_facts import IInstanceFacts
from src.platform.ports.outbound.passkey_verifier import IPasskeyVerifier
from src.platform.ports.outbound.password_hasher import IPasswordHasher
from src.platform.ports.outbound.replay_guard import IReplayGuard
from src.platform.ports.outbound.repositories.api_key_repository import IApiKeyRepository
from src.platform.ports.outbound.repositories.passkey_repository import IPasskeyRepository
from src.platform.ports.outbound.repositories.security_event_repository import (
    ISecurityEventRepository,
)
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.token_service import ITokenService
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

RefusedReason = Literal["system_user", "last_admin"]

# Platform's passkey login keeps a challenge this long; the same prompt
# serves the re-authentication.
CHALLENGE_TTL_SECONDS = 600
# Platform's account deletion announces this event without any data.
USER_DELETED_EVENT = "user.deleted"


@dataclass(frozen=True)
class HandedOverRecipe:
    public_id: UUID
    title: str
    new_owner_name: str


@dataclass(frozen=True)
class RecipeFates:
    """What happens to the own recipes beyond those staying online and
    those passing to the household, under one choice."""

    # Private, shared and heirless household recipes, deleted.
    recipes_deleted: int
    drafts_deleted: int
    # Recipes and drafts another user's recipe uses, handed over to that user.
    recipes_handed_over: list[HandedOverRecipe]
    # Recipes and drafts that only ownerless recipes use; they stay ownerless.
    sub_recipes_kept_online: int


@dataclass(frozen=True)
class SelfDeletionImpact:
    # Published recipes visible to every member that stay online without an owner.
    recipes_kept_online: int
    # Household recipes that pass to another household member.
    recipes_to_household: int
    # Private, shared and heirless household recipes, deleted.
    recipes_deleted: int
    drafts_deleted: int
    # Recipes and drafts another user's recipe uses, handed over to that user.
    recipes_handed_over: list[HandedOverRecipe]
    # Recipes and drafts that only ownerless recipes use; they stay ownerless.
    sub_recipes_kept_online: int
    # The same fates when the user deletes the public recipes too; None
    # when that choice is not offered.
    if_public_deleted: RecipeFates | None
    # Whether the user may delete the recipes that would stay online.
    can_delete_public_recipes: bool
    ingredients_kept: int
    lists_handed_over: int
    lists_deleted: int
    in_household: bool
    # Why the account cannot be deleted, or None.
    refused_reason: RefusedReason | None
    backup_keep_days: int
    backups_clear_by: date


@dataclass(frozen=True)
class SelfDeletionCommand:
    email: str
    password: str | None = None
    passkey_challenge_token: str | None = None
    passkey_credential: dict[str, Any] | None = None
    # Delete the recipes that would stay online; only when users may choose.
    delete_public_recipes: bool = False


@dataclass(frozen=True)
class _HandOver:
    # None keeps the recipe without an owner, next to the ownerless recipes using it.
    new_owner: User | None
    visibility: RecipeVisibility
    user_ids: frozenset[int]
    group_ids: frozenset[int]


@dataclass(frozen=True)
class _Plan:
    kept_online: list[Recipe]
    to_household: list[Recipe]
    deleted: list[Recipe]
    drafts: list[Recipe]
    heir: User | None
    # The recipes and drafts handed over instead of deleted, with their fate.
    handed_over: list[tuple[Recipe, _HandOver]]
    # Those staying without an owner, since only ownerless recipes use them.
    kept_ownerless: list[tuple[Recipe, _HandOver]]


class DeleteOwnAccount:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        household_repo: IHouseholdRepository,
        account_data: DeleteAccountData,
        deletion: RecipeDeletion,
        user_repo: IUserRepository,
        api_key_repo: IApiKeyRepository,
        security_event_repo: ISecurityEventRepository,
        passkey_repo: IPasskeyRepository,
        settings_repo: ISettingsRepository,
        file_repo: IStoredFileRepository,
        hasher: IPasswordHasher,
        verifier: IPasskeyVerifier,
        tokens: ITokenService,
        replay: IReplayGuard,
        facts: IInstanceFacts,
        uow: IUnitOfWork,
        events: IEventPublisher | None = None,
    ) -> None:
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._households = household_repo
        self._account = account_data
        self._deletion = deletion
        self._users = user_repo
        self._keys = api_key_repo
        self._security_events = security_event_repo
        self._passkeys = passkey_repo
        self._settings = settings_repo
        self._files = file_repo
        self._hasher = hasher
        self._verifier = verifier
        self._tokens = tokens
        self._replay = replay
        self._facts = facts
        self._uow = uow
        self._events = events

    async def _refused_reason(self, user: User) -> RefusedReason | None:
        if user.is_systemuser:
            return "system_user"
        if not user.has_permission(Permission.WRITE_USERS):
            return None
        others = [
            u
            for u in await self._users.list_all()
            if u.id != user.id and u.is_active and u.has_permission(Permission.WRITE_USERS)
        ]
        return None if others else "last_admin"

    async def _plan(self, user: User, *, delete_public: bool) -> _Plan:
        owned = await self._recipes.owned_by(user.id)
        drafts = [r for r in owned if r.status is not RecipeStatus.PUBLISHED]
        published = [r for r in owned if r.status is RecipeStatus.PUBLISHED]
        heir = await self._household_heir(user)
        kept, to_household, deleted = [], [], []
        for recipe in published:
            every_member = recipe.visibility in (
                RecipeVisibility.INSTANCE,
                RecipeVisibility.PEERS,
                RecipeVisibility.PUBLIC,
            )
            if every_member and not delete_public:
                kept.append(recipe)
            elif recipe.visibility is RecipeVisibility.HOUSEHOLD and heir is not None:
                to_household.append(recipe)
            else:
                deleted.append(recipe)
        fates = await self._hand_overs(user, [*deleted, *drafts], kept, to_household, heir)
        staying = [(r, fates[r.id]) for r in [*deleted, *drafts] if r.id in fates]
        return _Plan(
            kept,
            to_household,
            [r for r in deleted if r.id not in fates],
            [r for r in drafts if r.id not in fates],
            heir,
            [(r, f) for r, f in staying if f.new_owner is not None],
            [(r, f) for r, f in staying if f.new_owner is None],
        )

    async def _hand_overs(
        self,
        user: User,
        candidates: list[Recipe],
        kept_online: list[Recipe],
        to_household: list[Recipe],
        heir: User | None,
    ) -> dict[int, _HandOver]:
        """Which of the recipes about to be deleted another recipe that stays
        uses, with their new owner (None when only ownerless recipes use them)
        and visibility. A recipe handed over, kept or passing to the household
        counts with its new owner, so the rule reaches down the tree;
        sub-recipes form no cycles and nest at most three levels, so the
        fixpoint comes within a few rounds."""
        if not candidates:
            return {}
        parent_ids = await self._recipes.parent_ids([r.id for r in candidates])
        parents = {
            p.id: p
            for p in await self._recipes.get_many(
                sorted({i for ids in parent_ids.values() for i in ids})
            )
        }
        inherited = {r.id for r in to_household}
        ownerless = {r.id for r in kept_online}
        users: dict[int, User | None] = {}
        households: dict[int, frozenset[int]] = {}

        async def account(user_id: int) -> User | None:
            if user_id not in users:
                users[user_id] = await self._users.get(user_id)
            return users[user_id]

        async def household_of(user_id: int | None) -> frozenset[int]:
            if user_id is None:
                return frozenset()
            if user_id not in households:
                household = await self._households.of_user(user_id)
                members = household.member_ids if household is not None else []
                households[user_id] = frozenset(members) - {user.id}
            return households[user_id]

        async def readers(recipe: Recipe, fates: dict[int, _HandOver]) -> Readers | None:
            fate = fates.get(recipe.id)
            owner_id: int | None
            if fate is not None:
                owner_id = fate.new_owner.id if fate.new_owner is not None else None
                visibility, user_ids, group_ids = fate.visibility, fate.user_ids, fate.group_ids
            elif recipe.id in inherited and heir is not None:
                owner_id, visibility = heir.id, RecipeVisibility.HOUSEHOLD
                user_ids, group_ids = frozenset(), frozenset()
            elif recipe.owner_id is not None and recipe.owner_id != user.id:
                owner_id, visibility = recipe.owner_id, recipe.visibility
                user_ids = frozenset(recipe.shared_user_ids)
                group_ids = frozenset(recipe.shared_group_ids)
            elif recipe.id in ownerless:
                owner_id, visibility = None, recipe.visibility
                user_ids, group_ids = frozenset(), frozenset()
            else:
                return None
            return Readers(
                owner_id=owner_id,
                visibility=visibility,
                user_ids=user_ids,
                group_ids=group_ids,
                household_ids=await household_of(owner_id),
            )

        fates: dict[int, _HandOver] = {}
        for _ in range(len(candidates) + 1):
            changed = False
            for recipe in candidates:
                using = [
                    r
                    for r in [
                        await readers(parents[i], fates) for i in parent_ids.get(recipe.id, [])
                    ]
                    if r is not None
                ]
                owners = [a for a in [await account(r.owner_id) for r in using if r.owner_id] if a]
                if not using:
                    continue
                new_owner = min(owners, key=lambda u: (u.created, u.id)) if owners else None
                widened = handed_over_visibility(
                    Readers(
                        owner_id=user.id,
                        visibility=recipe.visibility,
                        user_ids=frozenset(recipe.shared_user_ids),
                        group_ids=frozenset(recipe.shared_group_ids),
                        household_ids=frozenset(),
                    ),
                    using,
                    new_owner_id=new_owner.id if new_owner is not None else None,
                    new_owner_household=await household_of(new_owner.id if new_owner else None),
                    leaving_id=user.id,
                )
                fate = _HandOver(new_owner, widened.visibility, widened.user_ids, widened.group_ids)
                if fates.get(recipe.id) != fate:
                    fates[recipe.id] = fate
                    changed = True
            if not changed:
                break
        return fates

    async def _household_heir(self, user: User) -> User | None:
        household = await self._households.of_user(user.id)
        if household is None:
            return None
        accounts = [
            u
            for u in [await self._users.get(m) for m in household.member_ids if m != user.id]
            if u is not None
        ]
        return min(accounts, key=lambda u: (u.created, u.id)) if accounts else None

    @staticmethod
    def _fates(plan: _Plan) -> RecipeFates:
        return RecipeFates(
            recipes_deleted=len(plan.deleted),
            drafts_deleted=len(plan.drafts),
            recipes_handed_over=[
                HandedOverRecipe(
                    public_id=recipe.public_id,
                    title=resolve(recipe.translations, None, recipe.original_locale)[1].title,
                    new_owner_name=fate.new_owner.display_name if fate.new_owner else "",
                )
                for recipe, fate in plan.handed_over
            ],
            sub_recipes_kept_online=len(plan.kept_ownerless),
        )

    async def impact(self, user: User) -> SelfDeletionImpact:
        privacy = await self._settings.get_privacy()
        plan = await self._plan(user, delete_public=False)
        fates = self._fates(plan)
        offered = privacy.users_may_change_visibility and bool(plan.kept_online)
        handed, deleted = await self._account.list_fates(user)
        retention = self._facts.backup_retention()
        return SelfDeletionImpact(
            recipes_kept_online=len(plan.kept_online),
            recipes_to_household=len(plan.to_household),
            recipes_deleted=fates.recipes_deleted,
            drafts_deleted=fates.drafts_deleted,
            recipes_handed_over=fates.recipes_handed_over,
            sub_recipes_kept_online=fates.sub_recipes_kept_online,
            if_public_deleted=(
                self._fates(await self._plan(user, delete_public=True)) if offered else None
            ),
            can_delete_public_recipes=privacy.users_may_change_visibility,
            ingredients_kept=len(await self._ingredients.ids_owned_by(user.id)),
            lists_handed_over=handed,
            lists_deleted=deleted,
            in_household=await self._households.of_user(user.id) is not None,
            refused_reason=await self._refused_reason(user),
            backup_keep_days=retention.keep_days,
            backups_clear_by=retention.gone_by,
        )

    async def _confirm(self, user: User, cmd: SelfDeletionCommand) -> None:
        if cmd.email.strip().lower() != user.email.strip().lower():
            raise SelfDeletionConfirmationError("Type your e-mail address to confirm.")
        if cmd.password is not None:
            if not await self._hasher.verify(cmd.password, user.hashed_password):
                raise PasswordConfirmationError("The password is wrong.")
            return
        if cmd.passkey_challenge_token and cmd.passkey_credential is not None:
            await self._confirm_passkey(user, cmd.passkey_challenge_token, cmd.passkey_credential)
            return
        raise SelfDeletionConfirmationError("Confirm with your password or a passkey.")

    async def _confirm_passkey(
        self, user: User, challenge_token: str, credential: dict[str, Any]
    ) -> None:
        rejected = PasswordConfirmationError("The passkey did not confirm this account.")
        claims = self._tokens.read(challenge_token)
        if claims is None or claims.scope != token_scope.PASSKEY_LOGIN or not claims.chl:
            raise rejected
        if not await self._replay.consume_once(f"passkey:{claims.chl}", CHALLENGE_TTL_SECONDS):
            raise rejected
        credential_id = self._verifier.credential_id_of(credential)
        passkey = (
            await self._passkeys.get_by_credential_id(credential_id) if credential_id else None
        )
        if passkey is None or passkey.user_id != user.id:
            raise rejected
        try:
            self._verifier.verify_authentication(
                credential=credential,
                challenge=claims.chl,
                public_key=passkey.public_key,
                sign_count=passkey.sign_count,
            )
        except Exception as exc:
            raise rejected from exc

    async def execute(self, user: User, cmd: SelfDeletionCommand) -> None:
        reason = await self._refused_reason(user)
        if reason == "system_user":
            raise SystemUserProtectedError("The system user cannot delete itself.")
        if reason == "last_admin":
            raise LastAdministratorError(
                "You are the only administrator; give someone else the right to manage users first."
            )
        await self._confirm(user, cmd)
        privacy = await self._settings.get_privacy()
        plan = await self._plan(
            user, delete_public=cmd.delete_public_recipes and privacy.users_may_change_visibility
        )
        now = now_utc()
        owned_ids = [str(r.public_id) for r in await self._recipes.owned_by(user.id)]
        for recipe, fate in [*plan.handed_over, *plan.kept_ownerless]:
            recipe.pass_to(fate.new_owner.id if fate.new_owner is not None else None)
            recipe.visibility = fate.visibility
            recipe.shared_user_ids = sorted(fate.user_ids)
            recipe.shared_group_ids = sorted(fate.group_ids)
            recipe.changed = now
            await self._recipes.save(recipe)
        for recipe in plan.kept_online:
            recipe.pass_to(None)
            recipe.changed = now
            await self._recipes.save(recipe)
        for recipe in plan.to_household:
            assert plan.heir is not None
            recipe.pass_to(plan.heir.id)
            recipe.changed = now
            await self._recipes.save(recipe)
        for recipe in [*plan.drafts, *plan.deleted]:
            await self._deletion.stage(recipe, unlink_parents=True)
        await self._ingredients.reassign_owner(user.id, None)
        await self._account.settle_variations(
            user, delete_public=cmd.delete_public_recipes and privacy.users_may_change_visibility
        )
        await self._account.tell_peers(owned_ids)
        await self._account.leave_household(user)
        await self._account.hand_over_lists(user)
        for key in await self._keys.list_all():
            if key.creator_id == user.id:
                service = await self._users.get(key.service_user_id)
                if service is not None:
                    await self._security_events.delete_involving(service.id)
                    await self._users.delete(service)
        await self._security_events.delete_involving(user.id)
        await delete_avatar_of(self._files, user)
        await self._users.delete(user)
        await self._security_events.add(
            SecurityEvent(
                event_type=SecurityEventType.USER_DELETED,
                outcome=SecurityEventOutcome.SUCCESS,
                created=now,
                detail={"self_deletion": True},
            )
        )
        if self._events is not None:
            await self._events.publish(USER_DELETED_EVENT, {})
        await self._uow.commit()
