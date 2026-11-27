"""
The mail template editor: each kind's templates per language with the
packaged defaults, saving, preview with sample values, and template files
in and out, like glados. A saved template is checked by rendering it with
the kind's sample values, so a broken one never reaches a send.
"""

import re
from dataclasses import dataclass

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.mailer import Mailer
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.domain.entities.settings import MailTemplateText
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.services.mail_templates import CONTENT_LOCALES
from src.platform.domain.services.mail_templates import MAIL_TEMPLATE_SPECS
from src.platform.domain.services.mail_templates import MailTemplateSpec
from src.platform.domain.value_objects.mail import MailTemplateKind
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.mail_renderer import IMailRenderer
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork

TEMPLATE_FILE_MAX_BYTES = 256 * 1024
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class LocaleTemplate:
    locale: str
    subject: str
    body: str
    # False while the packaged default is in use.
    customized: bool


@dataclass(frozen=True)
class KindTemplates:
    spec: MailTemplateSpec
    templates: list[LocaleTemplate]


class ManageMailTemplates:
    def __init__(
        self,
        *,
        settings_repo: ISettingsRepository,
        renderer: IMailRenderer,
        mailer: Mailer,
        audit: SecurityAudit,
        uow: IUnitOfWork,
    ) -> None:
        self._settings = settings_repo
        self._renderer = renderer
        self._mailer = mailer
        self._audit = audit
        self._uow = uow

    def _default(self, kind: MailTemplateKind, locale: str) -> MailTemplateText:
        packaged = self._renderer.packaged(kind, locale) or self._renderer.packaged(kind, "en-GB")
        if packaged is None:
            return MailTemplateText(
                subject=MAIL_TEMPLATE_SPECS[kind].default_subject.get(locale, ""), body=""
            )
        return MailTemplateText(subject=packaged[0], body=packaged[1])

    def default(self, kind: MailTemplateKind, locale: str) -> MailTemplateText:
        return self._default(kind, locale)

    async def list_all(self) -> list[KindTemplates]:
        overrides = (await self._settings.get_mail_templates()).overrides
        answer: list[KindTemplates] = []
        for kind, spec in MAIL_TEMPLATE_SPECS.items():
            rows: list[LocaleTemplate] = []
            for locale in CONTENT_LOCALES:
                custom = overrides.get(kind.value, {}).get(locale)
                if custom is not None and custom.body.strip():
                    rows.append(LocaleTemplate(locale, custom.subject, custom.body, True))
                else:
                    text = self._default(kind, locale)
                    rows.append(LocaleTemplate(locale, text.subject, text.body, False))
            answer.append(KindTemplates(spec=spec, templates=rows))
        return answer

    async def preview(self, kind: MailTemplateKind, text: MailTemplateText) -> tuple[str, str]:
        context = await self._mailer.base_context() | MAIL_TEMPLATE_SPECS[kind].sample_context
        try:
            return await self._mailer.render(text, context)
        except ValueError as exc:
            raise InvalidInputError(str(exc)) from exc

    async def save(
        self,
        actor: User,
        kind: MailTemplateKind,
        texts: dict[str, MailTemplateText],
        *,
        context: RequestContext,
    ) -> None:
        """Saves the given languages; a blank body goes back to the default."""
        unknown = set(texts) - set(CONTENT_LOCALES)
        if unknown:
            raise InvalidInputError(f"Unknown languages: {', '.join(sorted(unknown))}.")
        settings = await self._settings.get_mail_templates()
        by_locale = dict(settings.overrides.get(kind.value, {}))
        for locale, text in texts.items():
            if not text.body.strip():
                by_locale.pop(locale, None)
                continue
            if not text.subject.strip():
                raise InvalidInputError(f"The {locale} template needs a subject.")
            await self.preview(kind, text)
            by_locale[locale] = MailTemplateText(subject=text.subject.strip(), body=text.body)
        if by_locale:
            settings.overrides[kind.value] = by_locale
        else:
            settings.overrides.pop(kind.value, None)
        await self._settings.save_mail_templates(settings)
        await self._audit.record(
            SecurityEventType.SETTINGS_CHANGED,
            actor=actor,
            context=context,
            detail={
                "section": "mail_templates",
                "fields": [f"{kind.value}.{loc}" for loc in texts],
            },
        )
        await self._uow.commit()

    async def import_file(
        self,
        actor: User,
        kind: MailTemplateKind,
        locale: str,
        data: bytes,
        *,
        context: RequestContext,
    ) -> None:
        """Saves an HTML template file; its <title> is the subject."""
        if len(data) > TEMPLATE_FILE_MAX_BYTES:
            raise InvalidInputError("A template file holds at most 256 KB.")
        try:
            body = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidInputError("A template file must be UTF-8 HTML.") from exc
        match = _TITLE.search(body)
        subject = match.group(1).strip() if match else ""
        if not subject:
            raise InvalidInputError("The template file needs a <title>, the mail's subject.")
        await self.save(
            actor, kind, {locale: MailTemplateText(subject=subject, body=body)}, context=context
        )

    async def export_file(self, kind: MailTemplateKind, locale: str) -> tuple[str, str]:
        """The file name and HTML of the template in use for the language;
        exported files import again unchanged."""
        overrides = (await self._settings.get_mail_templates()).overrides
        custom = overrides.get(kind.value, {}).get(locale)
        text = custom if custom is not None and custom.body.strip() else self._default(kind, locale)
        title = f"<title>{text.subject}</title>"
        if _TITLE.search(text.body):
            body = _TITLE.sub(lambda _m: title, text.body, count=1)
        else:
            body = f"{title}\n{text.body}"
        return f"{kind.value}.{locale}.html", body
