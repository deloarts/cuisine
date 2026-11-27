"""The MCP surface: authentication, the tool list, recipe drafts, budgets
and the agent call log."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB

MCP = "/api/v1/mcp"
_ACCEPT = {"Accept": "application/json, text/event-stream"}
EXPIRES = (datetime.now(UTC) + timedelta(days=7)).isoformat()


async def _token(client: httpx.AsyncClient, permissions: list[str]) -> str:
    # Agent tokens need the AI agents consent.
    await client.put(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)
    created = await client.post(
        f"{WEB}/users/me/personal-access-tokens",
        headers=CSRF,
        json={"name": "agent", "permissions": permissions, "expires_at": EXPIRES},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["token"])


async def rpc(
    client: httpx.AsyncClient, token: str | None, method: str, params: dict[str, Any] | None = None
) -> httpx.Response:
    headers = dict(_ACCEPT)
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    body: dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    return await client.post(MCP, json=body, headers=headers)


async def call(
    client: httpx.AsyncClient, token: str, tool: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    response = await rpc(client, token, "tools/call", {"name": tool, "arguments": arguments})
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()["result"]
    return result


async def _cook_token(
    make_user: MakeUser, client: httpx.AsyncClient, extra: list[str] | None = None
) -> str:
    permissions = ["write:recipes", "write:ingredients", "use:mcp", "write:pat"]
    await make_user("chef", permissions=permissions)
    await login(client, "chef@example.com", "cook-password-1")
    return await _token(client, extra or ["use:mcp", "write:recipes", "write:ingredients"])


async def test_missing_or_wrong_token_is_refused(client: httpx.AsyncClient) -> None:
    missing = await rpc(client, None, "tools/list")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"].startswith("Bearer")
    assert (await rpc(client, "cuisine_pat_nope", "tools/list")).status_code == 401


async def test_token_needs_use_mcp(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    await make_user("chef", permissions=["write:recipes", "write:pat"])
    await login(client, "chef@example.com", "cook-password-1")
    token = await _token(client, ["write:recipes"])
    assert (await rpc(client, token, "tools/list")).status_code == 403


async def test_tool_list_follows_the_tokens_permissions(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _cook_token(make_user, client, ["use:mcp"])
    listed = await rpc(client, token, "tools/list")
    names = {t["name"] for t in listed.json()["result"]["tools"]}
    assert "search_recipes" in names
    assert "create_recipe_draft" not in names


async def test_agent_creates_a_draft_with_new_ingredients(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _cook_token(make_user, client)
    result = await call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "Kaiserschmarrn",
            "base_servings": 2,
            "tags": ["Dessert"],
            "steps": [
                {
                    "text": "Eier trennen und Teig rühren",
                    "ingredients": [
                        {"name": "Ei", "amount": 4, "unit": "piece"},
                        {"name": "Mehl", "amount": 150, "unit": "g"},
                    ],
                },
                {"text": "Mit Staubzucker servieren", "ingredients": [{"name": "Staubzucker"}]},
            ],
            "idempotency_key": "kaiserschmarrn-1",
        },
    )
    assert result["isError"] is False, result
    created = result["structuredContent"]
    assert created["status"] == "draft"
    assert len(created["created_ingredients"]) == 3

    draft = (await client.get(f"{WEB}/recipes/{created['id']}")).json()
    assert draft["status"] == "draft"
    assert draft["created_via"] == "mcp"
    assert [t["name"] for t in draft["tags"]] == ["Dessert"]
    ingredients = (await client.get(f"{WEB}/ingredients", params={"status": "draft"})).json()
    assert ingredients["total"] == 3

    replay = await call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "x",
            "steps": [{"text": "y"}],
            "idempotency_key": "kaiserschmarrn-1",
        },
    )
    assert replay["structuredContent"]["replayed"] is True
    assert (await client.get(f"{WEB}/recipes", params={"status": "drafts"})).json()["total"] == 1

    calls = (await client.get(f"{WEB}/users/me/agent-calls")).json()
    assert calls["total"] == 2
    assert calls["items"][-1]["created_refs"][0].startswith("recipe:")


async def test_agent_errors_are_results_not_protocol_errors(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _cook_token(make_user, client)
    bad = await call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "x",
            "steps": [{"text": "y", "ingredients": [{"name": "Ei", "unit": "bucket"}]}],
        },
    )
    assert bad["isError"] is True
    assert "unit" in bad["content"][0]["text"]
    unknown = await call(client, token, "no_such_tool", {})
    assert unknown["isError"] is True


async def test_agents_only_change_drafts(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _cook_token(make_user, client)
    created = (
        await call(
            client,
            token,
            "create_recipe_draft",
            {"original_locale": "de-AT", "title": "Suppe", "steps": [{"text": "Kochen"}]},
        )
    )["structuredContent"]
    await client.post(f"{WEB}/recipes/{created['id']}/publish", headers=CSRF)
    refused = await call(
        client,
        token,
        "add_recipe_translation",
        {"recipe_id": created["id"], "locale": "en-GB", "title": "Soup", "steps": ["Cook"]},
    )
    assert refused["isError"] is True


async def test_draft_budget(
    make_user: MakeUser, client: httpx.AsyncClient, admin: httpx.AsyncClient, resources: None
) -> None:
    await admin.put(
        f"{WEB}/settings/agents",
        headers=CSRF,
        json={
            "enabled": True,
            "calls_per_minute": 100,
            "drafts_per_hour": 1,
            "token_max_lifetime_days": 30,
        },
    )
    token = await _cook_token(make_user, client)
    args = {"original_locale": "de-AT", "title": "Suppe", "steps": [{"text": "Kochen"}]}
    assert (await call(client, token, "create_recipe_draft", args))["isError"] is False
    second = await call(client, token, "create_recipe_draft", args)
    assert second["isError"] is True
    assert "drafts" in second["content"][0]["text"]


async def test_agent_tokens_have_a_shorter_lifetime(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await make_user("chef", permissions=["use:mcp", "write:pat"])
    await login(client, "chef@example.com", "cook-password-1")
    await client.put(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)
    too_long = await client.post(
        f"{WEB}/users/me/personal-access-tokens",
        headers=CSRF,
        json={
            "name": "agent",
            "permissions": ["use:mcp"],
            "expires_at": (datetime.now(UTC) + timedelta(days=90)).isoformat(),
        },
    )
    assert too_long.status_code == 422


async def test_agent_access_can_be_switched_off(
    make_user: MakeUser, client: httpx.AsyncClient, admin: httpx.AsyncClient, resources: None
) -> None:
    await admin.put(
        f"{WEB}/settings/agents",
        headers=CSRF,
        json={
            "enabled": False,
            "calls_per_minute": 100,
            "drafts_per_hour": 10,
            "token_max_lifetime_days": 30,
        },
    )
    token = await _cook_token(make_user, client)
    assert (await rpc(client, token, "tools/list")).status_code == 403
