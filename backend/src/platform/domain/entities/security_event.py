"""One entry of the security log: who did what to which account, from where."""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class SecurityEvent(Entity):
    event_type: SecurityEventType
    outcome: SecurityEventOutcome
    created: datetime
    actor_id: int | None = None
    target_user_id: int | None = None
    detail: dict[str, object] = field(default_factory=dict)
    client_ip: str | None = None
    user_agent: str | None = None
