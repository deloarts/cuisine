# Cuisine Backend

See the root [CLAUDE.md](../CLAUDE.md) for what to run, the Don't list, and where every rule is
documented.

## Backend-specific

- Conventions: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md) sections 1 to 3 and 6 for the
  concepts; the rules are in [docs/reference/](../docs/reference/README.md) `architecture.md`,
  `backend-conventions.md`, `persistence.md`, `auth.md`, `file-storage.md` and `testing.md`.
- `src/platform` holds users, groups, auth, settings, file storage, the agent call log and the MCP
  server; `src/cookbook` holds the recipe domain and depends on Platform, never the other way round.
  Its rules are in `docs/reference/cookbook.md`; agent tools follow `docs/reference/mcp-tools.md`.
  `src/bootstrap` is the composition root.
- The OpenAPI snapshot in `openapi/openapi.json` is written by `scripts/export_openapi.py` and
  checked in CI with `--check`. After changing a route or schema, re-export and run
  `npm run generate:api-types` in `frontend/`.
- Version bumps go through `scripts/bump_version.sh X.Y.Z` at the repo root, never by editing one
  version file alone ([docs/RELEASING.md](../docs/RELEASING.md)).
