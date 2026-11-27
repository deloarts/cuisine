"""
What the source of a mirror says about allergens and diet markers, joined
with this instance's catalogue when a mirror is read.

Everything else derived on a mirror comes from the local catalogue. For
safety, allergens and diet markers are the union of both: each local
ingredient a peer's ingredient maps to carries, inside that peer's mirrors,
the allergens and markers the peer sent for it (kept with the mapping, the
latest the peer sent); plain-text lines carry the peer's own. An allergen or
marker this release does not know is kept as unknown: the recipe then fits
no diet, and the viewer's warnings and the dinner guest check treat every
restriction of that kind as possibly not fitting. Over-warning is the
intended failure direction, so a tree mixing a mirror and local recipes may
warn about the local part too.

The mirror's own details (source URL, author, plain lines) are assembled
here as `MirrorInfo` for the detail.
"""

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from datetime import datetime
from typing import Any

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.mirror import MappingAction
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.entities.mirror import RecipeMirror
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.diet_rules import breaks
from src.cookbook.domain.services.restriction_rules import RestrictionWarning
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository


def _known_allergens(values: Iterable[str]) -> frozenset[Allergen]:
    return frozenset(Allergen(v) for v in values if v in Allergen)


def _known_markers(values: Iterable[str]) -> frozenset[DietMarker]:
    return frozenset(DietMarker(v) for v in values if v in DietMarker)


def _unknown_allergens(values: Iterable[str]) -> frozenset[str]:
    return frozenset(v for v in values if v not in Allergen)


def _unknown_markers(values: Iterable[str]) -> frozenset[str]:
    return frozenset(v for v in values if v not in DietMarker)


@dataclass(frozen=True)
class SourceFacts:
    # Per local ingredient, what the peer said about its own ingredient.
    by_ingredient: dict[int, tuple[frozenset[Allergen], frozenset[DietMarker]]] = field(
        default_factory=dict
    )
    plain_allergens: frozenset[Allergen] = frozenset()
    plain_markers: frozenset[DietMarker] = frozenset()
    unknown_allergens: frozenset[str] = frozenset()
    unknown_markers: frozenset[str] = frozenset()

    @property
    def empty(self) -> bool:
        return not (
            self.by_ingredient
            or self.plain_allergens
            or self.plain_markers
            or self.unknown_allergens
            or self.unknown_markers
        )

    def ingredients(self, base: Mapping[int, Ingredient]) -> Mapping[int, Ingredient]:
        """The lookups with the peer's allergens and markers added to the
        local ingredients they map to."""
        if not self.by_ingredient:
            return base
        result = dict(base)
        for ingredient_id, (allergens, markers) in self.by_ingredient.items():
            local = base.get(ingredient_id)
            if local is None:
                continue
            result[ingredient_id] = replace(
                local,
                allergens=sorted(set(local.allergens) | allergens, key=lambda a: a.value),
                diet_markers=sorted(set(local.diet_markers) | markers, key=lambda m: m.value),
            )
        return result

    def allergens(self, derived: Iterable[Allergen]) -> list[Allergen]:
        return sorted(set(derived) | self.plain_allergens, key=lambda a: a.value)

    def diets(self, derived: Iterable[Diet]) -> list[Diet]:
        """No diet is claimed while a marker is unknown."""
        if self.unknown_markers:
            return []
        return [d for d in derived if not breaks(d, self.plain_markers)]

    def warnings(self, restrictions: Iterable[FoodRestriction]) -> list[RestrictionWarning]:
        """The restrictions that plain-text lines or unknown values break
        or might break; they name no local ingredient."""
        found = []
        for restriction in restrictions:
            hit = False
            if restriction.allergen is not None:
                hit = restriction.allergen in self.plain_allergens or bool(self.unknown_allergens)
            elif restriction.diet is not None:
                hit = breaks(restriction.diet, self.plain_markers) or bool(self.unknown_markers)
            if hit:
                found.append(
                    RestrictionWarning(
                        restriction_id=restriction.id,
                        kind=restriction.kind,
                        allergen=restriction.allergen,
                        ingredient_id=restriction.ingredient_id,
                        diet=restriction.diet,
                        family_id=restriction.family_id,
                        matching_ingredient_ids=[],
                    )
                )
        return found

    def merged(self, other: "SourceFacts") -> "SourceFacts":
        by_ingredient = dict(self.by_ingredient)
        for key, (allergens, markers) in other.by_ingredient.items():
            mine = by_ingredient.get(key, (frozenset(), frozenset()))
            by_ingredient[key] = (mine[0] | allergens, mine[1] | markers)
        return SourceFacts(
            by_ingredient=by_ingredient,
            plain_allergens=self.plain_allergens | other.plain_allergens,
            plain_markers=self.plain_markers | other.plain_markers,
            unknown_allergens=self.unknown_allergens | other.unknown_allergens,
            unknown_markers=self.unknown_markers | other.unknown_markers,
        )


