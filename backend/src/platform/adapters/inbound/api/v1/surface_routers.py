"""
The small surfaces: the public info the login page reads, the robots.txt
and the web app manifest of the instance, the personal access token surface (/api/v1/pat) and the
API key surface (/api/v1/key). The cookbook's anonymous recipe routes are
mounted on the public surface too (`public_recipes_router.py`).
"""

import hashlib
import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import Query
from fastapi import Response
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from fastapi.responses import RedirectResponse

from src.platform.adapters.inbound.api.auth_deps import get_api_key_user
from src.platform.adapters.inbound.api.auth_deps import get_pat_user
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_manage_files
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.adapters.inbound.api.download_headers import etag_matches
from src.platform.adapters.inbound.api.download_headers import file_download_response
from src.platform.adapters.inbound.api.schemas.misc_schema import VersionResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import FeatureSettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import PublicBannerResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import PublicInfoResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import PublicMaintenanceResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import WebAppIconResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import WebAppManifestResponse
from src.platform.adapters.inbound.api.schemas.user_schema import UserSummaryResponse
from src.platform.application.use_cases.files.manage_files import ManageFiles
from src.platform.const import VERSION
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import StoredFileNotFoundError
from src.platform.domain.services.banner_rules import banner_is_active
from src.platform.domain.services.banner_rules import banner_message
from src.platform.domain.services.legal_rules import privacy_mode_of
from src.platform.domain.services.maintenance_rules import maintenance_message
from src.shared_kernel.domain.services.clock import now_utc

public_router = APIRouter(tags=["public"])
pat_router = APIRouter(tags=["pat"])
key_router = APIRouter(tags=["key"])


@public_router.get("/info", response_model=PublicInfoResponse)
async def public_info(
    locale: str = Query("en-GB", pattern="^(en-GB|de-AT)$"),
    p: Platform = Depends(get_platform),
) -> PublicInfoResponse:
    general = await p.settings.get_general()
    maintenance = await p.settings.get_maintenance()
    features = await p.settings.get_features()
    privacy = await p.settings.get_privacy()
    mode = privacy_mode_of(privacy, peering=features.peering)
    return PublicInfoResponse(
        instance_name=general.instance_name,
        default_language=general.default_language,
        version=VERSION,
        accent_color=general.accent_color,
        login_background_key=(
            hashlib.sha256(general.login_background_file_id.encode()).hexdigest()[:12]
            if general.login_background_file_id
            else None
        ),
        login_steam=general.login_steam,
        unit_system=general.unit_system,
        date_format=general.date_format,
        time_format=general.time_format,
        first_day_of_week=general.first_day_of_week,
        maintenance=PublicMaintenanceResponse(
            enabled=maintenance.enabled,
            message=maintenance_message(maintenance, locale) if maintenance.enabled else None,
            since=maintenance.since,
        ),
        features=FeatureSettingsSchema(
            agents=features.agents,
            webhooks=features.webhooks,
            households=features.households,
            dinner_guests=features.dinner_guests,
            usda=features.usda,
            peering=features.peering,
        ),
        privacy_mode=mode.mode.value,
        default_recipe_visibility=mode.default_visibility,
        imprint_published=await p.legal.current(LegalKind.IMPRINT) is not None,
        privacy_statement_published=await p.legal.current(LegalKind.PRIVACY) is not None,
        allow_public_recipes=privacy.allow_public_recipes,
        index_public_recipes=privacy.indexing_allowed,
    )


# Crawlers may fetch the public recipe pages, the script and styles that
# render them and the anonymous API they read, and nothing else.
_ROBOTS_INDEX = (
    "User-agent: *\nAllow: /public/\nAllow: /assets/\nAllow: /api/v1/public/\nDisallow: /\n"
)
_ROBOTS_NONE = "User-agent: *\nDisallow: /\n"


@public_router.get(
    "/robots.txt",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {}}}},
)
async def public_robots(p: Platform = Depends(get_platform)) -> PlainTextResponse:
    """The robots.txt of the instance, which the frontend serves at
    /robots.txt: everything closed, unless the administrator lets search
    engines index the public recipes while they are allowed."""
    privacy = await p.settings.get_privacy()
    body = _ROBOTS_INDEX if privacy.indexing_allowed else _ROBOTS_NONE
    return PlainTextResponse(body, headers={"Cache-Control": "public, max-age=300"})


