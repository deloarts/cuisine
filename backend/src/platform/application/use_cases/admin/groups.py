"""
Groups: freely named permission bundles. Changing a group's permissions or
members is checked against the acting user's own permissions, so nobody can
hand out more than they hold through a group. Taking rights away is capped
the same way: removing a permission from a group needs that permission, and
removing a member or deleting the group needs every permission the group
grants.
"""

from dataclasses import dataclass

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.user import User
from src.platform.domain.entities.user_group import UserGroup
from src.platform.domain.exceptions import DuplicateGroupError
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import UserGroupNotFoundError
from src.platform.domain.exceptions import UserNotFoundError
from src.platform.domain.services.permission_rules import assert_grantable_by
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.user_group_repository import IUserGroupRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class GroupCommand:
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
    member_ids: list[str] | None = None


class ManageGroups:
    def __init__(
        self,
        *,
        group_repo: IUserGroupRepository,
        user_repo: IUserRepository,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._groups = group_repo
        self._users = user_repo
        self._audit = audit
        self._uow = uow

    async def list_all(self) -> list[UserGroup]:
        return await self._groups.list_all()

    async def get(self, public_id: str) -> UserGroup:
        group = await self._groups.get_by_public_id(public_id)
        if group is None:
            raise UserGroupNotFoundError("No such group.")
        return group

    async def _member_ids(self, public_ids: list[str]) -> list[int]:
        ids: list[int] = []
        for public_id in dict.fromkeys(public_ids):
            user = await self._users.get_by_public_id(public_id)
            if user is None or user.is_service_account:
                raise UserNotFoundError("One of the members does not exist.")
            ids.append(user.id)
        return ids

    async def _name(self, name: str, exclude_id: int | None) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise InvalidInputError("The group name must not be empty.")
        if await self._groups.name_taken(cleaned, exclude_id):
            raise DuplicateGroupError("A group with this name already exists.")
        return cleaned

    async def create(self, actor: User, cmd: GroupCommand, *, context: RequestContext) -> UserGroup:
        permissions = sorted(set(cmd.permissions or []))
        assert_grantable_by(actor, permissions)
        group = await self._groups.save(
            UserGroup(
                name=await self._name(cmd.name or "", None),
                description=(cmd.description or "").strip(),
                permissions=permissions,
                created=now_utc(),
                member_ids=await self._member_ids(cmd.member_ids or []),
            )
        )
        await self._audit.record(
            SecurityEventType.GROUP_CREATED,
            actor=actor,
            context=context,
            detail={"group": group.name, "permissions": permissions},
        )
        await self._uow.commit()
        return group

    async def update(
        self, actor: User, public_id: str, cmd: GroupCommand, *, context: RequestContext
    ) -> UserGroup:
        group = await self.get(public_id)
        before = {"permissions": list(group.permissions), "members": list(group.member_ids)}
        if cmd.name is not None:
            group.name = await self._name(cmd.name, group.id)
        if cmd.description is not None:
            group.description = cmd.description.strip()
        if cmd.permissions is not None:
            assert_grantable_by(actor, set(cmd.permissions) ^ set(group.permissions))
            group.permissions = sorted(set(cmd.permissions))
        if cmd.member_ids is not None:
            members = await self._member_ids(cmd.member_ids)
            if set(members) ^ set(group.member_ids):
                # Adding someone hands them the whole bundle, and removing
                # someone takes it away.
                assert_grantable_by(actor, group.permissions)
            group.member_ids = members
        saved = await self._groups.save(group)
        await self._audit.record(
            SecurityEventType.GROUP_CHANGED,
            actor=actor,
            context=context,
            detail={
                "group": saved.name,
                "before": before,
                "after": {"permissions": saved.permissions, "members": saved.member_ids},
            },
        )
        await self._uow.commit()
        return saved

    async def delete(self, actor: User, public_id: str, *, context: RequestContext) -> None:
        group = await self.get(public_id)
        assert_grantable_by(actor, group.permissions)
        await self._groups.delete(group)
        await self._audit.record(
            SecurityEventType.GROUP_DELETED,
            actor=actor,
            context=context,
            detail={"group": group.name},
        )
        await self._uow.commit()
