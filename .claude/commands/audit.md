---
description: Run a read-only codebase audit across the dimensions below
argument-hint: [dimension or scope, e.g. security, database, backend/src/platform/application, frontend/src/features/auth]
---

Run a READ-ONLY audit of the codebase (`backend/` and/or `frontend/` as relevant to scope). Do not
modify any source files. Do not commit anything.

## Scope

Arguments given: `$ARGUMENTS`

- If `$ARGUMENTS` names a dimension (see the list below), audit only that dimension across the
  whole codebase.
- If `$ARGUMENTS` names a path (e.g. `backend/src/platform/application`,
  `frontend/src/features/auth`), audit all applicable dimensions but restrict findings to that
  path.
- If `$ARGUMENTS` is empty, run a broad audit across all dimensions.

Dimensions, each judged against the rules in `docs/reference/`:
- architecture and layering (`architecture.md`: inward-only imports, no SQLAlchemy, Pydantic or
  FastAPI in `domain/` or `shared_kernel/`, wiring only in `bootstrap/`, Platform never importing
  `cookbook`)
- code duplication and component duplication
- code rot (stale comments, TODOs, workarounds that outlived their reason)
- typing hygiene (mypy strict, `Any` and `type: ignore` usage, TypeScript `any` and casts)
- database and migrations (`persistence.md`, `development-migrations.md`)
- stores and the API layer (`frontend-conventions.md` sections 2 and 5)
- performance (N+1 queries, missing indexes, oversized payloads, blocking calls in async code per
  `docs/DEVELOPMENT.md` section 7)
- security (for depth, use `/security-audit`)
- API surface and OpenAPI (schemas vs DTOs, error codes, consistency across routers)
- UX consistency (OpenVue usage, scoped CSS, no utility CSS, no `prefers-color-scheme` in
  components)
- accessibility
- i18n (key parity, hardcoded strings, German in informal "Du", no German outside locale files)
- logging discipline (`backend-conventions.md` section 6)
- tests (`testing.md` section 3: every route has the happy path, the refusal and each domain
  error; every security rule has its own test)
- dead code and dependencies
- docs drift (rules in `docs/` that the code no longer follows, or the reverse)

## Before starting

Read the reports in earlier `.audit/audit-<date>/` folders first, if any exist. They track
residual items and conventions already accepted in a prior audit.

## Method

1. Fan out parallel read-only Explore subagents, one per dimension in scope. Each subagent
   searches and reads only, with no edits.
2. Before reporting any finding, verify it: it must cite a concrete `file:line`, and you must
   re-check that file:line yourself before it goes in the report. Do not report a finding you have
   not personally verified.
3. Cross-check candidate findings against earlier audit reports and drop duplicates.

## Output

Write a report to `.audit/audit-<today's date>/report.md` (create the folder; use `YYYY-MM-DD`).
Structure:
- Findings ranked by severity (high, medium, low).
- Each finding as a work package: **Finding** (what and why), **Files** (file:line references),
  **Approach** (how it would be fixed), **Risk**, **Effort**.

Then send the user a short summary: the dimensions covered, the count of findings by severity
and the report path. Do not include the full report inline unless the user asks.

Hard constraints: this is read-only. Do not edit, create, or delete any source file. Do not run
`git add` or `git commit`. The only file you write is the audit report itself.

Minimize token usage. Don't assume anything.
