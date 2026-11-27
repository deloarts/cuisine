from datetime import datetime

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.webhook_models import WebhookDeliveryModel
from src.platform.adapters.outbound.persistence.models.webhook_models import (
    WebhookSubscriptionModel,
)
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.platform.domain.entities.webhook import WebhookDelivery
from src.platform.domain.entities.webhook import WebhookSubscription
from src.platform.domain.value_objects.webhook_event import DeliveryStatus


def _subscription(row: WebhookSubscriptionModel) -> WebhookSubscription:
    return WebhookSubscription(
        id=row.id,
        public_id=row.public_id,
        name=row.name,
        url=row.url,
        events=list(row.events or []),
        # Empty when no configured key decrypts it; the sender then logs why.
        secret=row.secret or "",
        enabled=row.enabled,
        created=row.created,
        changed=row.changed,
    )


def _delivery(row: WebhookDeliveryModel) -> WebhookDelivery:
    return WebhookDelivery(
        id=row.id,
        public_id=row.public_id,
        subscription_id=row.subscription_id,
        event=row.event,
        payload=dict(row.payload or {}),
        status=DeliveryStatus(row.status),
        attempts=row.attempts,
        next_attempt_at=row.next_attempt_at,
        last_attempt_at=row.last_attempt_at,
        http_status=row.http_status,
        duration_ms=row.duration_ms,
        error=row.error,
        created=row.created,
        subject_user_id=row.subject_user_id,
    )


class SqlAlchemyWebhookSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_all(self) -> list[WebhookSubscription]:
        rows = await self._db.scalars(
            select(WebhookSubscriptionModel).order_by(WebhookSubscriptionModel.name)
        )
        return [_subscription(r) for r in rows.all()]

    async def get_by_public_id(self, public_id: str) -> WebhookSubscription | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(WebhookSubscriptionModel).where(WebhookSubscriptionModel.public_id == uid)
        )
        return _subscription(row) if row is not None else None

    async def get(self, subscription_id: int) -> WebhookSubscription | None:
        row = await self._db.get(WebhookSubscriptionModel, subscription_id)
        return _subscription(row) if row is not None else None

    async def listening_to(self, event: str) -> list[WebhookSubscription]:
        # The event list is JSON; a household has a handful of webhooks, so
        # filtering in Python keeps this portable across Postgres and SQLite.
        rows = await self._db.scalars(
            select(WebhookSubscriptionModel).where(WebhookSubscriptionModel.enabled.is_(True))
        )
        return [_subscription(r) for r in rows.all() if event in (r.events or [])]

    async def save(self, subscription: WebhookSubscription) -> WebhookSubscription:
        row = (
            await self._db.get(WebhookSubscriptionModel, subscription.id)
            if subscription.id
            else None
        )
        if row is None:
            row = WebhookSubscriptionModel(public_id=subscription.public_id)
            self._db.add(row)
        row.name = subscription.name
        row.url = subscription.url
        row.events = list(subscription.events)
        row.secret = subscription.secret
        row.enabled = subscription.enabled
        row.created = subscription.created
        row.changed = subscription.changed
        await self._db.flush()
        return _subscription(row)

    async def delete(self, subscription: WebhookSubscription) -> None:
        row = await self._db.get(WebhookSubscriptionModel, subscription.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()


class SqlAlchemyWebhookDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, delivery: WebhookDelivery) -> WebhookDelivery:
        row = WebhookDeliveryModel(public_id=delivery.public_id)
        self._write(row, delivery)
        self._db.add(row)
        await self._db.flush()
        return _delivery(row)

    async def save(self, delivery: WebhookDelivery) -> WebhookDelivery:
        row = await self._db.get(WebhookDeliveryModel, delivery.id)
        if row is None:
            return await self.add(delivery)
        self._write(row, delivery)
        await self._db.flush()
        return _delivery(row)

    @staticmethod
    def _write(row: WebhookDeliveryModel, delivery: WebhookDelivery) -> None:
        row.subscription_id = delivery.subscription_id
        row.event = delivery.event
        row.payload = dict(delivery.payload)
        row.status = delivery.status.value
        row.attempts = delivery.attempts
        row.next_attempt_at = delivery.next_attempt_at
        row.last_attempt_at = delivery.last_attempt_at
        row.http_status = delivery.http_status
        row.duration_ms = delivery.duration_ms
        row.error = delivery.error
        row.created = delivery.created
        row.subject_user_id = delivery.subject_user_id

    async def get_by_public_id(
        self, subscription_id: int, public_id: str
    ) -> WebhookDelivery | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(WebhookDeliveryModel).where(
                WebhookDeliveryModel.public_id == uid,
                WebhookDeliveryModel.subscription_id == subscription_id,
            )
        )
        return _delivery(row) if row is not None else None

    async def list_page(
        self, subscription_id: int, *, limit: int, offset: int
    ) -> tuple[list[WebhookDelivery], int]:
        where = WebhookDeliveryModel.subscription_id == subscription_id
        rows = await self._db.scalars(
            select(WebhookDeliveryModel)
            .where(where)
            .order_by(WebhookDeliveryModel.created.desc(), WebhookDeliveryModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        total = await self._db.scalar(
            select(func.count()).select_from(WebhookDeliveryModel).where(where)
        )
        return [_delivery(r) for r in rows.all()], int(total or 0)

    async def claim_due(self, now: datetime, *, limit: int) -> list[WebhookDelivery]:
        candidates = await self._db.scalars(
            select(WebhookDeliveryModel.id)
            .where(
                WebhookDeliveryModel.status == DeliveryStatus.PENDING.value,
                WebhookDeliveryModel.next_attempt_at <= now,
            )
            .order_by(WebhookDeliveryModel.next_attempt_at, WebhookDeliveryModel.id)
            .limit(limit)
        )
        claimed: list[WebhookDelivery] = []
        for delivery_id in candidates.all():
            # Conditional on still being pending, so of two workers racing
            # for the same row exactly one update matches.
            result = await self._db.execute(
                update(WebhookDeliveryModel)
                .where(
                    WebhookDeliveryModel.id == delivery_id,
                    WebhookDeliveryModel.status == DeliveryStatus.PENDING.value,
                )
                .values(status=DeliveryStatus.SENDING.value, last_attempt_at=now)
                .execution_options(synchronize_session=False)
            )
            if getattr(result, "rowcount", 0) == 1:
                row = await self._db.get(WebhookDeliveryModel, delivery_id, populate_existing=True)
                if row is not None:
                    claimed.append(_delivery(row))
        return claimed

    async def release_stale(self, older_than: datetime) -> int:
        result = await self._db.execute(
            update(WebhookDeliveryModel)
            .where(
                WebhookDeliveryModel.status == DeliveryStatus.SENDING.value,
                WebhookDeliveryModel.last_attempt_at < older_than,
            )
            .values(status=DeliveryStatus.PENDING.value)
            .execution_options(synchronize_session=False)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def recent_statuses(self, subscription_id: int, limit: int) -> list[str]:
        rows = await self._db.scalars(
            select(WebhookDeliveryModel.status)
            .where(
                WebhookDeliveryModel.subscription_id == subscription_id,
                WebhookDeliveryModel.event != "ping",
                WebhookDeliveryModel.status.in_(
                    [DeliveryStatus.SUCCEEDED.value, DeliveryStatus.FAILED.value]
                ),
            )
            .order_by(WebhookDeliveryModel.last_attempt_at.desc(), WebhookDeliveryModel.id.desc())
            .limit(limit)
        )
        return list(rows.all())

    async def prune(self, older_than: datetime) -> int:
        result = await self._db.execute(
            delete(WebhookDeliveryModel)
            .where(
                WebhookDeliveryModel.created < older_than,
                WebhookDeliveryModel.status.in_(
                    [DeliveryStatus.SUCCEEDED.value, DeliveryStatus.FAILED.value]
                ),
            )
            .execution_options(synchronize_session=False)
        )
        return int(getattr(result, "rowcount", 0) or 0)
