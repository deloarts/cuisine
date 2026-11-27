# formats

The exchange formats: what recipes and the catalogue look like when they leave an instance as a file, and later as a peering payload. The concept is in [CONTRIBUTING.md section 1](../CONTRIBUTING.md#1-architecture-in-one-page); exporting and importing recipes as `.cui` files is in [cookbook.md section 3e](cookbook.md#3e-recipe-export-and-import-cui).

- [1 formats and versions](#1-formats-and-versions)
- [2 where the code lives](#2-where-the-code-lives)
- [3 the cuisine-recipes document](#3-the-cuisine-recipes-document)
- [4 the cuisine-catalogue document](#4-the-cuisine-catalogue-document)
- [5 compatibility rules](#5-compatibility-rules)
- [6 adding a version](#6-adding-a-version)
- [7 schema files and golden fixtures](#7-schema-files-and-golden-fixtures)
- [8 peering protocol messages](#8-peering-protocol-messages)

## 1 formats and versions

1. Two formats exist, each with its own version number: `cuisine-recipes` (the `recipes.json` of a `.cui` file, a zip with media type `application/vnd.cuisine.recipe+zip` that also holds the images under `files/`) and `cuisine-catalogue` (one JSON file). Both are at version 1.
2. Three kinds of version are kept apart. The app version is informative only and never decides anything. The format versions say how a document is shaped. The peering protocol version (the `/api/peering/v1` path) and its negotiation are in [peering.md section 5](peering.md#5-versions-and-the-support-window).
3. A document names its format and version at the top (`format`, `version`). A reader refuses a document of another format, and a version newer than it knows, with a message naming both versions.
4. A format is neither the database nor the internal revision snapshot ([cookbook.md section 3c](cookbook.md#3c-recipe-revisions)). A migration or a snapshot refactor never changes a document; only a change to the format dataclasses does.

## 2 where the code lives

1. `src/cookbook/application/services/formats/` holds the format layer. It is an application service rather than an adapter because the archive use case builds and reads the documents itself; it uses plain, frozen standard library dataclasses and pure functions, no Pydantic, no SQLAlchemy and no I/O.
2. `recipes_v1.py` and `catalogue_v1.py` declare the dataclasses of each version. Their field lists are the contract.
3. `recipe_mapper.py` and `catalogue_mapper.py` translate domain records into those dataclasses, naming every field they write. The recipe mapper does not go through `revisions.build_snapshot`; it uses `SnapshotRefs` only as the lookup from internal ids to public ids and names.
4. `codec.py` turns dataclasses into JSON (`to_json`), reads JSON back into them (`read`) and derives their JSON Schema (`json_schema`). Format fields use only `str`, `int`, `float`, `bool`, `Any`, `Literal`, another format dataclass, `list[X]`, `dict[str, X]` and `X | None`; the `doc` entry of a field's metadata becomes its description in the schema.
5. `specs.py` names each format (`RECIPES`, `CATALOGUE`) with its current version, the dataclasses of every released version and the upgrade chain. `FormatSpec.read(raw)` is the one entry point for reading a document.
6. The import side (matching catalogue entries, remapping ids, creating drafts) stays in the use case that imports, such as `RecipeArchive`; it works on the dataclasses, never on raw JSON.

## 3 the cuisine-recipes document

1. Top level: `format`, `version`, `exported_at`, `instance_id` (the exporting instance, so a recipe is identified at its source by `instance_id` and its own `id`), `recipes`, `catalogue` and `files`.
2. Each recipe entry has its public id at the source (`id`), `title`, `status`, its content under `snapshot`, its `variations` and `author_name`, the author's display name, which only peering payloads set and only while the author shows it on paired instances; `author_avatar`, set under the same rule, names the entry of `files` that holds the author's avatar. The content key is called `snapshot` because the first release wrote the revision snapshot there; the field list in `RecipeContentV1` is the contract now. Status, visibility, shares and the personal layer (ratings, notes, favourites, cook events) are never part of a document.
3. The content's `ingredients` holds the recipe's declared ingredient list in the shape of a step's lines; it was added to version 1 with an empty default, so files without it read as recipes whose steps alone count ([cookbook.md section 3](cookbook.md#3-recipes-and-what-is-derived)).
3a. Steps, ingredient lines, declared lines and equipment lines carry their public ids at the source (`id`), and so do variations. An importer never takes them over as its own; it derives its ids from them and the local recipe's public id, so updating an earlier import recognises the same step, line or variation again ([cookbook.md section 3e](cookbook.md#3e-recipe-export-and-import-cui)), and a peer can compare two revisions.
4. Records are named by public id: ingredients, units, tags and equipment by the key of their entry in `catalogue`, sub-recipes by the `id` of another recipe of the document, images by the key of their entry in `files`. `names` in the content records the names of everything the recipe refers to, so an importer can name what it could not place.
5. A variation carries its public id at the source, name, note, locale, `private` and its changes in the shape of the variation rules ([cookbook.md section 3f](cookbook.md#3f-variations-co-editors-and-copies)), records again by public id. A document carries the variations the exporter may see (`can_view_variation`): those as visible as the recipe, and a private one only when the exporter is its author.
6. `author_name` of a variation is the author's display name, never the full name behind a nickname or the e-mail address, and only when the exporter is the author or the author's "show my name on paired instances" setting is on; otherwise it is null. A file goes wherever its holder sends it, so the setting meant for other instances applies to files too. Its `author_avatar` is set in peering payloads only, under the same rule as the name, and names an entry of `files`.
7. The `catalogue` holds an entry for every unit, tag, ingredient and equipment item the recipes and their variations name, including the units of the ingredients' conversions.

## 4 the cuisine-catalogue document

1. Top level: `format`, `version`, `exported_at`, `instance_id`, and `units`, `tags`, `categories`, `families`, `ingredients` and `equipment`, each an object keyed by the entry's public id at the source. It carries no images.
2. An ingredient entry holds names and plural names per locale, aliases, its category and family (seed key, names and source id), nutrition, extended nutrients, season months, density, conversions (by unit key), allergens and diet markers. Units carry code, kind, factor, names, plural names and abbreviations; tags carry kind and colour; equipment carries kind, names, aliases, icon and the `basic` flag.
3. Version 1 of `cuisine-recipes` uses the same entry dataclasses for its `catalogue`, so both documents match entries the same way (`application/services/catalogue_matching.py`): seed key first, then name or alias in any language, units by code. The source public id is never taken over. An ingredient's `category` and `family` carry the source `id`, so a catalogue file importer resolves them to the entry of the same document first; conversions name a key of the document's `units`. Exporting and importing the catalogue file is in [cookbook.md section 4d](cookbook.md#4d-the-catalogue-file).
4. Enum values (unit and tag kinds, allergens, diet markers, equipment kinds) travel as text. A reader that does not know a value keeps it where it can and reports it where it cannot; an importer never fails on it.

## 5 compatibility rules

1. Within a format version, changes are additive only: a new field always has a default, and no field is renamed, retyped, removed or given another meaning. A change of meaning in allergens, markers, units or amounts is always breaking and bumps the version.
2. Readers ignore every field they do not know, at every level, so a document from a newer release of the same version still reads. A missing field takes its default; a missing required field or a value of the wrong type refuses the document with the path of the value (422 `RecipeArchiveError` for an archive, 422 `CatalogueFileError` for a catalogue file).
3. Files import forever: an importer reads every format version ever released, through the upgrade chain. The support window of the current and the previous version applies to the peering protocol only, not to files.
4. A writer always writes the current version.

## 6 adding a version

1. Copy the current version's module to a new one (`recipes_v2.py`) and change it there; a released module is never edited except to add fields with defaults.
2. Write one upgrade function that turns a raw version 1 document into a raw version 2 document and register it in `specs.py` under `upgrades[1]`; add the new dataclass under `versions[2]` and raise `current`. The chain applies the upgrades one after the other, so version 3 needs only `upgrades[2]`.
3. Point the mappers and the importing use case at the new dataclasses.
4. Run `make formats` to write the new schema file, and add a golden fixture for the new version (section 7). The CHANGELOG and [RELEASING.md](../RELEASING.md) mark the release that bumps a format version.

## 7 schema files and golden fixtures

1. `backend/formats/<format>.v<version>.schema.json` holds the JSON Schema (draft 2020-12) of every released version, derived from the dataclasses by `scripts/export_formats.py` (`make formats`). They are committed; `--check` exits 1 when a file is out of date or belongs to no known version, and runs in `make gates`, CI and as the `export-formats` pre-commit hook. Unknown properties are allowed everywhere, as readers ignore them. Never edit a schema file by hand.
2. `tests/unit/test_formats.py` checks that the schema files match the dataclasses, that the upgrade chain covers every released version, and that a catalogue document validates against its schema and reads back unchanged. `tests/integration/test_recipe_formats.py` checks that an export validates against the recipe schema.
3. One golden fixture per format version lives in `backend/tests/fixtures/formats/` (`cuisine-recipes.v1.cui`, written once by the exporter of the first release) and must import on every build with the asserted result. A golden fixture is never regenerated or edited: it is the proof that old files still import. A new version adds its own fixture next to it.

## 8 peering protocol messages

1. The messages of the peering protocol have JSON Schemas too, per protocol version: `backend/formats/cuisine-peering.v<version>.<message>.schema.json` for `handshake-request`, `handshake-response`, `hello-response`, `event` and `changes-response` ([peering.md](peering.md) describes each). They are derived from the dataclasses in `src/platform/application/services/peering_messages.py` (`PROTOCOL_MESSAGES`) by the same `scripts/export_formats.py`, with the same `--check` in `make gates`, CI and the `export-formats` pre-commit hook.
2. The rules of section 5 apply: within a protocol version, messages change additively only and readers ignore unknown fields; a breaking change is a new protocol version with its own dataclasses and schema files. `tests/integration/test_peer_channels.py` validates real messages of both instances against the schemas.
