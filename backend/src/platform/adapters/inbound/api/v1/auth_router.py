"""
/api/v1/auth: the login steps and the logout. Public, apart from the
logout, which needs the session it ends.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import Response
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import get_web_identity
from src.platform.adapters.inbound.api.deps import get_logout
from src.platform.adapters.inbound.api.deps import get_passkey_login
from src.platform.adapters.inbound.api.deps import get_password_login
from src.platform.adapters.inbound.api.deps import get_totp_login
from src.platform.adapters.inbound.api.schemas.auth_schema import LoginResponse
from src.platform.adapters.inbound.api.schemas.auth_schema import PasskeyLoginRequest
from src.platform.adapters.inbound.api.schemas.auth_schema import PasskeyOptionsResponse
from src.platform.adapters.inbound.api.schemas.auth_schema import PasswordLoginRequest
from src.platform.adapters.inbound.api.schemas.auth_schema import TotpLoginRequest
from src.platform.application.dto.context import RequestContext
from src.platform.application.dto.login_dto import PasskeyLoginCommand
from src.platform.application.dto.login_dto import PasswordLoginCommand
from src.platform.application.dto.login_dto import SessionIssued
from src.platform.application.dto.login_dto import TotpChallengeIssued
from src.platform.application.dto.login_dto import TotpLoginCommand
from src.platform.application.use_cases.auth.logout import Logout
from src.platform.application.use_cases.auth.passkey_login import PasskeyLogin
from src.platform.application.use_cases.auth.password_login import PasswordLogin
from src.platform.application.use_cases.auth.totp_login import TotpLogin
from src.platform.application.use_cases.auth.validate_web_token import WebIdentity
from src.platform.infrastructure.security.cookies import TRUSTED_DEVICE_COOKIE
from src.platform.infrastructure.security.cookies import clear_session_cookie
from src.platform.infrastructure.security.cookies import set_session_cookie
from src.platform.infrastructure.security.cookies import set_trusted_device_cookie

router = APIRouter(tags=["auth"])


def start_session(response: Response, issued: SessionIssued) -> LoginResponse:
    """Sets the session cookie, and the trusted-device cookie when one was
    granted, and answers the session status."""
    set_session_cookie(response, issued.access_token, issued.cookie_max_age)
    if issued.trusted_device_secret:
        set_trusted_device_cookie(
            response, issued.trusted_device_secret, issued.trusted_device_max_age
        )
    return LoginResponse(status="session")


@router.post("/login", response_model=LoginResponse)
async def login(
    body: PasswordLoginRequest,
    request: Request,
    response: Response,
    context: RequestContext = Depends(get_request_context),
    use_case: PasswordLogin = Depends(get_password_login),
) -> LoginResponse:
    result = await use_case.execute(
        PasswordLoginCommand(
            login=body.login,
            password=body.password,
            context=context,
            trusted_device_secret=request.cookies.get(TRUSTED_DEVICE_COOKIE),
        )
    )
    if isinstance(result, SessionIssued):
        return start_session(response, result)
    if isinstance(result, TotpChallengeIssued):
        return LoginResponse(
            status="totp_required",
            partial_token=result.partial_token,
            trusted_device_days=result.trusted_device_days,
        )
    return LoginResponse(status="totp_setup_required", setup_token=result.setup_token)


@router.post("/login/totp", response_model=LoginResponse)
async def login_totp(
    body: TotpLoginRequest,
    response: Response,
    context: RequestContext = Depends(get_request_context),
    use_case: TotpLogin = Depends(get_totp_login),
) -> LoginResponse:
    issued = await use_case.execute(
        TotpLoginCommand(
            partial_token=body.partial_token,
            code=body.code,
            trust_device=body.trust_device,
            context=context,
        )
    )
    return start_session(response, issued)


@router.post("/login/passkey/options", response_model=PasskeyOptionsResponse)
async def passkey_options(
    use_case: PasskeyLogin = Depends(get_passkey_login),
) -> PasskeyOptionsResponse:
    challenge = use_case.options()
    return PasskeyOptionsResponse(
        options=challenge.options, challenge_token=challenge.challenge_token
    )


@router.post("/login/passkey", response_model=LoginResponse)
async def login_passkey(
    body: PasskeyLoginRequest,
    response: Response,
    context: RequestContext = Depends(get_request_context),
    use_case: PasskeyLogin = Depends(get_passkey_login),
) -> LoginResponse:
    issued = await use_case.execute(
        PasskeyLoginCommand(
            challenge_token=body.challenge_token, credential=body.credential, context=context
        )
    )
    return start_session(response, issued)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    identity: WebIdentity = Depends(get_web_identity),
    context: RequestContext = Depends(get_request_context),
    use_case: Logout = Depends(get_logout),
) -> None:
    await use_case.execute(identity, context=context)
    clear_session_cookie(response)
