"""Webhooks and in-app notices."""

from datetime import datetime
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema
from src.platform.adapters.inbound.api.schemas.user_schema import UserSummaryResponse

ContentLocale = Literal["en-GB", "de-AT"]


class WebhookEventResponse(ResponseSchema):
    key: str
    description: str


class WebhookSubscriptionRequest(RequestSchema):
    name: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=2048)
    events: list[str] = Field(min_length=1)
    enabled: bool = True


class WebhookSubscriptionResponse(ResponseSchema):
    id: UUID
    name: str
    url: str
    events: list[str]
    enabled: bool
    created: datetime
    changed: datetime


class WebhookSecretResponse(WebhookSubscriptionResponse):
    """Answers create and rotate: the only time the secret is shown."""

    secret: str


class WebhookDeliveryResponse(ResponseSchema):
    id: UUID
    event: str
    # pending, sending, succeeded or failed
    status: str
    attempts: int
    next_attempt_at: datetime | None
    last_attempt_at: datetime | None
    http_status: int | None
    duration_ms: int
    error: str | None
    created: datetime
    payload: dict[str, Any]


class NoticeTextSchema(RequestSchema):
    title: str = Field(default="", max_length=120)
    body: str = Field(default="", max_length=5000)


class NoticeRequest(RequestSchema):
    texts: dict[ContentLocale, NoticeTextSchema]
    active: bool = True


class NoticeTextResponse(ResponseSchema):
    title: str
    body: str


class NoticeAdminResponse(ResponseSchema):
    id: UUID
    texts: dict[str, NoticeTextResponse]
    active: bool
    created: datetime
    changed: datetime
    acknowledged: int
    # The active people the notice is shown to.
    audience: int


class NoticeResponse(ResponseSchema):
    """A pending notice for the signed-in user, in their language."""

    id: UUID
    locale: str
    title: str
    body: str
    created: datetime


class AcknowledgementResponse(ResponseSchema):
    user: UserSummaryResponse
    acknowledged_at: datetime


class AcknowledgementOverviewResponse(ResponseSchema):
    notice_id: UUID
    acknowledged: list[AcknowledgementResponse]
    pending: list[UserSummaryResponse]
