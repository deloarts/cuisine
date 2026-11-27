"""
"Download my data": everything the signed-in user holds in cuisine, as one
JSON document. The profile and the consents come from Platform's user
entity; the cookbook adds the user's recipes (in the editable shape of a
revision snapshot, with status and visibility), ingredients they own,
favourites, ratings, private notes, cook events, the meal plan entries they
made, their shopping lists, food restrictions, household and kitchen.

Other people's data stays out: a favourite, rating, note or cook event of a
recipe the user can no longer see names no title, a household lists only
its members' names, and a shared list shows its items, which every member
edits, but not who added them.
"""

from datetime import date
from typing import Any

from src.cookbook.application.services.revisions import RevisionRecorder
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.application.use_cases.equipment.kitchen import ManageKitchen
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.revisions import build_snapshot
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.value_objects.viewer import Viewer
from src.cookbook.ports.outbound.repositories.cooking_repositories import ICookEventRepository
from src.cookbook.ports.outbound.repositories.cooking_repositories import IMealPlanRepository
from src.cookbook.ports.outbound.repositories.cooking_repositories import IShoppingListRepository
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.household_repository import IHouseholdRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import ICookNoteRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import IFavouriteRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import (
    IFoodRestrictionRepository,
)
from src.cookbook.ports.outbound.repositories.personal_repositories import IRatingRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.shared_kernel.domain.services.clock import now_utc

FORMAT = "cuisine-personal-data"
FORMAT_VERSION = 1
# Every cook event and plan entry of a user, without a practical limit.
_ALL_EVENTS = 1_000_000
_FIRST_DAY = date(1, 1, 1)
_LAST_DAY = date(9999, 12, 31)


def _title(recipe: Recipe) -> str:
    return resolve(recipe.translations, None, recipe.original_locale)[1].title


