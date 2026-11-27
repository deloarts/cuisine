"""
A webhook subscription and the deliveries made to it. A delivery is written
in the transaction of the change that caused it and sent afterwards by the
webhook worker, so an event is never sent for a change that rolled back and
never lost when the receiver is down.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

from src.platform.domain.value_objects.webhook_event import DeliveryStatus
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class WebhookSubscription(Entity):
    name: str
    url: str
    # Registered event keys.
    events: list[str] = field(default_factory=list)
    # The Standard Webhooks signing secret, whsec_<base64>. Shown once when
    # created or rotated; stored encrypted.
    secret: str = ""
    enabled: bool = True
    created: datetime
    changed: datetime


@dataclass(kw_only=True)
class WebhookDelivery(Entity):
    subscription_id: int
    event: str
    # The full JSON body, as sent on every attempt.
    payload: dict[str, Any] = field(default_factory=dict)
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    next_attempt_at: datetime | None = None
    last_attempt_at: datetime | None = None
    http_status: int | None = None
    duration_ms: int = 0
    # A short category, never the receiver's text.
    error: str | None = None
    created: datetime
    # The user the payload describes, if any. Deleting that user deletes the
    # delivery, so no trace of a deleted person stays in the log.
    subject_user_id: int | None = None
