"""Builds response schemas from entities where ids have to be translated:
the API only ever exposes public ids, so internal ids of groups, members and
actors are looked up and replaced."""

from uuid import UUID

from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.schemas.group_schema import GroupResponse
from src.platform.adapters.inbound.api.schemas.security_schema import AgentCallResponse
from src.platform.adapters.inbound.api.schemas.security_schema import SecurityEventResponse
from src.platform.adapters.inbound.api.schemas.user_schema import UserResponse
from src.platform.adapters.inbound.api.schemas.user_schema import user_response
from src.platform.domain.entities.agent_call import AgentCall
from src.platform.domain.entities.security_event import SecurityEvent
from src.platform.domain.entities.user import User
from src.platform.domain.entities.user_group import UserGroup


async def present_users[R: UserResponse](p: Platform, cls: type[R], users: list[User]) -> list[R]:
    group_ids = sorted({g for u in users for g in u.group_ids})
    groups = {g.id: g.public_id for g in await p.groups.get_many(group_ids)}
    avatars = await p.files.public_ids([u.avatar_file_id for u in users if u.avatar_file_id])
    return [user_response(cls, u, groups, avatars) for u in users]


async def present_user[R: UserResponse](p: Platform, cls: type[R], user: User) -> R:
    return (await present_users(p, cls, [user]))[0]


async def present_groups(p: Platform, groups: list[UserGroup]) -> list[GroupResponse]:
    members: dict[int, UUID] = {}
    wanted = {m for g in groups for m in g.member_ids}
    if wanted:
        members = {u.id: u.public_id for u in await p.users.list_all() if u.id in wanted}
    return [
        GroupResponse(
            id=g.public_id,
            name=g.name,
            description=g.description,
            permissions=sorted(g.permissions),
            member_ids=[members[m] for m in g.member_ids if m in members],
            created=g.created,
        )
        for g in groups
    ]


async def present_events(p: Platform, events: list[SecurityEvent]) -> list[SecurityEventResponse]:
    ids = {i for e in events for i in (e.actor_id, e.target_user_id) if i is not None}
    people: dict[int, User] = {}
    for user_id in ids:
        user = await p.users.get(user_id)
        if user is not None:
            people[user_id] = user

    def ref(user_id: int | None) -> tuple[UUID | None, str | None]:
        user = people.get(user_id) if user_id is not None else None
        return (user.public_id, user.full_name) if user else (None, None)

    result = []
    for e in events:
        actor_id, actor_name = ref(e.actor_id)
        target_id, target_name = ref(e.target_user_id)
        result.append(
            SecurityEventResponse(
                id=e.public_id,
                created=e.created,
                event_type=e.event_type.value,
                outcome=e.outcome.value,
                actor_id=actor_id,
                actor_name=actor_name,
                target_user_id=target_id,
                target_name=target_name,
                detail=e.detail,
                client_ip=e.client_ip,
                user_agent=e.user_agent,
            )
        )
    return result


async def present_agent_calls(p: Platform, calls: list[AgentCall]) -> list[AgentCallResponse]:
    people: dict[int, User] = {}
    for user_id in {c.user_id for c in calls}:
        user = await p.users.get(user_id)
        if user is not None:
            people[user_id] = user
    return [
        AgentCallResponse(
            id=c.public_id,
            called_at=c.called_at,
            user_id=people[c.user_id].public_id if c.user_id in people else None,
            user_name=people[c.user_id].full_name if c.user_id in people else None,
            token_kind=c.token_kind.value,
            token_name=c.token_name,
            tool=c.tool,
            arguments=c.arguments,
            outcome=c.outcome.value,
            duration_ms=c.duration_ms,
            error=c.error,
            created_refs=c.created_refs,
        )
        for c in calls
    ]
