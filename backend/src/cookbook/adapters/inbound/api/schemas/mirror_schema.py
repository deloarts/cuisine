"""Requests and answers of the administrator's side of mirrors: recipes from
paired instances waiting for a decision and the catalogue mappings per
peer."""

from datetime import datetime
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import Field

from src.cookbook.adapters.inbound.api.schemas.recipe_schema import PeerRef
from src.platform.adapters.inbound.api.schemas.base import RequestSchema
from src.platform.adapters.inbound.api.schemas.base import ResponseSchema

MappingKindValue = Literal["unit", "tag", "ingredient", "equipment"]
DecisionValue = Literal["map", "create", "plain", "none"]


class CatalogueSuggestion(ResponseSchema):
    """A local entry that probably means the same, found by name or alias;
    never taken without a decision."""

    id: UUID
    name: str


class NeededEntryResponse(ResponseSchema):
    """A catalogue entry of the peer without a mapping here. Allowed
    decisions: units `map` or `none`; tags `map`, `create` or `none`;
    ingredients and equipment `map`, `create` or `plain`."""

    kind: MappingKindValue
    source_id: str
    name: str
    names: dict[str, str]
    suggestion: CatalogueSuggestion | None
    # For ingredients: the category a created ingredient would get.
    category_suggestion: CatalogueSuggestion | None
    allergens: list[str]
    diet_markers: list[str]


class IncomingSubRecipe(ResponseSchema):
    source_id: str
    # Null when the peer does not share the sub-recipe with this instance.
    title: str | None
    # Mirrored here already, or waiting in the queue too.
    mirrored: bool
    waiting: bool


class IncomingRecipeResponse(ResponseSchema):
    id: UUID
    peer: PeerRef
    source_id: UUID
    title: str
    description: str
    author_name: str | None
    # pending or rejected.
    status: Literal["pending", "rejected"]
    # new: no mirror yet; update: an update of a mirror that waits for the
    # entries below, while the mirror keeps its previous revision.
    kind: Literal["new", "update"]
    # The mirror a held update belongs to.
    mirror_id: UUID | None
    received_at: datetime
    decided_at: datetime | None
    entries: list[NeededEntryResponse]
    sub_recipes: list[IncomingSubRecipe]


class MappingDecisionRequest(RequestSchema):
    kind: MappingKindValue
    source_id: str = Field(max_length=64)
    action: DecisionValue
    # The local entry for `map`.
    target_id: UUID | None = None
    # For `create` of an ingredient: its category; null leaves it
    # uncategorised.
    category_id: UUID | None = None


class AcceptIncomingRecipeRequest(RequestSchema):
    decisions: list[MappingDecisionRequest] = Field(default_factory=list, max_length=2000)


class AcceptedRecipeResponse(ResponseSchema):
    """The mirror the accepted recipe became or updated."""

    id: UUID
    title: str


class AcceptedWaitingResponse(ResponseSchema):
    """How many waiting recipes of a peer became mirrors."""

    accepted: int


class MappingCorrectionRequest(RequestSchema):
    action: DecisionValue
    target_id: UUID | None = None
    category_id: UUID | None = None


class PeerMappingResponse(ResponseSchema):
    kind: MappingKindValue
    source_id: str
    # The peer's name of the entry.
    name: str
    # map, plain or none; null while undecided.
    action: Literal["map", "plain", "none"] | None
    target_id: UUID | None
    target_name: str | None
    # The local entry was created from the peer's data.
    created_here: bool
    # seed_key (matched automatically) or decision.
    matched_by: Literal["seed_key", "decision"] | None
    # How many mirrors of the peer name the entry.
    used_by: int
    updated: datetime


class PeerSuggestionResponse(ResponseSchema):
    """One field of a local entry with the value a paired instance offers.
    Field names and values follow the catalogue file and the reference data
    updates; references are shown by name and conversions as unit code to
    grams. Other names and conversions show the local value joined with the
    peer's."""

    peer: PeerRef
    # The entry's public id at the peer.
    source_id: str
    field: str
    current: Any
    suggested: Any
    # Conversions only: the peer's units without a mapping here, left out.
    unmapped_units: list[str]


class PeerSuggestionGroupResponse(ResponseSchema):
    """Every suggestion for one local entry. `warning` is true when an
    allergen or diet marker suggestion is among them."""

    kind: MappingKindValue
    id: UUID
    name: str
    warning: bool
    suggestions: list[PeerSuggestionResponse]


class PeerSuggestionRequest(RequestSchema):
    """Names one suggestion: the peer, the kind, the entry's public id at
    the peer and the field."""

    peer_id: UUID
    kind: MappingKindValue
    source_id: str = Field(min_length=1, max_length=64)
    field: str = Field(min_length=1, max_length=64)
