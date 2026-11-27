"""Who may see and change a recipe or an ingredient, and the shape rules a
recipe must follow.

A draft is its owner's alone. A published recipe is visible to its owner
and, by its visibility, to nobody else, the owner's household, the chosen
users and groups, every signed-in user (instance), every signed-in user and
every paired instance (peers), or anyone (public).
Private means private for administrators too: manage:recipes only reaches
recipes the manager can see.

A public recipe reads as an instance recipe while the instance does not
allow public recipes, and a peers recipe reads as an instance recipe while
peering is off (`effective_visibility`). A signed-in viewer reads all three
alike; the difference matters for the anonymous visitor of the public pages,
who reads only published recipes that are public in effect, for paired
instances, for the sub-recipe rule and for what responses report."""

from dataclasses import dataclass

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import InvalidRecipeError
from src.cookbook.domain.exceptions import MirrorReadOnlyError
from src.cookbook.domain.exceptions import NotOwnerError
from src.cookbook.domain.services.translations import assert_translations
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.domain.value_objects.viewer import Viewer
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

MAX_SERVINGS = 100
MAX_MINUTES = 10_000
MAX_STEPS = 100
MAX_INGREDIENTS_PER_STEP = 50
MAX_DECLARED_INGREDIENTS = 200


@dataclass(frozen=True)
class VisibilitySwitches:
    """The instance switches a stored visibility is read through: whether
    public recipes are allowed and whether peering is on."""

    public_allowed: bool = False
    peering: bool = False

    def effective(self, visibility: RecipeVisibility) -> RecipeVisibility:
        return effective_visibility(
            visibility, public_allowed=self.public_allowed, peering=self.peering
        )


def effective_visibility(
    visibility: RecipeVisibility, *, public_allowed: bool, peering: bool = False
) -> RecipeVisibility:
    """The visibility that applies: public reads as instance while the
    instance does not allow public recipes, and peers reads as instance
    while peering is off. The stored value never changes."""
    if visibility is RecipeVisibility.PUBLIC and not public_allowed:
        return RecipeVisibility.INSTANCE
    if visibility is RecipeVisibility.PEERS and not peering:
        return RecipeVisibility.INSTANCE
    return visibility


def can_view_recipe(viewer: Viewer, recipe: Recipe) -> bool:
    if viewer.anonymous:
        # A visitor who is not signed in reads a published recipe whose
        # effective visibility is public, so nothing while the instance
        # does not allow public recipes. The SQL filter of the recipe
        # repository repeats this rule.
        return (
            recipe.status is RecipeStatus.PUBLISHED
            and effective_visibility(recipe.visibility, public_allowed=viewer.public_allowed)
            is RecipeVisibility.PUBLIC
        )
    if recipe.owner_id is not None and recipe.owner_id == viewer.id:
        return True
    if recipe.status is not RecipeStatus.PUBLISHED:
        return False
    match recipe.visibility:
        case RecipeVisibility.INSTANCE | RecipeVisibility.PEERS | RecipeVisibility.PUBLIC:
            # A signed-in user of this instance reads peers and public
            # recipes whether or not peering is on and public recipes are
            # allowed.
            return True
        case RecipeVisibility.HOUSEHOLD:
            return recipe.owner_id is not None and recipe.owner_id in viewer.household_member_ids
        case RecipeVisibility.SHARED:
            return viewer.id in recipe.shared_user_ids or bool(
                viewer.group_ids & set(recipe.shared_group_ids)
            )
        case _:
            return False


def can_edit_recipe(viewer: Viewer, recipe: Recipe) -> bool:
    """The content: the owner and the co-editors with write:recipes, and
    manage:recipes, each only on a recipe they can see. Nobody edits a
    mirror; it changes only at its source."""
    if recipe.is_mirror or not can_view_recipe(viewer, recipe):
        return False
    if viewer.user.has_permission(Permission.MANAGE_RECIPES):
        return True
    if not viewer.user.has_permission(Permission.WRITE_RECIPES):
        return False
    return recipe.owner_id == viewer.id or viewer.id in recipe.co_editor_ids


def can_delete_recipe(viewer: Viewer, recipe: Recipe) -> bool:
    """Deleting, publishing and unpublishing: the owner with write:recipes
    or manage:recipes; never a co-editor as such, and nobody on a mirror,
    which goes only when its source withdraws it."""
    if recipe.is_mirror or not can_view_recipe(viewer, recipe):
        return False
    if viewer.user.has_permission(Permission.MANAGE_RECIPES):
        return True
    return viewer.user.has_permission(Permission.WRITE_RECIPES) and recipe.owner_id == viewer.id


def can_manage_co_editors(viewer: Viewer, recipe: Recipe) -> bool:
    """Only the owner chooses who edits the recipe with them."""
    return recipe.owner_id is not None and recipe.owner_id == viewer.id


_REACH = {
    RecipeVisibility.PRIVATE: 0,
    RecipeVisibility.HOUSEHOLD: 1,
    RecipeVisibility.SHARED: 1,
    RecipeVisibility.INSTANCE: 2,
    RecipeVisibility.PEERS: 3,
    RecipeVisibility.PUBLIC: 4,
}


