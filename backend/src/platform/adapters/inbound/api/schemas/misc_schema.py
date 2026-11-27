from uuid import UUID

from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class VersionResponse(ResponseSchema):
    version: str


class HealthResponse(ResponseSchema):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)


class ResolvedPublicIdResponse(ResponseSchema):
    """What a public id opens: the kind of page, the public id of its row
    (a step's recipe for a step) and the frontend path."""

    kind: str
    id: UUID
    route: str