def merge_warnings(
    found: list[RestrictionWarning], extra: list[RestrictionWarning]
) -> list[RestrictionWarning]:
    """One warning per restriction."""
    seen = {w.restriction_id for w in found}
    return [*found, *(w for w in extra if w.restriction_id not in seen)]


@dataclass(frozen=True)
class PlainLine:
    step: int
    position: int
    names: dict[str, str]
    amount: float | None
    unit_id: str | None
    notes: dict[str, str]
    allergens: list[str]
    diet_markers: list[str]
    labels: dict[str, str]


@dataclass(frozen=True)
class PlainEquipment:
    step: int
    names: dict[str, str]
    count: int | None
    notes: dict[str, str]


@dataclass(frozen=True)
class UnlinkedSubRecipe:
    step: int
    position: int
    titles: dict[str, str]
    amount: float | None
    unit_id: str | None


def mirror_author_avatar(mirror: RecipeMirror) -> str | None:
    """The local public id of the avatar the source sent with the recipe
    author's name, or None."""
    value = mirror.extras.get("author_avatar")
    return str(value) if value else None


def mirrored_variation_avatar(mirror: RecipeMirror, origin_public_id: str) -> str | None:
    """The local public id of the avatar the source sent with the name of
    a mirrored variation's author, or None."""
    avatars = mirror.extras.get("variation_author_avatars") or {}
    value = avatars.get(origin_public_id.lower()) if isinstance(avatars, dict) else None
    return str(value) if value else None


@dataclass(frozen=True)
class MirrorInfo:
    peer_id: str
    instance_name: str
    author_name: str | None
    # The local public id of the author's avatar, sent with the name.
    author_avatar: str | None
    # `<peer base url>/r/<origin public id>`.
    source_url: str
    source_revision: str
    accepted_at: datetime
    updated_at: datetime
    plain_lines: list[PlainLine]
    plain_equipment: list[PlainEquipment]
    unlinked_sub_recipes: list[UnlinkedSubRecipe]


def _plain_lines(extras: Mapping[str, Any]) -> list[PlainLine]:
    return [
        PlainLine(
            step=int(line.get("step", 0)),
            position=int(line.get("position", 0)),
            names={str(k): str(v) for k, v in (line.get("names") or {}).items()},
            amount=line.get("amount"),
            unit_id=line.get("unit_id"),
            notes={str(k): str(v) for k, v in (line.get("notes") or {}).items()},
            allergens=[str(a) for a in line.get("allergens") or []],
            diet_markers=[str(m) for m in line.get("diet_markers") or []],
            labels={str(k): str(v) for k, v in (line.get("labels") or {}).items()},
        )
        for line in extras.get("plain_lines") or []
    ]


