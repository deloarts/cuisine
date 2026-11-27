from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.common_schema import PersonRef
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class HouseholdRequest(RequestSchema):
    name: str = Field(min_length=1, max_length=128)


class InviteRequest(RequestSchema):
    user_id: UUID


class SentInvitationResponse(ResponseSchema):
    id: UUID
    invitee: PersonRef | None
    inviter: PersonRef | None
    created: datetime


class HouseholdResponse(ResponseSchema):
    id: UUID
    name: str
    # Every member, the viewer included; the recipe browser preselects them
    # as dinner guests.
    members: list[PersonRef]
    invitations: list[SentInvitationResponse]
    # The household's default shopping list.
    shopping_list_id: UUID | None
    created: datetime


class MyHouseholdResponse(ResponseSchema):
    household: HouseholdResponse | None


class HouseholdRef(ResponseSchema):
    id: UUID
    name: str


class ReceivedInvitationResponse(ResponseSchema):
    id: UUID
    household: HouseholdRef
    inviter: PersonRef | None
    created: datetime


class HouseholdMembershipResponse(ResponseSchema):
    """What administrators see: who belongs to which household."""

    id: UUID
    name: str
    members: list[PersonRef]