class ExportOwnData:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        unit_repo: IUnitRepository,
        family_repo: IIngredientFamilyRepository,
        favourite_repo: IFavouriteRepository,
        rating_repo: IRatingRepository,
        note_repo: ICookNoteRepository,
        restriction_repo: IFoodRestrictionRepository,
        cook_event_repo: ICookEventRepository,
        meal_plan_repo: IMealPlanRepository,
        list_repo: IShoppingListRepository,
        household_repo: IHouseholdRepository,
        user_repo: IUserRepository,
        revisions: RevisionRecorder,
        kitchen: ManageKitchen,
        viewers: ViewerResolver,
        variation_repo: IRecipeVariationRepository,
    ) -> None:
        self._variations = variation_repo
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._units = unit_repo
        self._families = family_repo
        self._favourites = favourite_repo
        self._ratings = rating_repo
        self._notes = note_repo
        self._restrictions = restriction_repo
        self._events = cook_event_repo
        self._plan = meal_plan_repo
        self._lists = list_repo
        self._households = household_repo
        self._users = user_repo
        self._revisions = revisions
        self._kitchen = kitchen
        self._viewers = viewers

    async def execute(self, user: User) -> dict[str, Any]:
        viewer = await self._viewers.of(user)
        return {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "exported_at": now_utc(),
            "profile": self._profile(user),
            "consents": [
                {"kind": "health_data", "granted_at": user.consent_health_data_at},
                {"kind": "ai_agents", "granted_at": user.consent_ai_agents_at},
            ],
            "recipes": await self._own_recipes(user),
            "variations": await self._own_variations(user, viewer),
            "ingredients": await self._own_ingredients(user),
            "favourites": await self._favourite_list(user, viewer),
            "ratings": await self._rating_list(user, viewer),
            "notes": await self._note_list(user, viewer),
            "cook_events": await self._cook_events(user, viewer),
            "meal_plan": await self._meal_plan(user, viewer),
            "shopping_lists": await self._shopping_lists(user, viewer),
            "food_restrictions": await self._food_restrictions(user),
            "household": await self._household(user),
            "kitchen": await self._kitchen_data(user),
        }

    @staticmethod
    def _profile(user: User) -> dict[str, Any]:
        return {
            "id": str(user.public_id),
            "full_name": user.full_name,
            "nickname": user.nickname,
            "show_nickname": user.show_nickname,
            "email": user.email,
            "created": user.created,
            "last_logged_in": user.last_logged_in,
            "language": user.language.value,
            "theme": {
                "preset": user.theme_preset.value,
                "surface": user.theme_surface.value,
                "primary": user.theme_primary.value,
                "dark_mode": user.theme_dark_mode,
            },
            "amount_style": user.amount_style.value,
            "permissions": user.permissions,
            "two_factor_enabled": user.totp_enabled,
            "share_restrictions_with_hosts": user.share_restrictions_with_hosts,
            "default_recipe_visibility": user.default_recipe_visibility,
            "show_name_on_public_recipes": user.show_name_on_public_recipes,
            "show_name_on_paired_instances": user.show_name_on_paired_instances,
            "recipe_cards": {
                "tips": user.recipe_show_tips,
                "notes": user.recipe_show_notes,
                "cooked": user.recipe_show_cooked,
                "rating": user.recipe_show_rating,
            },
            "recipe_highlight_mentions": user.recipe_highlight_mentions,
            "keep_screen_on": user.keep_screen_on,
            "privacy_acknowledged_version": user.privacy_acknowledged_version,
            "privacy_acknowledged_at": user.privacy_acknowledged_at,
        }

    async def _visible(self, viewer: Viewer, recipe_ids: list[int]) -> dict[int, Recipe]:
        return {
            r.id: r
            for r in await self._recipes.get_many(sorted(set(recipe_ids)))
            if can_view_recipe(viewer, r)
        }

    def _ref(self, visible: dict[int, Recipe], recipe_id: int | None) -> dict[str, Any] | None:
        """The recipe a record refers to, or a placeholder without a title
        when the user can no longer see it."""
        if recipe_id is None:
            return None
        recipe = visible.get(recipe_id)
        if recipe is None:
            return {"id": None, "title": None, "accessible": False}
        return {"id": str(recipe.public_id), "title": _title(recipe), "accessible": True}

    async def _own_recipes(self, user: User) -> list[dict[str, Any]]:
        return [
            {
                "id": str(recipe.public_id),
                "title": _title(recipe),
                "status": recipe.status.value,
                "visibility": recipe.visibility.value,
                "created": recipe.created,
                "changed": recipe.changed,
                "published_at": recipe.published_at,
                "content": build_snapshot(recipe, await self._revisions.refs(recipe)),
            }
            for recipe in await self._recipes.owned_by(user.id)
        ]

    async def _own_ingredients(self, user: User) -> list[dict[str, Any]]:
        owned = await self._ingredients.get_many(await self._ingredients.ids_owned_by(user.id))
        return [
            {
                "id": str(i.public_id),
                "status": i.status.value,
                "names": {k: v.name for k, v in i.translations.items()},
            }
            for i in owned
        ]

    async def _own_variations(self, user: User, viewer: Viewer) -> list[dict[str, Any]]:
        """The user's variations with their changes as stored (records by
        public id, steps by number at `based_on_revision`)."""
        own = await self._variations.by_author(user.id)
        visible = await self._visible(viewer, [v.recipe_id for v in own])
        return [
            {
                "id": str(v.public_id),
                "recipe": self._ref(visible, v.recipe_id),
                "name": v.name,
                "note": v.note,
                "locale": v.locale,
                "private": v.private,
                "based_on_revision": v.based_on_revision,
                "changes": v.changes,
                "created": v.created,
                "changed": v.changed,
            }
            for v in own
        ]

    async def _variation_refs(self, ids: list[int | None]) -> dict[int, dict[str, Any]]:
        found = await self._variations.get_many(sorted({i for i in ids if i is not None}))
        return {v.id: {"id": str(v.public_id), "name": v.name} for v in found}

    async def _favourite_list(self, user: User, viewer: Viewer) -> list[dict[str, Any] | None]:
        ids = await self._favourites.recipe_ids_of(user.id)
        visible = await self._visible(viewer, ids)
        return [self._ref(visible, i) for i in ids]

    async def _rating_list(self, user: User, viewer: Viewer) -> list[dict[str, Any]]:
        ratings = await self._ratings.list_for_user(user.id)
        visible = await self._visible(viewer, [r.recipe_id for r in ratings])
        variations = await self._variation_refs([r.variation_id for r in ratings])
        return [
            {
                "recipe": self._ref(visible, r.recipe_id),
                "variation": variations.get(r.variation_id) if r.variation_id else None,
                "stars": r.stars,
                "comment": r.comment,
                "created": r.created,
                "changed": r.changed,
            }
            for r in ratings
        ]

    async def _note_list(self, user: User, viewer: Viewer) -> list[dict[str, Any]]:
        notes = await self._notes.list_for_user(user.id)
        visible = await self._visible(viewer, [n.recipe_id for n in notes])
        return [
            {"recipe": self._ref(visible, n.recipe_id), "text": n.text, "changed": n.changed}
            for n in notes
        ]

    async def _cook_events(self, user: User, viewer: Viewer) -> list[dict[str, Any]]:
        events = await self._events.find(user_id=user.id, limit=_ALL_EVENTS)
        visible = await self._visible(viewer, [e.recipe_id for e in events])
        variations = await self._variation_refs([e.variation_id for e in events])
        return [
            {
                "recipe": self._ref(visible, e.recipe_id),
                "variation": variations.get(e.variation_id) if e.variation_id else None,
                "cooked_on": e.cooked_on,
                "servings": e.servings,
                "note": e.note,
                "created": e.created,
            }
            for e in sorted(events, key=lambda e: (e.cooked_on, e.id))
        ]

    async def _meal_plan(self, user: User, viewer: Viewer) -> list[dict[str, Any]]:
        """The entries the user made, in their personal plan and in their
        household's; the other members' entries are theirs."""
        entries = {
            e.id: e
            for scope in {None, viewer.household_id}
            for e in await self._plan.between(user.id, scope, _FIRST_DAY, _LAST_DAY)
            if e.user_id == user.id
        }
        ordered = sorted(entries.values(), key=lambda e: (e.plan_date, e.id))
        visible = await self._visible(viewer, [e.recipe_id for e in ordered if e.recipe_id])
        return [
            {
                "plan_date": e.plan_date,
                "slot": e.slot.value,
                "servings": e.servings,
                "recipe": self._ref(visible, e.recipe_id),
                "title": e.title,
                "household": e.household_id is not None,
            }
            for e in ordered
        ]

    async def _shopping_lists(self, user: User, viewer: Viewer) -> list[dict[str, Any]]:
        units = {u.id: u.code for u in await self._units.list_all()}
        result = []
        for shopping_list in await self._lists.list_for_user(user.id, viewer.household_id):
            items = await self._lists.items(shopping_list.id)
            ingredients = {
                i.id: i
                for i in await self._ingredients.get_many(
                    sorted({i.ingredient_id for i in items if i.ingredient_id})
                )
            }
            result.append(
                {
                    "name": shopping_list.name,
                    "is_owner": shopping_list.owner_id == user.id,
                    "household": shopping_list.household_id is not None,
                    "created": shopping_list.created,
                    "items": [
                        {
                            "name": (
                                _ingredient_name(ingredients[item.ingredient_id])
                                if item.ingredient_id in ingredients
                                else item.text
                            ),
                            "amount": item.amount,
                            "unit": units.get(item.unit_id) if item.unit_id else None,
                            "checked": item.checked,
                        }
                        for item in items
                    ],
                }
            )
        return result

    async def _food_restrictions(self, user: User) -> list[dict[str, Any]]:
        restrictions = await self._restrictions.list_for_user(user.id)
        ingredients = {
            i.id: i
            for i in await self._ingredients.get_many(
                sorted({r.ingredient_id for r in restrictions if r.ingredient_id})
            )
        }
        families = {f.id: f for f in await self._families.list_all()}
        return [
            {
                "kind": r.kind.value,
                "allergen": r.allergen.value if r.allergen else None,
                "ingredient": (
                    _ingredient_name(ingredients[r.ingredient_id])
                    if r.ingredient_id in ingredients
                    else None
                ),
                "family": (
                    resolve(families[r.family_id].translations, None, "en-GB")[1].name
                    if r.family_id in families
                    else None
                ),
                "diet": r.diet.value if r.diet else None,
                "note": r.note,
                "created": r.created,
            }
            for r in restrictions
        ]

    async def _household(self, user: User) -> dict[str, Any] | None:
        household = await self._households.of_user(user.id)
        if household is None:
            return None
        members = [await self._users.get(m) for m in household.member_ids]
        return {
            "name": household.name,
            "created": household.created,
            "members": [m.display_name for m in members if m is not None],
        }

    async def _kitchen_data(self, user: User) -> dict[str, Any] | None:
        kitchen, of_household = await self._kitchen.of(user)
        if kitchen is None:
            return None
        equipment = await self._equipment.get_many(kitchen.equipment_ids)
        return {
            "household": of_household,
            "set_up_at": kitchen.set_up_at,
            "equipment": sorted(resolve(e.translations, None, "en-GB")[1].name for e in equipment),
        }


def _ingredient_name(ingredient: Ingredient) -> str:
    return resolve(ingredient.translations, None, ingredient.original_locale)[1].name
