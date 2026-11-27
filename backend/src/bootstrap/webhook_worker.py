"""
The webhook worker: a task on each backend worker's event loop that sends
due webhook deliveries every few seconds. Deliveries are claimed one by one
in the database, so several workers never send the same one twice. The
worker starts with the app and stops with it; a delivery it was sending
when the process died goes back to pending after a few minutes.
"""

import asyncio

from src.bootstrap.worker_loop import run_forever
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_webhook_sender
from src.platform.adapters.inbound.api.deps import mailer
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.webhook_repository import (
    SqlAlchemyWebhookDeliveryRepository,
)
from src.platform.adapters.outbound.persistence.repositories.webhook_repository import (
    SqlAlchemyWebhookSubscriptionRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.platform.application.use_cases.admin.webhooks import DeliverWebhooks

INTERVAL_SECONDS = 5.0


async def deliver_once() -> int:
    async with SessionLocal() as db:
        run = DeliverWebhooks(
            subscriptions=SqlAlchemyWebhookSubscriptionRepository(db),
            deliveries=SqlAlchemyWebhookDeliveryRepository(db),
            settings_repo=SqlAlchemySettingsRepository(db),
            sender=get_webhook_sender(),
            uow=SqlAlchemyUnitOfWork(db),
            mailer=mailer(Platform(db)),
        )
        return await run.run()


def start_webhook_worker() -> asyncio.Task[None]:
    return asyncio.create_task(
        run_forever(
            deliver_once, interval=INTERVAL_SECONDS, failure="The webhook worker run failed."
        ),
        name="webhook-worker",
    )
