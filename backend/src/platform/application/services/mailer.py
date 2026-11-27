"""
Sends the instance's mails from templates: the administrator's template of
the first language in the chain, else the packaged default. Mail stays
optional: with mail off or no recipient, sending an alert does nothing;
a test mail raises so the admin sees why.
"""

import html
import logging
import re
from typing import Any

from src.platform.domain.entities.settings import MailTemplateText
from src.platform.domain.exceptions import MailDeliveryError
from src.platform.domain.exceptions import MailNotConfiguredError
from src.platform.domain.services.mail_templates import locale_chain
from src.platform.domain.services.mail_templates import pick_override
from src.platform.domain.value_objects.mail import AlertKind
from src.platform.domain.value_objects.mail import MailTemplateKind
from src.platform.ports.outbound.mail_renderer import IMailRenderer
from src.platform.ports.outbound.mail_renderer import ISendLimiter
from src.platform.ports.outbound.mail_service import IMailService
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository

ALERT_TITLES: dict[AlertKind, dict[str, str]] = {
    AlertKind.BACKUP_FAILED: {
        "en-GB": "The database backup failed",
        "de-AT": "Die Datenbanksicherung ist fehlgeschlagen",
    },
    AlertKind.WEBHOOK_DISABLED: {
        "en-GB": "A webhook was switched off",
        "de-AT": "Ein Webhook wurde abgeschaltet",
    },
    AlertKind.MAINTENANCE_SWITCHED: {
        "en-GB": "Maintenance mode changed",
        "de-AT": "Wartungsmodus geändert",
    },
    AlertKind.STORAGE_WARNING: {
        "en-GB": "A storage and backup warning",
        "de-AT": "Eine Warnung zu Speicher und Sicherung",
    },
}

log = logging.getLogger("cuisine")
_TAGS = re.compile(r"<[^>]+>")
_STYLE = re.compile(r"<(style|head)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def plain_text(rendered_html: str) -> str:
    """A text alternative for clients that do not show HTML."""
    text = _TAGS.sub("", _STYLE.sub("", rendered_html))
    lines = [line.strip() for line in html.unescape(text).splitlines()]
    return "\n".join(line for line in lines if line)


def content_locale(language: str) -> str:
    return "de-AT" if language == "deAT" else "en-GB"


class Mailer:
    def __init__(
        self,
        *,
        settings_repo: ISettingsRepository,
        mail: IMailService,
        renderer: IMailRenderer,
        limiter: ISendLimiter,
        domain: str,
    ) -> None:
        self._settings = settings_repo
        self._mail = mail
        self._renderer = renderer
        self._limiter = limiter
        self._domain = domain

    async def resolve(
        self, kind: MailTemplateKind, locale: str | None
    ) -> tuple[str, MailTemplateText]:
        """The template to send in: (locale, subject and body)."""
        general = await self._settings.get_general()
        chain = locale_chain(locale, content_locale(general.default_language.value))
        picked = pick_override((await self._settings.get_mail_templates()).overrides, kind, chain)
        if picked is not None:
            return picked
        for candidate in chain:
            packaged = self._renderer.packaged(kind, candidate)
            if packaged is not None:
                return candidate, MailTemplateText(subject=packaged[0], body=packaged[1])
        raise ValueError(f"No template for {kind.value}.")

    async def render(self, template: MailTemplateText, context: dict[str, Any]) -> tuple[str, str]:
        subject = self._renderer.render(template.subject, context).strip()
        return " ".join(subject.split()), self._renderer.render(template.body, context)

    def link(self, path: str) -> str:
        """An absolute link into the web app, for a mail's buttons."""
        return f"{self._domain.rstrip('/')}{path}"

    async def base_context(self) -> dict[str, Any]:
        general = await self._settings.get_general()
        return {"instance_name": general.instance_name, "domain": self._domain}

    async def send_template(
        self,
        kind: MailTemplateKind,
        *,
        to: str,
        locale: str | None,
        context: dict[str, Any],
    ) -> None:
        """Raises MailNotConfiguredError with mail off and MailDeliveryError
        when the server refuses or the hourly limit is reached."""
        settings = await self._settings.get_mail()
        if not settings.enabled or not settings.host or not settings.sender:
            raise MailNotConfiguredError("Mail delivery is not configured.")
        if not self._limiter.allow("instance", settings.send_limit_per_hour):
            raise MailDeliveryError("The hourly mail limit is reached.")
        _locale, template = await self.resolve(kind, locale)
        subject, body = await self.render(template, await self.base_context() | context)
        await self._mail.send(settings, to=to, subject=subject, text=plain_text(body), html=body)

    async def alert(self, kind: AlertKind, details: str) -> int:
        """Mails an operational alert to the alert recipients and returns how
        many got it. Never raises: an alert must not break what raised it."""
        try:
            settings = await self._settings.get_mail()
            if not settings.enabled or not settings.alert_recipients:
                return 0
            general = await self._settings.get_general()
            locale = content_locale(general.default_language.value)
            context = {"alert": kind.value, "title": ALERT_TITLES[kind][locale], "details": details}
            sent = 0
            for recipient in settings.alert_recipients:
                await self.send_template(
                    MailTemplateKind.OPERATIONAL_ALERT, to=recipient, locale=locale, context=context
                )
                sent += 1
            return sent
        except Exception:
            log.warning("The %s alert could not be mailed.", kind.value, exc_info=True)
            return 0
