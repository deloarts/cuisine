"""Ends the session the request was made with."""

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.use_cases.auth.validate_web_token import WebIdentity
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.user_session_repository import IUserSessionRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


class Logout:
    def __init__(
        self, *, session_repo: IUserSessionRepository, audit: SecurityAudit, uow: IUnitOfWork
    ) -> None:
        self._sessions = session_repo
        self._audit = audit
        self._uow = uow

    async def execute(self, identity: WebIdentity, *, context: RequestContext) -> None:
        if identity.session is not None:
            identity.session.revoked_at = now_utc()
            await self._sessions.save(identity.session)
        await self._audit.record(
            SecurityEventType.LOGOUT, actor=identity.user, target=identity.user, context=context
        )
        await self._uow.commit()
