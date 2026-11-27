"""Whether the banner shows right now, and in which language."""

from datetime import datetime

from src.platform.domain.entities.settings import BannerSettings

FALLBACK_LOCALE = "en-GB"


def banner_is_active(settings: BannerSettings, now: datetime) -> bool:
    if not settings.enabled or not any(t.strip() for t in settings.messages.values()):
        return False
    if settings.starts_at and now < settings.starts_at:
        return False
    return not (settings.ends_at and now >= settings.ends_at)


def banner_message(settings: BannerSettings, locale: str) -> str:
    """The message in `locale`, else en-GB, else any text there is."""
    for candidate in (locale, FALLBACK_LOCALE):
        text = settings.messages.get(candidate, "").strip()
        if text:
            return text
    return next((t.strip() for t in settings.messages.values() if t.strip()), "")
