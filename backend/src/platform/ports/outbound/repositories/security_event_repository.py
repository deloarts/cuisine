from datetime import datetime
from typing import Protocol

from src.platform.domain.entities.security_event import SecurityEvent
from src.platform.ports.outbound.repositories.log_filters import SecurityEventFilter


class ISecurityEventRepository(Protocol):
    async def add(self, event: SecurityEvent) -> None: ...
    async def delete_involving(self, user_id: int) -> None: ...
    async def delete_older_than(self, cutoff: datetime) -> int: ...
    async def list_all(
        self,
        *,
        user_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
        filters: SecurityEventFilter | None = None,
    ) -> tuple[list[SecurityEvent], int]:
        """A page, newest first, and the total. With `user_id`, only the
        events where that user is the actor or the target."""
        ...
