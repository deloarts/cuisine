from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.user_models import UserGroupMemberModel
from src.platform.adapters.outbound.persistence.models.user_models import UserGroupModel
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.platform.domain.entities.user_group import UserGroup


class SqlAlchemyUserGroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _to_entities(self, rows: list[UserGroupModel]) -> list[UserGroup]:
        ids = [row.id for row in rows]
        members: dict[int, list[int]] = {i: [] for i in ids}
        if ids:
            result = await self._db.execute(
                select(UserGroupMemberModel.group_id, UserGroupMemberModel.user_id).where(
                    UserGroupMemberModel.group_id.in_(ids)
                )
            )
            for group_id, user_id in result.all():
                members[group_id].append(user_id)
        return [
            UserGroup(
                id=row.id,
                public_id=row.public_id,
                name=row.name,
                description=row.description,
                permissions=list(row.permissions or []),
                created=row.created,
                member_ids=sorted(members.get(row.id, [])),
            )
            for row in rows
        ]

    async def get_by_public_id(self, public_id: str) -> UserGroup | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(UserGroupModel).where(UserGroupModel.public_id == uid))
        return (await self._to_entities([row]))[0] if row is not None else None

    async def get_many(self, ids: list[int]) -> list[UserGroup]:
        if not ids:
            return []
        rows = await self._db.scalars(select(UserGroupModel).where(UserGroupModel.id.in_(ids)))
        return await self._to_entities(list(rows.all()))

    async def get_many_by_public_id(self, public_ids: list[str]) -> list[UserGroup]:
        uids = [u for u in (parse_public_id(p) for p in public_ids) if u is not None]
        if not uids:
            return []
        rows = await self._db.scalars(
            select(UserGroupModel).where(UserGroupModel.public_id.in_(uids))
        )
        return await self._to_entities(list(rows.all()))

    async def name_taken(self, name: str, exclude_id: int | None = None) -> bool:
        query = (
            select(func.count())
            .select_from(UserGroupModel)
            .where(func.lower(UserGroupModel.name) == name.strip().lower())
        )
        if exclude_id is not None:
            query = query.where(UserGroupModel.id != exclude_id)
        return bool(await self._db.scalar(query))

    async def list_all(self) -> list[UserGroup]:
        rows = await self._db.scalars(
            select(UserGroupModel).order_by(func.lower(UserGroupModel.name))
        )
        return await self._to_entities(list(rows.all()))

    async def save(self, group: UserGroup) -> UserGroup:
        row = await self._db.get(UserGroupModel, group.id) if group.id else None
        if row is None:
            row = UserGroupModel(public_id=group.public_id, created=group.created)
            self._db.add(row)
        row.name = group.name
        row.description = group.description
        row.permissions = sorted(set(group.permissions))
        await self._db.flush()
        await self._db.execute(
            delete(UserGroupMemberModel).where(UserGroupMemberModel.group_id == row.id)
        )
        for user_id in sorted(set(group.member_ids)):
            self._db.add(UserGroupMemberModel(user_id=user_id, group_id=row.id))
        await self._db.flush()
        return (await self._to_entities([row]))[0]

    async def delete(self, group: UserGroup) -> None:
        await self._db.execute(
            delete(UserGroupMemberModel).where(UserGroupMemberModel.group_id == group.id)
        )
        row = await self._db.get(UserGroupModel, group.id)
        if row is not None:
            await self._db.delete(row)
        await self._db.flush()
