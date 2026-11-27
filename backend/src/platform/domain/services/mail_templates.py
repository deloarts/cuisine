"""
One declaration per mail kind: the variables its template may use (the
editor's chips), the subject when nothing else names one, and the sample
values the preview renders with. Resolution picks the administrator's
template of the first language in the fallback chain with a non-blank body;
without one the packaged file of the first language that ships one is used.
Adapted from glados's mail template specs.
"""

from dataclasses import dataclass
from typing import Any

from src.platform.domain.entities.settings import MailTemplateText
from src.platform.domain.value_objects.mail import MailTemplateKind

CONTENT_LOCALES = ("en-GB", "de-AT")
FALLBACK_LOCALE = "en-GB"
_SAMPLE_DOMAIN = "https://cuisine.example.com"


@dataclass(frozen=True)
class MailTemplateSpec:
    kind: MailTemplateKind
    variables: tuple[str, ...]
    default_subject: dict[str, str]
    sample_context: dict[str, Any]


MAIL_TEMPLATE_SPECS: dict[MailTemplateKind, MailTemplateSpec] = {
    MailTemplateKind.TEST_MAIL: MailTemplateSpec(
        kind=MailTemplateKind.TEST_MAIL,
        variables=("instance_name", "domain", "full_name"),
        default_subject={
            "en-GB": "{{ instance_name }}: test mail",
            "de-AT": "{{ instance_name }}: Testmail",
        },
        sample_context={"instance_name": "Cuisine", "domain": _SAMPLE_DOMAIN, "full_name": "Anna"},
    ),
    MailTemplateKind.OPERATIONAL_ALERT: MailTemplateSpec(
        kind=MailTemplateKind.OPERATIONAL_ALERT,
        variables=("instance_name", "domain", "alert", "title", "details"),
        default_subject={
            "en-GB": "{{ instance_name }}: {{ title }}",
            "de-AT": "{{ instance_name }}: {{ title }}",
        },
        sample_context={
            "instance_name": "Cuisine",
            "domain": _SAMPLE_DOMAIN,
            "alert": "backup_failed",
            "title": "The nightly backup failed",
            "details": "pg_dump exited with an error at 03:00 UTC.",
        },
    ),
    MailTemplateKind.USER_CREATED: MailTemplateSpec(
        kind=MailTemplateKind.USER_CREATED,
        variables=("instance_name", "domain", "full_name", "email", "login_url", "created_by"),
        default_subject={
            "en-GB": "Welcome to {{ instance_name }}",
            "de-AT": "Willkommen bei {{ instance_name }}",
        },
        sample_context={
            "instance_name": "Cuisine",
            "domain": _SAMPLE_DOMAIN,
            "full_name": "Anna",
            "email": "anna@example.com",
            "login_url": f"{_SAMPLE_DOMAIN}/login",
            "created_by": "Max",
        },
    ),
}


def locale_chain(requested: str | None, default: str | None) -> list[str]:
    chain: list[str] = []
    for candidate in (requested, default, FALLBACK_LOCALE):
        if candidate and candidate in CONTENT_LOCALES and candidate not in chain:
            chain.append(candidate)
    return chain


def pick_override(
    overrides: dict[str, dict[str, MailTemplateText]], kind: MailTemplateKind, chain: list[str]
) -> tuple[str, MailTemplateText] | None:
    """The administrator's template of the first language in the chain with
    a non-blank body; a blank body counts as absent, so an untranslated
    language falls back instead of sending an empty mail."""
    by_locale = overrides.get(kind.value, {})
    for locale in chain:
        text = by_locale.get(locale)
        if text is not None and text.body.strip():
            return locale, text
    return None
