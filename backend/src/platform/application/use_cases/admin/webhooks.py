"""
The admin side of webhooks: subscriptions, their delivery log, test sends
and retries, and the delivery run the webhook worker calls.
"""

import json
from dataclasses import dataclass
from datetime import timedelta

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.mailer import Mailer
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.user import User
from src.platform.domain.entities.webhook import WebhookDelivery
from src.platform.domain.entities.webhook import WebhookSubscription
from src.platform.domain.exceptions import InvalidWebhookConfigurationError
from src.platform.domain.exceptions import WebhookDeliveryNotFoundError
from src.platform.domain.exceptions import WebhookSubscriptionNotFoundError
from src.platform.domain.services.webhook_rules import envelope
from src.platform.domain.services.webhook_rules import new_webhook_secret
from src.platform.domain.services.webhook_rules import next_attempt_after
from src.platform.domain.services.webhook_rules import succeeded
from src.platform.domain.value_objects.mail import AlertKind
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.domain.value_objects.webhook_event import PING
from src.platform.domain.value_objects.webhook_event import DeliveryStatus
from src.platform.domain.value_objects.webhook_event import is_webhook_event
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.webhook_repository import IWebhookDeliveryRepository
from src.platform.ports.outbound.repositories.webhook_repository import (
    IWebhookSubscriptionRepository,
)
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.platform.ports.outbound.webhook_sender import IWebhookSender
from src.platform.ports.outbound.webhook_sender import IWebhookTargetGuard
from src.shared_kernel.domain.services.clock import now_utc

# A delivery claimed this long ago without an outcome belongs to a worker
# that died; it goes back to pending.
STALE_SENDING = timedelta(minutes=5)
# A subscription whose newest deliveries all failed for good this many
# times in a row is switched off.
SWITCH_OFF_AFTER_FAILURES = 3


@dataclass
class SubscriptionInput:
    name: str
    url: str
    events: list[str]
    enabled: bool


