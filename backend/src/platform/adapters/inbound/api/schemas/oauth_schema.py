"""Schemas of the OAuth consent page, the connected apps and the client
registration."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class ClientRegistrationRequest(BaseModel):
    """The client metadata of RFC 7591. Unlike every other request schema it
    ignores unknown fields, since the RFC asks a server to ignore metadata
    it does not understand and clients send plenty of it."""

    model_config = ConfigDict(extra="ignore")

    redirect_uris: list[str] = Field(default_factory=list)
    client_name: str | None = None
    client_uri: str | None = None
    token_endpoint_auth_method: str | None = None
    grant_types: list[str] | None = None
    response_types: list[str] | None = None


class AuthorizationRequestSchema(RequestSchema):
    """The query of the authorization URL, which the consent page forwards
    as it received it."""

    client_id: str = Field(max_length=128)
    redirect_uri: str | None = Field(default=None, max_length=2000)
    response_type: str | None = Field(default=None, max_length=32)
    code_challenge: str | None = Field(default=None, max_length=128)
    code_challenge_method: str | None = Field(default=None, max_length=16)
    state: str | None = Field(default=None, max_length=2000)
    scope: str | None = Field(default=None, max_length=1000)
    resource: str | None = Field(default=None, max_length=2000)


class AuthorizationPromptResponse(ResponseSchema):
    # Self-declared by the app, so the page shows it as plain text.
    client_name: str
    client_uri: str | None
    # Where the app sends the browser back to; the page shows it next to the
    # name, so a look-alike name with a foreign host stands out.
    redirect_host: str
    # The permissions the person may grant, and the ones the app asked for.
    offered: list[str]
    requested: list[str]
    # Set when the request is broken in a way the app has to hear about; the
    # page sends the browser there at once instead of asking.
    error_redirect: str | None


class AuthorizationDecisionRequest(RequestSchema):
    request: AuthorizationRequestSchema
    approve: bool
    permissions: list[str] = Field(default_factory=list, max_length=10)


class AuthorizationDecisionResponse(ResponseSchema):
    redirect_to: str


class ConnectedAppResponse(ResponseSchema):
    id: UUID
    client_name: str
    client_uri: str | None
    redirect_host: str
    permissions: list[str]
    created: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
