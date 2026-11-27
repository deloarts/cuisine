"""Mail templates, operations, legal pages and consents."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema
from src.platform.adapters.inbound.api.schemas.user_schema import UserSummaryResponse

ContentLocale = Literal["en-GB", "de-AT"]


class MailTemplateTextSchema(RequestSchema):
    subject: str = Field(default="", max_length=255)
    body: str = Field(default="", max_length=256 * 1024)


class MailTemplateLocaleResponse(ResponseSchema):
    locale: str
    subject: str
    body: str
    customized: bool


class MailTemplateKindResponse(ResponseSchema):
    kind: str
    variables: list[str]
    sample_context: dict[str, object]
    templates: list[MailTemplateLocaleResponse]


class MailTemplatePreviewResponse(ResponseSchema):
    subject: str
    html: str


class AlertResponse(ResponseSchema):
    kind: str
    description: str


class BackupRunResponse(ResponseSchema):
    trigger: str
    started: datetime
    finished: datetime | None
    ok: bool | None
    file: str | None


class RestoreStepResponse(ResponseSchema):
    text: str
    command: str | None


class LogEntryResponse(ResponseSchema):
    time: datetime
    level: str
    logger: str
    message: str


class LegalPageResponse(ResponseSchema):
    kind: str
    version: int
    locale: str
    # Markdown; the privacy statement includes its privacy mode section.
    body: str
    published_at: datetime


class LegalPublishRequest(RequestSchema):
    texts: dict[ContentLocale, str]


class LegalVersionResponse(ResponseSchema):
    id: UUID
    kind: str
    version: int
    texts: dict[str, str]
    published_at: datetime
    privacy_mode: str | None
    default_visibility: str | None
    allow_public_recipes: bool | None = None
    peering_enabled: bool | None = None


class LegalDraftResponse(ResponseSchema):
    locale: str
    body: str


class PrivacyStatusResponse(ResponseSchema):
    current_version: int | None
    acknowledged_version: int | None
    pending: bool


class PrivacyAcknowledgementEntry(ResponseSchema):
    user: UserSummaryResponse
    # The version the person acknowledged last, null when never.
    version: int | None
    acknowledged_at: datetime | None


class PrivacyAcknowledgementOverviewResponse(ResponseSchema):
    """Who acknowledged the current privacy statement version and who is
    still asked, among the active people (service accounts are never asked).
    Before the first statement both lists are empty."""

    current_version: int | None
    acknowledged: list[PrivacyAcknowledgementEntry]
    pending: list[PrivacyAcknowledgementEntry]


class PrivacyAcknowledgeRequest(RequestSchema):
    version: int = Field(ge=1)


class ConsentResponse(ResponseSchema):
    # health_data or ai_agents
    kind: str
    granted: bool
    granted_at: datetime | None


class BackupRetentionResponse(ResponseSchema):
    keep_days: int
    # For data deleted today, the day it is gone from every backup.
    gone_by: str
