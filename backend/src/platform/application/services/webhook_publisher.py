"""
Records an event for every webhook subscription listening to it. The
deliveries are written in the caller's transaction, so they exist exactly
when the change that caused them is committed; the webhook worker sends
them afterwards. Any use case of Platform or the cookbook publishes through
this service with an event from the catalogue.
"""

from typing import Any

from src.platform.domain.entities.webhook import WebhookDelivery
from src.platform.domain.services.webhook_rules import envelope
from src.platform.domain.value_objects.webhook_event import DeliveryStatus
from src.platform.domain.value_objects.webhook_event import is_webhook_event
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.webhook_repository import IWebhookDeliveryRepository
from src.platform.ports.outbound.repositories.webhook_repository import (
    IWebhookSubscriptionRepository,
)
from src.shared_kernel.domain.services.clock import now_utc


class WebhookPublisher:
    def __init__(
        self,
        *,
        subscriptions: IWebhookSubscriptionRepository,
        deliveries: IWebhookDeliveryRepository,
        settings_repo: ISettingsRepository,
    ) -> None:
        self._subscriptions = subscriptions
        self._deliveries = deliveries
        self._settings = settings_repo

    async def publish(
        self, event: str, data: dict[str, Any], *, subject_user_id: int | None = None
    ) -> int:
        """Queues the event and returns how many deliveries it made. The
        caller commits. `subject_user_id` names the user the payload
        describes, so deleting that user deletes these deliveries too."""
        if not is_webhook_event(event):
            raise ValueError(f"Webhook event {event!r} is not in the catalogue.")
        if not (await self._settings.get_notifications()).webhooks_enabled:
            return 0
        now = now_utc()
        made = 0
        for subscription in await self._subscriptions.listening_to(event):
            await self._deliveries.add(
                WebhookDelivery(
                    subscription_id=subscription.id,
                    event=event,
                    payload=envelope(event, data, now),
                    status=DeliveryStatus.PENDING,
                    next_attempt_at=now,
                    created=now,
                    subject_user_id=subject_user_id,
                )
            )
            made += 1
        return made
