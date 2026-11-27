"""IMailService over SMTP with aiosmtplib.

The configured host passes the webhook target guard first, with private
networks allowed, since a relay on the household's network is normal, but
loopback, link-local, cloud metadata addresses and the stack's own services
refused. A failed delivery answers with a fixed message, and the reason from
the server or the socket goes only to the log, so the test mail cannot be
used to read banners or map ports inside the stack.
"""

import logging
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import aiosmtplib

from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.domain.entities.settings import MailSettings
from src.platform.domain.exceptions import InvalidWebhookConfigurationError
from src.platform.domain.exceptions import MailDeliveryError
from src.platform.domain.exceptions import MailNotConfiguredError

log = logging.getLogger("cuisine")

_TIMEOUT_SECONDS = 15
# The dev stack's mail catcher is a stack service, and the one an SMTP
# setting may name.
_ALLOWED_STACK_HOSTS = frozenset({"mailpit"})
DELIVERY_FAILED_MESSAGE = "The mail server refused the message or could not be reached."


class SmtpMailService:
    def __init__(self, guard: WebhookTargetGuard) -> None:
        self._guard = guard

    async def send(
        self, settings: MailSettings, *, to: str, subject: str, text: str, html: str | None = None
    ) -> None:
        if not settings.enabled or not settings.host or not settings.sender:
            raise MailNotConfiguredError("Mail delivery is not configured.")
        message = EmailMessage()
        message["From"] = (
            formataddr((settings.sender_name, settings.sender))
            if settings.sender_name
            else settings.sender
        )
        message["To"] = to
        if settings.reply_to:
            message["Reply-To"] = settings.reply_to
        message["Subject"] = subject
        message.set_content(text)
        if html is not None:
            message.add_alternative(html, subtype="html")
        try:
            await self._guard.check_host(
                settings.host,
                settings.port,
                allow_private=True,
                subject="mail server",
                stack_exceptions=_ALLOWED_STACK_HOSTS,
            )
        except InvalidWebhookConfigurationError as exc:
            raise MailDeliveryError(str(exc)) from exc
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.host,
                port=settings.port,
                username=settings.username or None,
                password=settings.password or None,
                use_tls=settings.security == "tls",
                start_tls=settings.security == "starttls",
                tls_context=_tls_context(settings.verify_certificate),
                timeout=_TIMEOUT_SECONDS,
            )
        except (aiosmtplib.SMTPException, OSError) as exc:
            log.warning("Mail delivery to the SMTP server failed: %s", exc)
            raise MailDeliveryError(DELIVERY_FAILED_MESSAGE) from exc


def _tls_context(verify: bool) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if not verify:
        # For a relay on the home network with a self-signed certificate;
        # the admin switched verification off knowingly.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context
