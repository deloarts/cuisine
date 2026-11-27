---
name: backend
description: Implementing a backend feature, API endpoint, use case, model or repository in Cuisine. Load when adding or changing anything under backend/src in service of a new operation, field, permission or table.
---

# Cuisine backend conventions

Every backend rule is documented in `docs/reference/` (the guides in `docs/` explain the
concepts). Read the parts that apply before writing code:

- New endpoint: `recipes.md` section 1. New field: section 2 (the full fan-out). New domain
  error: section 3. New permission: section 4. New admin settings field: section 6.
- Use cases, permissions, errors, DTOs vs schemas, ids, logging: `backend-conventions.md`.
- Layers and where code goes: `architecture.md` and the `architecture` skill.
- Engine and sessions, models and column types, repositories, the unit of work, settings:
  `persistence.md`.
- Sessions, CSRF, TOTP, passkeys, tokens, the security log: `auth.md`.
- Images and documents, accepted types, download headers: `file-storage.md`.
- Datetime and async rules: `docs/DEVELOPMENT.md` section 7.
- Tests (fixtures, the `CSRF` header, SQLite, what every route needs): `testing.md`.

## Schema changes

A new or changed model needs a migration. Load the `migrations` skill before touching anything
under `backend/alembic/`, and export a new model from its package's `models/__init__.py` so
Alembic sees it.

## Before calling it done

Run the backend gates and the targeted tests listed in `CLAUDE.md`, or `/test` for the whole
picture. After a route or schema change, run `make api` so the OpenAPI snapshot and the frontend
types follow. Never edit `backend/openapi/openapi.json` by hand. If an existing test looks wrong
given your change, say so and ask before touching it.
