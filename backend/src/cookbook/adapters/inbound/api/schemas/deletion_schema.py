from datetime import date
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.common_schema import RecipeRef
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class AccountDeletionImpact(ResponseSchema):
    """What deleting an account touches, for the confirmation dialog.
    Backups keep the data until they rotate out."""

    # Published recipes per visibility: private, household, shared, instance,
    # peers, public.
    recipes: dict[str, int]
    # Always deleted.
    drafts: int
    ingredients: int
    lists_handed_over: int
    lists_deleted: int
    in_household: bool
    # Deleted data stays in existing backups for this many days
    # (BACKUP__KEEP_DAYS) and is gone from them by `backups_clear_by`.
    backup_keep_days: int
    backups_clear_by: date


class HandedOverRecipe(ResponseSchema):
    """An own recipe or draft that another user's recipe uses as a
    sub-recipe; it passes to that recipe's owner instead of being deleted."""

    id: UUID
    title: str
    new_owner_name: str


class SelfDeletionRecipeFates(ResponseSchema):
    """What happens to the own recipes when the user deletes the public
    recipes too, in the fields of the same names in `SelfDeletionImpact`."""

    recipes_deleted: int
    drafts_deleted: int
    recipes_handed_over: list[HandedOverRecipe]
    sub_recipes_kept_online: int


class SelfDeletionImpact(ResponseSchema):
    """What deleting the own account does, computed for this user and this
    instance. Backups keep the data until they rotate out."""

    # Published recipes visible to every member that stay online without an
    # owner, unless the user deletes them (`can_delete_public_recipes`).
    recipes_kept_online: int
    # Household recipes that pass to the remaining member with the oldest account.
    recipes_to_household: int
    # Private and shared recipes, and household recipes nobody inherits.
    recipes_deleted: int
    drafts_deleted: int
    # Recipes and drafts another user's recipe uses; they pass to the owner
    # of the using recipe (the one with the oldest account when several),
    # with their visibility widened to the using recipe's readers.
    recipes_handed_over: list[HandedOverRecipe]
    # Recipes and drafts that only recipes staying online without an owner
    # use; they stay online without an owner as well.
    sub_recipes_kept_online: int
    # The deleted, handed-over and kept recipes when the user deletes the
    # public recipes too; null when that choice is not offered.
    if_public_deleted: SelfDeletionRecipeFates | None
    # Whether the instance lets users choose visibility, so they may delete
    # the recipes that would stay online.
    can_delete_public_recipes: bool
    # Ingredients the user created; they stay in the catalogue without an owner.
    ingredients_kept: int
    lists_handed_over: int
    lists_deleted: int
    in_household: bool
    # Why the account cannot be deleted, or null: the system user, or the
    # only remaining administrator.
    refused_reason: Literal["system_user", "last_admin"] | None
    backup_keep_days: int
    backups_clear_by: date


class PasskeyConfirmation(RequestSchema):
    """An assertion over a challenge from `POST /api/v1/auth/login/passkey/options`."""

    challenge_token: str
    credential: dict[str, Any]


class SelfDeletionRequest(RequestSchema):
    """Confirms the deletion with the own e-mail address and either the
    password or a passkey assertion."""

    email: str = Field(max_length=254)
    password: str | None = Field(default=None, max_length=1024)
    passkey: PasskeyConfirmation | None = None
    # Delete the recipes that would stay online instead; only honoured when
    # the instance lets users choose visibility.
    delete_public_recipes: bool = False


class RecipeDeletionImpact(ResponseSchema):
    # A recipe using this one as a sub-recipe blocks the deletion.
    blocked: bool
    used_by: list[RecipeRef]
    # Recipes using it that the viewer cannot see.
    used_by_hidden_count: int


class IngredientDeletionImpact(ResponseSchema):
    # Base ingredients cannot be deleted.
    seeded: bool
    # The number of recipes using it, and those the viewer can see.
    recipe_count: int
    recipes: list[RecipeRef]
    # Whether the viewer may merge it into another ingredient instead.
    can_merge: bool


class UnitDeletionImpact(ResponseSchema):
    seeded: bool
    in_use: bool


class MergeRequest(RequestSchema):
    into_id: UUID
