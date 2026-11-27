"""
Delivers one webhook payload with httpx, signed the Standard Webhooks way
(https://www.standardwebhooks.com), so a receiver can check who sent it and
when:

    webhook-id:        <delivery id, the same on every retry>
    webhook-timestamp: <Unix seconds at sending>
    webhook-signature: v1,<base64 HMAC-SHA256 of "{id}.{timestamp}.{body}">
    X-Cuisine-Event:   <event key>

The HMAC key is the secret without its `whsec_` prefix, base64-decoded,
which is what the Standard Webhooks libraries do.

The target guard checks the URL and resolves its host before sending, and
the request goes to the first address it returned, with the Host header and
TLS server name kept as the hostname. Redirects are not followed and the
response body is never read. Errors are short categories, never the raw
exception, so the delivery log shows nothing a receiver answered. Adapted
from glados.
"""

import base64
import binascii
import hashlib
import hmac
import ssl
import time

import httpx

from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.domain.exceptions import InvalidWebhookConfigurationError
from src.platform.domain.services.webhook_rules import SECRET_PREFIX
from src.platform.ports.outbound.webhook_sender import WebhookSendResult
from src.shared_kernel.domain.services.clock import now_utc

TIMEOUT_SECONDS = 10.0


def sign_payload(secret: str, message_id: str, timestamp: int, body: str) -> str:
    """The `webhook-signature` value. Raises ValueError for a malformed secret."""
    try:
        key = base64.b64decode(secret.removeprefix(SECRET_PREFIX), validate=True)
    except binascii.Error as exc:
        raise ValueError("The signing secret is not valid base64.") from exc
    if not key:
        raise ValueError("The signing secret is empty.")
    digest = hmac.new(key, f"{message_id}.{timestamp}.{body}".encode(), hashlib.sha256).digest()
    return f"v1,{base64.b64encode(digest).decode()}"


class HttpxWebhookSender:
    def __init__(
        self, guard: WebhookTargetGuard, *, timeout_seconds: float = TIMEOUT_SECONDS
    ) -> None:
        self._guard = guard
        self._timeout = timeout_seconds

    async def post(
        self,
        *,
        url: str,
        secret: str,
        event: str,
        delivery_id: str,
        body: str,
        allow_private: bool,
    ) -> WebhookSendResult:
        if not secret:
            return _failed("The signing secret is unreadable; rotate it.")
        timestamp = int(now_utc().timestamp())
        try:
            signature = sign_payload(secret, delivery_id, timestamp, body)
        except ValueError:
            return _failed("The signing secret is malformed; rotate it.")
        start = time.perf_counter()
        try:
            target = await self._guard.resolve(url, allow_private=allow_private)
        except InvalidWebhookConfigurationError as exc:
            return _failed(f"Refused: {exc}", start)
        original = httpx.URL(url)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Cuisine-Webhook",
            "Host": original.netloc.decode("ascii"),
            "webhook-id": delivery_id,
            "webhook-timestamp": str(timestamp),
            "webhook-signature": signature,
            "X-Cuisine-Event": event,
        }
        pinned = original.copy_with(host=target.addresses[0])
        try:
            async with (
                httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client,
                client.stream(
                    "POST",
                    pinned,
                    content=body,
                    headers=headers,
                    extensions={"sni_hostname": target.host},
                ) as response,
            ):
                status = response.status_code
            return WebhookSendResult(http_status=status, duration_ms=_elapsed(start), error=None)
        except httpx.HTTPError as exc:
            return _failed(_describe(exc), start)


def _describe(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "Timed out."
    if isinstance(exc, httpx.ConnectError):
        cause: BaseException | None = exc
        seen: set[int] = set()
        while cause is not None and id(cause) not in seen:
            if isinstance(cause, ssl.SSLError):
                return "TLS handshake or certificate verification failed."
            seen.add(id(cause))
            cause = cause.__cause__ or cause.__context__
        return "Connection failed."
    if isinstance(exc, httpx.RemoteProtocolError | httpx.LocalProtocolError):
        return "The receiver did not answer with valid HTTP."
    return "Request failed."


def _elapsed(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _failed(error: str, start: float | None = None) -> WebhookSendResult:
    return WebhookSendResult(
        http_status=None, duration_ms=0 if start is None else _elapsed(start), error=error
    )
