"""WebAuthn option generation and response verification."""

from dataclasses import dataclass
from typing import Any
from typing import Protocol


@dataclass(frozen=True)
class PasskeyOptions:
    # The JSON the browser passes to navigator.credentials.create/get.
    options: dict[str, Any]
    # The challenge, base64url, which the caller carries to the verify step.
    challenge: str


@dataclass(frozen=True)
class VerifiedPasskeyRegistration:
    credential_id: bytes
    public_key: bytes
    sign_count: int
    backed_up: bool
    transports: list[str]


class IPasskeyVerifier(Protocol):
    def registration_options(
        self,
        *,
        user_handle: bytes,
        # The name the authenticator lists the passkey under: the e-mail.
        account_name: str,
        display_name: str,
        exclude_credential_ids: list[bytes],
    ) -> PasskeyOptions: ...

    def verify_registration(
        self, *, credential: dict[str, Any], challenge: str
    ) -> VerifiedPasskeyRegistration: ...

    def authentication_options(self) -> PasskeyOptions: ...

    def credential_id_of(self, credential: dict[str, Any]) -> bytes | None: ...

    def verify_authentication(
        self,
        *,
        credential: dict[str, Any],
        challenge: str,
        public_key: bytes,
        sign_count: int,
    ) -> int:
        """Verifies the assertion and returns the new sign count."""
        ...
