"""
Fills the development database with demo data on top of the production
reference data, so the app can be tried in a browser right away.

It first runs the same reference seed as every start (units, categories,
tags and the base ingredients from src/bootstrap/data/), then adds demo data
only: the accounts anna (in the default groups Cooks and Kitchen helpers,
which it recreates if an administrator deleted them) and ben, a household
of admin and anna with its meal plan and continuous list, five recipes (one private, one shared,
homemade lasagna sheets used by a lasagna), a year of cook events, a meal
plan week, a normal list shared with ben, and the opt-ins and food restrictions
for the dinner guest check (anna vegetarian, ben intolerant to apples). It
creates no ingredients, units, tags or categories of its own: recipes use
base ingredients by key.

A fresh instance runs in instance mode (every recipe visible to every member,
locked). The demo shows the other visibilities, so the seed switches the
instance to user choice (default "instance") the way an administrator
would, which publishes a new privacy statement version. Admin adds the
variation "Mit Honig, ohne Rosinen" to anna's Kaiserschmarrn, and anna makes
admin a co-editor of it.

It refuses to run outside debug mode and does nothing when recipes already
exist. The database must be migrated first (the dev server does that on
start with MIGRATE_ON_STARTUP).

Usage (from backend/, or `make seed-dev` from the repo root):
    ENV_FILE=../.env.dev poetry run python scripts/seed_dev.py
"""

# The demo data below is kept one record per line, which is easier to read
# and edit than the formatter's wrapping, so its lines may run long.
# ruff: noqa: E501

import asyncio
import sys
from datetime import timedelta
from typing import Any

from src.bootstrap.cookbook_hooks import register_cookbook_hooks
from src.bootstrap.cookbook_seed import ensure_reference_data
from src.bootstrap.seed import COOKS
from src.bootstrap.seed import DEFAULT_GROUPS
from src.bootstrap.seed import KITCHEN_HELPERS
from src.bootstrap.seed import ensure_default_groups
from src.bootstrap.seed import ensure_system_user
from src.bootstrap.webhook_events import register_cookbook_webhook_events
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_manage_cook_events
from src.cookbook.adapters.inbound.api.deps import get_manage_households
from src.cookbook.adapters.inbound.api.deps import get_manage_meal_plan
from src.cookbook.adapters.inbound.api.deps import get_manage_personal
from src.cookbook.adapters.inbound.api.deps import get_manage_recipes
from src.cookbook.adapters.inbound.api.deps import get_manage_shopping_lists
from src.cookbook.adapters.inbound.api.deps import get_manage_variations
from src.cookbook.adapters.outbound.external.live_updates import InMemoryLivePublisher
from src.cookbook.application.services.variation_resolver import VariationChangeCommand
from src.cookbook.application.use_cases.personal.manage_personal import RestrictionCommand
from src.cookbook.application.use_cases.planning.shopping_lists import ItemCommand
from src.cookbook.application.use_cases.planning.shopping_lists import ItemUpdate
from src.cookbook.application.use_cases.recipes.manage_recipes import RecipeCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepIngredientCommand
from src.cookbook.application.use_cases.recipes.manage_variations import VariationCommand
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.domain.value_objects.enums import RestrictionKind
from src.cookbook.domain.value_objects.enums import VariationChangeKind
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_manage_groups
from src.platform.adapters.inbound.api.deps import get_manage_settings
from src.platform.adapters.inbound.api.deps import get_manage_users
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.admin.groups import GroupCommand
from src.platform.application.use_cases.admin.users import CreateUserCommand
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.language import Language
from src.platform.infrastructure.config.settings import cfg
from src.shared_kernel.domain.services.clock import now_utc

DE = "de-AT"
EN = "en-GB"
# Development-only passwords, printed at the end; the script refuses to run
# outside debug mode.
ANNA = ("anna@example.com", "anna-dev-password")
BEN = ("ben@example.com", "ben-dev-password")
CONTEXT = RequestContext(client_ip="127.0.0.1", user_agent="seed_dev")


def _i(key: str, amount: float | None, unit: str | None, note: str = "") -> dict[str, Any]:
    """A base ingredient by its reference key."""
    return {"ingredient": key, "amount": amount, "unit": unit, "note": note}


