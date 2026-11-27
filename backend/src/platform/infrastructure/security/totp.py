"""TOTP (time-based one-time password) utilities for 2FA. Wraps pyotp."""

import time

import pyotp

TOTP_STEP_SECONDS = 30
# How long a claimed step stays claimed in the replay guard: long enough to
# cover the step itself and the one pyotp still accepts on either side.
TOTP_REPLAY_TTL_SECONDS = 90


class PyOtpTotpService:
    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def provisioning_uri(self, secret: str, account: str, issuer: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=issuer)

    def current_step(self) -> int:
        return int(time.time()) // TOTP_STEP_SECONDS

    def verify(self, secret: str, code: str) -> bool:
        return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)
