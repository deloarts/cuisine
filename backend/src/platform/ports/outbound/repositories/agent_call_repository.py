from datetime import datetime
from typing import Protocol

from src.platform.domain.entities.agent_call import AgentCall
from src.platform.domain.value_objects.agent import AgentTokenKind
from src.platform.ports.outbound.repositories.log_filters import AgentCallFilter


class IAgentCallRepository(Protocol):
    async def append(self, call: AgentCall) -> AgentCall: ...
    async def delete_older_than(self, cutoff: datetime) -> int: ...
    async def count_since(
        self,
        kind: AgentTokenKind,
        token_id: int,
        since: datetime,
        *,
        drafts_only: bool = False,
    ) -> int: ...
    async def find_by_idempotency_key(
        self, kind: AgentTokenKind, token_id: int, tool: str, key: str
    ) -> AgentCall | None: ...
    async def list_page(
        self,
        *,
        user_id: int | None,
        limit: int,
        offset: int,
        filters: AgentCallFilter | None = None,
    ) -> tuple[list[AgentCall], int]: ...
    async def tools(self, *, user_id: int | None) -> list[str]:
        """The tool names in the log, for the table's filter."""
        ...
