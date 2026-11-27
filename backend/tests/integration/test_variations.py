"""Recipe variations: what is derived from them, who sees and changes them,
staleness, adopting them into the original, and the ratings and cook events
that name one."""

from datetime import date
from typing import Any

import httpx

from tests.integration.conftest import COOK_PERMISSIONS
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import grant_health_data
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id

TODAY = date.today().isoformat()


async def _ingredient(
    client: httpx.AsyncClient, name: str, markers: list[str], allergens: list[str] | None = None
) -> str:
    created = await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": name}},
            "diet_markers": markers,
            "allergens": allergens or [],
            "nutrition": {"kcal": 100},
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


async def _pancake(cook: httpx.AsyncClient) -> dict[str, Any]:
    """A recipe of three steps: milk and flour, sugar, then frying in
    butter. Milk and butter make it vegetarian but not vegan."""
    g = await unit_id(cook, "g")
    ml = await unit_id(cook, "ml")
    ids = {
        "milk": await _ingredient(cook, "Milch", ["dairy"], ["milk"]),
        "oat": await _ingredient(cook, "Haferdrink", []),
        "flour": await _ingredient(cook, "Mehl", [], ["gluten"]),
        "sugar": await _ingredient(cook, "Zucker", []),
        "honey": await _ingredient(cook, "Honig", ["honey"]),
        "butter": await _ingredient(cook, "Butter", ["dairy"], ["milk"]),
        "oil": await _ingredient(cook, "Öl", []),
        "g": g,
        "ml": ml,
    }
    recipe = await make_recipe(
        cook,
        "Palatschinken",
        [
            (
                "Milch und Mehl verrühren.",
                [
                    {"ingredient_id": ids["milk"], "amount": 250, "unit_id": ml},
                    {"ingredient_id": ids["flour"], "amount": 100, "unit_id": g},
                ],
            ),
            ("Zucker einrühren.", [{"ingredient_id": ids["sugar"], "amount": 20, "unit_id": g}]),
            (
                "In Butter backen.",
                [{"ingredient_id": ids["butter"], "amount": 20, "unit_id": g}],
            ),
        ],
    )
    return {"id": recipe["id"], **ids}


def _vegan(r: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "name": "Vegan",
        "locale": "de-AT",
        "changes": [
            {"kind": "swap", "ingredient_id": r["milk"], "to_ingredient_id": r["oat"]},
            {
                "kind": "swap",
                "step": 3,
                "ingredient_id": r["butter"],
                "to_ingredient_id": r["oil"],
                "keep_amount": False,
                "amount": 15,
                "unit_id": r["g"],
            },
        ],
        **extra,
    }


async def _vary(
    client: httpx.AsyncClient, recipe_id: str, body: dict[str, Any], status: int = 201
) -> dict[str, Any]:
    response = await client.post(f"{WEB}/recipes/{recipe_id}/variations", headers=CSRF, json=body)
    assert response.status_code == status, response.text
    result: dict[str, Any] = response.json()
    return result


async def _second_cook(make_user: MakeUser, client: httpx.AsyncClient) -> httpx.AsyncClient:
    await make_user("anna", permissions=COOK_PERMISSIONS)
    await login(client, "anna@example.com", "cook-password-1")
    return client


