"""Writes the security log. Every use case that changes who can sign in or
what they may do records it here, inside its own transaction, so the entry
and the change commit together."""

from src.platform.application.dto.context import RequestContext
from src.platform.domain.entities.security_event import SecurityEvent
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.security_event_repository import (
    ISecurityEventRepository,
)
from src.shared_kernel.domain.services.clock import now_utc


class SecurityAudit:
    def __init__(self, repo: ISecurityEventRepository) -> None:
        self._repo = repo

    async def record(
        self,
        event_type: SecurityEventType,
        *,
        actor: User | None,
        target: User | None = None,
        context: RequestContext | None = None,
        outcome: SecurityEventOutcome = SecurityEventOutcome.SUCCESS,
        detail: dict[str, object] | None = None,
    ) -> None:
        ctx = context or RequestContext()
        await self._repo.add(
            SecurityEvent(
                event_type=event_type,
                outcome=outcome,
                created=now_utc(),
                actor_id=actor.id if actor is not None and actor.id else None,
                target_user_id=target.id if target is not None and target.id else None,
                detail=detail or {},
                client_ip=ctx.client_ip,
                user_agent=ctx.user_agent,
            )
        )
