"""The anonymous public recipe pages: what a visitor who never signed in can
read, and above all what it cannot. Every test reads through the `visitor`
client, which holds no cookie."""

from io import BytesIO
from typing import Any

import httpx
import pytest
from PIL import Image

from src.platform import const
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.domain.entities.settings import PrivacySettings
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import unit_id

PUBLIC = "/api/v1/public/recipes"
# Keys that belong to the signed-in pages or the personal layer and must
# never appear in an anonymous response, at any depth.
FORBIDDEN_KEYS = {
    "owner",
    "owner_id",
    "username",
    "email",
    "visibility",
    "effective_visibility",
    "status",
    "rating_average",
    "rating_count",
    "rating_overall_average",
    "rating_overall_count",
    "own_rating",
    "own_note",
    "is_favourite",
    "has_warning",
    "warnings",
    "unsuitable_for_guests",
    "last_cooked",
    "last_cooked_by_me",
    "can_edit",
    "can_delete",
    "missing_equipment",
    "kitchen_ready",
    "variation_count",
    "based_on",
    "based_on_count",
    "ingredient_id",
    "line_id",
    "category_id",
    "missing_ingredient_ids",
    "created_via",
    "co_editor_ids",
    "shared_user_ids",
    "shared_group_ids",
}


async def _privacy(*, allow: bool, index: bool = False) -> None:
    """Writes the privacy settings straight to the database, so no privacy
    statement version is published and nobody has to acknowledge one."""
    async with SessionLocal() as db:
        await SqlAlchemySettingsRepository(db).save_privacy(
            PrivacySettings(
                default_recipe_visibility="instance",
                users_may_change_visibility=True,
                allow_public_recipes=allow,
                index_public_recipes=index,
            )
        )
        await db.commit()


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _png(size: int = 900) -> bytes:
    out = BytesIO()
    Image.new("RGB", (size, size), (200, 120, 40)).save(out, format="PNG")
    return out.getvalue()


async def _upload(client: httpx.AsyncClient, name: str = "oma-lasagne.png") -> str:
    uploaded = await client.post(
        f"{WEB}/files", headers=CSRF, files={"file": (name, _png(), "image/png")}
    )
    assert uploaded.status_code == 201, uploaded.text
    return str(uploaded.json()["id"])


async def _simple(cook: httpx.AsyncClient, title: str, **extra: Any) -> dict[str, Any]:
    salt = await make_ingredient(cook, f"Salz {title}", english=f"Salt {title}")
    return await make_recipe(cook, title, [("Würzen", [{"ingredient_id": salt["id"]}])], **extra)


@pytest.fixture
async def cook_id(cook: httpx.AsyncClient) -> str:
    return str((await cook.get(f"{WEB}/users/me")).json()["id"])


@pytest.mark.usefixtures("user_choice_privacy")
async def test_only_published_public_recipes_are_listed_and_readable(
    cook: httpx.AsyncClient, visitor: httpx.AsyncClient, cook_id: str
) -> None:
    await _privacy(allow=True)
    public = await _simple(cook, "Offen", visibility="public")
    hidden = [
        await _simple(cook, "Privat", visibility="private"),
        await _simple(cook, "Haushalt", visibility="household"),
        await _simple(cook, "Geteilt", visibility="shared", shared_user_ids=[cook_id]),
        await _simple(cook, "Instanz", visibility="instance"),
        await _simple(cook, "Entwurf", visibility="public", publish=False),
    ]

    page = await visitor.get(PUBLIC)
    assert page.status_code == 200, page.text
    assert [r["id"] for r in page.json()["items"]] == [public["id"]]
    assert page.json()["total"] == 1
    assert page.headers["x-robots-tag"] == "noindex"
    assert "set-cookie" not in page.headers

    assert (await visitor.get(f"{PUBLIC}/{public['id']}")).status_code == 200
    titles = ["Privat", "Haushalt", "Geteilt", "Instanz", "Entwurf"]
    for recipe, title in zip(hidden, titles, strict=True):
        response = await visitor.get(f"{PUBLIC}/{recipe['id']}")
        assert response.status_code == 404, recipe
        assert response.json()["code"] == "RecipeNotFoundError"
        found = await visitor.get(PUBLIC, params={"search": title})
        assert found.json()["items"] == []
    assert (await visitor.get(f"{PUBLIC}/not-an-id")).status_code == 404

    # Narrowing a public recipe takes it off the public pages at once.
    edit = (await cook.get(f"{WEB}/recipes/{public['id']}/edit")).json()
    unpublished = await cook.post(f"{WEB}/recipes/{public['id']}/unpublish", headers=CSRF)
    assert unpublished.status_code == 200, unpublished.text
    assert edit["id"] == public["id"]
    assert (await visitor.get(f"{PUBLIC}/{public['id']}")).status_code == 404
    assert (await visitor.get(PUBLIC)).json()["items"] == []


