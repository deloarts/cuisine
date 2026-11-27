"""
/api/v1/web/users/me: the signed-in user's own account. Profile, avatar
and preferences, password, two-factor authentication, passkeys, sessions,
trusted devices, personal access tokens and their own security log.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Query
from fastapi import Response
from fastapi import UploadFile
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import get_totp_enrolment_identity
from src.platform.adapters.inbound.api.auth_deps import get_web_identity
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_change_own_password
from src.platform.adapters.inbound.api.deps import get_list_agent_calls
from src.platform.adapters.inbound.api.deps import get_list_security_events
from src.platform.adapters.inbound.api.deps import get_manage_own_avatar
from src.platform.adapters.inbound.api.deps import get_manage_own_passkeys
from src.platform.adapters.inbound.api.deps import get_manage_own_sessions
from src.platform.adapters.inbound.api.deps import get_manage_own_totp
from src.platform.adapters.inbound.api.deps import get_manage_own_trusted_devices
from src.platform.adapters.inbound.api.deps import get_manage_pats
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.adapters.inbound.api.deps import get_update_own_profile
from src.platform.adapters.inbound.api.log_queries import AgentCallQuery
from src.platform.adapters.inbound.api.log_queries import SecurityEventQuery
from src.platform.adapters.inbound.api.presenters import present_agent_calls
from src.platform.adapters.inbound.api.presenters import present_events
from src.platform.adapters.inbound.api.presenters import present_user
from src.platform.adapters.inbound.api.schemas.auth_schema import PasskeyOptionsResponse
from src.platform.adapters.inbound.api.schemas.base import Page
from src.platform.adapters.inbound.api.schemas.security_schema import AgentCallResponse
from src.platform.adapters.inbound.api.schemas.security_schema import CurrentSessionResponse
from src.platform.adapters.inbound.api.schemas.security_schema import PasskeyResponse
from src.platform.adapters.inbound.api.schemas.security_schema import PatCreatedResponse
from src.platform.adapters.inbound.api.schemas.security_schema import PatResponse
from src.platform.adapters.inbound.api.schemas.security_schema import RegisterPasskeyRequest
from src.platform.adapters.inbound.api.schemas.security_schema import RenamePasskeyRequest
from src.platform.adapters.inbound.api.schemas.security_schema import SecurityEventResponse
from src.platform.adapters.inbound.api.schemas.security_schema import SessionResponse
from src.platform.adapters.inbound.api.schemas.security_schema import TokenCreateRequest
from src.platform.adapters.inbound.api.schemas.security_schema import TotpConfirmRequest
from src.platform.adapters.inbound.api.schemas.security_schema import TotpConfirmResponse
from src.platform.adapters.inbound.api.schemas.security_schema import TotpEnrolmentResponse
from src.platform.adapters.inbound.api.schemas.security_schema import TotpEnrolRequest
from src.platform.adapters.inbound.api.schemas.security_schema import TrustedDeviceResponse
from src.platform.adapters.inbound.api.schemas.user_schema import ChangePasswordRequest
from src.platform.adapters.inbound.api.schemas.user_schema import CurrentUserResponse
from src.platform.adapters.inbound.api.schemas.user_schema import PasswordConfirmationRequest
from src.platform.adapters.inbound.api.schemas.user_schema import PrivacyModeResponse
from src.platform.adapters.inbound.api.schemas.user_schema import UpdateOwnProfileRequest
from src.platform.adapters.inbound.api.v1.auth_router import start_session
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.account.avatar import ManageOwnAvatar
from src.platform.application.use_cases.account.own_profile import ChangeOwnPassword
from src.platform.application.use_cases.account.own_profile import UpdateOwnProfile
from src.platform.application.use_cases.account.own_profile import UpdateOwnProfileCommand
from src.platform.application.use_cases.account.passkeys import ManageOwnPasskeys
from src.platform.application.use_cases.account.sessions import ManageOwnSessions
from src.platform.application.use_cases.account.sessions import ManageOwnTrustedDevices
from src.platform.application.use_cases.account.totp import ManageOwnTotp
from src.platform.application.use_cases.admin.agent_calls import ListAgentCalls
from src.platform.application.use_cases.admin.security_events import ListSecurityEvents
from src.platform.application.use_cases.admin.tokens import ManagePats
from src.platform.application.use_cases.admin.tokens import TokenCommand
from src.platform.application.use_cases.auth.validate_web_token import WebIdentity
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.passkey import Passkey
from src.platform.domain.entities.personal_access_token import PersonalAccessToken
from src.platform.domain.entities.user import User
from src.platform.domain.services.legal_rules import acknowledgement_pending
from src.platform.domain.services.legal_rules import privacy_mode_of
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.repositories.log_filters import AgentCallFilter
from src.platform.ports.outbound.repositories.log_filters import SecurityEventFilter

router = APIRouter(prefix="/users/me", tags=["account"])

_write_pat = require_permission(Permission.WRITE_PAT)


def _pat(token: PersonalAccessToken) -> PatResponse:
    return PatResponse(
        id=token.public_id,
        name=token.name,
        token_prefix=token.token_prefix,
        permissions=token.permissions,
        created=token.created,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
    )


async def _me(p: Platform, user: User) -> CurrentUserResponse:
    """The own profile plus the privacy statement state, the instance's
    privacy mode and the consents, which only the user themselves sees."""
    base = await present_user(p, CurrentUserResponse, user)
    current = await p.legal.current(LegalKind.PRIVACY)
    mode = privacy_mode_of(
        await p.settings.get_privacy(), peering=(await p.settings.get_features()).peering
    )
    return base.model_copy(
        update={
            "privacy_acknowledgement_pending": acknowledgement_pending(user, current),
            "privacy_version": current.version if current else None,
            "privacy_acknowledged_version": user.privacy_acknowledged_version,
            "privacy_mode": PrivacyModeResponse(
                mode=mode.mode.value,
                default_visibility=mode.default_visibility,
                allow_public_recipes=mode.allow_public_recipes,
            ),
            "consent_health_data_at": user.consent_health_data_at,
            "consent_ai_agents_at": user.consent_ai_agents_at,
        }
    )


@router.get("", response_model=CurrentUserResponse)
async def read_me(
    user: User = Depends(get_current_user), p: Platform = Depends(get_platform)
) -> CurrentUserResponse:
    return await _me(p, user)


@router.patch("", response_model=CurrentUserResponse)
async def update_me(
    body: UpdateOwnProfileRequest,
    user: User = Depends(get_current_user),
    use_case: UpdateOwnProfile = Depends(get_update_own_profile),
    p: Platform = Depends(get_platform),
) -> CurrentUserResponse:
    saved = await use_case.execute(user, UpdateOwnProfileCommand(**body.model_dump()))
    return await _me(p, saved)


@router.put("/avatar", response_model=CurrentUserResponse)
async def replace_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    use_case: ManageOwnAvatar = Depends(get_manage_own_avatar),
    p: Platform = Depends(get_platform),
) -> CurrentUserResponse:
    """Sets the avatar to the uploaded image, replacing and deleting the
    previous one. Images only; 413 when too large, 415 for other types."""
    saved = await use_case.replace(
        user,
        data=await file.read(),
        file_name=file.filename or "avatar",
        content_type=file.content_type or "application/octet-stream",
    )
    return await _me(p, saved)


@router.delete("/avatar", response_model=CurrentUserResponse)
async def remove_avatar(
    user: User = Depends(get_current_user),
    use_case: ManageOwnAvatar = Depends(get_manage_own_avatar),
    p: Platform = Depends(get_platform),
) -> CurrentUserResponse:
    """Removes the avatar and deletes its file; the initials show again."""
    return await _me(p, await use_case.remove(user))


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    identity: WebIdentity = Depends(get_web_identity),
    context: RequestContext = Depends(get_request_context),
    use_case: ChangeOwnPassword = Depends(get_change_own_password),
) -> None:
    await use_case.execute(
        identity.user,
        current_password=body.current_password,
        new_password=body.new_password,
        current_session_id=str(identity.session.public_id) if identity.session else None,
        context=context,
    )


# ── Two-factor authentication ────────────────────────────────────────


@router.post("/totp/enroll", response_model=TotpEnrolmentResponse)
async def enroll_totp(
    body: TotpEnrolRequest | None = None,
    identity: WebIdentity = Depends(get_totp_enrolment_identity),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnTotp = Depends(get_manage_own_totp),
) -> TotpEnrolmentResponse:
    enrolment = await use_case.enroll(
        identity.user,
        password=body.password if body is not None else None,
        via_setup_token=identity.session is None,
        context=context,
    )
    return TotpEnrolmentResponse(
        secret=enrolment.secret, provisioning_uri=enrolment.provisioning_uri
    )


@router.post("/totp/confirm", response_model=TotpConfirmResponse)
async def confirm_totp(
    body: TotpConfirmRequest,
    response: Response,
    identity: WebIdentity = Depends(get_totp_enrolment_identity),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnTotp = Depends(get_manage_own_totp),
) -> TotpConfirmResponse:
    issued = await use_case.confirm(
        identity.user, body.code, via_setup_token=identity.session is None, context=context
    )
    if issued is not None:
        start_session(response, issued)
    return TotpConfirmResponse(session_started=issued is not None)


@router.post("/totp/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_totp(
    body: PasswordConfirmationRequest,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnTotp = Depends(get_manage_own_totp),
) -> None:
    await use_case.disable(user, body.password, context=context)


# ── Passkeys ─────────────────────────────────────────────────────────


def _passkey_response(passkey: Passkey) -> PasskeyResponse:
    return PasskeyResponse(
        id=passkey.public_id,
        name=passkey.name,
        created=passkey.created,
        last_used_at=passkey.last_used_at,
        backed_up=passkey.backed_up,
    )


@router.get("/passkeys", response_model=list[PasskeyResponse])
async def list_passkeys(
    user: User = Depends(get_current_user),
    use_case: ManageOwnPasskeys = Depends(get_manage_own_passkeys),
) -> list[PasskeyResponse]:
    return [_passkey_response(p) for p in await use_case.list_all(user)]


@router.post("/passkeys/options", response_model=PasskeyOptionsResponse)
async def passkey_registration_options(
    user: User = Depends(get_current_user),
    use_case: ManageOwnPasskeys = Depends(get_manage_own_passkeys),
) -> PasskeyOptionsResponse:
    challenge = await use_case.registration_options(user)
    return PasskeyOptionsResponse(
        options=challenge.options, challenge_token=challenge.challenge_token
    )


@router.post("/passkeys", response_model=PasskeyResponse, status_code=status.HTTP_201_CREATED)
async def register_passkey(
    body: RegisterPasskeyRequest,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnPasskeys = Depends(get_manage_own_passkeys),
) -> PasskeyResponse:
    passkey = await use_case.register(
        user,
        challenge_token=body.challenge_token,
        credential=body.credential,
        name=body.name,
        context=context,
    )
    return _passkey_response(passkey)


@router.patch("/passkeys/{passkey_id}", response_model=PasskeyResponse)
async def rename_passkey(
    passkey_id: str,
    body: RenamePasskeyRequest,
    user: User = Depends(get_current_user),
    use_case: ManageOwnPasskeys = Depends(get_manage_own_passkeys),
) -> PasskeyResponse:
    return _passkey_response(await use_case.rename(user, passkey_id, body.name))


@router.delete("/passkeys/{passkey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_passkey(
    passkey_id: str,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnPasskeys = Depends(get_manage_own_passkeys),
) -> None:
    await use_case.remove(user, passkey_id, context=context)


# ── Sessions and trusted devices ─────────────────────────────────────


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    identity: WebIdentity = Depends(get_web_identity),
    use_case: ManageOwnSessions = Depends(get_manage_own_sessions),
) -> list[SessionResponse]:
    current = identity.session.public_id if identity.session else None
    return [
        SessionResponse(
            id=s.public_id,
            created=s.created,
            last_seen_at=s.last_seen_at,
            user_agent=s.user_agent,
            client_ip=s.client_ip,
            current=s.public_id == current,
        )
        for s in await use_case.list_all(identity.user)
    ]


# Declared before the "/sessions/{session_id}" routes, so the literal path
# is never read as a session id.
@router.get("/sessions/current", response_model=CurrentSessionResponse)
async def read_current_session(
    identity: WebIdentity = Depends(get_web_identity),
    use_case: ManageOwnSessions = Depends(get_manage_own_sessions),
) -> CurrentSessionResponse:
    current = await use_case.current(identity.user, identity.session)
    return CurrentSessionResponse(expires_at=current.expires_at, server_time=current.server_time)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnSessions = Depends(get_manage_own_sessions),
) -> None:
    await use_case.revoke(user, session_id, context=context)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_other_sessions(
    identity: WebIdentity = Depends(get_web_identity),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnSessions = Depends(get_manage_own_sessions),
) -> None:
    current = str(identity.session.public_id) if identity.session else None
    await use_case.revoke_others(identity.user, current, context=context)


@router.get("/trusted-devices", response_model=list[TrustedDeviceResponse])
async def list_trusted_devices(
    user: User = Depends(get_current_user),
    use_case: ManageOwnTrustedDevices = Depends(get_manage_own_trusted_devices),
) -> list[TrustedDeviceResponse]:
    return [
        TrustedDeviceResponse(
            id=d.public_id,
            created=d.created,
            expires_at=d.expires_at,
            user_agent=d.user_agent,
            last_used_at=d.last_used_at,
        )
        for d in await use_case.list_all(user)
    ]


@router.delete("/trusted-devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_trusted_device(
    device_id: str,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnTrustedDevices = Depends(get_manage_own_trusted_devices),
) -> None:
    await use_case.revoke(user, device_id, context=context)


@router.delete("/trusted-devices", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_trusted_devices(
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnTrustedDevices = Depends(get_manage_own_trusted_devices),
) -> None:
    await use_case.revoke_all(user, context=context)


# ── Personal access tokens ───────────────────────────────────────────


@router.get("/personal-access-tokens", response_model=list[PatResponse])
async def list_pats(
    user: User = Depends(_write_pat),
    use_case: ManagePats = Depends(get_manage_pats),
) -> list[PatResponse]:
    return [_pat(t) for t in await use_case.list_all(user)]


@router.post(
    "/personal-access-tokens",
    response_model=PatCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pat(
    body: TokenCreateRequest,
    user: User = Depends(_write_pat),
    context: RequestContext = Depends(get_request_context),
    use_case: ManagePats = Depends(get_manage_pats),
) -> PatCreatedResponse:
    created = await use_case.create(
        user,
        TokenCommand(name=body.name, permissions=body.permissions, expires_at=body.expires_at),
        context=context,
    )
    return PatCreatedResponse(**_pat(created.token).model_dump(), token=created.secret)


@router.delete("/personal-access-tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_pat(
    token_id: str,
    user: User = Depends(_write_pat),
    context: RequestContext = Depends(get_request_context),
    use_case: ManagePats = Depends(get_manage_pats),
) -> None:
    await use_case.revoke(user, token_id, context=context)


# ── Own security log ─────────────────────────────────────────────────


@router.get("/security-events", response_model=Page[SecurityEventResponse])
async def list_own_security_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    filters: SecurityEventFilter = SecurityEventQuery,
    user: User = Depends(get_current_user),
    use_case: ListSecurityEvents = Depends(get_list_security_events),
    p: Platform = Depends(get_platform),
) -> Page[SecurityEventResponse]:
    events, total = await use_case.own(user, limit=limit, offset=offset, filters=filters)
    return Page(items=await present_events(p, events), total=total)


@router.get("/agent-calls/tools", response_model=list[str])
async def list_own_agent_call_tools(
    user: User = Depends(get_current_user),
    use_case: ListAgentCalls = Depends(get_list_agent_calls),
) -> list[str]:
    """The tool names in the user's own agent call log."""
    return await use_case.tools(user_id=user.id)


@router.get("/agent-calls", response_model=Page[AgentCallResponse])
async def list_own_agent_calls(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    filters: AgentCallFilter = AgentCallQuery,
    user: User = Depends(get_current_user),
    use_case: ListAgentCalls = Depends(get_list_agent_calls),
    p: Platform = Depends(get_platform),
) -> Page[AgentCallResponse]:
    """The tool calls the user's agents made with the user's tokens."""
    calls, total = await use_case.own(user, limit=limit, offset=offset, filters=filters)
    return Page(items=await present_agent_calls(p, calls), total=total)
