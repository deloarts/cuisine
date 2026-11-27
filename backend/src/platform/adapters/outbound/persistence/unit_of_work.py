"""Thin wrapper around an AsyncSession for commit and rollback control. A
constraint violation at commit is translated into the port's own error, so
the application layer never sees SQLAlchemy."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.ports.outbound.unit_of_work import ConstraintViolationError


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConstraintViolationError(str(exc.orig)) from exc

    async def rollback(self) -> None:
        await self._session.rollback()
