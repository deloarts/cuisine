"""Reading the agent call log: a user's own calls, or every call for the
holders of read:security_log."""

from src.platform.domain.entities.agent_call import AgentCall
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.repositories.agent_call_repository import IAgentCallRepository
from src.platform.ports.outbound.repositories.log_filters import AgentCallFilter


class ListAgentCalls:
    def __init__(self, *, repo: IAgentCallRepository) -> None:
        self._calls = repo

    async def own(
        self, user: User, *, limit: int, offset: int, filters: AgentCallFilter | None = None
    ) -> tuple[list[AgentCall], int]:
        return await self._calls.list_page(
            user_id=user.id, limit=limit, offset=offset, filters=filters
        )

    async def all(
        self,
        *,
        user_id: int | None,
        limit: int,
        offset: int,
        filters: AgentCallFilter | None = None,
    ) -> tuple[list[AgentCall], int]:
        return await self._calls.list_page(
            user_id=user_id, limit=limit, offset=offset, filters=filters
        )

    async def tools(self, *, user_id: int | None) -> list[str]:
        return await self._calls.tools(user_id=user_id)