# The frontend's default accent (the 500 shade of its "cuisine" palette),
# which also paints the icons, for an instance without its own accent.
_DEFAULT_THEME_COLOR = "#c2410c"
_MANIFEST_ICONS = (
    WebAppIconResponse(src="/icons/icon-192.png", sizes="192x192", type="image/png", purpose="any"),
    WebAppIconResponse(src="/icons/icon-512.png", sizes="512x512", type="image/png", purpose="any"),
    WebAppIconResponse(
        src="/icons/icon-maskable-512.png", sizes="512x512", type="image/png", purpose="maskable"
    ),
)


class _ManifestJSONResponse(JSONResponse):
    media_type = "application/manifest+json"


@public_router.get(
    "/manifest.webmanifest",
    response_model=WebAppManifestResponse,
    response_class=_ManifestJSONResponse,
)
async def public_manifest(p: Platform = Depends(get_platform)) -> _ManifestJSONResponse:
    """The web app manifest, so the instance installs under its own name, in
    its default language and with its accent colour. index.html links it
    here, below /api, so it needs no route of its own in front of the app.
    Browsers fetch it without credentials, so it must stay public."""
    general = await p.settings.get_general()
    language = general.default_language.value
    manifest = WebAppManifestResponse(
        id="/",
        name=general.instance_name,
        short_name=general.instance_name,
        lang=f"{language[:2]}-{language[2:]}",
        dir="ltr",
        start_url="/",
        scope="/",
        display="standalone",
        theme_color=general.accent_color or _DEFAULT_THEME_COLOR,
        background_color="#ffffff",
        icons=list(_MANIFEST_ICONS),
    )
    return _ManifestJSONResponse(
        manifest.model_dump(), headers={"Cache-Control": "public, max-age=300"}
    )


@public_router.get("/banner", response_model=PublicBannerResponse | None)
async def public_banner(
    locale: str = Query("en-GB", pattern="^(en-GB|de-AT)$"),
    p: Platform = Depends(get_platform),
) -> PublicBannerResponse | None:
    """The active banner, or null. Public, since the login page shows it."""
    banner = await p.settings.get_banner()
    if not banner_is_active(banner, now_utc()):
        return None
    message = banner_message(banner, locale)
    served = next((k for k, v in banner.messages.items() if v.strip() == message), locale)
    fingerprint = json.dumps(
        [banner.severity.value, sorted(banner.messages.items()), str(banner.starts_at)]
    )
    return PublicBannerResponse(
        severity=banner.severity,
        message=message,
        locale=served,
        dismissible=banner.dismissible,
        ends_at=banner.ends_at,
        key=hashlib.sha256(fingerprint.encode()).hexdigest()[:16],
    )


_BRANDING_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {"content": {"image/webp": {}}},
    304: {},
    307: {},
    404: {},
}


@public_router.get(
    "/branding/login-background", response_class=Response, responses=_BRANDING_RESPONSES
)
async def public_login_background(
    if_none_match: str | None = Header(default=None),
    p: Platform = Depends(get_platform),
    files: ManageFiles = Depends(get_manage_files),
) -> Response:
    """The background photo of the sign-in screens, without a session, since
    nobody is signed in there. Only the file the general settings name is
    served here."""
    general = await p.settings.get_general()
    if general.login_background_file_id is None:
        raise StoredFileNotFoundError("No login background is set.")
    return await _branding_image(general.login_background_file_id, if_none_match, files)


async def _branding_image(
    public_id: str, if_none_match: str | None, files: ManageFiles
) -> Response:
    """Serves a branding image in full size, answering a matching ETag with
    304 and redirecting to the storage provider when it hands out links."""
    stored = await files.get(public_id)
    etag = files.etag_of(stored, thumbnail=False)
    if etag_matches(if_none_match, etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    presigned = await files.content_url(stored, thumbnail=False, inline=True)
    if presigned is not None:
        return RedirectResponse(presigned.url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    content = await files.content(public_id, thumbnail=False)
    return file_download_response(
        content.data,
        content.file_name,
        content_type=content.content_type,
        etag=content.etag,
        disposition="inline",
    )


@pat_router.get("/version", response_model=VersionResponse)
async def pat_version(_user: User = Depends(get_pat_user)) -> VersionResponse:
    return VersionResponse(version=VERSION)


@pat_router.get("/users/me", response_model=UserSummaryResponse)
async def pat_me(user: User = Depends(get_pat_user)) -> UserSummaryResponse:
    return UserSummaryResponse(id=user.public_id, display_name=user.display_name)


@key_router.get("/whoami", response_model=UserSummaryResponse)
async def key_whoami(user: User = Depends(get_api_key_user)) -> UserSummaryResponse:
    return UserSummaryResponse(id=user.public_id, display_name=user.display_name)
