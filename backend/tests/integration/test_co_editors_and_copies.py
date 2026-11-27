"""Public mode as the default, co-editors, "Copy as my recipe", and what
happens to a deleted account's variations."""

from typing import Any

import httpx
import pytest

from tests.integration.conftest import COOK_PERMISSIONS
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id


async def _recipe(cook: httpx.AsyncClient, title: str = "Gulasch", **extra: Any) -> dict[str, Any]:
    beef = await make_ingredient(cook, f"Rind {title}")
    g = await unit_id(cook, "g")
    return await make_recipe(
        cook,
        title,
        [("Anbraten.", [{"ingredient_id": beef["id"], "amount": 500, "unit_id": g}])],
        **extra,
    )


def _body(edit: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "original_locale": edit["original_locale"],
        "translations": edit["translations"],
        "base_servings": edit["base_servings"],
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
        **extra,
    }


async def _anna(make_user: MakeUser, client: httpx.AsyncClient) -> dict[str, Any]:
    anna = await make_user("anna", permissions=COOK_PERMISSIONS)
    await login(client, "anna@example.com", "cook-password-1")
    return anna


async def test_a_fresh_instance_runs_in_peers_mode(cook: httpx.AsyncClient) -> None:
    privacy = (await cook.get(f"{WEB}/settings/privacy")).json()
    assert privacy == {
        "default_recipe_visibility": "peers",
        "users_may_change_visibility": False,
        "allow_public_recipes": False,
        "index_public_recipes": False,
    }
    recipe = await _recipe(cook, visibility="private")
    assert recipe["visibility"] == "peers"
    assert recipe["can_change_visibility"] is False


