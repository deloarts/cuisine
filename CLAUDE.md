# Cuisine

Cuisine is a self-hosted cookbook for a household, its friends and its family (recipes,
ingredients, photos, later a live shared shopping list). This repo holds the Python 3.13
FastAPI backend (`backend/`, hexagonal layers, SQLAlchemy 2.0, async I/O) and the Vue 3 +
TypeScript frontend (`frontend/`, OpenVue 1, Pinia, Vite, Vitest). It is built on the
blueprint of the Glados project, with less modularity: hexagonal layers, but no bounded
contexts and no import contracts (`docs/adr/0001-hexagonal-without-bounded-contexts.md`).

## Where the rules live

`docs/` is the single source of truth for conventions. This file only adds AI-specific
behaviour. The guides in `docs/*.md` explain concepts, and `docs/reference/*.md` holds the
exact rules (`docs/reference/README.md` indexes every file):

| Topic | Guide | Reference |
| ----- | ----- | --------- |
| Architecture, layers, where code goes, wiring | `docs/CONTRIBUTING.md` section 1 | `architecture.md` |
| Recipes: endpoint, field, domain error, permission, frontend feature, settings tab | `docs/CONTRIBUTING.md` section 2 | `recipes.md` |
| Cookbook rules: languages, permissions, derived data, privacy, shopping lists | `docs/CONTRIBUTING.md` section 1 | `cookbook.md` |
| MCP surface for AI agents | `docs/MCP_INTEGRATION.md` | `mcp-tools.md` |
| Exchange formats: `.cui` and catalogue files, versions, schemas, golden fixtures | `docs/CONTRIBUTING.md` section 1 | `formats.md` |
| Peering: pairing, versions, signed requests, peer channels, mirrors | `docs/CONTRIBUTING.md` section 1 | `peering.md` |
| Backend conventions: use cases, permissions, DTOs and schemas, errors, logging | `docs/CONTRIBUTING.md` section 3 | `backend-conventions.md` |
| Persistence, the unit of work, column types | `docs/CONTRIBUTING.md` section 3.4 | `persistence.md` |
| Auth: sessions, TOTP, passkeys, tokens, the security log | `docs/CONTRIBUTING.md` section 3.5 | `auth.md` |
| File storage: images, documents, download headers, storage providers | `docs/CONTRIBUTING.md` section 3.6 | `file-storage.md` |
| Admin area: host and storage readings, branding, webhooks, banner, notices | `docs/OPERATIONS.md` | `admin-area.md` |
| Frontend conventions, i18n and "Du" | `docs/CONTRIBUTING.md` sections 4 and 5 | `frontend-conventions.md` |
| Testing | `docs/CONTRIBUTING.md` section 6, `docs/DEVELOPMENT.md` section 6 | `testing.md` |
| Local setup, env, migrations | `docs/DEVELOPMENT.md` | `development-migrations.md` |
| Releases and CI | `docs/RELEASING.md` | `releasing-ci.md`, `releasing-github-setup.md` |
| Install, operations | `docs/INSTALLATION.md`, `docs/OPERATIONS.md` | |
| Why the code is shaped this way | `docs/adr/` | |

When a rule you need is missing from `docs/`, add it there, not here.

## Commands and what to run unprompted

Backend (from `backend/`):
- Tests: run only the tests written or touched this session, targeted:
  `poetry run pytest tests/path/test_x.py -q` (or `-k <name>`). The whole suite is
  `make test` from the repo root; run it only when asked.
- Gates: `poetry run ruff check src tests scripts alembic`,
  `poetry run ruff format --check src tests scripts alembic`, `poetry run mypy src scripts tests`
  (strict).
- After changing a route or schema: `poetry run python scripts/export_openapi.py`, then
  `npm run generate:api-types` in `frontend/` (`make api` does both; so does the
  `export-openapi` pre-commit hook).
- Dev server: `make infra` (repo root), then `make dev-backend` (:3000).
- Alembic: never run `alembic upgrade` against a real database unprompted; state the file path
  and revision instead. An authored but unapplied migration on disk is normal.

Frontend (from `frontend/`):
- `npm run test:unit:run -- <spec path>` for the specs you touched.
- Gates: `npm run type-check`, `npm run lint:check`, `npm run check:i18n`,
  `npm run check:api-types`. `npm run ci` runs them all with the unit tests.

## Don't

1. Never add a "Co-Authored-By" (or any AI) trailer to commit messages, and never commit or
   push unprompted; wait for an explicit ask every time.
2. Never break the layer rule (adapters → application → ports → domain, inward only), and never
   import SQLAlchemy, Pydantic or FastAPI in `domain/` or in `src/shared_kernel/`.
3. Never apply migrations to any database unprompted, and never point tests or dev scripts at a
   real database; tests use a throwaway SQLite file.
4. Never touch, move or delete `.local/` (it holds the pre-rebuild snapshot) or commit it.
5. Never hand-edit generated files (`frontend/src/core/api/generated/webSchema.ts`,
   `backend/openapi/openapi.json`, `frontend/src/components.d.ts`).
6. Never change an existing test to make new code pass without flagging it first.
7. Always write German user-facing copy in informal "Du", never "Sie".
8. Never write German in code, identifiers, comments, docstrings, log messages or docs; the repo
   language is English. German belongs only in locale files.
9. Never run prettier in `frontend/`: match the single-quote, no-semicolon style by hand.
10. Never introduce Tailwind or any utility-CSS framework; use scoped CSS or OpenVue.
11. Never use `@media (prefers-color-scheme: dark)` in Vue components; OpenVue's variables and
    the `.p-dark` class handle theming.
12. Never reference plan points or decision ids (e.g. `D13`) or `.playground/` in code comments
    or docs: plans are local working artifacts; code and docs must stand alone.

## Writing style for comments and docs

Docstrings and comments are precise and human readable, never padded: normal sentences with
normal commas, no em dashes or dash-joined clauses, no bullet-style fragments. Say what the thing
does and why it exists, then stop. Full rule: `docs/CONTRIBUTING.md` section 8.

## Workflow

- `.playground/` (gitignored) is the planning hub: one folder per effort,
  `<topic>-<YYYY-MM-DD>/plan.md` with Goal, pinned Decisions, Findings and the implementation
  breakdown. Pinned decisions are settled; do not relitigate them without a new reason from the
  user.
