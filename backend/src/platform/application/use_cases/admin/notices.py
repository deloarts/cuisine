"""In-app notices: the administrator's list, editing and acknowledgement
overview, and each user's own pending notices."""

from dataclasses import dataclass
from datetime import datetime

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.notice import Notice
from src.platform.domain.entities.notice import NoticeText
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import NoticeNotFoundError
from src.platform.domain.services.notice_rules import validate_notice_texts
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.notice_repository import INoticeRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class NoticeSummary:
    notice: Notice
    acknowledged: int
    audience: int


@dataclass(frozen=True)
class AcknowledgementOverview:
    notice: Notice
    acknowledged: list[tuple[User, datetime]]
    pending: list[User]


def _audience(users: list[User]) -> list[User]:
    """Who a notice is shown to: every active person, not service accounts."""
    return [u for u in users if u.is_active and not u.is_service_account]


class ManageNotices:
    def __init__(
        self,
        *,
        notices: INoticeRepository,
        user_repo: IUserRepository,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._notices = notices
        self._users = user_repo
        self._audit = audit
        self._uow = uow

    async def get(self, public_id: str) -> Notice:
        found = await self._notices.get_by_public_id(public_id)
        if found is None:
            raise NoticeNotFoundError("No such notice.")
        return found

    async def list_all(self) -> list[NoticeSummary]:
        counts = await self._notices.acknowledgement_counts()
        audience = len(_audience(await self._users.list_all()))
        return [
            NoticeSummary(notice=n, acknowledged=counts.get(n.id, 0), audience=audience)
            for n in await self._notices.list_all()
        ]

    async def _record(
        self, actor: User, action: str, notice: Notice, context: RequestContext
    ) -> None:
        await self._audit.record(
            SecurityEventType.SETTINGS_CHANGED,
            actor=actor,
            context=context,
            detail={"section": "notices", "action": action, "notice": str(notice.public_id)},
        )

    async def create(
        self, actor: User, texts: dict[str, NoticeText], active: bool, *, context: RequestContext
    ) -> Notice:
        now = now_utc()
        saved = await self._notices.save(
            Notice(
                texts=validate_notice_texts(texts),
                active=active,
                created=now,
                changed=now,
                created_by_id=actor.id or None,
            )
        )
        await self._record(actor, "created", saved, context)
        await self._uow.commit()
        return saved

    async def update(
        self,
        actor: User,
        public_id: str,
        texts: dict[str, NoticeText],
        active: bool,
        *,
        context: RequestContext,
    ) -> Notice:
        """Editing keeps the acknowledgements; a notice that changed its
        meaning is a new notice."""
        notice = await self.get(public_id)
        notice.texts = validate_notice_texts(texts)
        notice.active = active
        notice.changed = now_utc()
        saved = await self._notices.save(notice)
        await self._record(actor, "changed", saved, context)
        await self._uow.commit()
        return saved

    async def delete(self, actor: User, public_id: str, *, context: RequestContext) -> None:
        notice = await self.get(public_id)
        await self._record(actor, "deleted", notice, context)
        await self._notices.delete(notice)
        await self._uow.commit()

    async def overview(self, public_id: str) -> AcknowledgementOverview:
        notice = await self.get(public_id)
        people = {u.id: u for u in _audience(await self._users.list_all())}
        acknowledged: list[tuple[User, datetime]] = []
        for ack in await self._notices.acknowledgements(notice.id):
            user = people.pop(ack.user_id, None)
            if user is not None:
                acknowledged.append((user, ack.acknowledged_at))
        pending = sorted(people.values(), key=lambda u: u.display_name.lower())
        return AcknowledgementOverview(notice=notice, acknowledged=acknowledged, pending=pending)


class OwnNotices:
    def __init__(self, *, notices: INoticeRepository, uow: IUnitOfWork) -> None:
        self._notices = notices
        self._uow = uow

    async def pending(self, user: User) -> list[Notice]:
        if user.is_service_account:
            return []
        return await self._notices.pending_for(user.id)

    async def acknowledge(self, user: User, public_id: str) -> None:
        notice = await self._notices.get_by_public_id(public_id)
        if notice is None or not notice.active:
            raise NoticeNotFoundError("No such notice.")
        await self._notices.acknowledge(notice.id, user.id, now_utc())
        await self._uow.commit()