class MirrorFacts:
    def __init__(self, *, mirror_repo: IMirrorRepository, peer_repo: IPeerRepository) -> None:
        self._mirrors = mirror_repo
        self._peers = peer_repo

    @staticmethod
    def _tree(recipe: Recipe, tree: Mapping[int, Recipe]) -> set[int]:
        """The recipe and every sub-recipe below it."""
        found = {recipe.id}
        frontier = list(recipe.sub_recipe_ids)
        while frontier:
            sub_id = frontier.pop()
            if sub_id in found or sub_id not in tree:
                continue
            found.add(sub_id)
            frontier.extend(tree[sub_id].sub_recipe_ids)
        return found

    async def for_recipes(
        self, recipes: list[Recipe], tree: Mapping[int, Recipe]
    ) -> dict[int, SourceFacts]:
        """Per recipe whose tree holds a mirror, what the sources add."""
        everything = {**tree, **{r.id: r for r in recipes}}
        mirror_ids = [r.id for r in everything.values() if r.is_mirror]
        if not mirror_ids:
            return {}
        mirrors = await self._mirrors.for_recipes(mirror_ids)
        known: dict[int, dict[int, tuple[frozenset[Allergen], frozenset[DietMarker]]]] = {}
        unknown: dict[int, dict[int, tuple[frozenset[str], frozenset[str]]]] = {}
        for peer_id in {m.peer_id for m in mirrors.values()}:
            known[peer_id], unknown[peer_id] = {}, {}
            for mapping in await self._mirrors.mappings(peer_id):
                if (
                    mapping.kind is not MappingKind.INGREDIENT
                    or mapping.action is not MappingAction.MAP
                    or mapping.local_id is None
                ):
                    continue
                allergens = [str(a) for a in mapping.remote_data.get("allergens") or []]
                markers = [str(m) for m in mapping.remote_data.get("diet_markers") or []]
                mine = known[peer_id].get(mapping.local_id, (frozenset(), frozenset()))
                known[peer_id][mapping.local_id] = (
                    mine[0] | _known_allergens(allergens),
                    mine[1] | _known_markers(markers),
                )
                odd = unknown[peer_id].get(mapping.local_id, (frozenset(), frozenset()))
                unknown[peer_id][mapping.local_id] = (
                    odd[0] | _unknown_allergens(allergens),
                    odd[1] | _unknown_markers(markers),
                )
        own: dict[int, SourceFacts] = {}
        for recipe_id, mirror in mirrors.items():
            recipe = everything.get(recipe_id)
            if recipe is None:
                continue
            used = set(recipe.ingredient_ids)
            plain = _plain_lines(mirror.extras)
            plain_allergens = [a for line in plain for a in line.allergens]
            plain_markers = [m for line in plain for m in line.diet_markers]
            odd_allergens = _unknown_allergens(plain_allergens)
            odd_markers = _unknown_markers(plain_markers)
            for ingredient_id, (ua, um) in unknown[mirror.peer_id].items():
                if ingredient_id in used:
                    odd_allergens |= ua
                    odd_markers |= um
            own[recipe_id] = SourceFacts(
                by_ingredient={k: v for k, v in known[mirror.peer_id].items() if k in used},
                plain_allergens=_known_allergens(plain_allergens),
                plain_markers=_known_markers(plain_markers),
                unknown_allergens=odd_allergens,
                unknown_markers=odd_markers,
            )
        result: dict[int, SourceFacts] = {}
        for recipe in recipes:
            facts = SourceFacts()
            for member in self._tree(recipe, everything):
                if member in own:
                    facts = facts.merged(own[member])
            if not facts.empty:
                result[recipe.id] = facts
        return result

    async def info(self, recipe: Recipe) -> MirrorInfo | None:
        """The mirror's details for its page."""
        if not recipe.is_mirror:
            return None
        mirror: RecipeMirror | None = await self._mirrors.get(recipe.id)
        peer = await self._peers.get(recipe.mirror_peer_id) if recipe.mirror_peer_id else None
        if mirror is None or peer is None:
            return None
        extras = mirror.extras
        return MirrorInfo(
            peer_id=str(peer.public_id),
            instance_name=peer.name,
            author_name=mirror.source_author_name,
            author_avatar=mirror_author_avatar(mirror),
            source_url=f"{peer.base_url.rstrip('/')}/r/{mirror.origin_public_id}",
            source_revision=mirror.source_revision,
            accepted_at=mirror.accepted_at,
            updated_at=mirror.updated_at,
            plain_lines=_plain_lines(extras),
            plain_equipment=[
                PlainEquipment(
                    step=int(item.get("step", 0)),
                    names={str(k): str(v) for k, v in (item.get("names") or {}).items()},
                    count=item.get("count"),
                    notes={str(k): str(v) for k, v in (item.get("notes") or {}).items()},
                )
                for item in extras.get("plain_equipment") or []
            ],
            unlinked_sub_recipes=[
                UnlinkedSubRecipe(
                    step=int(item.get("step", 0)),
                    position=int(item.get("position", 0)),
                    titles={str(k): str(v) for k, v in (item.get("titles") or {}).items()},
                    amount=item.get("amount"),
                    unit_id=item.get("unit_id"),
                )
                for item in extras.get("unlinked_sub_recipes") or []
            ],
        )

    async def instance_names(
        self, recipes: Iterable[Recipe]
    ) -> dict[int, tuple[str, str | None, str | None]]:
        """Per mirror, the source instance's name, the author's name and the
        author's avatar, for the summaries."""
        ids = [r.id for r in recipes if r.is_mirror]
        if not ids:
            return {}
        mirrors = await self._mirrors.for_recipes(ids)
        names: dict[int, str] = {}
        for peer_id in {m.peer_id for m in mirrors.values()}:
            peer = await self._peers.get(peer_id)
            names[peer_id] = peer.name if peer is not None else ""
        return {
            recipe_id: (names.get(m.peer_id, ""), m.source_author_name, mirror_author_avatar(m))
            for recipe_id, m in mirrors.items()
        }
