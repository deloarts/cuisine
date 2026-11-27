"""Rendering mail templates, and the packaged defaults shipped with the app."""

from typing import Any
from typing import Protocol

from src.platform.domain.value_objects.mail import MailTemplateKind


class IMailRenderer(Protocol):
    def render(self, source: str, context: dict[str, Any]) -> str:
        """Renders admin-authored template text, sandboxed and escaped.
        Raises ValueError with a readable message for a broken template."""
        ...

    def packaged(self, kind: MailTemplateKind, locale: str) -> tuple[str, str] | None:
        """The shipped (subject, body) of a kind in a language, if any."""
        ...


class ISendLimiter(Protocol):
    def allow(self, key: str, limit: int) -> bool:
        """Counts one send for `key` and says whether it stays within
        `limit` per hour; 0 means no limit."""
        ...