def _sub(title: str, amount: float | None, unit: str | None) -> dict[str, Any]:
    """A recipe of this seed, by its title, used as a sub-recipe."""
    return {"sub_recipe": title, "amount": amount, "unit": unit, "note": ""}


# In creation order: a sub-recipe comes before the recipes that use it.
# "author" is admin or anna; tags by their English name.
RECIPES: tuple[dict[str, Any], ...] = (
    {
        "title": "Kaiserschmarrn", "author": "anna", "visibility": "instance",
        "description": "Der flaumige Klassiker aus der Pfanne, mit Rosinen und Staubzucker.",
        "tips": "Dazu passt Zwetschkenröster.",
        "servings": 2, "prep": 15, "cook": 15, "difficulty": Difficulty.MEDIUM,
        "tags": ["Dessert", "Austrian"],
        "steps": [
            ("Eier trennen. Dotter mit Milch, Mehl und einer Prise Salz glatt rühren.", None,
             [_i("egg", 4, "piece"), _i("milk", 250, "ml"), _i("flour", 150, "g"), _i("salt", 1, "pinch")]),
            ("Eiklar mit Zucker steif schlagen und unter den Teig heben.", None, [_i("sugar", 30, "g")]),
            ("Butter in einer Pfanne schmelzen, Teig eingießen, Rosinen darüberstreuen und bei mittlerer Hitze stocken lassen.", 5,
             [_i("butter", 30, "g"), _i("raisins", 40, "g")]),
            ("Wenden, mit zwei Gabeln in Stücke reißen und fertig braten. Mit Staubzucker bestreut servieren.", 5,
             [_i("icing_sugar", None, None, "zum Bestreuen")]),
        ],
        "english": {
            "title": "Kaiserschmarrn",
            "description": "The fluffy shredded pancake classic, with raisins and icing sugar.",
            "tips": "Serve with plum compote.",
            "steps": [
                "Separate the eggs. Whisk the yolks with milk, flour and a pinch of salt.",
                "Beat the whites with the sugar until stiff and fold them in.",
                "Melt butter in a pan, pour in the batter, scatter the raisins and let it set over medium heat.",
                "Turn, tear into pieces with two forks and finish frying. Dust with icing sugar.",
            ],
        },
    },
    {
        "title": "Wiener Schnitzel mit Erdäpfelsalat", "author": "admin", "visibility": "shared",
        "description": "Dünn geklopftes Kalbsschnitzel, goldbraun herausgebacken.",
        "tips": "Die Panier soll Wellen schlagen: Pfanne dabei sanft schwenken.",
        "servings": 4, "prep": 30, "cook": 25, "rest": 30, "difficulty": Difficulty.MEDIUM,
        "tags": ["Lunch", "Austrian", "Main course"],
        "steps": [
            ("Erdäpfel kochen, schälen und in Scheiben schneiden. Mit fein gehackter Zwiebel, Essig, Öl, Salz und Pfeffer marinieren und ziehen lassen.", 25,
             [_i("potato", 800, "g"), _i("onion", 1, "piece", "fein gehackt"), _i("vinegar", 3, "tbsp"), _i("salt", None, None), _i("black_pepper", None, None)]),
            ("Schnitzel dünn klopfen, salzen und in Mehl, verquirltem Ei und Bröseln panieren.", None,
             [_i("veal", 600, "g"), _i("flour", 60, "g"), _i("egg", 2, "piece"), _i("breadcrumbs", 120, "g")]),
            ("In reichlich heißem Öl schwimmend goldbraun backen. Mit Zitronenspalten servieren.", 4,
             [_i("sunflower_oil", 300, "ml"), _i("lemon", 1, "piece", "in Spalten")]),
        ],
    },
    {
        "title": "Spaghetti al pomodoro", "author": "anna", "visibility": "private",
        "description": "Schnelle Tomatensauce mit Knoblauch, Basilikum und Parmesan.",
        "tips": "",
        "servings": 2, "prep": 5, "cook": 20, "difficulty": Difficulty.EASY,
        "tags": ["Dinner", "Italian", "Quick"],
        "steps": [
            ("Knoblauch in Olivenöl anschwitzen, Tomaten dazugeben und 15 Minuten köcheln.", 15,
             [_i("garlic", 2, "clove", "in Scheiben"), _i("olive_oil", 2, "tbsp"), _i("chopped_tomatoes", 400, "g")]),
            ("Spaghetti in Salzwasser al dente kochen.", 10, [_i("spaghetti", 200, "g"), _i("salt", None, None)]),
            ("Mit der Sauce vermengen, mit Basilikum und Parmesan servieren.", None,
             [_i("basil", 0.5, "bunch"), _i("parmesan", 30, "g", "frisch gerieben")]),
        ],
    },
    {
        "title": "Lasagneblätter", "author": "admin", "visibility": "instance",
        "description": "Frischer Nudelteig für etwa 500 g Lasagneblätter.",
        "tips": "Hält eingewickelt einen Tag im Kühlschrank.",
        "servings": 4, "prep": 20, "rest": 30, "difficulty": Difficulty.MEDIUM,
        "yield": (500, "g"),
        "tags": ["Italian"],
        "steps": [
            ("Mehl, Grieß und Eier zu einem glatten Teig kneten und zugedeckt rasten lassen.", 30,
             [_i("flour", 200, "g"), _i("semolina", 100, "g"), _i("egg", 3, "piece")]),
            ("Dünn ausrollen und in Blätter von der Größe der Form schneiden.", None, []),
        ],
    },
    {
        "title": "Lasagne", "author": "admin", "visibility": "instance",
        "description": "Mit Ragù, Béchamel und selbst gemachten Blättern.",
        "tips": "Vor dem Anschneiden zehn Minuten ruhen lassen.",
        "servings": 4, "prep": 40, "cook": 45, "rest": 10, "difficulty": Difficulty.HARD,
        "tags": ["Main course", "Italian"],
        "steps": [
            ("Zwiebel, Karotte und Knoblauch in Olivenöl anschwitzen, Faschiertes anbraten, Tomaten dazugeben und 30 Minuten köcheln.", 30,
             [_i("onion", 1, "piece", "fein gehackt"), _i("carrot", 1, "piece", "fein gehackt"), _i("garlic", 2, "clove"),
              _i("olive_oil", 2, "tbsp"), _i("beef_mince", 500, "g"), _i("chopped_tomatoes", 800, "g"), _i("salt", None, None), _i("black_pepper", None, None)]),
            ("Für die Béchamel Butter schmelzen, Mehl einrühren, nach und nach Milch dazugießen und mit Muskat würzen.", 10,
             [_i("butter", 50, "g"), _i("flour", 50, "g"), _i("milk", 500, "ml"), _i("nutmeg", None, None)]),
            ("Ragù, Blätter und Béchamel abwechselnd schichten, mit Parmesan bestreuen und bei 180 °C backen.", 45,
             [_sub("Lasagneblätter", 500, "g"), _i("parmesan", 50, "g", "gerieben")]),
        ],
    },
)  # fmt: skip


