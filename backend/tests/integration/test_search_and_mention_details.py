"""What the editor's @ suggestions and mention errors need: the alias an
ingredient search matched, and where an invalid mention sits."""

import httpx

from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient


async def test_search_names_the_alias_it_matched(cook: httpx.AsyncClient) -> None:
    created = await cook.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": "Paradeiser"}},
            "aliases": {"de-AT": ["Tomate", "Tomaten"]},
        },
    )
    assert created.status_code == 201, created.text
    by_alias = (await cook.get(f"{WEB}/ingredients", params={"search": "tomat"})).json()
    assert by_alias["items"][0]["name"] == "Paradeiser"
    assert by_alias["items"][0]["matched_alias"] == "Tomate"
    by_name = (await cook.get(f"{WEB}/ingredients", params={"search": "parad"})).json()
    assert by_name["items"][0]["matched_alias"] is None
    unfiltered = (await cook.get(f"{WEB}/ingredients")).json()
    assert unfiltered["items"][0]["matched_alias"] is None


async def test_an_ingredient_mention_error_names_step_locale_and_target(
    cook: httpx.AsyncClient,
) -> None:
    salt = await make_ingredient(cook, "Salz", english="salt")
    token = f"@[salt](ingredient:{salt['id']})"
    refused = await cook.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"title": "Wasser"}},
            "steps": [
                {
                    "translations": {
                        "de-AT": {"text": "Kochen."},
                        "en-GB": {"text": f"Add {token}."},
                    }
                }
            ],
        },
    )
    assert refused.status_code == 422
    body = refused.json()
    assert body["code"] == "InvalidMentionError"
    assert (body["step"], body["locale"]) == (1, "en-GB")
    assert (body["mention_kind"], body["mention_id"]) == ("ingredient", salt["id"])
