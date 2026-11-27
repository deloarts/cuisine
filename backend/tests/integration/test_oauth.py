"""OAuth for hosted AI clients: discovery, client registration, the consent
page's calls, the token endpoint with PKCE and refresh rotation, the MCP
surface with an OAuth access token, and every way a connection ends."""

import base64
import hashlib
import secrets
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.test_mcp import rpc

OAUTH = "/api/v1/oauth"
REDIRECT = "https://chatgpt.com/connector_platform_oauth_redirect"
AGENT_PERMISSIONS = ["use:mcp", "write:recipes", "write:ingredients"]


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _query(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


async def _register(client: httpx.AsyncClient, **extra: Any) -> dict[str, Any]:
    body = {"redirect_uris": [REDIRECT], "client_name": "ChatGPT"}
    body.update({"token_endpoint_auth_method": "none", **extra})
    response = await client.post(f"{OAUTH}/register", json=body)
    assert response.status_code == 201, response.text
    registered: dict[str, Any] = response.json()
    return registered


def _authorize_query(client_id: str, challenge: str, **extra: str) -> dict[str, str]:
    return {
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "xyz",
        **extra,
    }


async def _approve(
    client: httpx.AsyncClient,
    client_id: str,
    challenge: str,
    permissions: list[str] | None = None,
) -> str:
    query = _authorize_query(client_id, challenge)
    decided = await client.post(
        f"{WEB}/oauth/authorize/decision",
        headers=CSRF,
        json={"request": query, "approve": True, "permissions": permissions or AGENT_PERMISSIONS},
    )
    assert decided.status_code == 200, decided.text
    params = _query(decided.json()["redirect_to"])
    assert params["state"] == "xyz"
    return params["code"]


async def _exchange(
    client: httpx.AsyncClient, client_id: str, code: str, verifier: str, **extra: str
) -> httpx.Response:
    return await client.post(
        f"{OAUTH}/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            **extra,
        },
    )


async def _refresh(client: httpx.AsyncClient, client_id: str, refresh: str) -> httpx.Response:
    return await client.post(
        f"{OAUTH}/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh, "client_id": client_id},
    )


async def _chef(make_user: MakeUser, client: httpx.AsyncClient) -> None:
    await make_user("chef", permissions=AGENT_PERMISSIONS)
    await login(client, "chef@example.com", "cook-password-1")
    await client.put(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)


async def _connect(
    make_user: MakeUser, client: httpx.AsyncClient, permissions: list[str] | None = None
) -> tuple[str, dict[str, Any]]:
    """Registers a public client, approves it as the chef and redeems the
    code. Returns the client id and the token response."""
    await _chef(make_user, client)
    client_id = (await _register(client))["client_id"]
    verifier, challenge = _pkce()
    code = await _approve(client, client_id, challenge, permissions)
    response = await _exchange(client, client_id, code, verifier)
    assert response.status_code == 200, response.text
    return client_id, response.json()


async def _tool_names(client: httpx.AsyncClient, token: str) -> set[str]:
    listed = await rpc(client, token, "tools/list")
    assert listed.status_code == 200, listed.text
    return {t["name"] for t in listed.json()["result"]["tools"]}


# ── Discovery ────────────────────────────────────────────────────────


async def test_discovery_documents_and_the_mcp_challenge(client: httpx.AsyncClient) -> None:
    resource = await client.get("/.well-known/oauth-protected-resource/api/v1/mcp")
    assert resource.status_code == 200
    assert resource.json()["resource"] == "http://localhost:5173/api/v1/mcp"
    assert resource.json()["authorization_servers"] == ["http://localhost:5173"]
    assert (await client.get("/.well-known/oauth-protected-resource")).status_code == 200

    server = (await client.get("/.well-known/oauth-authorization-server")).json()
    assert server["issuer"] == "http://localhost:5173"
    assert server["authorization_endpoint"] == "http://localhost:5173/oauth/authorize"
    assert server["token_endpoint"] == "http://localhost:5173/api/v1/oauth/token"
    assert server["code_challenge_methods_supported"] == ["S256"]

    refused = await rpc(client, None, "tools/list")
    assert refused.status_code == 401
    challenge = refused.headers["www-authenticate"]
    assert 'resource_metadata="http://localhost:5173/.well-known/oauth-protected-resource' in (
        challenge
    )
    expired = await rpc(client, "cuisine_oat_nope", "tools/list")
    assert expired.status_code == 401
    assert 'error="invalid_token"' in expired.headers["www-authenticate"]


# ── The happy path ───────────────────────────────────────────────────


