"""
/api/v1/public/recipes: the public recipe pages, read without signing in.

A separate router set rather than optional authentication on the web
routes: nothing here reads a session, sets a cookie or touches the personal
layer. What a visitor sees is decided by the anonymous `Viewer` in
`ReadPublicRecipes` (published recipes that are public in effect, nothing
while public recipes are not allowed). Every route is rate limited per
client address and answers `X-Robots-Tag: noindex`, since the JSON and the
images are never meant to be indexed by themselves. Images come only in
display size (the thumbnail), never as the original bytes.
"""

from dataclasses import replace
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import Query
from fastapi import Response
from fastapi import status
from fastapi.responses import RedirectResponse

from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_read_public_recipes
from src.cookbook.adapters.inbound.api.public_presenter import PublicPresenter
from src.cookbook.adapters.inbound.api.public_presenter import public_tag
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import (
    PublicRecipeDetailResponse,
)
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import (
    PublicRecipeSummaryResponse,
)
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicTag
from src.cookbook.application.use_cases.recipes.read_public_recipes import ReadPublicRecipes
from src.cookbook.domain.services.recipe_rules import MAX_SERVINGS
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import Difficulty
from src.platform.adapters.inbound.api.deps import get_manage_files
from src.platform.adapters.inbound.api.download_headers import build_download_headers
from src.platform.adapters.inbound.api.download_headers import etag_matches
from src.platform.adapters.inbound.api.rate_limit import limit_anonymous_requests
from src.platform.adapters.inbound.api.schemas.base import Page
from src.platform.application.use_cases.files.manage_files import ManageFiles

# Browsers may keep an image a few minutes; shared caches may not, so an
# image stops being served soon after its recipe stops being public.
_IMAGE_CACHE = "private, max-age=300, must-revalidate"
# The name a public image is served under, never the uploader's file name.
_IMAGE_NAME = "image.webp"


async def _noindex(response: Response) -> None:
    response.headers["X-Robots-Tag"] = "noindex"


router = APIRouter(
    prefix="/recipes",
    tags=["public-recipes"],
    dependencies=[Depends(limit_anonymous_requests), Depends(_noindex)],
)


async def get_public_locale(
    locale: ContentLocale | None = Query(
        None, description="The language to read in; defaults to the instance's language."
    ),
    c: Cookbook = Depends(get_cookbook),
) -> str:
    if locale is not None:
        return locale.value
    general = await c.platform.settings.get_general()
    return ui_locale(general.default_language.value)


async def get_public_presenter(
    c: Cookbook = Depends(get_cookbook),
    locale: str = Depends(get_public_locale),
    use_case: ReadPublicRecipes = Depends(get_read_public_recipes),
) -> PublicPresenter:
    return PublicPresenter(c, await use_case.viewer(), locale)


@router.get("", response_model=Page[PublicRecipeSummaryResponse])
async def list_public_recipes(
    search: str | None = Query(None, max_length=128),
    tag_id: list[str] = Query(default_factory=list, max_length=20),
    diets: list[Diet] = Query(
        default_factory=list, description="Only recipes that fit every one of these diets."
    ),
    max_minutes: int | None = Query(None, ge=1),
    difficulty: Difficulty | None = Query(None),
    sort: Literal["newest", "title"] = Query("newest"),
    limit: int = Query(24, ge=1, le=48),
    offset: int = Query(0, ge=0, le=10_000),
    c: Cookbook = Depends(get_cookbook),
    presenter: PublicPresenter = Depends(get_public_presenter),
    use_case: ReadPublicRecipes = Depends(get_read_public_recipes),
) -> Page[PublicRecipeSummaryResponse]:
    """The public recipes, newest first or by title, with text search and
    the filters that need no personal data."""
    tag_ids: list[int] = []
    for public_id in tag_id:
        tag = await c.tags.get_by_public_id(public_id)
        # An unknown tag matches nothing rather than everything.
        tag_ids.append(tag.id if tag else -1)
    summaries, total, lookups = await use_case.list(
        search=search,
        tag_ids=tag_ids,
        diets=diets,
        max_total_minutes=max_minutes,
        difficulty=difficulty,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return Page(items=await presenter.summaries(summaries, lookups), total=total)


@router.get("/tags", response_model=list[PublicTag])
async def list_public_recipe_tags(
    locale: str = Depends(get_public_locale),
    use_case: ReadPublicRecipes = Depends(get_read_public_recipes),
) -> list[PublicTag]:
    """The tags the public recipes carry, for the tag filter."""
    return [public_tag(t, locale) for t in await use_case.tags()]


@router.get("/{recipe_id}", response_model=PublicRecipeDetailResponse)
async def read_public_recipe(
    recipe_id: str,
    servings: int | None = Query(None, ge=1, le=MAX_SERVINGS),
    presenter: PublicPresenter = Depends(get_public_presenter),
    use_case: ReadPublicRecipes = Depends(get_read_public_recipes),
) -> PublicRecipeDetailResponse:
    """One public recipe with what is derived from it, scaled to `servings`.
    Anything that is not a public recipe answers 404 like an unknown id."""
    return await presenter.detail(await use_case.view(recipe_id, servings=servings))


@router.get(
    "/{recipe_id}/images/{image_id}",
    response_class=Response,
    responses={200: {"content": {"image/webp": {}}}, 304: {}, 307: {}, 404: {}},
)
async def read_public_recipe_image(
    recipe_id: str,
    image_id: str,
    if_none_match: str | None = Header(default=None),
    use_case: ReadPublicRecipes = Depends(get_read_public_recipes),
    files: ManageFiles = Depends(get_manage_files),
) -> Response:
    """An image of a public recipe (its cover or a step image) in display
    size, inline. The original is never served here, and a file that is not
    an image of a recipe the visitor may see answers 404."""
    await use_case.assert_image(recipe_id, image_id)
    return await _public_thumbnail(image_id, if_none_match, files)


@router.get(
    "/{recipe_id}/author-avatar",
    response_class=Response,
    responses={200: {"content": {"image/webp": {}}}, 304: {}, 307: {}, 404: {}},
)
async def read_public_recipe_author_avatar(
    recipe_id: str,
    if_none_match: str | None = Header(default=None),
    use_case: ReadPublicRecipes = Depends(get_read_public_recipes),
    files: ManageFiles = Depends(get_manage_files),
) -> Response:
    """The avatar of a public recipe's author in display size, only while
    the author shows their name on public recipes (`author_avatar` on the
    recipe); 404 otherwise, like an unknown recipe."""
    return await _public_thumbnail(await use_case.author_avatar(recipe_id), if_none_match, files)


async def _public_thumbnail(
    image_id: str, if_none_match: str | None, files: ManageFiles
) -> Response:
    """Serves the thumbnail of a file the caller checked, under a neutral
    name and with the short, private cache of the public pages."""
    stored = await files.get(image_id)
    etag = files.etag_of(stored, thumbnail=True)
    headers = build_download_headers(
        _IMAGE_NAME, content_type=stored.content_type, etag=etag, disposition="inline"
    )
    headers["Cache-Control"] = _IMAGE_CACHE
    headers["X-Robots-Tag"] = "noindex"
    if etag_matches(if_none_match, etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    # The presigned URL repeats the file name, so it gets the neutral one.
    presigned = await files.content_url(
        replace(stored, file_name=_IMAGE_NAME), thumbnail=True, inline=True
    )
    if presigned is not None:
        return RedirectResponse(
            presigned.url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"},
        )
    content = await files.content(image_id, thumbnail=True)
    return Response(content=content.data, media_type=content.content_type, headers=headers)
