from typing import Protocol

from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.legal import LegalVersion


class ILegalRepository(Protocol):
    async def current(self, kind: LegalKind) -> LegalVersion | None:
        """The newest published version, or None."""
        ...

    async def history(self, kind: LegalKind) -> list[LegalVersion]:
        """Every version, newest first."""
        ...

    async def add(self, version: LegalVersion) -> LegalVersion: ...
