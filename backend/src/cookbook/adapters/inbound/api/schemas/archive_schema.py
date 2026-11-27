from typing import Literal

from src.platform.adapters.inbound.api.schemas.base import ResponseSchema


class ImportedRecipeResponse(ResponseSchema):
    # The recipe's id on the exporting instance.
    source_id: str
    # The new draft here, or the earlier import the file updated.
    id: str
    title: str
    # True when the import updated the importer's earlier import of it.
    updated: bool


class ImportConflictResponse(ResponseSchema):
    """Something of the archive that could not be placed as it was."""

    kind: Literal[
        "unit",
        "tag",
        "ingredient",
        "equipment",
        "sub_recipe",
        "image",
        "title",
        "variation",
        "status",
    ]
    name: str
    detail: str
    # The title of the imported recipe it concerns, when it concerns one.
    recipe: str | None


class RecipeImportResponse(ResponseSchema):
    recipes: list[ImportedRecipeResponse]
    # Names of the draft ingredients and equipment items the import created
    # for the catalogue review queue.
    created_ingredients: list[str]
    created_equipment: list[str]
    matched_ingredients: int
    matched_equipment: int
    conflicts: list[ImportConflictResponse]


class EarlierImportResponse(ResponseSchema):
    """A recipe of the importer's that an earlier import of the same source
    recipe created."""

    id: str
    title: str
    status: Literal["draft", "published"]


class ImportPreviewRecipeResponse(ResponseSchema):
    source_id: str
    title: str
    # Set when the importer imported this recipe before; the import then
    # updates it when its source id is among `update`, else adds a new copy.
    earlier: EarlierImportResponse | None


class RecipeImportPreviewResponse(ResponseSchema):
    recipes: list[ImportPreviewRecipeResponse]