def narrower(sub: Recipe, parent: Recipe, *, public_allowed: bool, peering: bool = False) -> bool:
    """Whether some reader of `parent` may not see `sub`. Both are judged by
    their effective visibility, so an instance sub-recipe of a public recipe
    only counts as narrower while public recipes are allowed, and one of a
    peers recipe only while peering is on."""
    sub_visibility = effective_visibility(
        sub.visibility, public_allowed=public_allowed, peering=peering
    )
    parent_visibility = effective_visibility(
        parent.visibility, public_allowed=public_allowed, peering=peering
    )
    if sub.status is not RecipeStatus.PUBLISHED:
        return sub.owner_id != parent.owner_id or parent_visibility is not RecipeVisibility.PRIVATE
    if parent_visibility is RecipeVisibility.PRIVATE and sub.owner_id == parent.owner_id:
        return False
    reach_sub, reach_parent = _REACH[sub_visibility], _REACH[parent_visibility]
    if reach_sub != reach_parent:
        return reach_sub < reach_parent
    if sub_visibility in (
        RecipeVisibility.INSTANCE,
        RecipeVisibility.PEERS,
        RecipeVisibility.PUBLIC,
    ):
        return False
    if sub_visibility is not parent_visibility or sub.owner_id != parent.owner_id:
        return True
    if sub_visibility is RecipeVisibility.SHARED:
        return not (
            set(parent.shared_user_ids) <= set(sub.shared_user_ids)
            and set(parent.shared_group_ids) <= set(sub.shared_group_ids)
        )
    return False


def can_change_visibility(viewer: Viewer, recipe: Recipe) -> bool:
    """Only the owner decides who sees a recipe; a manager edits content."""
    return recipe.owner_id is not None and recipe.owner_id == viewer.id


def assert_not_mirror(viewer: Viewer, recipe: Recipe) -> None:
    """A mirror the viewer can see answers that it is read only, rather than
    that the viewer lacks a permission."""
    if recipe.is_mirror and can_view_recipe(viewer, recipe):
        raise MirrorReadOnlyError(
            "This recipe comes from another instance and is read only here; copy it as your "
            "own recipe to change it."
        )


def assert_can_edit_recipe(viewer: Viewer, recipe: Recipe) -> None:
    assert_not_mirror(viewer, recipe)
    if not can_edit_recipe(viewer, recipe):
        raise NotOwnerError("Only its author or someone with manage:recipes may change it.")


def assert_can_delete_recipe(viewer: Viewer, recipe: Recipe) -> None:
    assert_not_mirror(viewer, recipe)
    if not can_delete_recipe(viewer, recipe):
        raise NotOwnerError(
            "Only its owner or someone with manage:recipes may delete, publish or unpublish it."
        )


def can_edit_ingredient(user: User, ingredient: Ingredient) -> bool:
    if user.has_permission(Permission.MANAGE_INGREDIENTS):
        return True
    return user.has_permission(Permission.WRITE_INGREDIENTS) and ingredient.owner_id == user.id


def assert_can_edit_ingredient(user: User, ingredient: Ingredient) -> None:
    if not can_edit_ingredient(user, ingredient):
        raise NotOwnerError("Only its author or someone with manage:ingredients may change it.")


def _minutes(value: int | None, what: str) -> None:
    if value is not None and not 0 <= value <= MAX_MINUTES:
        raise InvalidRecipeError(f"The {what} must be between 0 and {MAX_MINUTES} minutes.")


def validate_recipe(recipe: Recipe) -> None:
    assert_translations(recipe.translations, recipe.original_locale, "recipe")
    for text in recipe.translations.values():
        if not text.title.strip():
            raise InvalidRecipeError("Every translation of the recipe needs a title.")
    if not 1 <= recipe.base_servings <= MAX_SERVINGS:
        raise InvalidRecipeError(f"The servings must be between 1 and {MAX_SERVINGS}.")
    _minutes(recipe.prep_minutes, "preparation time")
    _minutes(recipe.cook_minutes, "cooking time")
    _minutes(recipe.rest_minutes, "resting time")
    if recipe.source_url and not recipe.source_url.startswith(("http://", "https://")):
        raise InvalidRecipeError("The source must be an http or https address.")
    if recipe.yield_amount is not None and recipe.yield_amount <= 0:
        raise InvalidRecipeError("The yield must be positive.")
    if (recipe.yield_amount is None) != (recipe.yield_unit_id is None):
        raise InvalidRecipeError("A yield needs an amount and a unit.")
    if len(recipe.steps) > MAX_STEPS:
        raise InvalidRecipeError(f"A recipe has at most {MAX_STEPS} steps.")
    for number, step in enumerate(recipe.steps, start=1):
        if (
            recipe.original_locale not in step.translations
            or not step.translations[recipe.original_locale].text.strip()
        ):
            raise InvalidRecipeError(f"Step {number} needs its text in the original language.")
        _minutes(step.duration_minutes, f"duration of step {number}")
        if len(step.ingredients) > MAX_INGREDIENTS_PER_STEP:
            raise InvalidRecipeError(f"Step {number} has too many ingredients.")
        for si in step.ingredients:
            if (si.ingredient_id is None) == (si.sub_recipe_id is None):
                raise InvalidRecipeError(
                    f"Every ingredient of step {number} names an ingredient or a recipe."
                )
            if si.amount is not None and si.amount < 0:
                raise InvalidRecipeError(f"Step {number} has a negative amount.")
    if len(recipe.ingredients) > MAX_DECLARED_INGREDIENTS:
        raise InvalidRecipeError("The ingredient list of the recipe is too long.")
    for line in recipe.ingredients:
        if (line.ingredient_id is None) == (line.sub_recipe_id is None):
            raise InvalidRecipeError(
                "Every line of the ingredient list names an ingredient or a recipe."
            )
        if line.amount is not None and line.amount < 0:
            raise InvalidRecipeError("The ingredient list has a negative amount.")


def validate_publishable(recipe: Recipe) -> None:
    validate_recipe(recipe)
    if not recipe.steps:
        raise InvalidRecipeError("A recipe needs at least one step before it is published.")
