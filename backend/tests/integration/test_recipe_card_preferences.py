"""The recipe card preferences on the own profile: every card is on for a
new account, each one turns off and on alone, and only the user's own
`GET /users/me` carries them."""

import httpx

from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB

CARDS = ("recipe_show_tips", "recipe_show_notes", "recipe_show_cooked", "recipe_show_rating")


def _cards(me: dict[str, object]) -> dict[str, object]:
    return {name: me[name] for name in CARDS}


async def test_every_card_is_shown_by_default(cook: httpx.AsyncClient) -> None:
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert _cards(me) == dict.fromkeys(CARDS, True)


async def test_cards_turn_off_and_on_one_at_a_time(cook: httpx.AsyncClient) -> None:
    changed = await cook.patch(
        f"{WEB}/users/me",
        headers=CSRF,
        json={"recipe_show_tips": False, "recipe_show_rating": False},
    )
    assert changed.status_code == 200, changed.text
    assert _cards(changed.json()) == {
        "recipe_show_tips": False,
        "recipe_show_notes": True,
        "recipe_show_cooked": True,
        "recipe_show_rating": False,
    }

    # A partial update leaves the other cards alone.
    await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"recipe_show_tips": True})
    await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"recipe_show_cooked": False})
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert _cards(me) == {
        "recipe_show_tips": True,
        "recipe_show_notes": True,
        "recipe_show_cooked": False,
        "recipe_show_rating": False,
    }


async def test_the_cards_are_not_shown_to_others(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"recipe_show_notes": False})
    users = (await admin.get(f"{WEB}/users")).json()
    rows = users["items"] if isinstance(users, dict) else users
    assert rows
    assert all("recipe_show_notes" not in row for row in rows)


async def test_mention_highlighting_is_on_by_default_and_turns_off(cook: httpx.AsyncClient) -> None:
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert me["recipe_highlight_mentions"] is True

    changed = await cook.patch(
        f"{WEB}/users/me", headers=CSRF, json={"recipe_highlight_mentions": False}
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["recipe_highlight_mentions"] is False
    # The card preferences stay as they were.
    assert _cards(changed.json()) == dict.fromkeys(CARDS, True)


async def test_keep_screen_on_is_on_by_default_and_turns_off(cook: httpx.AsyncClient) -> None:
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert me["keep_screen_on"] is True

    changed = await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"keep_screen_on": False})
    assert changed.status_code == 200, changed.text
    assert changed.json()["keep_screen_on"] is False
    assert (await cook.get(f"{WEB}/users/me")).json()["keep_screen_on"] is False