async def _user(
    p: Platform,
    admin: User,
    email: str,
    password: str,
    full_name: str,
    groups: list[str],
    language: Language,
) -> User:
    return await get_manage_users(p).create(
        admin,
        CreateUserCommand(
            full_name=full_name,
            email=email,
            password=password,
            permissions=[],
            group_ids=groups,
            language=language,
        ),
        context=CONTEXT,
    )


async def seed() -> None:
    if await ensure_system_user():
        await ensure_default_groups()
    await ensure_reference_data()
    async with SessionLocal() as db:
        p = Platform(db)
        c = Cookbook(p)
        admin = next(u for u in await p.users.list_all() if u.is_systemuser)
        if (await c.recipes.find(RecipeQuery(viewer_id=admin.id, limit=1)))[1]:
            print("The database already has recipes; nothing seeded.")
            return

        groups = {g.name: g for g in await get_manage_groups(p).list_all()}
        for default in DEFAULT_GROUPS:
            if default.name in (COOKS, KITCHEN_HELPERS) and default.name not in groups:
                groups[default.name] = await get_manage_groups(p).create(
                    admin,
                    GroupCommand(
                        name=default.name,
                        description=default.description,
                        permissions=list(default.permissions),
                    ),
                    context=CONTEXT,
                )
        anna_groups = [str(groups[name].public_id) for name in (COOKS, KITCHEN_HELPERS)]
        cooks = groups[COOKS]
        # The demo has private and shared recipes, which instance mode (the
        # default of a fresh instance) does not allow.
        await get_manage_settings(p).save_privacy(
            admin,
            PrivacySettings(default_recipe_visibility="instance", users_may_change_visibility=True),
            context=CONTEXT,
        )
        await p.uow.commit()
        anna = await _user(p, admin, *ANNA, "Anna Beispiel", anna_groups, Language.DE_AT)
        ben = await _user(p, admin, *BEN, "Ben Beispiel", [], Language.EN_GB)
        # Both demo guests enter food restrictions below, which needs the
        # health data consent, and share them with hosts for dinner guests.
        for guest in (anna, ben):
            guest.share_restrictions_with_hosts = True
            guest.consent_health_data_at = now_utc()
            await p.users.save(guest)
        await p.uow.commit()

        households = get_manage_households(c)
        home = await households.create(admin, "Familie Beispiel")
        invitation = await households.invite(admin, str(anna.public_id))
        await households.accept(anna, str(invitation.public_id))

        keys = {
            i["ingredient"]
            for r in RECIPES
            for _, _, items in r["steps"]
            for i in items
            if "ingredient" in i
        } | {"apple", "honey"}
        ingredients = await c.ingredients.by_seed_keys(sorted(keys))
        missing = sorted(keys - set(ingredients))
        if missing:
            raise SystemExit(f"Base ingredients missing (deleted?): {', '.join(missing)}")
        units = {u.code: u for u in await c.units.list_all()}
        tags = {t.translations[EN].name: t for t in await c.tags.list_all() if EN in t.translations}

        recipes = get_manage_recipes(c)
        authors = {"admin": admin, "anna": anna}
        made: dict[str, tuple[Recipe, User]] = {}
        for data in RECIPES:
            author = authors[data["author"]]
            steps = []
            for text, duration, items in data["steps"]:
                lines = []
                for item in items:
                    unit = units[item["unit"]] if item["unit"] else None
                    lines.append(
                        StepIngredientCommand(
                            ingredient_id=str(ingredients[item["ingredient"]].public_id)
                            if "ingredient" in item
                            else None,
                            sub_recipe_id=str(made[item["sub_recipe"]][0].public_id)
                            if "sub_recipe" in item
                            else None,
                            amount=item["amount"],
                            unit_id=str(unit.public_id) if unit else None,
                            notes={DE: NoteText(item["note"])} if item["note"] else {},
                        )
                    )
                steps.append(
                    StepCommand(
                        translations={DE: StepText(text)},
                        duration_minutes=duration,
                        ingredients=lines,
                    )
                )
            yield_amount, yield_unit = data.get("yield", (None, None))
            recipe = await recipes.create(
                author,
                RecipeCommand(
                    original_locale=DE,
                    translations={DE: RecipeText(data["title"], data["description"], data["tips"])},
                    base_servings=data["servings"],
                    prep_minutes=data.get("prep"),
                    cook_minutes=data.get("cook"),
                    rest_minutes=data.get("rest"),
                    difficulty=data["difficulty"],
                    tag_ids=[str(tags[t].public_id) for t in data["tags"] if t in tags],
                    steps=steps,
                    yield_amount=yield_amount,
                    yield_unit_id=str(units[yield_unit].public_id) if yield_unit else None,
                    visibility=RecipeVisibility(data["visibility"]),
                    shared_group_ids=[str(cooks.public_id)]
                    if data["visibility"] == "shared"
                    else [],
                ),
            )
            recipe = await recipes.publish(author, str(recipe.public_id))
            english = data.get("english")
            if english:
                recipe = await recipes.add_translation(
                    author,
                    str(recipe.public_id),
                    EN,
                    RecipeText(english["title"], english["description"], english["tips"]),
                    [StepText(s) for s in english["steps"]],
                )
            made[data["title"]] = (recipe, author)

        kaiserschmarrn = made["Kaiserschmarrn"][0]
        await get_manage_variations(c).create(
            admin,
            str(kaiserschmarrn.public_id),
            VariationCommand(
                name="Mit Honig, ohne Rosinen",
                note="Honig statt Zucker im Eischnee, und die Rosinen bleiben weg.",
                locale=DE,
                changes=[
                    VariationChangeCommand(
                        kind=VariationChangeKind.SWAP,
                        step=2,
                        ingredient_id=str(ingredients["sugar"].public_id),
                        to_ingredient_id=str(ingredients["honey"].public_id),
                        keep_amount=False,
                        amount=25,
                        unit_id=str(units["g"].public_id),
                    ),
                    VariationChangeCommand(
                        kind=VariationChangeKind.REMOVE_LINE,
                        step=3,
                        ingredient_id=str(ingredients["raisins"].public_id),
                    ),
                ],
            ),
        )
        # Admin edits anna's Kaiserschmarrn with her.
        await recipes.set_co_editors(anna, str(kaiserschmarrn.public_id), [str(admin.public_id)])

        personal = get_manage_personal(c)
        await personal.add_restriction(
            anna, RestrictionCommand(kind=RestrictionKind.DIET, diet=Diet.VEGETARIAN)
        )
        await personal.add_restriction(
            ben,
            RestrictionCommand(
                kind=RestrictionKind.INTOLERANCE, ingredient_id=str(ingredients["apple"].public_id)
            ),
        )

        events = get_manage_cook_events(c)
        today = now_utc().date()
        cooked = [
            made[t]
            for t in (
                "Kaiserschmarrn",
                "Wiener Schnitzel mit Erdäpfelsalat",
                "Spaghetti al pomodoro",
                "Lasagne",
            )
        ]
        for index, days_ago in enumerate((2, 9, 23, 40, 75, 130, 200, 300, 365)):
            recipe, cook = cooked[index % len(cooked)]
            await events.create(
                cook, str(recipe.public_id), today - timedelta(days=days_ago), recipe.base_servings
            )

        shopping = get_manage_shopping_lists(c, InMemoryLivePublisher())
        household_list = await c.shopping_lists.of_household(home.id)
        assert household_list is not None
        grillfest = await shopping.create(admin, "Grillfest", [str(ben.public_id)])
        plan = get_manage_meal_plan(c, shopping)
        monday = today - timedelta(days=today.weekday())
        for offset, title in enumerate(
            (
                "Kaiserschmarrn",
                "Wiener Schnitzel mit Erdäpfelsalat",
                "Spaghetti al pomodoro",
                "Lasagne",
            )
        ):
            recipe, author = made[title]
            # The household plan; each recipe is planned by its author, who
            # can always see it, even the private one.
            await plan.add(
                author,
                plan_date=monday + timedelta(days=offset * 2),
                slot=MealSlot.DINNER,
                recipe_id=str(recipe.public_id),
                title="",
                servings=2,
            )
        await plan.to_shopping_list(
            admin, monday, monday + timedelta(days=6), str(household_list.public_id)
        )
        # The household list is continuous: tick two items so "Recently
        # bought" has something to show. Grillfest is a normal list that
        # shows the day it deletes itself if nobody uses it.
        for item in (await c.shopping_lists.items(household_list.id))[:2]:
            await shopping.update_item(
                anna, str(household_list.public_id), str(item.public_id), ItemUpdate(checked=True)
            )
        for text in ("Grillkohle", "Servietten"):
            await shopping.add_item(admin, str(grillfest.public_id), ItemCommand(text=text))

    print(
        f"Seeded the demo data: {len(RECIPES)} recipes on the base catalogue, cook events, a meal plan and lists.\n"
        f"Accounts: {ANNA[0]} / {ANNA[1]} (groups Cooks and Kitchen helpers, vegetarian), {BEN[0]} / {BEN[1]} (intolerant to apples).\n"
        "Both share their restrictions with hosts. Admin and anna share the household "
        "'Familie Beispiel' with its meal plan and list.\n"
        "Privacy mode set to user choice (default: instance), since the demo has private and "
        "shared recipes; a fresh instance starts in instance mode."
    )


def main() -> int:
    if not cfg.debug:
        print("seed_dev only runs in debug mode (DEBUG=true).", file=sys.stderr)
        return 1
    # The app registers these at startup; the script runs the same use cases
    # outside the app, so it registers them itself.
    register_cookbook_webhook_events()
    register_cookbook_hooks()
    asyncio.run(seed())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
