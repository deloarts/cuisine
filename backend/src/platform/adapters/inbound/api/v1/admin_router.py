"""
/api/v1/web: account and group administration, the permission catalogue,
API keys and the instance-wide security log.
"""

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Query
from fastapi import UploadFile
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import require_any_permission
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_list_agent_calls
from src.platform.adapters.inbound.api.deps import get_list_security_events
from src.platform.adapters.inbound.api.deps import get_manage_api_keys
from src.platform.adapters.inbound.api.deps import get_manage_groups
from src.platform.adapters.inbound.api.deps import get_manage_users
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.adapters.inbound.api.log_queries import AgentCallQuery
from src.platform.adapters.inbound.api.log_queries import SecurityEventQuery
from src.platform.adapters.inbound.api.presenters import present_agent_calls
from src.platform.adapters.inbound.api.presenters import present_events
from src.platform.adapters.inbound.api.presenters import present_groups
from src.platform.adapters.inbound.api.presenters import present_user
from src.platform.adapters.inbound.api.presenters import present_users
from src.platform.adapters.inbound.api.schemas.base import Page
from src.platform.adapters.inbound.api.schemas.group_schema import CreateGroupRequest
from src.platform.adapters.inbound.api.schemas.group_schema import GroupResponse
from src.platform.adapters.inbound.api.schemas.group_schema import GroupSummaryResponse
from src.platform.adapters.inbound.api.schemas.group_schema import PermissionResponse
from src.platform.adapters.inbound.api.schemas.group_schema import UpdateGroupRequest
from src.platform.adapters.inbound.api.schemas.security_schema import AgentCallResponse
from src.platform.adapters.inbound.api.schemas.security_schema import ApiKeyCreatedResponse
from src.platform.adapters.inbound.api.schemas.security_schema import ApiKeyResponse
from src.platform.adapters.inbound.api.schemas.security_schema import SecurityEventResponse
from src.platform.adapters.inbound.api.schemas.security_schema import TokenCreateRequest
from src.platform.adapters.inbound.api.schemas.user_schema import CreateUserRequest
from src.platform.adapters.inbound.api.schemas.user_schema import DirectoryUserResponse
from src.platform.adapters.inbound.api.schemas.user_schema import UpdateUserRequest
from src.platform.adapters.inbound.api.schemas.user_schema import UserResponse
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.admin.agent_calls import ListAgentCalls
from src.platform.application.use_cases.admin.groups import GroupCommand
from src.platform.application.use_cases.admin.groups import ManageGroups
from src.platform.application.use_cases.admin.security_events import ListSecurityEvents
from src.platform.application.use_cases.admin.tokens import ManageApiKeys
from src.platform.application.use_cases.admin.tokens import TokenCommand
from src.platform.application.use_cases.admin.users import CreateUserCommand
from src.platform.application.use_cases.admin.users import ManageUsers
from src.platform.application.use_cases.admin.users import UpdateUserCommand
from src.platform.domain.entities.api_key import ApiKey
from src.platform.domain.entities.user import User
from src.platform.domain.services.permission_rules import NEVER_GRANTABLE_TO_TOKENS
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.repositories.log_filters import AgentCallFilter
from src.platform.ports.outbound.repositories.log_filters import SecurityEventFilter

router = APIRouter()

_users = require_permission(Permission.WRITE_USERS)
_groups = require_permission(Permission.WRITE_GROUPS)
_group_readers = require_any_permission(Permission.WRITE_GROUPS, Permission.WRITE_USERS)
_security_log = require_permission(Permission.READ_SECURITY_LOG)


def _ids(values: list[UUID] | None) -> list[str] | None:
    return [str(v) for v in values] if values is not None else None


# ── Users ────────────────────────────────────────────────────────────