async def test_co_editors_edit_content_only(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _recipe(cook)
    anna = await _anna(make_user, client)
    rid = recipe["id"]
    # Before being added, anna may not edit.
    edit = (await cook.get(f"{WEB}/recipes/{rid}/edit")).json()
    assert (
        await client.put(f"{WEB}/recipes/{rid}", headers=CSRF, json=_body(edit))
    ).status_code == 403
    assert edit["can_manage_co_editors"] is True and edit["co_editors"] == []

    added = await cook.put(
        f"{WEB}/recipes/{rid}/co-editors", headers=CSRF, json={"user_ids": [anna["id"]]}
    )
    assert added.status_code == 200, added.text
    assert [p["display_name"] for p in added.json()] == ["Anna"]

    mine = (await client.get(f"{WEB}/recipes/{rid}/edit")).json()
    assert mine["can_edit"] is True
    assert mine["can_delete"] is False
    assert mine["can_manage_co_editors"] is False
    body = _body(mine, revision_note="mehr Paprika")
    body["steps"][0]["translations"] = {"de-AT": {"text": "Scharf anbraten."}}
    saved = await client.put(f"{WEB}/recipes/{rid}", headers=CSRF, json=body)
    assert saved.status_code == 200, saved.text
    history = (await client.get(f"{WEB}/recipes/{rid}/revisions")).json()["items"]
    assert history[0]["author"]["display_name"] == "Anna"
    detail = (await client.get(f"{WEB}/recipes/{rid}")).json()
    assert detail["can_edit"] is True and detail["can_delete"] is False

    # Not the deletion, the status or the co-editors.
    assert (await client.delete(f"{WEB}/recipes/{rid}", headers=CSRF)).status_code == 403
    assert (await client.post(f"{WEB}/recipes/{rid}/unpublish", headers=CSRF)).status_code == 403
    again = await client.put(f"{WEB}/recipes/{rid}/co-editors", headers=CSRF, json={"user_ids": []})
    assert again.status_code == 403
    listed = (await client.get(f"{WEB}/recipes/{rid}/co-editors")).json()
    assert [p["id"] for p in listed] == [anna["id"]]


@pytest.mark.usefixtures("user_choice_privacy")
async def test_co_editors_must_see_the_recipe_and_never_change_its_visibility(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    hidden = await _recipe(cook, "Geheim", visibility="private")
    anna = await _anna(make_user, client)
    refused = await cook.put(
        f"{WEB}/recipes/{hidden['id']}/co-editors", headers=CSRF, json={"user_ids": [anna["id"]]}
    )
    assert refused.status_code == 422
    assert refused.json()["code"] == "CoEditorError"
    me = (await cook.get(f"{WEB}/users/me")).json()
    owner = await cook.put(
        f"{WEB}/recipes/{hidden['id']}/co-editors", headers=CSRF, json={"user_ids": [me["id"]]}
    )
    assert owner.status_code == 422

    shared = await _recipe(cook, "Geteilt", visibility="shared", shared_user_ids=[anna["id"]])
    added = await cook.put(
        f"{WEB}/recipes/{shared['id']}/co-editors", headers=CSRF, json={"user_ids": [anna["id"]]}
    )
    assert added.status_code == 200, added.text
    edit = (await client.get(f"{WEB}/recipes/{shared['id']}/edit")).json()
    assert edit["can_change_visibility"] is False
    saved = await client.put(
        f"{WEB}/recipes/{shared['id']}", headers=CSRF, json=_body(edit, visibility="instance")
    )
    assert saved.json()["visibility"] == "shared"


async def test_copy_as_my_recipe(
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    original = await _recipe(cook)
    await _anna(make_user, client)
    copied = await client.post(f"{WEB}/recipes/{original['id']}/copy", headers=CSRF)
    assert copied.status_code == 201, copied.text
    copy = copied.json()
    assert copy["status"] == "draft"
    assert copy["owner"]["display_name"] == "Anna"
    assert copy["based_on"]["recipe"]["id"] == original["id"]
    assert copy["based_on"]["owner"]["display_name"] == "Cook"
    assert copy["steps"][0]["ingredients"][0]["amount"] == 500
    # A draft copy is its owner's alone, so the original counts no copy yet.
    assert (await cook.get(f"{WEB}/recipes/{original['id']}")).json()["based_on_count"] == 0
    published = await client.post(f"{WEB}/recipes/{copy['id']}/publish", headers=CSRF)
    assert published.status_code == 200
    detail = (await cook.get(f"{WEB}/recipes/{original['id']}")).json()
    assert detail["based_on_count"] == 1
    copies = (await cook.get(f"{WEB}/recipes/{original['id']}/copies")).json()
    assert [(c["recipe"]["id"], c["owner"]["display_name"]) for c in copies] == [
        (copy["id"], "Anna")
    ]
    # The copy is independent: changing it leaves the original alone.
    edit = (await client.get(f"{WEB}/recipes/{copy['id']}/edit")).json()
    body = _body(edit)
    body["steps"][0]["ingredients"][0]["amount"] = 900
    await client.put(f"{WEB}/recipes/{copy['id']}", headers=CSRF, json=body)
    unchanged = (await cook.get(f"{WEB}/recipes/{original['id']}")).json()
    assert unchanged["steps"][0]["ingredients"][0]["amount"] == 500
    # Deleting the original clears the link.
    assert (await cook.delete(f"{WEB}/recipes/{original['id']}", headers=CSRF)).status_code == 204
    assert (await client.get(f"{WEB}/recipes/{copy['id']}")).json()["based_on"] is None

    await login_system(client)
    await make_user("reader")
    await login(client, "reader@example.com", "cook-password-1")
    refused = await client.post(f"{WEB}/recipes/{copy['id']}/copy", headers=CSRF)
    assert refused.status_code == 403


async def _variation(client: httpx.AsyncClient, recipe_id: str, **extra: Any) -> str:
    response = await client.post(
        f"{WEB}/recipes/{recipe_id}/variations",
        headers=CSRF,
        json={
            "name": "Mild",
            "locale": "de-AT",
            "changes": [{"kind": "step_text", "step": 1, "text": "Sanft anbraten."}],
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_self_deletion_keeps_shared_variations_of_public_recipes(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _recipe(cook)
    await _anna(make_user, client)
    shared = await _variation(client, recipe["id"])
    hidden = await _variation(client, recipe["id"], private=True)
    deleted = await client.request(
        "DELETE",
        f"{WEB}/users/me",
        headers=CSRF,
        json={"email": "anna@example.com", "password": "cook-password-1"},
    )
    assert deleted.status_code == 204, deleted.text
    listed = (await cook.get(f"{WEB}/recipes/{recipe['id']}/variations")).json()
    assert [(v["id"], v["author"]) for v in listed] == [(shared, None)]
    assert hidden not in {v["id"] for v in listed}


async def test_admin_deletion_keeps_shared_variations_of_public_recipes(
    admin: httpx.AsyncClient,
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    other_client: httpx.AsyncClient,
) -> None:
    recipe = await _recipe(cook)
    anna = await make_user("anna", permissions=COOK_PERMISSIONS)
    await login(other_client, "anna@example.com", "cook-password-1")
    kept = await _variation(other_client, recipe["id"])
    gone = await admin.delete(f"{WEB}/users/{anna['id']}", headers=CSRF)
    assert gone.status_code == 204, gone.text
    await login(other_client, "cook@example.com", "cook-password-1")
    listed = (await other_client.get(f"{WEB}/recipes/{recipe['id']}/variations")).json()
    assert [(v["id"], v["author"]) for v in listed] == [(kept, None)]
