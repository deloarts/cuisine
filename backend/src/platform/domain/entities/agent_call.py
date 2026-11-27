"""
One tool call an AI agent made through the MCP surface. The log tells an
agent's actions apart from its user's own, and its counts enforce the call
and draft budgets of a token.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

from src.platform.domain.value_objects.agent import AgentCallOutcome
from src.platform.domain.value_objects.agent import AgentTokenKind
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class AgentCall(Entity):
    called_at: datetime
    user_id: int
    token_kind: AgentTokenKind
    # The id of the personal access token or API key the call used.
    token_id: int
    token_name: str
    tool: str
    # The arguments, cut to a few kilobytes, so the log stays small.
    arguments: dict[str, Any] = field(default_factory=dict)
    outcome: AgentCallOutcome = AgentCallOutcome.OK
    duration_ms: int = 0
    error: str | None = None
    # References of the records a draft tool created, such as recipe:<id>.
    created_refs: list[str] = field(default_factory=list)
    # A draft tool's idempotency key; a repeated call answers with the first
    # call's records.
    idempotency_key: str | None = None
    # The answer of a successful draft call with an idempotency key, so a
    # repeated call answers exactly as the first one did.
    result: Any = None
    # Whether the tool creates drafts, for the hourly draft budget.
    is_draft: bool = False