@router.get("/users/directory", response_model=list[DirectoryUserResponse], tags=["users"])
async def user_directory(
    _user: User = Depends(get_current_user),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> list[DirectoryUserResponse]:
    """Names and avatars of the active accounts, for every signed-in user, so
    recipes can show who wrote them and pickers can show whom they offer."""
    users = [u for u in await use_case.list_all() if u.is_active]
    avatars = await p.files.public_ids([u.avatar_file_id for u in users if u.avatar_file_id])
    return [
        DirectoryUserResponse(
            id=u.public_id,
            display_name=u.display_name,
            avatar_id=avatars.get(u.avatar_file_id) if u.avatar_file_id else None,
        )
        for u in users
    ]


@router.get("/users", response_model=list[UserResponse], tags=["users"])
async def list_users(
    limit: int | None = Query(None, ge=1, le=500, description="At most this many users."),
    offset: int = Query(0, ge=0),
    _actor: User = Depends(_users),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> list[UserResponse]:
    """Every account by name, or one page of them with `limit` and `offset`."""
    users = await use_case.list_all(limit=limit, offset=offset)
    return await present_users(p, UserResponse, users)


@router.post(
    "/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["users"]
)
async def create_user(
    body: CreateUserRequest,
    actor: User = Depends(_users),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> UserResponse:
    data = body.model_dump()
    data["group_ids"] = _ids(body.group_ids)
    user = await use_case.create(actor, CreateUserCommand(**data), context=context)
    return await present_user(p, UserResponse, user)


@router.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def read_user(
    user_id: str,
    _actor: User = Depends(_users),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> UserResponse:
    return await present_user(p, UserResponse, await use_case.get(user_id))


@router.patch("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    actor: User = Depends(_users),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> UserResponse:
    data = body.model_dump()
    data["group_ids"] = _ids(body.group_ids)
    user = await use_case.update(actor, user_id, UpdateUserCommand(**data), context=context)
    return await present_user(p, UserResponse, user)


# Deleting an account is routed by the composition root together with the
# packages that hand over the account's data (DELETE /users/{user_id} in the
# cookbook's accounts router), on ManageUsers.delete.


@router.post("/users/{user_id}/reset-totp", response_model=UserResponse, tags=["users"])
async def reset_user_totp(
    user_id: str,
    actor: User = Depends(_users),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> UserResponse:
    user = await use_case.reset_totp(actor, user_id, context=context)
    return await present_user(p, UserResponse, user)


@router.put("/users/{user_id}/avatar", response_model=UserResponse, tags=["users"])
async def replace_user_avatar(
    user_id: str,
    file: UploadFile = File(...),
    actor: User = Depends(_users),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> UserResponse:
    """Sets the user's avatar to the uploaded image, replacing and deleting
    the previous one. Images only; 413 when too large, 415 for other types."""
    user = await use_case.replace_avatar(
        actor,
        user_id,
        data=await file.read(),
        file_name=file.filename or "avatar",
        content_type=file.content_type or "application/octet-stream",
        context=context,
    )
    return await present_user(p, UserResponse, user)


@router.delete("/users/{user_id}/avatar", response_model=UserResponse, tags=["users"])
async def remove_user_avatar(
    user_id: str,
    actor: User = Depends(_users),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageUsers = Depends(get_manage_users),
    p: Platform = Depends(get_platform),
) -> UserResponse:
    """Removes the user's avatar and deletes its file."""
    user = await use_case.remove_avatar(actor, user_id, context=context)
    return await present_user(p, UserResponse, user)


@router.post("/users/{user_id}/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["users"])
async def force_logout_user(
    user_id: str,
    actor: User = Depends(_users),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageUsers = Depends(get_manage_users),
) -> None:
    await use_case.force_logout(actor, user_id, context=context)


# ── Groups and permissions ───────────────────────────────────────────


@router.get("/permissions", response_model=list[PermissionResponse], tags=["groups"])
async def list_permissions(_user: User = Depends(get_current_user)) -> list[PermissionResponse]:
    return [
        PermissionResponse(name=p, grantable_to_tokens=p not in NEVER_GRANTABLE_TO_TOKENS)
        for p in Permission.ALL
    ]


@router.get("/groups/directory", response_model=list[GroupSummaryResponse], tags=["groups"])
async def group_directory(
    _user: User = Depends(get_current_user),
    use_case: ManageGroups = Depends(get_manage_groups),
) -> list[GroupSummaryResponse]:
    """Every group by id and name, for any signed-in user, so recipes can be
    shared with a group without the right to manage groups."""
    groups = sorted(await use_case.list_all(), key=lambda g: g.name.lower())
    return [GroupSummaryResponse(id=g.public_id, name=g.name) for g in groups]


@router.get("/groups", response_model=list[GroupResponse], tags=["groups"])
async def list_groups(
    _actor: User = Depends(_group_readers),
    use_case: ManageGroups = Depends(get_manage_groups),
    p: Platform = Depends(get_platform),
) -> list[GroupResponse]:
    return await present_groups(p, await use_case.list_all())


@router.post(
    "/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED, tags=["groups"]
)
async def create_group(
    body: CreateGroupRequest,
    actor: User = Depends(_groups),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageGroups = Depends(get_manage_groups),
    p: Platform = Depends(get_platform),
) -> GroupResponse:
    group = await use_case.create(
        actor,
        GroupCommand(
            name=body.name,
            description=body.description,
            permissions=body.permissions,
            member_ids=_ids(body.member_ids),
        ),
        context=context,
    )
    return (await present_groups(p, [group]))[0]


@router.patch("/groups/{group_id}", response_model=GroupResponse, tags=["groups"])
async def update_group(
    group_id: str,
    body: UpdateGroupRequest,
    actor: User = Depends(_groups),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageGroups = Depends(get_manage_groups),
    p: Platform = Depends(get_platform),
) -> GroupResponse:
    group = await use_case.update(
        actor,
        group_id,
        GroupCommand(
            name=body.name,
            description=body.description,
            permissions=body.permissions,
            member_ids=_ids(body.member_ids),
        ),
        context=context,
    )
    return (await present_groups(p, [group]))[0]


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["groups"])
async def delete_group(
    group_id: str,
    actor: User = Depends(_groups),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageGroups = Depends(get_manage_groups),
) -> None:
    await use_case.delete(actor, group_id, context=context)


# ── API keys ─────────────────────────────────────────────────────────

_keys = require_permission(Permission.MANAGE_API_KEYS)


def _key(key: ApiKey, service_user: User | None) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=key.public_id,
        name=key.name,
        token_prefix=key.token_prefix,
        permissions=sorted(service_user.permissions) if service_user else [],
        created=key.created,
        expires_at=key.expires_at,
        last_used_at=key.last_used_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse], tags=["api-keys"])
async def list_api_keys(
    _actor: User = Depends(_keys), use_case: ManageApiKeys = Depends(get_manage_api_keys)
) -> list[ApiKeyResponse]:
    return [_key(key, service_user) for key, service_user in await use_case.list_all()]


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["api-keys"],
)
async def create_api_key(
    body: TokenCreateRequest,
    actor: User = Depends(_keys),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageApiKeys = Depends(get_manage_api_keys),
) -> ApiKeyCreatedResponse:
    created = await use_case.create(
        actor,
        TokenCommand(name=body.name, permissions=body.permissions, expires_at=body.expires_at),
        context=context,
    )
    return ApiKeyCreatedResponse(
        **_key(created.key, created.service_user).model_dump(), token=created.secret
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["api-keys"])
async def revoke_api_key(
    key_id: str,
    actor: User = Depends(_keys),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageApiKeys = Depends(get_manage_api_keys),
) -> None:
    await use_case.revoke(actor, key_id, context=context)


# ── Security log ─────────────────────────────────────────────────────


@router.get("/security-events", response_model=Page[SecurityEventResponse], tags=["security-log"])
async def list_security_events(
    user_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    filters: SecurityEventFilter = SecurityEventQuery,
    _actor: User = Depends(_security_log),
    use_case: ListSecurityEvents = Depends(get_list_security_events),
    p: Platform = Depends(get_platform),
) -> Page[SecurityEventResponse]:
    internal_id: int | None = None
    if user_id is not None:
        user = await p.users.get_by_public_id(user_id)
        internal_id = user.id if user else -1
    events, total = await use_case.all(
        user_id=internal_id, limit=limit, offset=offset, filters=filters
    )
    return Page(items=await present_events(p, events), total=total)


@router.get("/agent-calls", response_model=Page[AgentCallResponse], tags=["security-log"])
async def list_agent_calls(
    user_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    filters: AgentCallFilter = AgentCallQuery,
    _actor: User = Depends(_security_log),
    use_case: ListAgentCalls = Depends(get_list_agent_calls),
    p: Platform = Depends(get_platform),
) -> Page[AgentCallResponse]:
    """Every agent tool call on the instance."""
    internal_id: int | None = None
    if user_id is not None:
        user = await p.users.get_by_public_id(user_id)
        internal_id = user.id if user else -1
    calls, total = await use_case.all(
        user_id=internal_id, limit=limit, offset=offset, filters=filters
    )
    return Page(items=await present_agent_calls(p, calls), total=total)


@router.get("/agent-calls/tools", response_model=list[str], tags=["security-log"])
async def list_agent_call_tools(
    _actor: User = Depends(_security_log),
    use_case: ListAgentCalls = Depends(get_list_agent_calls),
) -> list[str]:
    """The tool names in the whole log, for the table's filter."""
    return await use_case.tools(user_id=None)
