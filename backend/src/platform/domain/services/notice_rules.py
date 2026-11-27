"""Checks for in-app notices and the choice of language for a reader."""

from src.platform.domain.entities.notice import Notice
from src.platform.domain.entities.notice import NoticeText
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.services.settings_rules import CONTENT_LOCALES

TITLE_MAX = 120
BODY_MAX = 5000
FALLBACK_LOCALE = "en-GB"


def validate_notice_texts(texts: dict[str, NoticeText]) -> dict[str, NoticeText]:
    """The texts with blank locales dropped. Raises when a locale is
    unknown, a text is too long or no locale has a title."""
    unknown = set(texts) - CONTENT_LOCALES
    if unknown:
        raise InvalidInputError(f"Unknown notice languages: {', '.join(sorted(unknown))}.")
    kept: dict[str, NoticeText] = {}
    for locale, text in texts.items():
        title, body = text.title.strip(), text.body.strip()
        if not title and not body:
            continue
        if not title:
            raise InvalidInputError(f"The {locale} text of the notice needs a title.")
        if len(title) > TITLE_MAX or len(body) > BODY_MAX:
            raise InvalidInputError(
                f"A notice title holds at most {TITLE_MAX} characters, its text {BODY_MAX}."
            )
        kept[locale] = NoticeText(title=title, body=body)
    if not kept:
        raise InvalidInputError("The notice needs a title in at least one language.")
    return kept


def notice_text(notice: Notice, locale: str) -> tuple[str, NoticeText]:
    """The locale served and its text: the reader's, else en-GB, else any."""
    for candidate in (locale, FALLBACK_LOCALE):
        if candidate in notice.texts:
            return candidate, notice.texts[candidate]
    first = next(iter(sorted(notice.texts)))
    return first, notice.texts[first]
