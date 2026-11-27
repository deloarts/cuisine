"""An ingredient that takes a family's name joins that family, the amount
style a user reads recipes in, search order, and what agents read: the
user's language by default, notes and draft ingredients in a recipe, and
the first answer again when a draft call is repeated. Also how agents name
draft ingredients in every language."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient

MCP = "/api/v1/mcp"
ACCEPT = {"Accept": "application/json, text/event-stream"}


async def _family(admin: httpx.AsyncClient, de: str) -> dict[str, Any]:
    created = await admin.post(
        f"{WEB}/ingredient-families",
        headers=CSRF,
        json={"translations": {"de-AT": {"name": de}}},
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


async def _create(client: httpx.AsyncClient, name: str, **extra: Any) -> httpx.Response:
    return await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": name}},
            **extra,
        },
    )


async def test_an_ingredient_named_like_a_family_joins_it(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    vinegar = await _family(admin, "Essig")
    created = await _create(cook, "Essig")
    assert created.status_code == 201, created.text
    assert created.json()["family"]["id"] == vinegar["id"]


async def test_a_family_name_in_another_family_names_the_family(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    await _family(admin, "Öl")
    other = await _family(admin, "Fett")
    clash = await _create(cook, "Öl", family_id=other["id"])
    assert clash.status_code == 409
    body = clash.json()
    assert body["existing_kind"] == "family"
    assert "family" in body["detail"]


async def test_search_answers_exact_names_first(cook: httpx.AsyncClient) -> None:
    for name in ("Hirschhornsalz", "Kräutersalz", "Salz"):
        await make_ingredient(cook, name)
    found = (await cook.get(f"{WEB}/ingredients", params={"search": "Salz"})).json()["items"]
    assert next(i["name"] for i in found) == "Salz"


async def test_the_amount_style_is_a_preference_of_the_user(cook: httpx.AsyncClient) -> None:
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert me["amount_style"] == "decimals"
    saved = await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"amount_style": "fractions"})
    assert saved.status_code == 200, saved.text
    assert (await cook.get(f"{WEB}/users/me")).json()["amount_style"] == "fractions"


async def _agent(make_user: MakeUser, client: httpx.AsyncClient) -> str:
    permissions = ["write:recipes", "write:ingredients", "use:mcp", "write:pat"]
    await make_user("chef", permissions=permissions, language="deAT")
    await login(client, "chef@example.com", "cook-password-1")
    await client.put(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)
    created = await client.post(
        f"{WEB}/users/me/personal-access-tokens",
        headers=CSRF,
        json={
            "name": "agent",
            "permissions": ["use:mcp", "write:recipes", "write:ingredients"],
            "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["token"])


async def _call(
    client: httpx.AsyncClient, token: str, tool: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    response = await client.post(
        MCP,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
        headers={**ACCEPT, "Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()["result"]
    assert result["isError"] is False, result
    structured: dict[str, Any] = result["structuredContent"]
    return structured


DRAFT = {
    "original_locale": "de-AT",
    "title": "Apfelrotkraut",
    "steps": [{"text": "Kraut dünsten."}],
    "ingredients": [
        {"name": "Rotkraut", "amount": 1, "note": "fein geschnitten"},
        {"name": "Fett", "amount": 80, "unit": "g"},
    ],
    "idempotency_key": "rotkraut-1",
}


async def test_an_agent_reads_notes_and_draft_ingredients_in_its_language(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    await make_ingredient(client, "Rotkraut", english="red cabbage")
    created = await _call(client, token, "create_recipe_draft", DRAFT)

    recipe = await _call(client, token, "get_recipe", {"recipe_id": created["id"]})
    assert recipe["locale"] == "de-AT"
    lines = {line["name"]: line for line in recipe["ingredients"]}
    # The user reads German, so the catalogue names come in German too.
    assert set(lines) == {"Rotkraut", "Fett"}
    assert lines["Rotkraut"]["note"] == "fein geschnitten"
    # "Fett" became a draft ingredient, so the recipe claims no diet yet.
    assert recipe["diets"] == []
    (fat,) = created["created_ingredients"]
    assert recipe["unconfirmed_ingredient_ids"] == [fat["id"]]


async def test_a_repeated_draft_call_answers_as_the_first_one(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    first = await _call(client, token, "create_recipe_draft", DRAFT)
    again = await _call(client, token, "create_recipe_draft", DRAFT)
    assert again["replayed"] is True
    assert {k: v for k, v in again.items() if k != "replayed"} == first


async def test_an_agent_mentions_step_lines_by_name_and_gets_hints(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    onion = await make_ingredient(client, "Zwiebel")
    created = await _call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "Zwiebelschmalz",
            "steps": [
                {
                    "text": "@[Zwiebeln](ingredient) in @[Schmalz](ingredient) rösten.",
                    "ingredients": [
                        {"ingredient_id": onion["id"], "amount": 2},
                        {"name": "Schmalz", "amount": 100, "unit": "g"},
                    ],
                },
                {"text": "Salzen.", "ingredients": [{"name": "Salz"}]},
            ],
        },
    )
    (schmalz,) = [i for i in created["created_ingredients"] if i["name"] == "Schmalz"]
    edit = (await client.get(f"{WEB}/recipes/{created['id']}/edit")).json()
    text = edit["steps"][0]["translations"]["de-AT"]["text"]
    assert text == (
        f"@[Zwiebeln](ingredient:{onion['id']}) in @[Schmalz](ingredient:{schmalz['id']}) rösten."
    )
    hints = " ".join(created["hints"])
    # Step 2 names salt without a mention, and the new ingredients have no markers.
    assert "step 2" in hints
    assert "Schmalz" in hints


async def test_a_named_mention_off_its_step_is_a_correctable_error(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    response = await client.post(
        MCP,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_recipe_draft",
                "arguments": {
                    "original_locale": "de-AT",
                    "title": "Butterbrot",
                    "steps": [{"text": "@[Butter](ingredient) aufstreichen."}],
                },
            },
        },
        headers={**ACCEPT, "Authorization": f"Bearer {token}"},
    )
    result = response.json()["result"]
    assert result["isError"] is True
    assert "Step 1" in result["content"][0]["text"]


async def test_a_recipe_with_only_an_overall_list_gets_a_hint(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    created = await _call(
        client,
        token,
        "create_recipe_draft",
        {**DRAFT, "idempotency_key": None, "title": "Rotkraut ohne Schritte"},
    )
    assert any("No step lists" in hint for hint in created["hints"])


async def test_an_agent_is_asked_for_every_language_and_may_mention_by_name(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    onion = await make_ingredient(client, "Zwiebel", english="onion")
    created = await _call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "Röstzwiebeln",
            "steps": [
                {
                    "text": "@[Zwiebeln](ingredient) rösten.",
                    "ingredients": [{"ingredient_id": onion["id"], "amount": 2}],
                }
            ],
        },
    )
    assert any("en-GB" in hint for hint in created["hints"])
    translated = await _call(
        client,
        token,
        "add_recipe_translation",
        {
            "recipe_id": created["id"],
            "locale": "en-GB",
            "title": "Fried onions",
            "steps": ["Fry the @[onions](ingredient)."],
        },
    )
    assert translated["locales"] == ["de-AT", "en-GB"]
    assert translated["hints"] == []
    edit = (await client.get(f"{WEB}/recipes/{created['id']}/edit")).json()
    text = edit["steps"][0]["translations"]["en-GB"]["text"]
    assert text == f"Fry the @[onions](ingredient:{onion['id']})."


async def _refused(
    client: httpx.AsyncClient, token: str, tool: str, arguments: dict[str, Any]
) -> str:
    response = await client.post(
        MCP,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
        headers={**ACCEPT, "Authorization": f"Bearer {token}"},
    )
    result = response.json()["result"]
    assert result["isError"] is True, result
    return str(result["content"][0]["text"])


async def test_an_agent_names_a_draft_ingredient_in_every_language(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    created = await _call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "Schmalzbrot",
            "steps": [{"text": "Streichen.", "ingredients": [{"name": "Schmalz", "amount": 30}]}],
        },
    )
    (schmalz,) = created["created_ingredients"]
    assert any(
        "add_ingredient_translation" in hint and schmalz["id"] in hint for hint in created["hints"]
    )
    translated = await _call(
        client,
        token,
        "add_ingredient_translation",
        {
            "ingredient_id": schmalz["id"],
            "locale": "en-GB",
            "name": "lard",
            "aliases": ["pork fat"],
        },
    )
    assert translated["locales"] == ["de-AT", "en-GB"]
    assert translated["hints"] == []
    found = await _call(
        client, token, "search_ingredients", {"query": "pork fat", "locale": "en-GB"}
    )
    assert [i["id"] for i in found["ingredients"]] == [schmalz["id"]]


async def test_an_agent_leaves_catalogue_ingredients_and_taken_names_alone(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _agent(make_user, client)
    onion = await make_ingredient(client, "Zwiebel", english="onion")
    refused = await _refused(
        client,
        token,
        "add_ingredient_translation",
        {"ingredient_id": onion["id"], "locale": "en-GB", "name": "shallot"},
    )
    assert "draft" in refused
    made = await _call(
        client,
        token,
        "create_ingredient",
        {"original_locale": "de-AT", "names": {"de-AT": {"name": "Schalotte"}}},
    )
    assert any("en-GB" in hint for hint in made["hints"])
    taken = await _refused(
        client,
        token,
        "add_ingredient_translation",
        {"ingredient_id": made["id"], "locale": "en-GB", "name": "onion"},
    )
    assert "already the name" in taken
