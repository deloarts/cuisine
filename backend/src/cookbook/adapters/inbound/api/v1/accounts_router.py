"""/api/v1/web/users/{user_id}: deleting an account, with the handover of
its cookbook data in the same transaction. Mounted by the composition root
in place of a plain delete, since Platform does not know the cookbook. Also
/users/me: a user deleting their own account, which Platform's deletion
refuses."""

import json
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Response
from fastapi import status
from fastapi.encoders import jsonable_encoder

from src.cookbook.adapters.inbound.api.deps import get_delete_account_data
from src.cookbook.adapters.inbound.api.deps import get_delete_own_account
from src.cookbook.adapters.inbound.api.deps import get_export_own_data
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import AccountDeletionImpact
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import HandedOverRecipe
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import SelfDeletionImpact
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import SelfDeletionRecipeFates
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import SelfDeletionRequest
from src.cookbook.application.use_cases.accounts.delete_account import DeleteAccountData
from src.cookbook.application.use_cases.accounts.delete_own_account import DeleteOwnAccount
from src.cookbook.application.use_cases.accounts.delete_own_account import (
    HandedOverRecipe as HandedOverRecipeView,
)
from src.cookbook.application.use_cases.accounts.delete_own_account import SelfDeletionCommand
from src.cookbook.application.use_cases.accounts.export_own_data import ExportOwnData
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import get_instance_facts
from src.platform.adapters.inbound.api.deps import get_manage_users
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.admin.users import ManageUsers
from src.platform.domain.entities.user import User
from src.platform.domain.services.content_types import content_disposition
from src.platform.domain.value_objects.permission import Permission
from src.platform.infrastructure.security.cookies import clear_session_cookie
from src.platform.ports.outbound.instance_facts import IInstanceFacts
from src.shared_kernel.domain.services.clock import now_utc

router = APIRouter(tags=["users"])

_users = require_permission(Permission.WRITE_USERS)


# The own account comes first, so /users/me never matches /users/{user_id}.


@router.get(
    "/users/me/export",
    tags=["account"],
    response_class=Response,
    responses={200: {"content": {"application/json": {}}, "description": "The data as a file."}},
)
async def export_own_data(
    user: User = Depends(get_current_user),
    use_case: ExportOwnData = Depends(get_export_own_data),
) -> Response:
    """Download my data: the profile, consents and every cookbook record
    of the signed-in user as one JSON file."""
    data = jsonable_encoder(await use_case.execute(user))
    name = f"cuisine-data-{now_utc().date().isoformat()}.json"
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": content_disposition(name, inline=False),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


def _handed_over(recipes: list[HandedOverRecipeView]) -> list[HandedOverRecipe]:
    return [
        HandedOverRecipe(id=r.public_id, title=r.title, new_owner_name=r.new_owner_name)
        for r in recipes
    ]


@router.get("/users/me/deletion-impact", response_model=SelfDeletionImpact, tags=["account"])
async def own_deletion_impact(
    user: User = Depends(get_current_user),
    use_case: DeleteOwnAccount = Depends(get_delete_own_account),
) -> SelfDeletionImpact:
    """What deleting the own account would do, for the confirmation dialog."""
    impact = await use_case.impact(user)
    other = impact.if_public_deleted
    return SelfDeletionImpact(
        recipes_kept_online=impact.recipes_kept_online,
        recipes_to_household=impact.recipes_to_household,
        recipes_deleted=impact.recipes_deleted,
        drafts_deleted=impact.drafts_deleted,
        recipes_handed_over=_handed_over(impact.recipes_handed_over),
        sub_recipes_kept_online=impact.sub_recipes_kept_online,
        if_public_deleted=(
            SelfDeletionRecipeFates(
                recipes_deleted=other.recipes_deleted,
                drafts_deleted=other.drafts_deleted,
                recipes_handed_over=_handed_over(other.recipes_handed_over),
                sub_recipes_kept_online=other.sub_recipes_kept_online,
            )
            if other is not None
            else None
        ),
        can_delete_public_recipes=impact.can_delete_public_recipes,
        ingredients_kept=impact.ingredients_kept,
        lists_handed_over=impact.lists_handed_over,
        lists_deleted=impact.lists_deleted,
        in_household=impact.in_household,
        refused_reason=impact.refused_reason,
        backup_keep_days=impact.backup_keep_days,
        backups_clear_by=impact.backups_clear_by,
    )


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT, tags=["account"])
async def delete_own_account(
    body: SelfDeletionRequest,
    response: Response,
    user: User = Depends(get_current_user),
    use_case: DeleteOwnAccount = Depends(get_delete_own_account),
) -> None:
    """Deletes the own account terminally after re-authentication (password
    or passkey assertion) and the typed e-mail address, and ends the session."""
    await use_case.execute(
        user,
        SelfDeletionCommand(
            email=body.email,
            password=body.password,
            passkey_challenge_token=body.passkey.challenge_token if body.passkey else None,
            passkey_credential=body.passkey.credential if body.passkey else None,
            delete_public_recipes=body.delete_public_recipes,
        ),
    )
    clear_session_cookie(response)


@router.get("/users/{user_id}/deletion-impact", response_model=AccountDeletionImpact)
async def account_deletion_impact(
    user_id: str,
    _actor: User = Depends(_users),
    users: ManageUsers = Depends(get_manage_users),
    account: DeleteAccountData = Depends(get_delete_account_data),
    facts: IInstanceFacts = Depends(get_instance_facts),
) -> AccountDeletionImpact:
    impact = await account.impact(await users.get(user_id))
    retention = facts.backup_retention()
    return AccountDeletionImpact(
        recipes=impact.recipes,
        drafts=impact.drafts,
        ingredients=impact.ingredients,
        lists_handed_over=impact.lists_handed_over,
        lists_deleted=impact.lists_deleted,
        in_household=impact.in_household,
        backup_keep_days=retention.keep_days,
        backups_clear_by=retention.gone_by,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    new_owner_id: str | None = Query(
        None, description="The person who takes over the recipes and ingredients."
    ),
    ownerless_visibility: Literal["keep", "instance", "delete"] = Query(
        "instance",
        description="Without a new owner: keep the recipes' visibility, make them visible "
        "to every signed-in user (public recipes stay public), or delete them. Private and "
        "household recipes cannot keep theirs.",
    ),
    actor: User = Depends(_users),
    context: RequestContext = Depends(get_request_context),
    users: ManageUsers = Depends(get_manage_users),
    account: DeleteAccountData = Depends(get_delete_account_data),
) -> None:
    """Deletes the account terminally and without a trace."""

    async def hand_over(user: User) -> None:
        await account.stage(
            user, new_owner_id=new_owner_id, ownerless_visibility=ownerless_visibility
        )

    await users.delete(actor, user_id, context=context, before_delete=hand_over)
