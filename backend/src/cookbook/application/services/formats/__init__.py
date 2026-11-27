"""
The exchange formats: what a recipe or the catalogue looks like when it
leaves this instance as a file (`.cui`, the catalogue file) and, later, as a
peering payload. The rules are in docs/reference/formats.md.

A format is neither the database nor the internal revision snapshot. Each
format version is a set of plain, frozen dataclasses (`recipes_v1.py`,
`catalogue_v1.py`), and mappers translate between the domain and those
dataclasses (`recipe_mapper.py`, `catalogue_mapper.py`), so a migration or a
snapshot refactor never changes what another instance receives. `codec.py`
turns the dataclasses into JSON and back, ignoring unknown fields, and
derives the JSON Schema that `scripts/export_formats.py` checks in.
`specs.py` names every format with its current version and the upgrade chain
that reads older versions.
"""
