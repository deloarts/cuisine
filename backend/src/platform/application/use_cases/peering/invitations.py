"""
Peering invitations: a one-time code with a short expiry that the inviting
instance's administrator passes on out of band, as a link the other
instance's administrator pastes into their admin area. Only the code's
SHA-256 is stored; the link is shown once.
"""

from dataclasses import dataclass
from datetime import timedelta

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.peer import PeerInvitation
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PeerInvitationNotFoundError
from src.platform.domain.services.peering_rules import INVITATION_LIFETIME
from src.platform.domain.services.peering_rules import hash_code
from src.platform.domain.services.peering_rules import invitation_link
from src.platform.domain.services.peering_rules import new_invitation_code
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.peer_repository import IPeerInvitationRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# Invitations that expired this long ago are deleted when a new one is
# created; until then a late attempt is recognised as expired in the log.
KEEP_EXPIRED = timedelta(days=30)


@dataclass(frozen=True)
class CreatedInvitation:
    invitation: PeerInvitation
    # The only time the link, and with it the code, is available.
    link: str


class ManagePeerInvitations:
    def __init__(
        self,
        *,
        invitations: IPeerInvitationRepository,
        base_url: str,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._invitations = invitations
        self._base_url = base_url
        self._audit = audit
        self._uow = uow

    async def list_open(self) -> list[PeerInvitation]:
        return await self._invitations.list_open(now_utc())

    async def create(self, actor: User, *, context: RequestContext) -> CreatedInvitation:
        now = now_utc()
        await self._invitations.purge_expired_before(now - KEEP_EXPIRED)
        code = new_invitation_code()
        saved = await self._invitations.add(
            PeerInvitation(
                code_hash=hash_code(code),
                created_by_id=actor.id or None,
                created=now,
                expires_at=now + INVITATION_LIFETIME,
            )
        )
        await self._audit.record(
            SecurityEventType.PEER_INVITATION_CREATED,
            actor=actor,
            context=context,
            detail={"invitation": str(saved.public_id)},
        )
        await self._uow.commit()
        return CreatedInvitation(invitation=saved, link=invitation_link(self._base_url, code))

    async def revoke(self, actor: User, public_id: str, *, context: RequestContext) -> None:
        found = await self._invitations.get_by_public_id(public_id)
        if found is None or found.used_at is not None:
            raise PeerInvitationNotFoundError("No such open invitation.")
        await self._invitations.delete(found)
        await self._audit.record(
            SecurityEventType.PEER_INVITATION_REVOKED,
            actor=actor,
            context=context,
            detail={"invitation": str(found.public_id)},
        )
        await self._uow.commit()
