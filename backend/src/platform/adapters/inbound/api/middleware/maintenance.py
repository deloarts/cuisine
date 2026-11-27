"""
Refuses writes with 503 while maintenance mode is on. The state is read
from the settings at most every few seconds per worker, so switching it on
reaches every worker within that time; the worker that switched it sees
the change at once.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response

from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.domain.entities.settings import MaintenanceSettings
from src.platform.domain.services.maintenance_rules import maintenance_message
from src.platform.domain.services.maintenance_rules import refused_in_maintenance

CACHE_SECONDS = 3.0


class MaintenanceState:
    """The cached maintenance settings of this worker."""

    def __init__(self) -> None:
        self._value: MaintenanceSettings | None = None
        self._read_at = 0.0

    async def current(self) -> MaintenanceSettings:
        if self._value is None or time.monotonic() - self._read_at > CACHE_SECONDS:
            async with SessionLocal() as db:
                self._value = await SqlAlchemySettingsRepository(db).get_maintenance()
            self._read_at = time.monotonic()
        return self._value

    def forget(self) -> None:
        self._value = None


maintenance_state = MaintenanceState()


class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if refused_in_maintenance(request.method, request.url.path):
            settings = await maintenance_state.current()
            if settings.enabled:
                wants_german = "de" in request.headers.get("accept-language", "")[:5].lower()
                message = maintenance_message(settings, "de-AT" if wants_german else "en-GB")
                return JSONResponse(
                    {"detail": message, "code": "MaintenanceModeError"},
                    status_code=503,
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)
