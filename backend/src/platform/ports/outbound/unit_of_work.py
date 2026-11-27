"""Transaction boundary protocol. Use cases stage their writes through the
repositories and commit once, so a request either writes everything or
nothing."""

from typing import Protocol


class ConstraintViolationError(Exception):
    """A write broke a unique, foreign key or not-null constraint."""


class IUnitOfWork(Protocol):
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
