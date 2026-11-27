from typing import Any
from typing import Literal

from pydantic import Field

from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class PasswordLoginRequest(RequestSchema):
    # The e-mail address, or `system` for the system user.
    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class TotpLoginRequest(RequestSchema):
    partial_token: str
    code: str = Field(min_length=6, max_length=10)
    trust_device: bool = False


class PasskeyLoginRequest(RequestSchema):
    challenge_token: str
    credential: dict[str, Any]


class LoginResponse(ResponseSchema):
    """What the login step leads to. `session`: signed in, the cookie is
    set. `totp_required`: send the code with `partial_token`.
    `totp_setup_required`: enrol with `setup_token` as a bearer token."""

    status: Literal["session", "totp_required", "totp_setup_required"]
    partial_token: str | None = None
    setup_token: str | None = None
    trusted_device_days: int = 0


class PasskeyOptionsResponse(ResponseSchema):
    options: dict[str, Any]
    challenge_token: str
