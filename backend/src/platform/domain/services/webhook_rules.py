"""Signing secrets, the retry schedule and the payload envelope of webhook
deliveries."""

import base64
import secrets
from datetime import datetime
from datetime import timedelta
from typing import Any

SECRET_PREFIX = "whsec_"
# The waits after the 1st, 2nd, ... failed attempt. After the last one the
# delivery fails for good.
RETRY_DELAYS = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
)
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1


def new_webhook_secret() -> str:
    return SECRET_PREFIX + base64.b64encode(secrets.token_bytes(32)).decode()


def next_attempt_after(attempts: int, now: datetime) -> datetime | None:
    """When to try again after `attempts` failed attempts, None when the
    delivery has used them all."""
    if attempts >= MAX_ATTEMPTS:
        return None
    return now + RETRY_DELAYS[attempts - 1]


def succeeded(http_status: int | None) -> bool:
    return http_status is not None and 200 <= http_status < 300


def envelope(event: str, data: dict[str, Any], occurred_at: datetime) -> dict[str, Any]:
    """The body every delivery carries."""
    return {"type": event, "timestamp": occurred_at.isoformat(), "data": data}
