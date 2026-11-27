"""/api/v1/web/households: the viewer's household, its invitations and
membership, and the membership overview for administrators. No route reads
another household's meal plan or lists."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from src.cookbook.adapters.inbound.api.context import get_presenter
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_manage_households
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.schemas.household_schema import HouseholdMembershipResponse
from src.cookbook.adapters.inbound.api.schemas.household_schema import HouseholdRef
from src.cookbook.adapters.inbound.api.schemas.household_schema import HouseholdRequest
from src.cookbook.adapters.inbound.api.schemas.household_schema import HouseholdResponse
from src.cookbook.adapters.inbound.api.schemas.household_schema import InviteRequest
from src.cookbook.adapters.inbound.api.schemas.household_schema import MyHouseholdResponse
from src.cookbook.adapters.inbound.api.schemas.household_schema import ReceivedInvitationResponse
from src.cookbook.adapters.inbound.api.schemas.household_schema import SentInvitationResponse
from src.cookbook.application.use_cases.households.manage_households import ManageHouseholds
from src.cookbook.domain.entities.household import Household
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(prefix="/households", tags=["households"])
admin_router = APIRouter(tags=["households"])

_admins = require_permission(Permission.WRITE_USERS)


async def _household(
    household: Household, presenter: Presenter, c: Cookbook, use_case: ManageHouseholds
) -> HouseholdResponse:
    invitations = await use_case.pending_invitations(household)
    people = await presenter.people(
        [
            *household.member_ids,
            *(i.invitee_id for i in invitations),
            *(i.inviter_id for i in invitations),
        ]
    )
    shopping_list = await c.shopping_lists.of_household(household.id)
    return HouseholdResponse(
        id=household.public_id,
        name=household.name,
        members=[p for m in household.member_ids if (p := people.get(m)) is not None],
        invitations=[
            SentInvitationResponse(
                id=i.public_id,
                invitee=people.get(i.invitee_id),
                inviter=people.get(i.inviter_id) if i.inviter_id else None,
                created=i.created,
            )
            for i in invitations
        ],
        shopping_list_id=shopping_list.public_id if shopping_list else None,
        created=household.created,
    )


@router.get("/mine", response_model=MyHouseholdResponse)
async def my_household(
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> MyHouseholdResponse:
    household = await use_case.mine(user)
    return MyHouseholdResponse(
        household=await _household(household, presenter, c, use_case) if household else None
    )


@router.post("", response_model=HouseholdResponse, status_code=status.HTTP_201_CREATED)
async def create_household(
    body: HouseholdRequest,
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> HouseholdResponse:
    """Founds a household with the viewer as its first member and creates
    its default shopping list."""
    return await _household(await use_case.create(user, body.name), presenter, c, use_case)


@router.put("/mine", response_model=HouseholdResponse)
async def rename_household(
    body: HouseholdRequest,
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> HouseholdResponse:
    return await _household(await use_case.rename(user, body.name), presenter, c, use_case)


@router.post("/mine/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_household(
    user: User = Depends(get_current_user),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> None:
    """The last member leaving dissolves the household with its plan and
    default list."""
    await use_case.leave(user)


@router.post(
    "/mine/invitations",
    response_model=SentInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_to_household(
    body: InviteRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> SentInvitationResponse:
    invitation = await use_case.invite(user, str(body.user_id))
    people = await presenter.people([invitation.invitee_id, invitation.inviter_id])
    return SentInvitationResponse(
        id=invitation.public_id,
        invitee=people.get(invitation.invitee_id),
        inviter=people.get(invitation.inviter_id) if invitation.inviter_id else None,
        created=invitation.created,
    )


@router.delete("/mine/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> None:
    await use_case.revoke(user, invitation_id)


@router.get("/invitations", response_model=list[ReceivedInvitationResponse])
async def my_invitations(
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> list[ReceivedInvitationResponse]:
    """The invitations the viewer received."""
    invitations = await use_case.invitations_for(user)
    people = await presenter.people(i.inviter_id for i in invitations)
    result = []
    for invitation in invitations:
        household = await use_case.household_of_invitation(invitation)
        if household is None:
            continue
        result.append(
            ReceivedInvitationResponse(
                id=invitation.public_id,
                household=HouseholdRef(id=household.public_id, name=household.name),
                inviter=people.get(invitation.inviter_id) if invitation.inviter_id else None,
                created=invitation.created,
            )
        )
    return result


@router.post("/invitations/{invitation_id}/accept", response_model=HouseholdResponse)
async def accept_invitation(
    invitation_id: str,
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> HouseholdResponse:
    household = await use_case.accept(user, invitation_id)
    return await _household(household, presenter, c, use_case)


@router.post("/invitations/{invitation_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_invitation(
    invitation_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> None:
    await use_case.decline(user, invitation_id)


@admin_router.get("/admin/households", response_model=list[HouseholdMembershipResponse])
async def household_memberships(
    _admin: User = Depends(_admins),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageHouseholds = Depends(get_manage_households),
) -> list[HouseholdMembershipResponse]:
    """Who belongs to which household, for user administration. Never the
    households' plans or lists."""
    households = await use_case.all()
    people = await presenter.people(m for h in households for m in h.member_ids)
    return [
        HouseholdMembershipResponse(
            id=h.public_id,
            name=h.name,
            members=[p for m in h.member_ids if (p := people.get(m)) is not None],
        )
        for h in households
    ]
