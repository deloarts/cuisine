"""Every route of the admin router refuses a signed-in user without its
permission, so a new route that forgets its gate fails here; plus the happy
paths the other admin tests leave out."""

import re
import uuid

import httpx
import pytest
from fastapi.routing import APIRoute

from src.platform.adapters.inbound.api.v1.admin_router import router
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.test_tokens import EXPIRES

# Routes any signed-in user may call: the people and group directories and
# the list of permission names.
OPEN_ROUTES = frozenset(
    {
        ("GET", "/users/directory"),
        ("GET", "/groups/directory"),
        ("GET", "/permissions"),
    }
)

GATED_ROUTES = sorted(
    (method, route.path)
    for route in router.routes
    if isinstance(route, APIRoute)
    for method in route.methods or ()
    if (method, route.path) not in OPEN_ROUTES
)


@pytest.fixture
async def plain(make_user: MakeUser, other_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """A second browser signed in as an account without any permission."""
    await make_user("plain")
    await login(other_client, "plain@example.com", "cook-password-1")
    return other_client


def test_the_walk_sees_every_admin_route() -> None:
    assert len(GATED_ROUTES) >= 15
    assert all(path for _, path in GATED_ROUTES)


@pytest.mark.parametrize(
    ("method", "path"), GATED_ROUTES, ids=[f"{m} {p}" for m, p in GATED_ROUTES]
)
async def test_every_gated_admin_route_refuses_without_the_permission(
    plain: httpx.AsyncClient, method: str, path: str
) -> None:
    url = WEB + re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
    kwargs: dict[str, object] = {"headers": CSRF}
    if method in ("POST", "PUT", "PATCH"):
        kwargs["json"] = {}
    response = await plain.request(method, url, **kwargs)  # type: ignore[arg-type]
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "PermissionDeniedError"


async def test_permissions_are_listed_for_everyone(plain: httpx.AsyncClient) -> None:
    listed = await plain.get(f"{WEB}/permissions")
    assert listed.status_code == 200
    by_name = {p["name"]: p for p in listed.json()}
    assert by_name["write:recipes"]["grantable_to_tokens"] is True
    assert by_name["write:users"]["grantable_to_tokens"] is False


async def test_a_group_is_changed_and_deleted(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    cook = await make_user("cook")
    created = await admin.post(f"{WEB}/groups", headers=CSRF, json={"name": "Family"})
    group_id = created.json()["id"]

    changed = await admin.patch(
        f"{WEB}/groups/{group_id}",
        headers=CSRF,
        json={
            "name": "Kitchen",
            "description": "Who cooks",
            "permissions": ["write:recipes"],
            "member_ids": [cook["id"]],
        },
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    assert (body["name"], body["description"]) == ("Kitchen", "Who cooks")
    assert body["permissions"] == ["write:recipes"]
    assert body["member_ids"] == [cook["id"]]

    deleted = await admin.delete(f"{WEB}/groups/{group_id}", headers=CSRF)
    assert deleted.status_code == 204
    assert all(g["id"] != group_id for g in (await admin.get(f"{WEB}/groups")).json())
    missing = await admin.patch(f"{WEB}/groups/{group_id}", headers=CSRF, json={"name": "X"})
    assert missing.status_code == 404


async def test_api_keys_are_listed(admin: httpx.AsyncClient) -> None:
    assert (await admin.get(f"{WEB}/api-keys")).json() == []
    created = await admin.post(
        f"{WEB}/api-keys", headers=CSRF, json={"name": "Home Assistant", "expires_at": EXPIRES}
    )
    assert created.status_code == 201, created.text
    listed = (await admin.get(f"{WEB}/api-keys")).json()
    assert [k["name"] for k in listed] == ["Home Assistant"]


async def test_users_are_listed_one_page_at_a_time(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    for name in ("anna", "ben", "cook"):
        await make_user(name)
    everyone = (await admin.get(f"{WEB}/users")).json()
    page = await admin.get(f"{WEB}/users", params={"limit": 2, "offset": 1})
    assert page.status_code == 200, page.text
    assert [u["id"] for u in page.json()] == [u["id"] for u in everyone[1:3]]
    too_many = await admin.get(f"{WEB}/users", params={"limit": 501})
    assert too_many.status_code == 422
