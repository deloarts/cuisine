"""Who an authenticated agent request acts as."""

from dataclasses import dataclass

from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.agent import AgentTokenKind


@dataclass(frozen=True)
class AgentPrincipal:
    # The token's user, narrowed to the token's permissions for a PAT, or
    # the service account of an API key.
    user: User
    token_kind: AgentTokenKind
    token_id: int
    token_name: str
