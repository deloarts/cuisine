"""
The catalogue of events a webhook can subscribe to. Platform registers its
own here; the cookbook registers its events from the composition root, so
this module never names a cookbook concept. A subscription may only name
registered events.
"""

from dataclasses import dataclass

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class DeliveryStatus(StrValueEnum):
    # Waiting for its first or next attempt.
    PENDING = "pending"
    # Claimed by a worker and being sent.
    SENDING = "sending"
    SUCCEEDED = "succeeded"
    # Every attempt failed; only a manual retry sends it again.
    FAILED = "failed"


@dataclass(frozen=True)
class WebhookEventType:
    key: str
    # One sentence for the admin's event picker.
    description: str


# Sent by "send test"; never subscribable, always delivered to the one
# subscription it tests.
PING = "ping"

USER_CREATED = WebhookEventType("user.created", "An administrator created an account.")
USER_DELETED = WebhookEventType(
    "user.deleted", "An account was deleted. The payload carries nothing about the person."
)
SETTINGS_CHANGED = WebhookEventType(
    "settings.changed", "An administrator saved a section of the admin settings."
)

_CATALOGUE: dict[str, WebhookEventType] = {}


def register_webhook_event(event: WebhookEventType) -> None:
    """Adds an event to the catalogue. Registering the same key twice with
    the same description is a no-op, so imports may repeat."""
    known = _CATALOGUE.get(event.key)
    if known is not None and known != event:
        raise ValueError(f"Webhook event {event.key!r} is registered twice.")
    _CATALOGUE[event.key] = event


def webhook_events() -> list[WebhookEventType]:
    return sorted(_CATALOGUE.values(), key=lambda e: e.key)


def is_webhook_event(key: str) -> bool:
    return key in _CATALOGUE


for _event in (USER_CREATED, USER_DELETED, SETTINGS_CHANGED):
    register_webhook_event(_event)
