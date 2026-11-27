"""Commands and outcomes of the login steps."""

from dataclasses import dataclass
from typing import Any

from src.platform.application.dto.context import RequestContext


@dataclass(frozen=True)
class PasswordLoginCommand:
    # The e-mail address, or `system` for the system user.
    login: str
    password: str
    context: RequestContext
    # The trusted-device cookie, when the browser sent one.
    trusted_device_secret: str | None = None


@dataclass(frozen=True)
class TotpLoginCommand:
    partial_token: str
    code: str
    trust_device: bool
    context: RequestContext


@dataclass(frozen=True)
class PasskeyLoginCommand:
    challenge_token: str
    credential: dict[str, Any]
    context: RequestContext


@dataclass(frozen=True)
class SessionIssued:
    access_token: str
    cookie_max_age: int
    session_public_id: str
    # A new trusted-device secret for the cookie, when the user asked for it.
    trusted_device_secret: str | None = None
    trusted_device_max_age: int = 0


@dataclass(frozen=True)
class TotpChallengeIssued:
    partial_token: str
    # How many days "trust this device" would last; 0 hides the option.
    trusted_device_days: int


@dataclass(frozen=True)
class TotpSetupRequired:
    setup_token: str


type PasswordLoginResult = SessionIssued | TotpChallengeIssued | TotpSetupRequired


@dataclass(frozen=True)
class PasskeyChallenge:
    options: dict[str, Any]
    challenge_token: str
