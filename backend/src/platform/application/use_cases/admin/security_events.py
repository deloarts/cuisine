"""Reading the security log: everybody their own entries, holders of
read:security_log the whole log."""

from src.platform.domain.entities.security_event import SecurityEvent
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.repositories.log_filters import SecurityEventFilter
from src.platform.ports.outbound.repositories.security_event_repository import (
    ISecurityEventRepository,
)

MAX_PAGE_SIZE = 200


class ListSecurityEvents:
    def __init__(self, *, repo: ISecurityEventRepository) -> None:
        self._repo = repo

    async def own(
        self,
        user: User,
        *,
        limit: int,
        offset: int,
        filters: SecurityEventFilter | None = None,
    ) -> tuple[list[SecurityEvent], int]:
        return await self._repo.list_all(
            user_id=user.id, limit=min(limit, MAX_PAGE_SIZE), offset=offset, filters=filters
        )

    async def all(
        self,
        *,
        user_id: int | None,
        limit: int,
        offset: int,
        filters: SecurityEventFilter | None = None,
    ) -> tuple[list[SecurityEvent], int]:
        return await self._repo.list_all(
            user_id=user_id, limit=min(limit, MAX_PAGE_SIZE), offset=offset, filters=filters
        )
