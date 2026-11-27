"""Announcing cookbook events to webhook subscribers. Platform's webhook
publisher fulfils it; the deliveries join the caller's transaction."""

from typing import Any
from typing import Protocol

# The event names the composition root registers in Platform's catalogue.
RECIPE_PUBLISHED = "recipe.published"
RECIPE_DELETED = "recipe.deleted"


class IEventPublisher(Protocol):
    async def publish(
        self, event: str, data: dict[str, Any], *, subject_user_id: int | None = None
    ) -> int: ...
