from datetime import datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.agent_call_models import AgentCallModel
from src.platform.domain.entities.agent_call import AgentCall
from src.platform.domain.value_objects.agent import AgentCallOutcome
from src.platform.domain.value_objects.agent import AgentTokenKind
from src.platform.ports.outbound.repositories.log_filters import AgentCallFilter


def _entity(row: AgentCallModel) -> AgentCall:
    return AgentCall(
        id=row.id,
        public_id=row.public_id,
        called_at=row.called_at,
        user_id=row.user_id,
        token_kind=AgentTokenKind(row.token_kind),
        token_id=row.token_id,
        token_name=row.token_name,
        tool=row.tool,
        arguments=dict(row.arguments or {}),
        outcome=AgentCallOutcome(row.outcome),
        duration_ms=row.duration_ms,
        error=row.error,
        created_refs=list(row.created_refs or []),
        idempotency_key=row.idempotency_key,
        result=row.result,
        is_draft=row.is_draft,
    )


class SqlAlchemyAgentCallRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def delete_older_than(self, cutoff: datetime) -> int:
        result = await self._db.execute(
            delete(AgentCallModel)
            .where(AgentCallModel.called_at < cutoff)
            .execution_options(synchronize_session=False)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def append(self, call: AgentCall) -> AgentCall:
        row = AgentCallModel(
            public_id=call.public_id,
            called_at=call.called_at,
            user_id=call.user_id,
            token_kind=call.token_kind.value,
            token_id=call.token_id,
            token_name=call.token_name,
            tool=call.tool,
            arguments=call.arguments,
            outcome=call.outcome.value,
            duration_ms=call.duration_ms,
            error=call.error,
            created_refs=call.created_refs,
            idempotency_key=call.idempotency_key,
            result=call.result,
            is_draft=call.is_draft,
        )
        self._db.add(row)
        await self._db.flush()
        return _entity(row)

    async def count_since(
        self,
        kind: AgentTokenKind,
        token_id: int,
        since: datetime,
        *,
        drafts_only: bool = False,
    ) -> int:
        query = (
            select(func.count())
            .select_from(AgentCallModel)
            .where(
                AgentCallModel.token_kind == kind.value,
                AgentCallModel.token_id == token_id,
                AgentCallModel.called_at >= since,
            )
        )
        if drafts_only:
            query = query.where(
                AgentCallModel.is_draft.is_(True),
                AgentCallModel.outcome == AgentCallOutcome.OK.value,
            )
        return int(await self._db.scalar(query) or 0)

    async def find_by_idempotency_key(
        self, kind: AgentTokenKind, token_id: int, tool: str, key: str
    ) -> AgentCall | None:
        row = await self._db.scalar(
            select(AgentCallModel)
            .where(
                AgentCallModel.token_kind == kind.value,
                AgentCallModel.token_id == token_id,
                AgentCallModel.tool == tool,
                AgentCallModel.idempotency_key == key,
                AgentCallModel.outcome == AgentCallOutcome.OK.value,
            )
            .order_by(AgentCallModel.id)
            .limit(1)
        )
        return _entity(row) if row is not None else None

    async def list_page(
        self,
        *,
        user_id: int | None,
        limit: int,
        offset: int,
        filters: AgentCallFilter | None = None,
    ) -> tuple[list[AgentCall], int]:
        f = filters or AgentCallFilter()
        criteria: list[Any] = []
        if user_id is not None:
            criteria.append(AgentCallModel.user_id == user_id)
        if f.tools:
            criteria.append(AgentCallModel.tool.in_(f.tools))
        if f.outcome is not None:
            criteria.append(AgentCallModel.outcome == f.outcome)
        if f.since is not None:
            criteria.append(AgentCallModel.called_at >= f.since)
        if f.until is not None:
            criteria.append(AgentCallModel.called_at < f.until)
        query = select(AgentCallModel).where(*criteria)
        count = select(func.count()).select_from(AgentCallModel).where(*criteria)
        order = (
            (AgentCallModel.called_at.asc(), AgentCallModel.id.asc())
            if f.oldest_first
            else (AgentCallModel.called_at.desc(), AgentCallModel.id.desc())
        )
        rows = await self._db.scalars(query.order_by(*order).limit(limit).offset(offset))
        return [_entity(r) for r in rows.all()], int(await self._db.scalar(count) or 0)

    async def tools(self, *, user_id: int | None) -> list[str]:
        query = select(AgentCallModel.tool).distinct()
        if user_id is not None:
            query = query.where(AgentCallModel.user_id == user_id)
        return sorted(str(t) for t in (await self._db.scalars(query)).all())
