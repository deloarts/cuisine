from datetime import datetime

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.notice_models import (
    NoticeAcknowledgementModel,
)
from src.platform.adapters.outbound.persistence.models.notice_models import NoticeModel
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.platform.domain.entities.notice import Notice
from src.platform.domain.entities.notice import NoticeAcknowledgement
from src.platform.domain.entities.notice import NoticeText


def _notice(row: NoticeModel) -> Notice:
    texts = {
        str(locale): NoticeText(title=str(t.get("title", "")), body=str(t.get("body", "")))
        for locale, t in dict(row.texts or {}).items()
        if isinstance(t, dict)
    }
    return Notice(
        id=row.id,
        public_id=row.public_id,
        texts=texts,
        active=row.active,
        created=row.created,
        changed=row.changed,
        created_by_id=row.created_by_id,
    )


class SqlAlchemyNoticeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_all(self) -> list[Notice]:
        rows = await self._db.scalars(select(NoticeModel).order_by(NoticeModel.created.desc()))
        return [_notice(r) for r in rows.all()]

    async def get_by_public_id(self, public_id: str) -> Notice | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(NoticeModel).where(NoticeModel.public_id == uid))
        return _notice(row) if row is not None else None

    async def save(self, notice: Notice) -> Notice:
        row = await self._db.get(NoticeModel, notice.id) if notice.id else None
        if row is None:
            row = NoticeModel(public_id=notice.public_id)
            self._db.add(row)
        row.texts = {
            locale: {"title": t.title, "body": t.body} for locale, t in notice.texts.items()
        }
        row.active = notice.active
        row.created = notice.created
        row.changed = notice.changed
        row.created_by_id = notice.created_by_id
        await self._db.flush()
        return _notice(row)

    async def delete(self, notice: Notice) -> None:
        row = await self._db.get(NoticeModel, notice.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()

    async def pending_for(self, user_id: int) -> list[Notice]:
        acknowledged = select(NoticeAcknowledgementModel.notice_id).where(
            NoticeAcknowledgementModel.user_id == user_id
        )
        rows = await self._db.scalars(
            select(NoticeModel)
            .where(NoticeModel.active.is_(True), NoticeModel.id.not_in(acknowledged))
            .order_by(NoticeModel.created, NoticeModel.id)
        )
        return [_notice(r) for r in rows.all()]

    async def acknowledge(self, notice_id: int, user_id: int, at: datetime) -> None:
        existing = await self._db.get(NoticeAcknowledgementModel, (notice_id, user_id))
        if existing is None:
            self._db.add(
                NoticeAcknowledgementModel(notice_id=notice_id, user_id=user_id, acknowledged_at=at)
            )
            await self._db.flush()

    async def acknowledgements(self, notice_id: int) -> list[NoticeAcknowledgement]:
        rows = await self._db.scalars(
            select(NoticeAcknowledgementModel)
            .where(NoticeAcknowledgementModel.notice_id == notice_id)
            .order_by(NoticeAcknowledgementModel.acknowledged_at)
        )
        return [
            NoticeAcknowledgement(user_id=r.user_id, acknowledged_at=r.acknowledged_at)
            for r in rows.all()
        ]

    async def acknowledgement_counts(self) -> dict[int, int]:
        rows = await self._db.execute(
            select(NoticeAcknowledgementModel.notice_id, func.count()).group_by(
                NoticeAcknowledgementModel.notice_id
            )
        )
        return {notice_id: int(count) for notice_id, count in rows.all()}
