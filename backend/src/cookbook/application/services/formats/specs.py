"""
Every exchange format with its current version, the dataclasses of every
version ever released (for the JSON Schema files) and the upgrade chain that
reads older versions.

Reading a document checks its `format`, then upgrades the raw JSON one
version at a time (`upgrades[n]` turns version n into n + 1) until it has
the current version, and reads that into the current dataclasses. Adding a
version therefore means: new dataclasses, the mappers writing them, one
upgrade function from the previous version, and an entry in `versions`.
A document of a newer version than this release knows is refused with a
message naming both versions.
"""

from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.cookbook.application.services.formats import catalogue_v1
from src.cookbook.application.services.formats import recipes_v1
from src.cookbook.application.services.formats.codec import FormatError
from src.cookbook.application.services.formats.codec import read

type Upgrade = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class FormatSpec[T]:
    name: str
    current: int
    # The dataclass of each released version, the current one included.
    versions: Mapping[int, type]
    # From version n to n + 1, for every n below the current version.
    upgrades: Mapping[int, Upgrade]
    # A human name for messages, such as "recipe file".
    label: str

    @property
    def document(self) -> type[T]:
        document: type[T] = self.versions[self.current]
        return document

    def upgrade(self, raw: Any) -> dict[str, Any]:
        """The raw document in the current version's shape."""
        if not isinstance(raw, dict) or raw.get("format") != self.name:
            raise FormatError(f"This is not a Cuisine {self.label}.")
        version = raw.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise FormatError(f"This {self.label} has no valid format version.")
        if version > self.current:
            raise FormatError(
                f"This {self.label} has format version {version}, made by a newer Cuisine; "
                f"this instance reads up to version {self.current}."
            )
        document: dict[str, Any] = dict(raw)
        while version < self.current:
            document = self.upgrades[version](document)
            version += 1
            document["version"] = version
        return document

    def read(self, raw: Any) -> T:
        """The raw document of any released version, read as the current
        version's dataclass."""
        return read(self.document, self.upgrade(raw))


RECIPES: FormatSpec[recipes_v1.RecipesDocumentV1] = FormatSpec(
    name=recipes_v1.FORMAT,
    current=1,
    versions={1: recipes_v1.RecipesDocumentV1},
    upgrades={},
    label="recipe file",
)

CATALOGUE: FormatSpec[catalogue_v1.CatalogueDocumentV1] = FormatSpec(
    name=catalogue_v1.FORMAT,
    current=1,
    versions={1: catalogue_v1.CatalogueDocumentV1},
    upgrades={},
    label="catalogue file",
)

FORMATS: tuple[FormatSpec[Any], ...] = (RECIPES, CATALOGUE)