async def test_a_variation_derives_its_own_diets_allergens_and_lines(
    cook: httpx.AsyncClient,
) -> None:
    r = await _pancake(cook)
    original = (await cook.get(f"{WEB}/recipes/{r['id']}")).json()
    assert "vegan" not in original["diets"]
    assert "milk" in original["allergens"]
    variation = await _vary(cook, r["id"], _vegan(r))
    assert variation["is_stale"] is False
    assert variation["based_on_revision"] == variation["current_revision"] == 1
    assert [c["applies"] for c in variation["changes"]] == [True, True]
    assert variation["changes"][0]["to_ingredient_name"] == "Haferdrink"

    view = (await cook.get(f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/view")).json()
    recipe = view["recipe"]
    assert "vegan" in recipe["diets"]
    assert "milk" not in recipe["allergens"]
    assert "gluten" in recipe["allergens"]
    names = {line["name"] for line in recipe["ingredients"]}
    assert {"Haferdrink", "Öl", "Mehl", "Zucker"} <= names
    assert not {"Milch", "Butter"} & names
    oil = next(i for i in recipe["steps"][2]["ingredients"] if i["name"] == "Öl")
    assert oil["amount"] == 15
    assert recipe["nutrition"]["per_serving"]["kcal"] is not None
    markers = view["steps"]
    assert markers[0]["lines"][0]["kind"] == "swapped"
    assert markers[0]["lines"][0]["swapped_from_name"] == "Milch"
    assert markers[1]["changed"] is False
    assert markers[2]["lines"][0]["change_id"] == variation["changes"][1]["id"]
    # Scaling follows the servings asked for, also for the variation.
    doubled = (
        await cook.get(
            f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/view", params={"servings": 4}
        )
    ).json()
    assert doubled["recipe"]["steps"][2]["ingredients"][0]["amount"] == 30


async def test_added_removed_lines_text_and_extra_steps(cook: httpx.AsyncClient) -> None:
    r = await _pancake(cook)
    variation = await _vary(
        cook,
        r["id"],
        {
            "name": "Mit Honig",
            "locale": "de-AT",
            "changes": [
                {"kind": "remove_line", "step": 2, "ingredient_id": r["sugar"]},
                {"kind": "step_text", "step": 2, "text": "Honig einrühren."},
                {
                    "kind": "add_line",
                    "step": 2,
                    "ingredient_id": r["honey"],
                    "amount": 1,
                    "note": "flüssig",
                },
                {
                    "kind": "extra_step",
                    "step": 3,
                    "text": f"Mit @[Honig](ingredient:{r['honey']}) beträufeln.",
                    "lines": [{"ingredient_id": r["honey"], "amount": 10, "unit_id": r["g"]}],
                },
            ],
        },
    )
    view = (await cook.get(f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/view")).json()
    steps = view["recipe"]["steps"]
    assert len(steps) == 4
    assert steps[1]["text"] == "Honig einrühren."
    assert [i["name"] for i in steps[1]["ingredients"]] == ["Honig"]
    assert steps[1]["ingredients"][0]["note"] == "flüssig"
    assert steps[3]["position"] == 4
    markers = view["steps"]
    assert markers[1]["text_changed"] is True
    assert markers[1]["removed"][0]["name"] == "Zucker"
    assert markers[1]["lines"] == [
        {
            "index": 0,
            "kind": "added",
            "change_id": variation["changes"][2]["id"],
            "swapped_from_ingredient_id": None,
            "swapped_from_name": None,
        }
    ]
    assert markers[3]["added"] is True and markers[3]["origin_step"] is None
    assert "vegetarian" in view["recipe"]["diets"] and "vegan" not in view["recipe"]["diets"]

    # A mention in an extra step must name one of its own lines.
    bad = await _vary(
        cook,
        r["id"],
        {
            "name": "Falsch",
            "locale": "de-AT",
            "changes": [
                {"kind": "extra_step", "step": 0, "text": f"@[Milch](ingredient:{r['milk']})"}
            ],
        },
        status=422,
    )
    assert bad["code"] == "InvalidMentionError"
    unknown_step = await _vary(
        cook,
        r["id"],
        {
            "name": "x",
            "locale": "de-AT",
            "changes": [{"kind": "step_text", "step": 9, "text": "y"}],
        },
        status=422,
    )
    assert unknown_step["code"] == "InvalidVariationError"
    missing_line = await _vary(
        cook,
        r["id"],
        {
            "name": "x",
            "locale": "de-AT",
            "changes": [{"kind": "remove_line", "step": 1, "ingredient_id": r["sugar"]}],
        },
        status=422,
    )
    assert missing_line["code"] == "InvalidVariationError"


async def test_browse_flags_variations_that_fit_diets_and_guests(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    r = await _pancake(cook)
    vegan = (await cook.get(f"{WEB}/recipes", params={"diets": "vegan"})).json()
    assert vegan["total"] == 0
    await _vary(cook, r["id"], _vegan(r))
    vegan = (await cook.get(f"{WEB}/recipes", params={"diets": "vegan"})).json()
    assert vegan["total"] == 1
    item = vegan["items"][0]
    assert item["variation_fits_diets"] is True
    assert item["variation_count"] == 1
    assert "vegan" not in item["diets"]

    guest = await make_user("guest")
    await login(client, "guest@example.com", "cook-password-1")
    await grant_health_data(client)
    await client.post(
        f"{WEB}/users/me/food-restrictions", headers=CSRF, json={"kind": "diet", "diet": "vegan"}
    )
    await client.patch(
        f"{WEB}/users/me", headers=CSRF, json={"share_restrictions_with_hosts": True}
    )
    page = (
        await cook.get(
            f"{WEB}/recipes",
            params={"guests": guest["id"], "hide_unsuitable_for_guests": True},
        )
    ).json()
    assert page["total"] == 1
    assert page["items"][0]["unsuitable_for_guests"] is True
    assert page["items"][0]["variation_fits_guests"] is True


async def test_private_variations_are_their_authors_alone(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    r = await _pancake(cook)
    hidden = await _vary(cook, r["id"], _vegan(r, private=True))
    shared = await _vary(cook, r["id"], _vegan(r, name="Geteilt"))
    # The admin holds manage:recipes and still never sees a private variation.
    listed = (await admin.get(f"{WEB}/recipes/{r['id']}/variations")).json()
    assert [v["id"] for v in listed] == [shared["id"]]
    assert (
        await admin.get(f"{WEB}/recipes/{r['id']}/variations/{hidden['id']}")
    ).status_code == 404
    assert (await admin.get(f"{WEB}/recipes/{r['id']}")).json()["variation_count"] == 1
    assert (await cook.get(f"{WEB}/recipes/{r['id']}")).json()["variation_count"] == 2
    gone = await admin.delete(f"{WEB}/recipes/{r['id']}/variations/{hidden['id']}", headers=CSRF)
    assert gone.status_code == 404
    rated = await admin.put(
        f"{WEB}/recipes/{r['id']}/rating",
        headers=CSRF,
        json={"stars": 3, "variation_id": hidden["id"]},
    )
    assert rated.status_code == 404


async def test_variations_follow_the_recipe_visibility(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    await admin.put(
        f"{WEB}/settings/privacy",
        headers=CSRF,
        json={"default_recipe_visibility": "instance", "users_may_change_visibility": True},
    )
    r = await _pancake(cook)
    variation = await _vary(cook, r["id"], _vegan(r))
    edit = (await cook.get(f"{WEB}/recipes/{r['id']}/edit")).json()
    narrowed = await cook.put(
        f"{WEB}/recipes/{r['id']}",
        headers=CSRF,
        json={
            "original_locale": edit["original_locale"],
            "translations": edit["translations"],
            "steps": [
                {
                    "translations": s["translations"],
                    "ingredients": [
                        {k: i[k] for k in ("ingredient_id", "amount", "unit_id")}
                        for i in s["ingredients"]
                    ],
                }
                for s in edit["steps"]
            ],
            "visibility": "private",
        },
    )
    assert narrowed.status_code == 200, narrowed.text
    assert (await admin.get(f"{WEB}/recipes/{r['id']}/variations")).status_code == 404
    assert (
        await admin.get(f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/view")
    ).status_code == 404
    assert (await _vary(admin, r["id"], _vegan(r), status=404))["code"] == "RecipeNotFoundError"


async def test_who_may_create_change_and_delete(
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    r = await _pancake(cook)
    await make_user("reader")
    anna = await _second_cook(make_user, client)
    # In instance mode every cook may vary every recipe.
    variation = await _vary(anna, r["id"], _vegan(r))
    assert variation["can_edit"] is True and variation["can_delete"] is True
    assert variation["can_adopt"] is False
    seen_by_owner = (await cook.get(f"{WEB}/recipes/{r['id']}/variations")).json()[0]
    assert seen_by_owner["can_edit"] is False
    assert seen_by_owner["can_delete"] is False
    assert seen_by_owner["can_adopt"] is True
    url = f"{WEB}/recipes/{r['id']}/variations/{variation['id']}"
    assert (await cook.put(url, headers=CSRF, json=_vegan(r))).status_code == 403
    assert (await cook.delete(url, headers=CSRF)).status_code == 403
    renamed = await anna.put(url, headers=CSRF, json=_vegan(r, name="Neu"))
    assert renamed.json()["name"] == "Neu"
    # manage:recipes removes an abusive variation.
    await login_system(client)
    assert (await client.delete(url, headers=CSRF)).status_code == 204
    assert (await cook.get(url)).status_code == 404

    # Without write:recipes nobody adds a variation.
    await login(client, "reader@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/recipes/{r['id']}/variations")).status_code == 200
    await _vary(client, r["id"], _vegan(r), status=403)


async def test_staleness_shows_the_old_step_text(cook: httpx.AsyncClient) -> None:
    r = await _pancake(cook)
    variation = await _vary(
        cook,
        r["id"],
        {
            "name": "Anders",
            "locale": "de-AT",
            "changes": [
                {"kind": "step_text", "step": 2, "text": "Weniger Zucker einrühren."},
                {"kind": "step_text", "step": 3, "text": "In Öl backen."},
            ],
        },
    )
    edit = (await cook.get(f"{WEB}/recipes/{r['id']}/edit")).json()
    steps = [
        {
            "translations": s["translations"],
            "ingredients": [
                {k: i[k] for k in ("ingredient_id", "amount", "unit_id")} for i in s["ingredients"]
            ],
        }
        for s in edit["steps"]
    ]
    steps[1]["translations"] = {"de-AT": {"text": "Den Zucker gut einrühren."}}
    saved = await cook.put(
        f"{WEB}/recipes/{r['id']}",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": edit["translations"],
            "steps": steps[:2],
        },
    )
    assert saved.status_code == 200, saved.text
    fresh = (await cook.get(f"{WEB}/recipes/{r['id']}/variations/{variation['id']}")).json()
    assert fresh["is_stale"] is True
    assert fresh["based_on_revision"] == 1 and fresh["current_revision"] == 2
    assert fresh["stale_steps"] == [
        {
            "step": 2,
            "state": "changed",
            "old_text": "Zucker einrühren.",
            "current_text": "Den Zucker gut einrühren.",
        },
        {"step": 3, "state": "deleted", "old_text": "In Butter backen.", "current_text": None},
    ]
    # The change to the deleted step stays visible but no longer applies.
    assert [c["applies"] for c in fresh["changes"]] == [True, False]
    view = (await cook.get(f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/view")).json()
    assert len(view["recipe"]["steps"]) == 2


async def test_adopting_writes_a_credited_revision(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    r = await _pancake(cook)
    anna = await _second_cook(make_user, client)
    variation = await _vary(
        anna,
        r["id"],
        {
            "name": "Mit Honig",
            "locale": "de-AT",
            "changes": [
                {"kind": "extra_step", "step": 1, "text": "Teig rasten lassen."},
                {
                    "kind": "swap",
                    "step": 2,
                    "ingredient_id": r["sugar"],
                    "to_ingredient_id": r["honey"],
                },
                {"kind": "step_text", "step": 3, "text": "In Öl backen."},
            ],
        },
    )
    url = f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/adopt"
    assert (await anna.post(url, headers=CSRF, json={})).status_code == 403
    first, second, third = (c["id"] for c in variation["changes"])
    adopted = await cook.post(url, headers=CSRF, json={"change_ids": [first, second]})
    assert adopted.status_code == 200, adopted.text
    body = adopted.json()
    steps = body["recipe"]["steps"]
    assert len(steps) == 4
    assert steps[1]["translations"]["de-AT"]["text"] == "Teig rasten lassen."
    assert steps[2]["ingredients"][0]["ingredient_name"] == "Honig"
    remaining = body["variation"]
    assert [c["id"] for c in remaining["changes"]] == [third]
    # The original's step 3 is step 4 now.
    assert remaining["changes"][0]["step"] == 4
    assert remaining["is_stale"] is False
    assert remaining["based_on_revision"] == remaining["current_revision"] == 2
    view = (await cook.get(f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/view")).json()
    assert view["recipe"]["steps"][3]["text"] == "In Öl backen."

    history = (await cook.get(f"{WEB}/recipes/{r['id']}/revisions")).json()["items"]
    assert history[0]["kind"] == "adopted"
    assert history[0]["note"] == "Mit Honig"
    assert history[0]["credited_author"]["display_name"] == "Anna"
    assert history[0]["author"]["display_name"] == "Cook"


async def test_ratings_and_cook_events_name_a_variation(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    r = await _pancake(cook)
    variation = await _vary(cook, r["id"], _vegan(r))
    anna = await _second_cook(make_user, client)
    rate = f"{WEB}/recipes/{r['id']}/rating"
    own = await anna.put(rate, headers=CSRF, json={"stars": 2})
    assert own.json()["rating_count"] == 1
    on_variation = await anna.put(
        rate, headers=CSRF, json={"stars": 5, "variation_id": variation["id"]}
    )
    assert on_variation.json() == {
        "stars": 5,
        "comment": "",
        "rating_average": 5.0,
        "rating_count": 1,
    }
    # One rating per user and variation: a second one replaces the first.
    again = await anna.put(rate, headers=CSRF, json={"stars": 4, "variation_id": variation["id"]})
    assert again.json()["rating_count"] == 1
    detail = (await anna.get(f"{WEB}/recipes/{r['id']}")).json()
    assert (detail["rating_average"], detail["rating_count"]) == (2.0, 1)
    assert (detail["rating_overall_average"], detail["rating_overall_count"]) == (3.0, 2)
    assert detail["own_rating"]["stars"] == 2
    listed = (await anna.get(f"{WEB}/recipes/{r['id']}/variations")).json()[0]
    assert (listed["rating_average"], listed["rating_count"]) == (4.0, 1)
    assert listed["own_rating"]["stars"] == 4
    view = (await anna.get(f"{WEB}/recipes/{r['id']}/variations/{variation['id']}/view")).json()
    assert view["recipe"]["rating_average"] == 4.0
    assert view["recipe"]["own_rating"]["stars"] == 4
    removed = await anna.delete(rate, headers=CSRF, params={"variation_id": variation["id"]})
    assert removed.json() == {"rating_average": None, "rating_count": 0}

    event = await anna.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={
            "recipe_id": r["id"],
            "variation_id": variation["id"],
            "cooked_on": TODAY,
            "servings": 2,
        },
    )
    assert event.status_code == 201, event.text
    assert event.json()["variation"] == {"id": variation["id"], "name": "Vegan"}


async def test_deleting_the_recipe_deletes_its_variations(cook: httpx.AsyncClient) -> None:
    r = await _pancake(cook)
    variation = await _vary(cook, r["id"], _vegan(r))
    assert (await cook.delete(f"{WEB}/recipes/{r['id']}", headers=CSRF)).status_code == 204
    exported = (await cook.get(f"{WEB}/users/me/export")).json()
    assert exported["variations"] == []
    assert variation["id"]


async def test_download_my_data_lists_own_variations(cook: httpx.AsyncClient) -> None:
    r = await _pancake(cook)
    variation = await _vary(cook, r["id"], _vegan(r, private=True))
    exported = (await cook.get(f"{WEB}/users/me/export")).json()
    assert [v["id"] for v in exported["variations"]] == [variation["id"]]
    assert exported["variations"][0]["recipe"]["title"] == "Palatschinken"
    assert exported["variations"][0]["private"] is True
    assert exported["variations"][0]["changes"][0]["kind"] == "swap"