@pytest.mark.usefixtures("user_choice_privacy")
async def test_nothing_is_public_while_public_recipes_are_not_allowed(
    cook: httpx.AsyncClient, visitor: httpx.AsyncClient
) -> None:
    await _privacy(allow=True)
    image = await _upload(cook)
    recipe = await _simple(cook, "Offen", visibility="public", cover_image_id=image)
    assert (await visitor.get(f"{PUBLIC}/{recipe['id']}/images/{image}")).status_code == 200

    await _privacy(allow=False)
    assert (await visitor.get(PUBLIC)).json() == {"items": [], "total": 0}
    assert (await visitor.get(f"{PUBLIC}/tags")).json() == []
    assert (await visitor.get(f"{PUBLIC}/{recipe['id']}")).status_code == 404
    assert (await visitor.get(f"{PUBLIC}/{recipe['id']}/images/{image}")).status_code == 404
    # The stored value stays, and signed-in users still read it.
    assert (await cook.get(f"{WEB}/recipes/{recipe['id']}")).status_code == 200

    await _privacy(allow=True)
    assert (await visitor.get(f"{PUBLIC}/{recipe['id']}")).status_code == 200


@pytest.mark.usefixtures("user_choice_privacy")
async def test_the_page_holds_nothing_personal_and_no_internal_ids(
    cook: httpx.AsyncClient,
    visitor: httpx.AsyncClient,
    admin: httpx.AsyncClient,
) -> None:
    await _privacy(allow=True)
    grams = await unit_id(cook, "g")
    flour = await make_ingredient(cook, "Mehl", kcal=350, allergens=["gluten"], english="Flour")
    recipe = await make_recipe(
        cook,
        "Brot",
        [
            (
                f"Das @[Mehl](ingredient:{flour['id']}) sieben",
                [{"ingredient_id": flour["id"], "amount": 500, "unit_id": grams}],
            )
        ],
        visibility="public",
    )
    # Personal records of a signed-in user on the recipe.
    for call in (
        cook.put(f"{WEB}/recipes/{recipe['id']}/favourite", headers=CSRF, json={"favourite": True}),
        cook.put(f"{WEB}/recipes/{recipe['id']}/rating", headers=CSRF, json={"stars": 5}),
        cook.put(f"{WEB}/recipes/{recipe['id']}/note", headers=CSRF, json={"text": "Geheim"}),
    ):
        response = await call
        assert response.status_code in (200, 204), response.text

    detail = await visitor.get(
        f"{PUBLIC}/{recipe['id']}", params={"servings": 4, "locale": "de-AT"}
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert not (_keys(body) & FORBIDDEN_KEYS), _keys(body) & FORBIDDEN_KEYS
    raw = detail.text
    assert flour["id"] not in raw
    assert grams not in raw
    assert "Geheim" not in raw
    assert "cook@example.com" not in raw
    assert body["author"] is None
    assert body["servings"] == 4
    assert body["ingredients"][0]["amount"] == 1000
    assert body["ingredients"][0]["unit"]["abbreviation"] == "g"
    assert body["steps"][0]["ingredients"][0]["amount"] == 1000
    assert body["allergens"] == ["gluten"]
    assert body["nutrition"]["total"]["kcal"] == pytest.approx(3500)
    assert body["steps"][0]["text"] == (
        "Das @[Mehl](ingredient:00000000-0000-0000-0000-000000000000) sieben"
    )
    assert "id" not in body["steps"][0]

    listed = (await visitor.get(PUBLIC)).json()
    assert not (_keys(listed) & FORBIDDEN_KEYS)
    assert listed["items"][0]["author"] is None

    # The author shows only by display name, and only by choice.
    shown = await cook.patch(
        f"{WEB}/users/me", headers=CSRF, json={"show_name_on_public_recipes": True}
    )
    assert shown.status_code == 200, shown.text
    detail = (await visitor.get(f"{PUBLIC}/{recipe['id']}")).json()
    assert detail["author"] == "Cook"
    assert "cook" not in {v for v in _string_values(detail) if v != "Cook"}
    assert (await visitor.get(PUBLIC)).json()["items"][0]["author"] == "Cook"
    assert admin is not None


def _string_values(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {s for v in value.values() for s in _string_values(v)}
    if isinstance(value, list):
        return {s for v in value for s in _string_values(v)}
    return {value} if isinstance(value, str) else set()


@pytest.mark.usefixtures("user_choice_privacy")
async def test_hidden_sub_recipes_and_their_mentions_keep_no_title_or_id(
    cook: httpx.AsyncClient, visitor: httpx.AsyncClient
) -> None:
    await _privacy(allow=True)
    hidden = await _simple(cook, "Geheime Sauce", visibility="instance")
    shown = await _simple(cook, "Offener Teig", visibility="public")
    draft = await _simple(cook, "Entwurfsfüllung", visibility="public", publish=False)
    parent = await make_recipe(
        cook,
        "Lasagne",
        [
            (
                f"Die @[Geheime Sauce](recipe:{hidden['id']}) mit dem "
                f"@[Offener Teig](recipe:{shown['id']}) und der "
                f"@[Entwurfsfüllung](recipe:{draft['id']}) schichten",
                [
                    {"sub_recipe_id": hidden["id"]},
                    {"sub_recipe_id": shown["id"]},
                    {"sub_recipe_id": draft["id"]},
                ],
            )
        ],
        visibility="public",
        # A stray mention outside the steps must not name the recipe either.
        translations={
            "de-AT": {
                "title": "Lasagne",
                "description": f"Mit @[Geheime Sauce](recipe:{hidden['id']})",
                "tips": f"Statt @[Geheime Sauce](recipe:{hidden['id']}) geht auch Pesto",
            }
        },
    )
    response = await visitor.get(f"{PUBLIC}/{parent['id']}")
    assert response.status_code == 200, response.text
    raw = response.text
    for secret in (hidden["id"], "Geheime Sauce", draft["id"], "Entwurfsfüllung"):
        assert secret not in raw, secret
    body = response.json()
    assert body["steps"][0]["text"] == (
        "Die @[?](recipe:00000000-0000-0000-0000-000000000000) mit dem "
        f"@[Offener Teig](recipe:{shown['id']}) und der "
        "@[?](recipe:00000000-0000-0000-0000-000000000000) schichten"
    )
    lines = body["steps"][0]["ingredients"]
    assert [line["sub_recipe"]["accessible"] for line in lines] == [False, True, False]
    assert lines[0]["sub_recipe"] == {
        "id": None,
        "title": None,
        "accessible": False,
        "cover_image_id": None,
    }
    assert lines[0]["name"] == ""
    assert lines[1]["sub_recipe"]["title"] == "Offener Teig"
    needs = {(n["sub_recipe"]["title"], n["sub_recipe"]["accessible"]) for n in body["needs"]}
    assert needs == {(None, False), ("Offener Teig", True)}


@pytest.mark.usefixtures("user_choice_privacy")
async def test_images_come_in_display_size_and_only_from_public_recipes(
    cook: httpx.AsyncClient, visitor: httpx.AsyncClient
) -> None:
    await _privacy(allow=True)
    cover = await _upload(cook)
    step_image = await _upload(cook)
    secret_image = await _upload(cook)
    loose_image = await _upload(cook)
    salt = await make_ingredient(cook, "Salz")
    public = await make_recipe(
        cook,
        "Offen",
        [("Würzen", [{"ingredient_id": salt["id"]}])],
        visibility="public",
        cover_image_id=cover,
    )
    edit = (await cook.get(f"{WEB}/recipes/{public['id']}/edit")).json()
    assert edit["cover_image_id"] == cover
    private = await _simple(cook, "Privat", visibility="private", cover_image_id=secret_image)
    payload = recipe_payload(
        "Mit Schrittbild", [("Schritt", [{"ingredient_id": salt["id"]}])], visibility="public"
    )
    payload["steps"][0]["image_id"] = step_image
    created = await cook.post(f"{WEB}/recipes", headers=CSRF, json=payload)
    assert created.status_code == 201, created.text
    stepped = created.json()
    published = await cook.post(f"{WEB}/recipes/{stepped['id']}/publish", headers=CSRF)
    assert published.status_code == 200, published.text

    served = await visitor.get(f"{PUBLIC}/{public['id']}/images/{cover}")
    assert served.status_code == 200, served.text
    assert served.headers["content-type"] == "image/webp"
    assert served.headers["content-disposition"].startswith("inline")
    assert "oma-lasagne" not in served.headers["content-disposition"]
    assert served.headers["x-content-type-options"] == "nosniff"
    assert served.headers["cache-control"].startswith("private")
    assert "set-cookie" not in served.headers
    with Image.open(BytesIO(served.content)) as image:
        assert max(image.size) <= const.THUMBNAIL_MAX_EDGE
    thumbnail = await cook.get(f"{WEB}/files/{cover}/content", params={"variant": "thumbnail"})
    original = await cook.get(f"{WEB}/files/{cover}/content")
    assert served.content == thumbnail.content
    assert served.content != original.content
    cached = await visitor.get(
        f"{PUBLIC}/{public['id']}/images/{cover}",
        headers={"If-None-Match": served.headers["etag"]},
    )
    assert cached.status_code == 304
    # There is no way to ask for the original.
    asked = await visitor.get(
        f"{PUBLIC}/{public['id']}/images/{cover}", params={"variant": "original"}
    )
    assert asked.content == thumbnail.content

    detail = (await visitor.get(f"{PUBLIC}/{stepped['id']}")).json()
    assert detail["steps"][0]["image_id"] == step_image
    step_served = await visitor.get(f"{PUBLIC}/{stepped['id']}/images/{step_image}")
    assert step_served.status_code == 200

    refused = [
        f"{PUBLIC}/{private['id']}/images/{secret_image}",
        f"{PUBLIC}/{public['id']}/images/{secret_image}",
        f"{PUBLIC}/{public['id']}/images/{loose_image}",
        f"{PUBLIC}/{public['id']}/images/{step_image}",
        f"{PUBLIC}/{stepped['id']}/images/{cover}",
        f"{PUBLIC}/{public['id']}/images/not-an-id",
    ]
    for url in refused:
        response = await visitor.get(url)
        assert response.status_code == 404, url
        assert response.json()["code"] == "StoredFileNotFoundError"
    # The web file routes still need a session.
    assert (await visitor.get(f"{WEB}/files/{cover}/content")).status_code == 401


@pytest.mark.usefixtures("user_choice_privacy")
async def test_search_tags_and_diet_filters(
    cook: httpx.AsyncClient, visitor: httpx.AsyncClient
) -> None:
    await _privacy(allow=True)
    tags = (await cook.get(f"{WEB}/tags", params={"locale": "en-GB"})).json()
    tag = tags[0]
    other_tag = tags[1]
    await _simple(cook, "Kürbissuppe", visibility="public", tag_ids=[tag["id"]])
    await _simple(cook, "Apfelstrudel", visibility="public")
    await _simple(cook, "Geheimsuppe", visibility="instance", tag_ids=[other_tag["id"]])

    found = (await visitor.get(PUBLIC, params={"search": "suppe"})).json()
    assert [r["title"] for r in found["items"]] == ["Kürbissuppe"]
    tagged = (await visitor.get(PUBLIC, params={"tag_id": tag["id"]})).json()
    assert [r["title"] for r in tagged["items"]] == ["Kürbissuppe"]
    assert (await visitor.get(PUBLIC, params={"tag_id": "nope"})).json()["items"] == []
    offered = (await visitor.get(f"{PUBLIC}/tags", params={"locale": "en-GB"})).json()
    assert [t["id"] for t in offered] == [tag["id"]]
    vegan = (await visitor.get(PUBLIC, params={"diets": "vegan"})).json()
    assert vegan["total"] == 2
    # Personal filters of the signed-in list do not exist here.
    personal = await visitor.get(PUBLIC, params={"favourites": "true", "mine": "true"})
    assert personal.json()["total"] == 2


@pytest.mark.usefixtures("user_choice_privacy")
async def test_the_anonymous_surface_is_rate_limited(
    cook: httpx.AsyncClient, visitor: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _privacy(allow=True)
    monkeypatch.setattr(const, "ANONYMOUS_REQUEST_LIMIT", 3)
    for _ in range(3):
        assert (await visitor.get(PUBLIC)).status_code == 200
    limited = await visitor.get(f"{PUBLIC}/tags")
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1
    # Signed-in pages and the public info have their own limits.
    assert (await visitor.get("/api/v1/public/info")).status_code == 200
    assert (await cook.get(f"{WEB}/recipes")).status_code == 200


async def test_public_info_reports_the_switches_and_robots_follows_them(
    visitor: httpx.AsyncClient,
) -> None:
    info = (await visitor.get("/api/v1/public/info")).json()
    assert (info["allow_public_recipes"], info["index_public_recipes"]) == (False, False)
    robots = await visitor.get("/api/v1/public/robots.txt")
    assert robots.status_code == 200
    assert robots.headers["content-type"].startswith("text/plain")
    assert robots.text == "User-agent: *\nDisallow: /\n"

    # Indexing alone means nothing while public recipes are not allowed.
    await _privacy(allow=False, index=True)
    info = (await visitor.get("/api/v1/public/info")).json()
    assert info["index_public_recipes"] is False
    assert (await visitor.get("/api/v1/public/robots.txt")).text == "User-agent: *\nDisallow: /\n"

    await _privacy(allow=True)
    info = (await visitor.get("/api/v1/public/info")).json()
    assert (info["allow_public_recipes"], info["index_public_recipes"]) == (True, False)
    assert (await visitor.get("/api/v1/public/robots.txt")).text.endswith("Disallow: /\n")
    assert "Allow: /public/" not in (await visitor.get("/api/v1/public/robots.txt")).text

    await _privacy(allow=True, index=True)
    info = (await visitor.get("/api/v1/public/info")).json()
    assert info["index_public_recipes"] is True
    text = (await visitor.get("/api/v1/public/robots.txt")).text
    assert "Allow: /public/\n" in text
    assert "Allow: /api/v1/public/\n" in text
    assert text.endswith("Disallow: /\n")


async def test_the_indexing_switch_alone_publishes_no_new_privacy_statement(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    published = await admin.post(
        f"{WEB}/admin/legal/privacy",
        headers=CSRF,
        json={"texts": {"en-GB": "# Privacy\n\n{{ privacy_mode }}"}},
    )
    assert published.status_code == 201, published.text
    await make_user("reader")
    await login(other_client, "reader@example.com", "cook-password-1")
    me = (await other_client.get(f"{WEB}/users/me")).json()
    acknowledged = await other_client.post(
        f"{WEB}/users/me/privacy/acknowledge",
        headers=CSRF,
        json={"version": me["privacy_version"]},
    )
    assert acknowledged.status_code in (200, 204), acknowledged.text

    current = (await admin.get(f"{WEB}/settings/privacy")).json()
    saved = await admin.put(
        f"{WEB}/settings/privacy", headers=CSRF, json=current | {"index_public_recipes": True}
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["index_public_recipes"] is True
    me = (await other_client.get(f"{WEB}/users/me")).json()
    assert me["privacy_acknowledgement_pending"] is False

    saved = await admin.put(
        f"{WEB}/settings/privacy", headers=CSRF, json=current | {"allow_public_recipes": True}
    )
    assert saved.status_code == 200, saved.text
    me = (await other_client.get(f"{WEB}/users/me")).json()
    assert me["privacy_acknowledgement_pending"] is True


async def test_legal_pages_are_readable_without_signing_in(visitor: httpx.AsyncClient) -> None:
    for kind in ("imprint", "privacy"):
        response = await visitor.get(f"/api/v1/public/legal/{kind}")
        # Unpublished pages answer 404, but never 401.
        assert response.status_code in (200, 404)


async def test_the_resolver_stays_signed_in_only(visitor: httpx.AsyncClient) -> None:
    response = await visitor.get(f"{WEB}/resolve/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401
