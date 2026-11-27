"""Sends a plain-text and HTML mail through the configured server."""

from typing import Protocol

from src.platform.domain.entities.settings import MailSettings


class IMailService(Protocol):
    async def send(
        self, settings: MailSettings, *, to: str, subject: str, text: str, html: str | None = None
    ) -> None: ...