async def test_an_approved_app_reaches_the_mcp_surface(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    await _chef(make_user, client)
    client_id = (await _register(client))["client_id"]
    _verifier, challenge = _pkce()
    prompt = await client.post(
        f"{WEB}/oauth/authorize/inspect",
        headers=CSRF,
        json=_authorize_query(client_id, challenge, scope="use:mcp write:recipes"),
    )
    assert prompt.status_code == 200, prompt.text
    body = prompt.json()
    assert body["client_name"] == "ChatGPT"
    assert body["redirect_host"] == "chatgpt.com"
    assert body["offered"] == AGENT_PERMISSIONS
    assert body["requested"] == ["use:mcp", "write:recipes"]
    assert body["error_redirect"] is None

    _client_id, tokens = await _connect_again(client, client_id)
    assert tokens["token_type"] == "Bearer"
    assert tokens["access_token"].startswith("cuisine_oat_")
    assert tokens["refresh_token"].startswith("cuisine_ort_")
    assert 0 < tokens["expires_in"] <= 3600
    assert tokens["scope"] == "use:mcp write:recipes write:ingredients"

    names = await _tool_names(client, tokens["access_token"])
    assert {"search_recipes", "create_recipe_draft"} <= names

    calls = await client.get(f"{WEB}/users/me/agent-calls")
    assert calls.status_code == 200

    apps = (await client.get(f"{WEB}/users/me/connected-apps")).json()
    assert len(apps) == 1
    assert apps[0]["client_name"] == "ChatGPT"
    assert apps[0]["redirect_host"] == "chatgpt.com"
    assert apps[0]["permissions"] == AGENT_PERMISSIONS
    assert apps[0]["expires_at"] is not None


async def _connect_again(
    client: httpx.AsyncClient, client_id: str, permissions: list[str] | None = None
) -> tuple[str, dict[str, Any]]:
    verifier, challenge = _pkce()
    code = await _approve(client, client_id, challenge, permissions)
    response = await _exchange(client, client_id, code, verifier)
    assert response.status_code == 200, response.text
    return client_id, response.json()


async def test_a_read_only_approval_hides_the_draft_tools(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    _client_id, tokens = await _connect(make_user, client, ["use:mcp"])
    assert tokens["scope"] == "use:mcp"
    names = await _tool_names(client, tokens["access_token"])
    assert "search_recipes" in names
    assert "create_recipe_draft" not in names


async def test_a_confidential_client_authenticates_with_basic(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await _chef(make_user, client)
    registered = await _register(client, token_endpoint_auth_method="client_secret_basic")
    client_id, secret = registered["client_id"], registered["client_secret"]
    verifier, challenge = _pkce()

    code = await _approve(client, client_id, challenge)
    wrong = base64.b64encode(f"{client_id}:nope".encode()).decode()
    refused = await client.post(
        f"{OAUTH}/token",
        headers={"Authorization": f"Basic {wrong}"},
        data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier},
    )
    assert refused.status_code == 401
    assert refused.json()["error"] == "invalid_client"

    code = await _approve(client, client_id, challenge)
    right = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    accepted = await client.post(
        f"{OAUTH}/token",
        headers={"Authorization": f"Basic {right}"},
        data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.headers["cache-control"] == "no-store"


# ── Codes and refresh tokens ─────────────────────────────────────────


async def test_the_code_needs_the_right_verifier_and_works_once(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await _chef(make_user, client)
    client_id = (await _register(client))["client_id"]
    verifier, challenge = _pkce()

    code = await _approve(client, client_id, challenge)
    other_verifier, _ = _pkce()
    wrong = await _exchange(client, client_id, code, other_verifier)
    assert wrong.status_code == 400
    assert wrong.json()["error"] == "invalid_grant"
    # The failed attempt used the code up.
    assert (await _exchange(client, client_id, code, verifier)).status_code == 400

    code = await _approve(client, client_id, challenge)
    first = await _exchange(client, client_id, code, verifier)
    assert first.status_code == 200
    again = await _exchange(client, client_id, code, verifier)
    assert again.json()["error"] == "invalid_grant"
    # A second redemption means the code leaked, so the grant it made ends.
    assert (await rpc(client, first.json()["access_token"], "tools/list")).status_code == 401


async def test_refresh_rotates_and_a_reused_refresh_token_ends_the_grant(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    client_id, tokens = await _connect(make_user, client)
    rotated = await _refresh(client, client_id, tokens["refresh_token"])
    assert rotated.status_code == 200, rotated.text
    new = rotated.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    assert (await rpc(client, new["access_token"], "tools/list")).status_code == 200

    reused = await _refresh(client, client_id, tokens["refresh_token"])
    assert reused.status_code == 400
    assert reused.json()["error"] == "invalid_grant"
    assert (await rpc(client, new["access_token"], "tools/list")).status_code == 401
    assert (await _refresh(client, client_id, new["refresh_token"])).status_code == 400
    assert (await client.get(f"{WEB}/users/me/connected-apps")).json() == []


async def test_a_refresh_token_belongs_to_its_client(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    _client_id, tokens = await _connect(make_user, client)
    other = (await _register(client))["client_id"]
    stolen = await _refresh(client, other, tokens["refresh_token"])
    assert stolen.json()["error"] == "invalid_grant"


async def test_a_new_approval_replaces_the_earlier_one(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    client_id, first = await _connect(make_user, client)
    _client_id, second = await _connect_again(client, client_id)
    assert (await rpc(client, first["access_token"], "tools/list")).status_code == 401
    assert (await rpc(client, second["access_token"], "tools/list")).status_code == 200
    assert len((await client.get(f"{WEB}/users/me/connected-apps")).json()) == 1


async def test_the_app_can_revoke_its_own_connection(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    client_id, tokens = await _connect(make_user, client)
    revoked = await client.post(
        f"{OAUTH}/revoke", data={"token": tokens["refresh_token"], "client_id": client_id}
    )
    assert revoked.status_code == 200
    assert (await rpc(client, tokens["access_token"], "tools/list")).status_code == 401


# ── The consent page ─────────────────────────────────────────────────


async def test_unknown_clients_and_redirects_are_shown_not_followed(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await _chef(make_user, client)
    client_id = (await _register(client))["client_id"]
    _verifier, challenge = _pkce()

    unknown = await client.post(
        f"{WEB}/oauth/authorize/inspect",
        headers=CSRF,
        json=_authorize_query("cuisine_oc_nope", challenge),
    )
    assert unknown.json()["code"] == "OAuthRedirectRejectedError"

    elsewhere = _authorize_query(client_id, challenge)
    elsewhere["redirect_uri"] = "https://evil.example/callback"
    rejected = await client.post(f"{WEB}/oauth/authorize/inspect", headers=CSRF, json=elsewhere)
    assert rejected.json()["code"] == "OAuthRedirectRejectedError"


async def test_a_broken_request_is_reported_to_the_app(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await _chef(make_user, client)
    client_id = (await _register(client))["client_id"]
    query = _authorize_query(client_id, "x" * 43, code_challenge_method="plain")
    prompt = await client.post(f"{WEB}/oauth/authorize/inspect", headers=CSRF, json=query)
    assert prompt.status_code == 200
    target = prompt.json()["error_redirect"]
    assert target.startswith(REDIRECT)
    assert _query(target)["error"] == "invalid_request"
    assert _query(target)["state"] == "xyz"


async def test_denying_returns_access_denied(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await _chef(make_user, client)
    client_id = (await _register(client))["client_id"]
    _verifier, challenge = _pkce()
    denied = await client.post(
        f"{WEB}/oauth/authorize/decision",
        headers=CSRF,
        json={"request": _authorize_query(client_id, challenge), "approve": False},
    )
    params = _query(denied.json()["redirect_to"])
    assert params["error"] == "access_denied"
    assert "code" not in params


async def test_approval_needs_use_mcp_and_the_consent(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await make_user("cook", permissions=["write:recipes"])
    await make_user("chef", permissions=AGENT_PERMISSIONS)
    await login(client, "cook@example.com", "cook-password-1")
    client_id = (await _register(client))["client_id"]
    _verifier, challenge = _pkce()
    query = _authorize_query(client_id, challenge)
    lacking = await client.post(f"{WEB}/oauth/authorize/inspect", headers=CSRF, json=query)
    assert lacking.status_code == 403
    assert lacking.json()["code"] == "PermissionDeniedError"

    await login(client, "chef@example.com", "cook-password-1")
    no_consent = await client.post(f"{WEB}/oauth/authorize/inspect", headers=CSRF, json=query)
    assert no_consent.json()["code"] == "ConsentRequiredError"


async def test_the_system_user_cannot_connect_apps(admin: httpx.AsyncClient) -> None:
    client_id = (await _register(admin))["client_id"]
    _verifier, challenge = _pkce()
    refused = await admin.post(
        f"{WEB}/oauth/authorize/inspect", headers=CSRF, json=_authorize_query(client_id, challenge)
    )
    assert refused.status_code == 403
    assert refused.json()["code"] == "SystemUserProtectedError"


# ── Registration and the agent settings ──────────────────────────────


async def test_registration_checks_redirect_uris(client: httpx.AsyncClient) -> None:
    for uri in ("http://example.com/cb", "https://example.com/cb#frag", "not a uri"):
        response = await client.post(f"{OAUTH}/register", json={"redirect_uris": [uri]})
        assert response.status_code == 400, uri
        assert response.json()["error"] == "invalid_redirect_uri"
    loopback = await client.post(
        f"{OAUTH}/register",
        json={"redirect_uris": ["http://127.0.0.1:33418/callback"], "client_name": "CLI"},
    )
    assert loopback.status_code == 201
    # A confidential client is the RFC default.
    assert loopback.json()["token_endpoint_auth_method"] == "client_secret_basic"
    assert loopback.json()["client_secret"].startswith("cuisine_ocs_")


def _agents(**changes: Any) -> dict[str, Any]:
    return {
        "enabled": True,
        "calls_per_minute": 120,
        "drafts_per_hour": 30,
        "token_max_lifetime_days": 30,
        "oauth_enabled": True,
        "oauth_redirect_hosts": [],
        **changes,
    }


async def test_the_redirect_host_allowlist(
    make_user: MakeUser, client: httpx.AsyncClient, login_system: LoginSystem
) -> None:
    await _chef(make_user, client)
    client_id = (await _register(client))["client_id"]

    await login_system(client)
    bad = await client.put(
        f"{WEB}/settings/agents", headers=CSRF, json=_agents(oauth_redirect_hosts=["*.ai"])
    )
    assert bad.status_code == 422
    saved = await client.put(
        f"{WEB}/settings/agents",
        headers=CSRF,
        json=_agents(oauth_redirect_hosts=[" Claude.AI ", "claude.ai"]),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["oauth_redirect_hosts"] == ["claude.ai"]

    refused = await client.post(f"{OAUTH}/register", json={"redirect_uris": [REDIRECT]})
    assert refused.json()["error"] == "invalid_redirect_uri"
    await client.post(
        f"{OAUTH}/register", json={"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]}
    )

    # A client registered before the change is refused at approval too.
    await login(client, "chef@example.com", "cook-password-1")
    _verifier, challenge = _pkce()
    late = await client.post(
        f"{WEB}/oauth/authorize/inspect", headers=CSRF, json=_authorize_query(client_id, challenge)
    )
    assert late.json()["code"] == "OAuthRedirectRejectedError"


async def test_switching_oauth_off_refuses_connected_apps(
    make_user: MakeUser, client: httpx.AsyncClient, login_system: LoginSystem
) -> None:
    _client_id, tokens = await _connect(make_user, client)
    await login_system(client)
    await client.put(f"{WEB}/settings/agents", headers=CSRF, json=_agents(oauth_enabled=False))
    assert (await rpc(client, tokens["access_token"], "tools/list")).status_code == 403
    registered = await client.post(f"{OAUTH}/register", json={"redirect_uris": [REDIRECT]})
    assert registered.status_code == 403
    assert registered.json()["error"] == "access_denied"


# ── Ending a connection ──────────────────────────────────────────────


async def test_the_person_revokes_a_connected_app(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    _client_id, tokens = await _connect(make_user, client)
    apps = (await client.get(f"{WEB}/users/me/connected-apps")).json()
    revoked = await client.delete(f"{WEB}/users/me/connected-apps/{apps[0]['id']}", headers=CSRF)
    assert revoked.status_code == 204
    assert (await rpc(client, tokens["access_token"], "tools/list")).status_code == 401
    again = await client.delete(f"{WEB}/users/me/connected-apps/{apps[0]['id']}", headers=CSRF)
    assert again.status_code == 404


async def test_withdrawing_the_consent_ends_connected_apps(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    _client_id, tokens = await _connect(make_user, client)
    await client.delete(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)
    assert (await rpc(client, tokens["access_token"], "tools/list")).status_code == 401
    assert (await client.get(f"{WEB}/users/me/connected-apps")).json() == []


async def test_signing_the_user_out_everywhere_ends_connected_apps(
    make_user: MakeUser, client: httpx.AsyncClient, login_system: LoginSystem
) -> None:
    client_id, tokens = await _connect(make_user, client)
    user_id = (await client.get(f"{WEB}/users/me")).json()["id"]
    await login_system(client)
    forced = await client.post(f"{WEB}/users/{user_id}/logout", headers=CSRF)
    assert forced.status_code == 204
    assert (await rpc(client, tokens["access_token"], "tools/list")).status_code == 401
    assert (await _refresh(client, client_id, tokens["refresh_token"])).status_code == 400


async def test_the_budget_belongs_to_the_grant(
    make_user: MakeUser, client: httpx.AsyncClient, login_system: LoginSystem
) -> None:
    client_id, tokens = await _connect(make_user, client)
    await login_system(client)
    await client.put(f"{WEB}/settings/agents", headers=CSRF, json=_agents(calls_per_minute=1))
    first = await rpc(
        client,
        tokens["access_token"],
        "tools/call",
        {"name": "list_tags", "arguments": {}},
    )
    assert first.json()["result"].get("isError") is not True, first.text
    fresh = (await _refresh(client, client_id, tokens["refresh_token"])).json()
    second = await rpc(
        client, fresh["access_token"], "tools/call", {"name": "list_tags", "arguments": {}}
    )
    assert second.json()["result"]["isError"] is True
