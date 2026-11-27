from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class GroupSummaryResponse(ResponseSchema):
    """What every signed-in user may see of a group: enough to share a
    recipe with it."""

    id: UUID
    name: str


class GroupResponse(ResponseSchema):
    id: UUID
    name: str
    description: str
    permissions: list[str]
    member_ids: list[UUID]
    created: datetime


class CreateGroupRequest(RequestSchema):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=2000)
    permissions: list[str] = Field(default_factory=list)
    member_ids: list[UUID] = Field(default_factory=list)


class UpdateGroupRequest(RequestSchema):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=2000)
    permissions: list[str] | None = None
    member_ids: list[UUID] | None = None


class PermissionResponse(ResponseSchema):
    name: str
    # False for the permissions a PAT or API key can never carry.
    grantable_to_tokens: bool
