---
description: Run the tests and quality gates relevant to the current changes
argument-hint: [path | pattern | all | backend | frontend | ci]
---

Run the relevant tests and quality gates for the current work. Follow these steps.

## 1. Determine scope

Arguments given: `$ARGUMENTS`

- If `$ARGUMENTS` is empty: inspect `git status` and scope by path prefix, `backend/` vs
  `frontend/`. Map changed backend files (`backend/src/...`) to their matching `backend/tests/`
  modules; map changed frontend files (`frontend/src/...`) to their colocated
  `__tests__/*.spec.ts`. Run the backend gates for any changed backend files and the frontend
  type-check and lint for any changed frontend files. Run `check:i18n` only if a locale file
  (`frontend/src/core/i18n/locales/*.ts`) changed. Run `check:api-types` and
  `export_openapi.py --check` only if a route, a schema, `backend/openapi/openapi.json` or
  `frontend/src/core/api/generated/webSchema.ts` changed. Run `tests/unit/test_migrations.py`
  if a model or anything under `backend/alembic/` changed.
- Image builds: CI builds both Docker images, and a build can fail where every gate passed.
  Run the Docker builds (step 2) for `all`, and in the default scope when a Dockerfile, a
  `.dockerignore`, anything under `backend/docker/` or `frontend/docker/`, or a dependency
  manifest (`frontend/package.json`, `frontend/package-lock.json`, `backend/pyproject.toml`,
  `backend/poetry.lock`) changed.
- If `$ARGUMENTS` is `ci`: skip the rest of this step and step 2, follow step 4 instead, and
  report as in step 3.
- If `$ARGUMENTS` is `all`: run the full gate set for both halves.
- If `$ARGUMENTS` is `backend` or `frontend`: run the full gate set, scoped to that half only.
- Otherwise treat `$ARGUMENTS` as a path or pattern and target it directly (a backend test path
  or `-k` expression, or a frontend spec path). Still run the gates for the affected half.

## 2. Run commands

Backend (`cd backend`):
- `poetry run pytest tests -q -n auto` for a full run (as `make test` does), or a targeted path
  when scoped, e.g. `poetry run pytest tests/integration/test_auth.py -q`
- `poetry run ruff check src tests scripts alembic`
- `poetry run ruff format --check src tests scripts alembic`
- `poetry run mypy src scripts tests`
- `poetry run python scripts/export_openapi.py --check`, when scope calls for it

Frontend (`cd frontend`):
- `npm run test:unit:run`, with a path filter when scoped, e.g.
  `npm run test:unit:run -- src/router/__tests__/guard.spec.ts`
- `npm run type-check`
- `npm run lint:check` (never `npm run lint`, which runs with `--fix`)
- `npm run check:i18n`, only if a locale file changed
- `npm run check:api-types`, only if scope calls for it
- `npm run build-only` for `all` and `frontend`

Docker images (repo root, see step 1 for when), the same builds `ci.yml` runs:
- `docker build -t cuisine-frontend:test-check -f frontend/docker/frontend.Dockerfile frontend`
- `docker build --target prod -t cuisine-backend:test-check -f backend/docker/backend.Dockerfile backend`
- Afterwards remove the tags: `docker image rm cuisine-frontend:test-check cuisine-backend:test-check`.
  If Docker is not running, report that as a gate that could not run.
- These build the working tree, so a file saved halfway through an edit ends up in the image.
  `ci` builds the committed `HEAD` instead.

Skip a half entirely if scope excludes it.

## 3. Report honestly

- Report failures verbatim, including file:line from the tool output. Do not paraphrase or
  summarize away a stack trace.
- No hedging like "mostly passing" or "just a couple of flaky failures". State the pass and fail
  count and list every failure.
- Never fix a failing test by changing the test itself to make it pass. If a test looks wrong,
  flag it explicitly and ask before touching it. This is a hard project rule.
