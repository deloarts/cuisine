"""Repositories of the login and token records: sessions, trusted devices,
passkeys, personal access tokens, API keys and the security log."""

from datetime import datetime
from typing import Any
from typing import Protocol
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

from src.platform.adapters.outbound.persistence.models.security_models import ApiKeyModel
from src.platform.adapters.outbound.persistence.models.security_models import PasskeyModel
from src.platform.adapters.outbound.persistence.models.security_models import (
    PersonalAccessTokenModel,
)
from src.platform.adapters.outbound.persistence.models.security_models import SecurityEventModel
from src.platform.adapters.outbound.persistence.models.security_models import TrustedDeviceModel
from src.platform.adapters.outbound.persistence.models.security_models import UserSessionModel
from src.platform.adapters.outbound.persistence.repositories._common import copy_entity_to_row
from src.platform.adapters.outbound.persistence.repositories._common import entity_from_row
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.platform.domain.entities.api_key import ApiKey
from src.platform.domain.entities.passkey import Passkey
from src.platform.domain.entities.personal_access_token import PersonalAccessToken
from src.platform.domain.entities.security_event import SecurityEvent
from src.platform.domain.entities.trusted_device import TrustedDevice
from src.platform.domain.entities.user_session import UserSession
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.log_filters import SecurityEventFilter
from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.services.clock import now_utc


class _PublicIdModel(Protocol):
    """A mapped model with a public id, as every model here is."""

    public_id: Mapped[UUID]

    def __init__(self, **kwargs: Any) -> None: ...


