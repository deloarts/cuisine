"""
Composition root: builds the FastAPI app, mounts every surface, adds the
middleware and runs the startup work (dev-only migrations, the system user
and cookbook resource seeds). Concrete classes are wired together only here and in the dependency
providers.
"""

from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import asynccontextmanager

from anyio import to_thread
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.routing import Route

from src.bootstrap.cookbook_hooks import register_cookbook_hooks
from src.bootstrap.cookbook_seed import ensure_cookbook_resources
from src.bootstrap.migrations import upgrade_to_head
from src.bootstrap.nightly_jobs import start_nightly_jobs
from src.bootstrap.peer_channel_worker import start_peer_channel_worker
from src.bootstrap.peering import register_cookbook_mirrors
from src.bootstrap.peering import register_cookbook_peering
from src.bootstrap.public_ids import register_cookbook_public_ids
from src.bootstrap.reference_router import admin_router as reference_admin_router
from src.bootstrap.reference_router import router as reference_router
from src.bootstrap.seed import ensure_default_groups
from src.bootstrap.seed import ensure_instance_id
from src.bootstrap.seed import ensure_system_user
from src.bootstrap.shopping_jobs import start_shopping_jobs
from src.bootstrap.webhook_events import register_cookbook_webhook_events
from src.bootstrap.webhook_worker import start_webhook_worker
from src.bootstrap.worker_loop import stop_worker
from src.cookbook.adapters.inbound.api.v1.accounts_router import router as accounts_router
from src.cookbook.adapters.inbound.api.v1.catalogue_file_router import (
    router as catalogue_file_router,
)
from src.cookbook.adapters.inbound.api.v1.cooking_router import router as cooking_router
from src.cookbook.adapters.inbound.api.v1.equipment_router import router as equipment_router
from src.cookbook.adapters.inbound.api.v1.households_router import (
    admin_router as household_admin_router,
)
from src.cookbook.adapters.inbound.api.v1.households_router import router as households_router
from src.cookbook.adapters.inbound.api.v1.ingredients_router import router as ingredients_router
from src.cookbook.adapters.inbound.api.v1.mirrors_router import (
    admin_router as incoming_recipes_router,
)
from src.cookbook.adapters.inbound.api.v1.mirrors_router import router as mirrors_router
from src.cookbook.adapters.inbound.api.v1.public_recipes_router import (
    router as public_recipes_router,
)
from src.cookbook.adapters.inbound.api.v1.recipe_archive_router import (
    router as recipe_archive_router,
)
from src.cookbook.adapters.inbound.api.v1.recipes_router import router as recipes_router
from src.cookbook.adapters.inbound.api.v1.resources_router import router as resources_router
from src.cookbook.adapters.inbound.api.v1.shopping_router import router as shopping_router
from src.cookbook.adapters.inbound.api.v1.variations_router import router as variations_router
from src.cookbook.adapters.inbound.mcp.catalog import COOKBOOK_AGENT_CATALOG
from src.platform.adapters.inbound.api.exception_handlers import register_exception_handlers
from src.platform.adapters.inbound.api.middleware.maintenance import MaintenanceMiddleware
from src.platform.adapters.inbound.api.middleware.security_headers import SecurityHeadersMiddleware
from src.platform.adapters.inbound.api.schemas.misc_schema import HealthResponse
from src.platform.adapters.inbound.api.v1.admin_router import router as admin_router
from src.platform.adapters.inbound.api.v1.admin_system_router import router as admin_system_router
from src.platform.adapters.inbound.api.v1.auth_router import router as auth_router
from src.platform.adapters.inbound.api.v1.files_router import router as files_router
from src.platform.adapters.inbound.api.v1.me_router import router as me_router
from src.platform.adapters.inbound.api.v1.notifications_router import router as notifications_router
from src.platform.adapters.inbound.api.v1.oauth_router import oauth_router
from src.platform.adapters.inbound.api.v1.oauth_router import well_known_router
from src.platform.adapters.inbound.api.v1.oauth_web_router import router as oauth_web_router
from src.platform.adapters.inbound.api.v1.operations_router import public_legal_router
from src.platform.adapters.inbound.api.v1.operations_router import router as operations_router
from src.platform.adapters.inbound.api.v1.peering_router import router as peering_router
from src.platform.adapters.inbound.api.v1.peers_router import router as peers_router
from src.platform.adapters.inbound.api.v1.resolve_router import router as resolve_router
from src.platform.adapters.inbound.api.v1.settings_router import router as settings_router
from src.platform.adapters.inbound.api.v1.surface_routers import key_router
from src.platform.adapters.inbound.api.v1.surface_routers import pat_router
from src.platform.adapters.inbound.api.v1.surface_routers import public_router
from src.platform.adapters.inbound.mcp.server import create_agent_app
from src.platform.adapters.outbound.persistence.session import engine
from src.platform.const import API_AUTH
from src.platform.const import API_KEY
from src.platform.const import API_MCP
from src.platform.const import API_OAUTH
from src.platform.const import API_PAT
from src.platform.const import API_PEERING
from src.platform.const import API_PUBLIC
from src.platform.const import API_WEB
from src.platform.const import CSRF_HEADER_NAME
from src.platform.const import NAME
from src.platform.const import VERSION
from src.platform.const import VERSION_HEADER
from src.platform.domain.value_objects.peering import CURRENT_PROTOCOL_VERSION
from src.platform.domain.value_objects.peering import VERSION_HEADER as PEERING_VERSION_HEADER
from src.platform.infrastructure.config.boot_guard import assert_safe_configuration
from src.platform.infrastructure.config.settings import cfg
from src.platform.infrastructure.logging.logger import log
from src.platform.infrastructure.redis_client import close_redis
from src.platform.infrastructure.redis_client import get_redis


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    assert_safe_configuration(cfg)
    if cfg.migrate_on_startup:
        log.info("Applying migrations (MIGRATE_ON_STARTUP).")
        await to_thread.run_sync(upgrade_to_head)
    if await ensure_system_user():
        await ensure_default_groups()
    await ensure_instance_id()
    await ensure_cookbook_resources()
    log.info("%s %s started.", NAME, VERSION)
    webhook_worker = start_webhook_worker()
    nightly = start_nightly_jobs()
    shopping = start_shopping_jobs()
    peer_channels = start_peer_channel_worker()
    yield
    for task in (peer_channels, shopping, nightly, webhook_worker):
        await stop_worker(task)
    await close_redis()
    await engine.dispose()


