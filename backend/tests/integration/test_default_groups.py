"""The default groups a fresh install starts with: created once, with known
permissions, and never doubled."""

import httpx

from src.bootstrap.seed import DEFAULT_GROUPS
from src.bootstrap.seed import ensure_default_groups
from src.platform.domain.value_objects.permission import Permission

WEB = "/api/v1/web"


async def test_the_default_groups_are_created_with_their_permissions(
    admin: httpx.AsyncClient,
) -> None:
    assert await ensure_default_groups() == len(DEFAULT_GROUPS)

    response = await admin.get(f"{WEB}/groups")
    assert response.status_code == 200, response.text
    groups = {g["name"]: g for g in response.json()}
    for default in DEFAULT_GROUPS:
        assert sorted(groups[default.name]["permissions"]) == sorted(default.permissions)
        assert groups[default.name]["description"] == default.description


async def test_a_second_run_creates_nothing() -> None:
    await ensure_default_groups()
    assert await ensure_default_groups() == 0


def test_every_default_permission_exists_and_none_is_left_out() -> None:
    granted = [p for g in DEFAULT_GROUPS for p in g.permissions]
    assert set(granted) <= set(Permission.ALL)
    assert sorted(granted) == sorted(Permission.ALL)
