"""
The cookbook's webhook events, registered in Platform's catalogue from the
composition root, so Platform never names a cookbook concept. A cookbook use
case publishes them through the request's WebhookPublisher (deps.Platform
.webhooks) with the payloads described here.
"""

from src.cookbook.ports.outbound import event_publisher as events
from src.platform.domain.value_objects.webhook_event import WebhookEventType
from src.platform.domain.value_objects.webhook_event import register_webhook_event

# data: {"recipe": {"id", "title", "description", "locale", "visibility"}},
# text in the original locale as plain text without Markdown or mentions.
RECIPE_PUBLISHED = WebhookEventType(
    events.RECIPE_PUBLISHED, "A recipe was published. Private recipes are never announced."
)
# data: {"recipe": {"id"}}
RECIPE_DELETED = WebhookEventType(events.RECIPE_DELETED, "A published recipe was deleted.")


def register_cookbook_webhook_events() -> None:
    for event in (RECIPE_PUBLISHED, RECIPE_DELETED):
        register_webhook_event(event)


register_cookbook_webhook_events()