class _SimpleRepository[E: Entity, M: _PublicIdModel]:
    """Load and save for entities that mirror their model column by column."""

    entity_cls: type[E]
    model_cls: type[M]

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    def _entity(self, row: M | None) -> E | None:
        return entity_from_row(self.entity_cls, row) if row is not None else None

    async def _first(self, *criteria: Any) -> E | None:
        return self._entity(await self._db.scalar(select(self.model_cls).where(*criteria)))

    async def _all(self, *criteria: Any, order_by: Any = None) -> list[E]:
        query = select(self.model_cls).where(*criteria)
        if order_by is not None:
            query = query.order_by(order_by)
        return [entity_from_row(self.entity_cls, row) for row in await self._db.scalars(query)]

    async def get_by_public_id(self, public_id: str) -> E | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        return await self._first(self.model_cls.public_id == uid)

    async def save(self, entity: E) -> E:
        entity_id: int = entity.id
        row = await self._db.get(self.model_cls, entity_id) if entity_id else None
        if row is None:
            row = self.model_cls(public_id=entity.public_id)
            self._db.add(row)
        copy_entity_to_row(entity, row, skip=frozenset())
        await self._db.flush()
        stored = self._entity(row)
        assert stored is not None
        return stored

    async def _delete(self, entity_id: int) -> None:
        row = await self._db.get(self.model_cls, entity_id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()


class SqlAlchemyUserSessionRepository(_SimpleRepository[UserSession, UserSessionModel]):
    entity_cls = UserSession
    model_cls = UserSessionModel

    async def list_active(self, user_id: int) -> list[UserSession]:
        return await self._all(
            UserSessionModel.user_id == user_id,
            UserSessionModel.revoked_at.is_(None),
            order_by=UserSessionModel.last_seen_at.desc(),
        )

    async def revoke_all(
        self, user_id: int, now: datetime, *, except_public_id: str | None = None
    ) -> int:
        query = (
            update(UserSessionModel)
            .where(UserSessionModel.user_id == user_id, UserSessionModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        keep = parse_public_id(except_public_id) if except_public_id else None
        if keep is not None:
            query = query.where(UserSessionModel.public_id != keep)
        result = cast(CursorResult[Any], await self._db.execute(query))
        return int(result.rowcount or 0)


class SqlAlchemyTrustedDeviceRepository(_SimpleRepository[TrustedDevice, TrustedDeviceModel]):
    entity_cls = TrustedDevice
    model_cls = TrustedDeviceModel

    async def get_by_token_hash(self, token_hash: str) -> TrustedDevice | None:
        return await self._first(TrustedDeviceModel.token_hash == token_hash)

    async def list_usable(self, user_id: int) -> list[TrustedDevice]:
        return await self._all(
            TrustedDeviceModel.user_id == user_id,
            TrustedDeviceModel.revoked_at.is_(None),
            TrustedDeviceModel.expires_at > now_utc(),
            order_by=TrustedDeviceModel.created.desc(),
        )

    async def revoke_all(self, user_id: int, now: datetime) -> int:
        result = cast(
            CursorResult[Any],
            await self._db.execute(
                update(TrustedDeviceModel)
                .where(
                    TrustedDeviceModel.user_id == user_id, TrustedDeviceModel.revoked_at.is_(None)
                )
                .values(revoked_at=now)
            ),
        )
        return int(result.rowcount or 0)


class SqlAlchemyPasskeyRepository(_SimpleRepository[Passkey, PasskeyModel]):
    entity_cls = Passkey
    model_cls = PasskeyModel

    async def get_by_credential_id(self, credential_id: bytes) -> Passkey | None:
        return await self._first(PasskeyModel.credential_id == credential_id)

    async def list_for_user(self, user_id: int) -> list[Passkey]:
        return await self._all(PasskeyModel.user_id == user_id, order_by=PasskeyModel.created)

    async def delete(self, passkey: Passkey) -> None:
        await self._delete(passkey.id)


class SqlAlchemyPatRepository(_SimpleRepository[PersonalAccessToken, PersonalAccessTokenModel]):
    entity_cls = PersonalAccessToken
    model_cls = PersonalAccessTokenModel

    async def get_by_token_hash(self, token_hash: str) -> PersonalAccessToken | None:
        return await self._first(PersonalAccessTokenModel.token_hash == token_hash)

    async def list_for_user(self, user_id: int) -> list[PersonalAccessToken]:
        return await self._all(
            PersonalAccessTokenModel.user_id == user_id,
            PersonalAccessTokenModel.revoked_at.is_(None),
            order_by=PersonalAccessTokenModel.created.desc(),
        )


class SqlAlchemyApiKeyRepository(_SimpleRepository[ApiKey, ApiKeyModel]):
    entity_cls = ApiKey
    model_cls = ApiKeyModel

    async def get_by_token_hash(self, token_hash: str) -> ApiKey | None:
        return await self._first(ApiKeyModel.token_hash == token_hash)

    async def list_all(self) -> list[ApiKey]:
        return await self._all(
            ApiKeyModel.revoked_at.is_(None), order_by=ApiKeyModel.created.desc()
        )


class SqlAlchemySecurityEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def delete_older_than(self, cutoff: datetime) -> int:
        result = await self._db.execute(
            delete(SecurityEventModel)
            .where(SecurityEventModel.created < cutoff)
            .execution_options(synchronize_session=False)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_involving(self, user_id: int) -> None:
        """Every event the user acted in or was the target of, for the
        deletion of their account."""
        await self._db.execute(
            delete(SecurityEventModel).where(
                (SecurityEventModel.actor_id == user_id)
                | (SecurityEventModel.target_user_id == user_id)
            )
        )

    async def add(self, event: SecurityEvent) -> None:
        self._db.add(
            SecurityEventModel(
                public_id=event.public_id,
                created=event.created,
                event_type=event.event_type.value,
                outcome=event.outcome.value,
                actor_id=event.actor_id,
                target_user_id=event.target_user_id,
                detail=event.detail,
                client_ip=event.client_ip,
                user_agent=(event.user_agent or "")[:512] or None,
            )
        )
        await self._db.flush()

    async def list_all(
        self,
        *,
        user_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
        filters: SecurityEventFilter | None = None,
    ) -> tuple[list[SecurityEvent], int]:
        f = filters or SecurityEventFilter()
        criteria: list[Any] = []
        if user_id is not None:
            criteria.append(
                or_(
                    SecurityEventModel.actor_id == user_id,
                    SecurityEventModel.target_user_id == user_id,
                )
            )
        if f.event_types:
            criteria.append(SecurityEventModel.event_type.in_(f.event_types))
        if f.outcome is not None:
            criteria.append(SecurityEventModel.outcome == f.outcome)
        if f.since is not None:
            criteria.append(SecurityEventModel.created >= f.since)
        if f.until is not None:
            criteria.append(SecurityEventModel.created < f.until)
        order = (
            (SecurityEventModel.created.asc(), SecurityEventModel.id.asc())
            if f.oldest_first
            else (SecurityEventModel.created.desc(), SecurityEventModel.id.desc())
        )
        total = await self._db.scalar(
            select(func.count()).select_from(SecurityEventModel).where(*criteria)
        )
        rows = await self._db.scalars(
            select(SecurityEventModel).where(*criteria).order_by(*order).limit(limit).offset(offset)
        )
        events = [
            SecurityEvent(
                id=row.id,
                public_id=row.public_id,
                event_type=SecurityEventType(row.event_type),
                outcome=SecurityEventOutcome(row.outcome),
                created=row.created,
                actor_id=row.actor_id,
                target_user_id=row.target_user_id,
                detail=dict(row.detail or {}),
                client_ip=row.client_ip,
                user_agent=row.user_agent,
            )
            for row in rows
        ]
        return events, int(total or 0)
