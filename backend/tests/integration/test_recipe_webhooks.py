"""The cookbook's webhook events: `recipe.published` with plain-text
content, never for private recipes, and `recipe.deleted` with the id."""

from typing import Any

import httpx
import pytest

from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.test_admin_area import FakeSender
from tests.integration.test_admin_area import _webhook
from tests.integration.test_admin_area import sender  # noqa: F401


async def _deliveries(admin: httpx.AsyncClient, hook: dict[str, Any]) -> list[dict[str, Any]]:
    log = (await admin.get(f"{WEB}/admin/webhooks/{hook['id']}/deliveries")).json()
    return list(reversed(log["items"]))


@pytest.mark.usefixtures("user_choice_privacy")
async def test_publishing_and_deleting_announce_the_recipe(
    admin: httpx.AsyncClient,
    cook: httpx.AsyncClient,
    sender: FakeSender,  # noqa: F811
) -> None:
    hook = await _webhook(admin, ["recipe.published", "recipe.deleted"])
    salt = await make_ingredient(cook, "Salz")
    token = f"@[Salz](ingredient:{salt['id']})"
    recipe = await make_recipe(
        cook,
        "**Suppe**",
        [(f"Mit {token} kochen.", [{"ingredient_id": salt["id"]}])],
        translations={"de-AT": {"title": "Suppe", "description": "Mit *viel* Liebe."}},
    )
    private = await make_recipe(cook, "Geheim", [("Kochen.", [])], visibility="private")
    draft = await make_recipe(cook, "Entwurf", [("Kochen.", [])], publish=False)

    deliveries = await _deliveries(admin, hook)
    assert [d["event"] for d in deliveries] == ["recipe.published"]
    data = deliveries[0]["payload"]["data"]["recipe"]
    assert data == {
        "id": recipe["id"],
        "title": "Suppe",
        "description": "Mit viel Liebe.",
        "locale": "de-AT",
        "visibility": "instance",
    }

    for gone in (recipe, private, draft):
        deleted = await cook.delete(f"{WEB}/recipes/{gone['id']}", headers=CSRF)
        assert deleted.status_code == 204, deleted.text
    events = [(d["event"], d["payload"]["data"]["recipe"]) for d in await _deliveries(admin, hook)]
    # Drafts that were never published are not announced; a published
    # private recipe's id goes out on deletion only.
    assert events[1:] == [
        ("recipe.deleted", {"id": recipe["id"]}),
        ("recipe.deleted", {"id": private["id"]}),
    ]
