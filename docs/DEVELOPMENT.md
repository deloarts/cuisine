# developing

How to run Cuisine on your machine, test it and change its database schema.

- [1 prerequisites](#1-prerequisites)
- [2 install dependencies](#2-install-dependencies)
- [3 configure the environment](#3-configure-the-environment)
- [4 run it](#4-run-it)
- [5 database migrations](#5-database-migrations)
- [6 tests and gates](#6-tests-and-gates)
- [7 datetime and async rules](#7-datetime-and-async-rules)

## 1 prerequisites

Python 3.13 with Poetry 2.4, Node 22 with npm, and Docker with the Compose plugin for Postgres and Redis. VS Code users open `cuisine.code-workspace`, which brings the launch configurations, tasks and recommended extensions.

## 2 install dependencies

```bash
make setup
```

This copies `.env.dev.example` to `.env.dev`, installs the backend with Poetry into a Python 3.13 virtualenv in Poetry's user cache (`~/.cache/pypoetry/virtualenvs`; `poetry env info -p` prints the path, and VS Code picks it up through the Python extension's Poetry support), installs the pre-commit hooks and runs `npm ci` in `frontend/`.

## 3 configure the environment

The backend reads its settings from environment variables, with `__` separating nested keys (`DATABASE__URL`). `ENV_FILE` names a file to read them from; the dev commands set `ENV_FILE=../.env.dev`. `.env.dev` points at the dev compose services on localhost, turns on `DEBUG` (plain-http cookies, the API docs under `/docs`) and `MIGRATE_ON_STARTUP`. Every setting is documented in `.env.example` and in `backend/src/platform/infrastructure/config/settings.py`.

## 4 run it

```bash
make infra          # Postgres on :5433, Redis on :6380 (off the default ports, so Glados's dev stack can run alongside)
make dev-backend    # uvicorn with reload on :3000, migrates the dev database on start
make dev-frontend   # Vite on :5173
make seed-dev       # once, after the first start: demo recipes, accounts, a household and lists
```

Sign in at http://localhost:5173 as `system` with the `INIT__PASSWORD` of `.env.dev`; the first sign-in sets up two-factor authentication, and the session ends 15 minutes after sign-in. `make seed-dev` prints the demo accounts it creates; it adds demo data only, on the reference data every start seeds ([reference/cookbook.md section 9](reference/cookbook.md#9-seeds)). In VS Code, the "Backend (uvicorn)" launch configuration runs the backend under the debugger.

`docker compose -f docker-compose.dev.yml --env-file .env.dev up -d` runs everything in containers instead, with hot reload for both halves and Mailpit on http://localhost:8025 to catch outgoing mail (mail server `mailpit`, port 1025, no encryption).

| Service | URL |
| ------- | --- |
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:3000/api/v1 |
| API docs (debug only) | http://localhost:3000/docs |
| Health, readiness | http://localhost:3000/health, http://localhost:3000/ready |

## 5 database migrations

Every schema change is an Alembic migration in `backend/alembic/versions`. After changing a model:

```bash
cd backend
ENV_FILE=../.env.dev poetry run alembic revision --autogenerate -m "add recipe table"
```

Read the generated file before keeping it, then apply it with `make migrate` (or restart the dev backend, which migrates on start). The rules for writing migrations, including the released-migrations-are-immutable rule, are in [reference/development-migrations.md](reference/development-migrations.md).

## 6 tests and gates

```bash
make test     # backend suite (parallel) and frontend unit tests
make gates    # ruff, mypy, the OpenAPI and format schema checks, type-check, lint, i18n parity, API types
```

The backend suite needs no running services: it uses a throwaway SQLite file and in-process fakes for Redis, and refuses to run against anything but SQLite. One test file runs with `cd backend && poetry run pytest tests/integration/test_auth.py -q`, one spec with `cd frontend && npm run test:unit:run -- src/router/__tests__/guard.spec.ts`. More in [reference/testing.md](reference/testing.md).

`make e2e-peering` pairs two throwaway backend processes on SQLite and runs the peering scenario between them over HTTP. It is on demand, not part of `make test` or CI, and needs no running services either ([reference/testing.md section 4](reference/testing.md#4-peering-end-to-end-run)).

## 7 datetime and async rules

Everything the app stores is UTC. Take the current time from `now_utc()` in `shared_kernel/domain/services/clock.py`, never from `datetime.now()`; ruff's DTZ rules flag naive datetimes. Columns use `UtcDateTime`, which reads values back as timezone-aware UTC on every backend.

Request handling is async end to end. Slow CPU work, bcrypt and image re-encoding, runs off the event loop (bcrypt through `anyio.to_thread`), and nothing in an `async def` may block on I/O; ruff's ASYNC rules catch the common cases.
