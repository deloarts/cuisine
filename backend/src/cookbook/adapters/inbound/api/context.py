"""Per-request context of the cookbook routes: the content language the
viewer reads in and the presenter built for it."""

from fastapi import Depends
from fastapi import Query

from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.domain.entities.user import User


async def get_locale(
    locale: ContentLocale | None = Query(
        None, description="The language to read in; defaults to the user's UI language."
    ),
    user: User = Depends(get_current_user),
) -> str:
    return locale.value if locale is not None else ui_locale(user.language.value)


async def get_presenter(
    c: Cookbook = Depends(get_cookbook),
    user: User = Depends(get_current_user),
    locale: str = Depends(get_locale),
) -> Presenter:
    return Presenter(c, await c.viewers.of(user), locale)
