from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class SessionResponse(ResponseSchema):
    id: UUID
    created: datetime
    last_seen_at: datetime
    user_agent: str | None
    client_ip: str | None
    current: bool


class CurrentSessionResponse(ResponseSchema):
    # When the session making the request ends at the latest, whatever the
    # user does; null when it has no absolute lifetime. The system user's
    # sessions end 15 minutes after sign-in.
    expires_at: datetime | None
    # The server's clock, so the client can correct for a skewed one.
    server_time: datetime


class TrustedDeviceResponse(ResponseSchema):
    id: UUID
    created: datetime
    expires_at: datetime
    user_agent: str | None
    last_used_at: datetime | None


class PasskeyResponse(ResponseSchema):
    id: UUID
    name: str
    created: datetime
    last_used_at: datetime | None
    backed_up: bool


class RegisterPasskeyRequest(RequestSchema):
    challenge_token: str
    credential: dict[str, Any]
    name: str = Field(default="Passkey", max_length=64)


class RenamePasskeyRequest(RequestSchema):
    name: str = Field(min_length=1, max_length=64)


class TotpEnrolmentResponse(ResponseSchema):
    secret: str
    provisioning_uri: str


class TotpEnrolRequest(RequestSchema):
    # The current password. A signed-in session must send it; the setup
    # token from the login step has proven the password already and may
    # leave it out.
    password: str | None = Field(default=None, min_length=1, max_length=1024)


class TotpConfirmRequest(RequestSchema):
    code: str = Field(min_length=6, max_length=10)


class TotpConfirmResponse(ResponseSchema):
    # True when the confirmation also signed the user in (forced enrolment).
    session_started: bool


class TokenCreateRequest(RequestSchema):
    name: str = Field(min_length=1, max_length=64)
    permissions: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class PatResponse(ResponseSchema):
    id: UUID
    name: str
    token_prefix: str
    permissions: list[str]
    created: datetime
    expires_at: datetime | None
    last_used_at: datetime | None


class PatCreatedResponse(PatResponse):
    # Shown once; only its hash is stored.
    token: str


class ApiKeyResponse(ResponseSchema):
    id: UUID
    name: str
    token_prefix: str
    permissions: list[str]
    created: datetime
    expires_at: datetime | None
    last_used_at: datetime | None


class ApiKeyCreatedResponse(ApiKeyResponse):
    token: str


class SecurityEventResponse(ResponseSchema):
    id: UUID
    created: datetime
    event_type: str
    outcome: str
    actor_id: UUID | None
    actor_name: str | None
    target_user_id: UUID | None
    target_name: str | None
    detail: dict[str, Any]
    client_ip: str | None
    user_agent: str | None


class AgentCallResponse(ResponseSchema):
    id: UUID
    called_at: datetime
    user_id: UUID | None
    user_name: str | None
    token_kind: str
    token_name: str
    tool: str
    arguments: dict[str, Any]
    outcome: str
    duration_ms: int
    error: str | None
    created_refs: list[str]