def build_web_router() -> APIRouter:
    web = APIRouter()
    # /users/me must come before /users/{user_id}.
    web.include_router(me_router)
    # Before the admin router, so the static /users/me/... paths come first.
    web.include_router(operations_router)
    web.include_router(cooking_router)
    web.include_router(accounts_router)
    web.include_router(admin_router)
    web.include_router(settings_router)
    web.include_router(admin_system_router)
    web.include_router(notifications_router)
    web.include_router(peers_router)
    web.include_router(files_router)
    web.include_router(resources_router)
    # Before the ingredients router, whose /nutrition/usda/{fdc_id} would
    # not match it anyway, but keeps the static path first.
    web.include_router(reference_router)
    web.include_router(reference_admin_router)
    web.include_router(catalogue_file_router)
    web.include_router(ingredients_router)
    web.include_router(equipment_router)
    web.include_router(recipe_archive_router)
    web.include_router(recipes_router)
    web.include_router(variations_router)
    web.include_router(mirrors_router)
    web.include_router(incoming_recipes_router)
    web.include_router(shopping_router)
    web.include_router(households_router)
    web.include_router(household_admin_router)
    web.include_router(resolve_router)
    web.include_router(oauth_web_router)
    return web


health_router = APIRouter(tags=["health"])


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness: the process answers."""
    return HealthResponse(status="ok")


@health_router.get("/ready", response_model=HealthResponse)
async def ready() -> JSONResponse:
    """Readiness: the database and Redis answer."""
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    try:
        await get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"
    healthy = all(v == "ok" for v in checks.values())
    body = HealthResponse(status="ok" if healthy else "degraded", checks=checks)
    return JSONResponse(body.model_dump(), status_code=200 if healthy else 503)


def create_app() -> FastAPI:
    register_cookbook_webhook_events()
    register_cookbook_hooks()
    register_cookbook_public_ids()
    register_cookbook_peering()
    register_cookbook_mirrors()
    app = FastAPI(
        title=NAME.capitalize(),
        version=VERSION,
        lifespan=lifespan,
        docs_url="/docs" if cfg.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json" if cfg.debug else None,
    )
    register_exception_handlers(app)

    app.include_router(auth_router, prefix=API_AUTH)
    app.include_router(build_web_router(), prefix=API_WEB)
    app.include_router(public_router, prefix=API_PUBLIC)
    app.include_router(public_legal_router, prefix=API_PUBLIC)
    app.include_router(public_recipes_router, prefix=API_PUBLIC)
    app.include_router(pat_router, prefix=API_PAT)
    app.include_router(key_router, prefix=API_KEY)
    # Other Cuisine instances; not part of the web app's OpenAPI snapshot.
    app.include_router(peering_router, prefix=API_PEERING, include_in_schema=False)
    app.include_router(health_router)
    # OAuth for hosted AI clients: the discovery documents at the root, as
    # RFC 8414 and RFC 9728 require, and the endpoints they call server to
    # server. Neither is part of the web app's OpenAPI snapshot.
    app.include_router(well_known_router, include_in_schema=False)
    app.include_router(oauth_router, prefix=API_OAUTH, include_in_schema=False)

    # The MCP surface for AI agents, one route for every method the
    # transport answers. Bearer tokens only, see AgentAuthMiddleware.
    app.router.routes.append(
        Route(
            API_MCP,
            create_agent_app([COOKBOOK_AGENT_CATALOG], version=VERSION),
            methods=["GET", "POST", "DELETE"],
            include_in_schema=False,
        )
    )

    @app.middleware("http")
    async def version_header(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers[VERSION_HEADER] = VERSION
        if request.url.path.startswith(API_PEERING):
            response.headers[PEERING_VERSION_HEADER] = str(CURRENT_PROTOCOL_VERSION)
        return response

    app.add_middleware(MaintenanceMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cfg.domain.rstrip("/")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", CSRF_HEADER_NAME, "X-Api-Key"],
        expose_headers=[VERSION_HEADER],
    )
    return app


app = create_app()