class ManageWebhooks:
    def __init__(
        self,
        *,
        subscriptions: IWebhookSubscriptionRepository,
        deliveries: IWebhookDeliveryRepository,
        settings_repo: ISettingsRepository,
        sender: IWebhookSender,
        guard: IWebhookTargetGuard,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._subscriptions = subscriptions
        self._deliveries = deliveries
        self._settings = settings_repo
        self._sender = sender
        self._guard = guard
        self._audit = audit
        self._uow = uow

    async def list_all(self) -> list[WebhookSubscription]:
        return await self._subscriptions.list_all()

    async def get(self, public_id: str) -> WebhookSubscription:
        found = await self._subscriptions.get_by_public_id(public_id)
        if found is None:
            raise WebhookSubscriptionNotFoundError("No such webhook.")
        return found

    async def _validated(self, data: SubscriptionInput) -> SubscriptionInput:
        name = data.name.strip()
        if not name:
            raise InvalidWebhookConfigurationError("The webhook needs a name.")
        events = sorted(set(data.events))
        unknown = [e for e in events if not is_webhook_event(e)]
        if unknown:
            raise InvalidWebhookConfigurationError(f"Unknown events: {', '.join(unknown)}.")
        if not events:
            raise InvalidWebhookConfigurationError("The webhook needs at least one event.")
        allow_private = (await self._settings.get_notifications()).allow_private_webhook_targets
        await self._guard.check(data.url.strip(), allow_private=allow_private)
        return SubscriptionInput(
            name=name, url=data.url.strip(), events=events, enabled=data.enabled
        )

    async def _record(
        self, actor: User, action: str, sub: WebhookSubscription, context: RequestContext
    ) -> None:
        await self._audit.record(
            SecurityEventType.SETTINGS_CHANGED,
            actor=actor,
            context=context,
            detail={"section": "webhooks", "action": action, "webhook": str(sub.public_id)},
        )

    async def create(
        self, actor: User, data: SubscriptionInput, *, context: RequestContext
    ) -> WebhookSubscription:
        """The returned subscription carries its secret, the only time the
        API shows it."""
        valid = await self._validated(data)
        now = now_utc()
        saved = await self._subscriptions.save(
            WebhookSubscription(
                name=valid.name,
                url=valid.url,
                events=valid.events,
                enabled=valid.enabled,
                secret=new_webhook_secret(),
                created=now,
                changed=now,
            )
        )
        await self._record(actor, "created", saved, context)
        await self._uow.commit()
        return saved

    async def update(
        self, actor: User, public_id: str, data: SubscriptionInput, *, context: RequestContext
    ) -> WebhookSubscription:
        sub = await self.get(public_id)
        valid = await self._validated(data)
        sub.name, sub.url, sub.events, sub.enabled = (
            valid.name,
            valid.url,
            valid.events,
            valid.enabled,
        )
        sub.changed = now_utc()
        saved = await self._subscriptions.save(sub)
        await self._record(actor, "changed", saved, context)
        await self._uow.commit()
        return saved

    async def rotate_secret(
        self, actor: User, public_id: str, *, context: RequestContext
    ) -> WebhookSubscription:
        sub = await self.get(public_id)
        sub.secret = new_webhook_secret()
        sub.changed = now_utc()
        saved = await self._subscriptions.save(sub)
        await self._record(actor, "secret_rotated", saved, context)
        await self._uow.commit()
        return saved

    async def delete(self, actor: User, public_id: str, *, context: RequestContext) -> None:
        sub = await self.get(public_id)
        await self._record(actor, "deleted", sub, context)
        await self._subscriptions.delete(sub)
        await self._uow.commit()

    async def deliveries(
        self, public_id: str, *, limit: int, offset: int
    ) -> tuple[list[WebhookDelivery], int]:
        sub = await self.get(public_id)
        return await self._deliveries.list_page(sub.id, limit=limit, offset=offset)

    async def send_test(self, public_id: str) -> WebhookDelivery:
        """Sends a ping to this subscription now, whatever events it names,
        and returns the logged delivery."""
        sub = await self.get(public_id)
        now = now_utc()
        delivery = await self._deliveries.add(
            WebhookDelivery(
                subscription_id=sub.id,
                event=PING,
                payload=envelope(PING, {"webhook": str(sub.public_id)}, now),
                status=DeliveryStatus.SENDING,
                created=now,
            )
        )
        return await self._send_and_commit(sub, delivery)

    async def retry(self, public_id: str, delivery_id: str) -> WebhookDelivery:
        """Sends a delivery again now, also one that failed for good. A
        manual retry does not count against the automatic attempts."""
        sub = await self.get(public_id)
        delivery = await self._deliveries.get_by_public_id(sub.id, delivery_id)
        if delivery is None:
            raise WebhookDeliveryNotFoundError("No such delivery.")
        delivery.status = DeliveryStatus.SENDING
        return await self._send_and_commit(sub, delivery, manual=True)

    async def _send_and_commit(
        self, sub: WebhookSubscription, delivery: WebhookDelivery, *, manual: bool = False
    ) -> WebhookDelivery:
        result = await deliver_once(
            sub, delivery, sender=self._sender, settings_repo=self._settings, manual=manual
        )
        saved = await self._deliveries.save(result)
        await self._uow.commit()
        return saved


async def deliver_once(
    sub: WebhookSubscription,
    delivery: WebhookDelivery,
    *,
    sender: IWebhookSender,
    settings_repo: ISettingsRepository,
    manual: bool = False,
) -> WebhookDelivery:
    """Sends one attempt and updates the delivery with its outcome and, on
    failure, its next attempt."""
    allow_private = (await settings_repo.get_notifications()).allow_private_webhook_targets
    result = await sender.post(
        url=sub.url,
        secret=sub.secret,
        event=delivery.event,
        delivery_id=str(delivery.public_id),
        body=json.dumps(delivery.payload, separators=(",", ":"), ensure_ascii=False),
        allow_private=allow_private,
    )
    now = now_utc()
    if not manual:
        delivery.attempts += 1
    delivery.last_attempt_at = now
    delivery.http_status = result.http_status
    delivery.duration_ms = result.duration_ms
    if succeeded(result.http_status):
        delivery.status = DeliveryStatus.SUCCEEDED
        delivery.error = None
        delivery.next_attempt_at = None
        return delivery
    delivery.error = result.error or f"The receiver answered {result.http_status}."
    retry_at = (
        None if manual or delivery.event == PING else next_attempt_after(delivery.attempts, now)
    )
    delivery.status = DeliveryStatus.PENDING if retry_at else DeliveryStatus.FAILED
    delivery.next_attempt_at = retry_at
    return delivery


class DeliverWebhooks:
    """One run of the webhook worker: releases deliveries of dead workers
    and sends what is due. A subscription whose last few deliveries all
    failed for good is switched off and the alert recipients are told; the
    retention purge prunes the old log."""

    def __init__(
        self,
        *,
        subscriptions: IWebhookSubscriptionRepository,
        deliveries: IWebhookDeliveryRepository,
        settings_repo: ISettingsRepository,
        sender: IWebhookSender,
        uow: IUnitOfWork,
        mailer: Mailer | None = None,
    ) -> None:
        self._subscriptions = subscriptions
        self._deliveries = deliveries
        self._settings = settings_repo
        self._sender = sender
        self._uow = uow
        self._mailer = mailer

    async def _switch_off_if_failing(self, sub: WebhookSubscription) -> None:
        statuses = await self._deliveries.recent_statuses(sub.id, SWITCH_OFF_AFTER_FAILURES)
        if len(statuses) < SWITCH_OFF_AFTER_FAILURES:
            return
        if any(s != DeliveryStatus.FAILED.value for s in statuses):
            return
        sub.enabled = False
        sub.changed = now_utc()
        await self._subscriptions.save(sub)
        if self._mailer is not None:
            await self._mailer.alert(
                AlertKind.WEBHOOK_DISABLED,
                f"The webhook {sub.name!r} was switched off after its last "
                f"{SWITCH_OFF_AFTER_FAILURES} deliveries failed for good.",
            )

    async def run(self, *, limit: int = 20) -> int:
        now = now_utc()
        await self._deliveries.release_stale(now - STALE_SENDING)
        claimed = await self._deliveries.claim_due(now, limit=limit)
        # The claim is committed before sending, so a second worker skips
        # these even while the requests are still in flight.
        await self._uow.commit()
        sent = 0
        for delivery in claimed:
            sub = await self._subscriptions.get(delivery.subscription_id)
            if sub is None:
                continue
            if not sub.enabled:
                delivery.status = DeliveryStatus.FAILED
                delivery.error = "The webhook is switched off."
                delivery.next_attempt_at = None
                await self._deliveries.save(delivery)
                continue
            updated = await deliver_once(
                sub, delivery, sender=self._sender, settings_repo=self._settings
            )
            await self._deliveries.save(updated)
            if updated.status == DeliveryStatus.FAILED:
                await self._switch_off_if_failing(sub)
            await self._uow.commit()
            sent += 1
        await self._uow.commit()
        return sent
