"""
Maps domain errors to HTTP responses. Each semantic base in
domain/exceptions.py has one status; its message is the response detail,
since domain messages are written for the user. An error outside these
bases answers 500 without echoing its message.
"""

from fastapi import FastAPI
from fastapi import Request
from fastapi import status
from fastapi.responses import JSONResponse

from src.platform.domain.exceptions import AuthenticationError
from src.platform.domain.exceptions import BadRequestError
from src.platform.domain.exceptions import ConflictError
from src.platform.domain.exceptions import DomainError
from src.platform.domain.exceptions import ForbiddenError
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import NotFoundError
from src.platform.domain.exceptions import PayloadTooLargeError
from src.platform.domain.exceptions import RateLimitedError
from src.platform.domain.exceptions import ServiceUnavailableError
from src.platform.domain.exceptions import UnsupportedFileTypeError
from src.platform.infrastructure.logging.logger import log
from src.platform.ports.outbound.unit_of_work import ConstraintViolationError

_STATUS_BY_BASE: tuple[tuple[type[DomainError], int], ...] = (
    (RateLimitedError, status.HTTP_429_TOO_MANY_REQUESTS),
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (ForbiddenError, status.HTTP_403_FORBIDDEN),
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (PayloadTooLargeError, status.HTTP_413_CONTENT_TOO_LARGE),
    (UnsupportedFileTypeError, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
    (InvalidInputError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (BadRequestError, status.HTTP_400_BAD_REQUEST),
    (ServiceUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
)


def status_for(exc: DomainError) -> int | None:
    for base, code in _STATUS_BY_BASE:
        if isinstance(exc, base):
            return code
    return None


async def _domain_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    code = status_for(exc)
    if code is None:
        log.error("Unmapped domain error: %r", exc)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitedError) and exc.retry_after_seconds:
        headers["Retry-After"] = str(exc.retry_after_seconds)
    body: dict[str, object] = {"detail": str(exc), "code": type(exc).__name__}
    # An error may name the record it refers to, such as the existing entry
    # behind a duplicate name; never a secret.
    extra = getattr(exc, "extra", None)
    if isinstance(extra, dict):
        body.update(extra)
    return JSONResponse(body, status_code=code, headers=headers)


async def _constraint_violation(_request: Request, exc: Exception) -> JSONResponse:
    log.warning("Constraint violation: %s", exc)
    return JSONResponse(
        {"detail": "The change conflicts with existing data.", "code": "ConstraintViolation"},
        status_code=status.HTTP_409_CONFLICT,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(ConstraintViolationError, _constraint_violation)
