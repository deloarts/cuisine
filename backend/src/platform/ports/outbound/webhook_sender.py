"""Sending one signed webhook request, and the policy for target URLs."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WebhookSendResult:
    http_status: int | None
    duration_ms: int
    # A short category when the request failed, never the receiver's text.
    error: str | None


class IWebhookSender(Protocol):
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
        """Never raises; failures come back in the result."""
        ...


class IWebhookTargetGuard(Protocol):
    async def check(self, url: str, *, allow_private: bool, subject: str = "webhook") -> None:
        """Raises InvalidWebhookConfigurationError when the URL may not be
        a target. `subject` names what the URL is for in the message, such
        as "webhook" or "peer"."""
        ...
