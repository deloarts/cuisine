"""Choosing the text to show from a record's translations, and the rules a
set of translations must follow."""

from collections.abc import Mapping

from src.cookbook.domain.value_objects.enums import ContentLocale
from src.platform.domain.exceptions import InvalidInputError

LOCALES: tuple[str, ...] = tuple(locale.value for locale in ContentLocale)


def resolve[T](translations: Mapping[str, T], wanted: str | None, original: str) -> tuple[str, T]:
    """The text in `wanted` when it exists, else in the original locale,
    else in any locale, with the locale actually served. A record always
    has its original text, so the last fallback only guards bad data."""
    for locale in (wanted, original, *sorted(translations)):
        if locale is not None and locale in translations:
            return locale, translations[locale]
    raise InvalidInputError("The record has no text in any language.")


def assert_locale(locale: str) -> None:
    if locale not in LOCALES:
        raise InvalidInputError(f"Unknown language {locale!r}; use one of {', '.join(LOCALES)}.")


def assert_translations(translations: Mapping[str, object], original: str, what: str) -> None:
    """Every key is a known locale and the original locale is present."""
    assert_locale(original)
    for locale in translations:
        assert_locale(locale)
    if original not in translations:
        raise InvalidInputError(f"The {what} needs its text in its original language {original}.")


def ui_locale(language: str) -> str:
    """The content locale of a UI language code (deAT, enGB)."""
    return {"deAT": ContentLocale.DE_AT.value, "enGB": ContentLocale.EN_GB.value}.get(
        language, ContentLocale.EN_GB.value
    )