- If a gate could not run (for example because that half's dependencies are not installed), say
  so plainly instead of skipping it silently.

## 4. CI replica (`ci`)

Runs what `.github/workflows/ci.yml` runs on a pull request, with every job enabled regardless of
the path filter. It differs from the other modes in three ways, each of which can let a CI
failure slip past a local run:

- It tests a clean clone of the committed `HEAD`, never the working tree. If `git status` shows
  uncommitted changes, say in the report that they were not tested.
- It installs from the lockfiles into an empty directory, so no warm `node_modules`, virtualenv
  or `tsbuildinfo` cache hides a failure.
- The frontend runs in a `node` container without network. Locally the dev backend on port 3000
  can answer a request a spec forgot to mock.

Keep going after a failing job; CI runs and reports them all. Commands run in `$CI_DIR` (or the
named subdirectory) unless noted.

### Setup

1. Clone into a new empty directory in the session scratchpad, or `mktemp -d` when there is
   none: `git clone --quiet . "$CI_DIR"` and
   `git -C "$CI_DIR" checkout --quiet --detach "$(git rev-parse HEAD)"`.
2. A throwaway Postgres like CI's service, on a port clear of the dev one:
   `docker run -d --rm --name cuisine-ci-postgres -e POSTGRES_USER=cuisine_ci -e POSTGRES_PASSWORD=cuisine_ci -e POSTGRES_DB=cuisine_ci -p 127.0.0.1:55432:5432 postgres:16`,
   then wait until `docker exec cuisine-ci-postgres pg_isready -U cuisine_ci` succeeds. It
   starts empty. Never point the migration job at any other database.
3. The frontend container, used below as `NODE_RUN`:
   `docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$CI_DIR:/repo" -w /repo/frontend node:<major>`,
   with the major version from `frontend/.nvmrc`.

If Docker is not running, the setup cannot be done; report that and stop.

### Jobs

- **images**, built first while the clone is still untouched by installs and test output (CI
  builds them only after backend and frontend passed; say so if one failed):
  `docker build -t cuisine-frontend:ci-check -f frontend/docker/frontend.Dockerfile frontend`
  and `docker build --target prod -t cuisine-backend:ci-check -f backend/docker/backend.Dockerfile backend`.
- **gitleaks**: download the release named by `GITLEAKS_VERSION` in `ci.yml`, verify it against
  `GITLEAKS_SHA256` and unpack it, as the job does, into `$CI_DIR/.ci-bin`. Then
  `.ci-bin/gitleaks git --redact --no-banner --verbose .`.
- **backend** (`backend/`): `poetry install --no-interaction`,
  `poetry run ruff check src tests scripts alembic`,
  `poetry run ruff format --check src tests scripts alembic`, `poetry run mypy src scripts tests`,
  `poetry run python scripts/export_openapi.py --check`, and
  `poetry run pytest tests -q -n auto --cov=src --cov-report=term-missing:skip-covered`.
- **backend-migrations** (`backend/`), with the job's `env` block, but `DATABASE__URL` set to
  `postgresql+psycopg://cuisine_ci:cuisine_ci@localhost:55432/cuisine_ci` and `ENV_FILE` unset:
  `poetry run alembic upgrade head`, `poetry run alembic check`,
  `poetry run alembic downgrade base`. This is the one place this command runs Alembic, and only
  against the container from setup step 2.
- **frontend** (`frontend/`, through `NODE_RUN`): `npm ci`, then with `--network none` added:
  `npm run type-check`, `npm run lint:check`, `npm run test:unit:run`, `npm run check:i18n`,
  `npm run check:api-types`, `npm run build-only`. Vitest fails the run on unhandled errors even
  when every test passed; report them like failures.

When `ci.yml` changes a job, change this list with it.

### Cleanup

Always, also after a failure: `docker stop cuisine-ci-postgres`,
`docker image rm cuisine-frontend:ci-check cuisine-backend:ci-check`,
`poetry env remove --all` in `$CI_DIR/backend` (the virtualenv may live outside the clone), then
delete `$CI_DIR`.

### Report

One line per CI job: passed, failed or skipped, with every failure reported in full as step 3
asks.
