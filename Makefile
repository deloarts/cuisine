# Thin wrappers over the commands documented in docs/DEVELOPMENT.md, so the
# common loops are one command each. Read a recipe to see what it runs.
#
#   make setup         install backend and frontend dependencies and the git hooks
#   make infra         start Postgres and Redis for the host dev loop
#   make migrate       apply Alembic migrations to the dev database (.env.dev)
#   make seed-dev      fill the migrated dev database with sample recipes and users
#   make dev-backend   run the backend with reload on :3000
#   make dev-frontend  run the Vite dev server on :5173
#   make test          the backend suite and the frontend unit tests
#   make gates         lint, format, type and contract checks of both halves
#   make api           re-export the OpenAPI snapshot and the frontend API types
#   make formats       re-export the JSON Schema of every exchange format version
#   make e2e-peering   pair two throwaway instances and run the peering scenario (on demand)

POETRY ?= poetry
NPM ?= npm
COMPOSE_DEV = docker compose -f docker-compose.dev.yml --env-file .env.dev
INFRA_SERVICES ?= postgres redis

.PHONY: help setup infra migrate seed-dev dev-backend dev-frontend test gates gates-backend gates-frontend api formats e2e-peering

help:
	@sed -n 's/^#   //p' Makefile

setup:
	test -f .env.dev || cp .env.dev.example .env.dev
	cd backend && $(POETRY) env use python3.13
	cd backend && $(POETRY) install
	cd backend && $(POETRY) run pre-commit install
	cd frontend && $(NPM) ci

infra:
	$(COMPOSE_DEV) up -d $(INFRA_SERVICES)

migrate:
	cd backend && ENV_FILE=../.env.dev $(POETRY) run alembic upgrade head

# Debug mode only; does nothing when the database already has recipes.
seed-dev:
	cd backend && ENV_FILE=../.env.dev $(POETRY) run python scripts/seed_dev.py

dev-backend:
	cd backend && ENV_FILE=../.env.dev $(POETRY) run uvicorn src.bootstrap.main:app --reload --port 3000

dev-frontend:
	cd frontend && $(NPM) run dev

# The backend tests run on a throwaway SQLite file and in-process fakes for
# Redis, so they need no running infrastructure.
test:
	cd backend && $(POETRY) run pytest tests -q -n auto
	cd frontend && $(NPM) run test:unit:run

gates: gates-backend gates-frontend

gates-backend:
	cd backend && $(POETRY) run ruff check src tests scripts alembic
	cd backend && $(POETRY) run ruff format --check src tests scripts alembic
	cd backend && $(POETRY) run mypy src scripts tests
	cd backend && $(POETRY) run python scripts/export_openapi.py --check
	cd backend && $(POETRY) run python scripts/export_formats.py --check

gates-frontend:
	cd frontend && $(NPM) run type-check
	cd frontend && $(NPM) run lint:check
	cd frontend && $(NPM) run check:i18n
	cd frontend && $(NPM) run check:api-types

api:
	cd backend && $(POETRY) run python scripts/export_openapi.py
	cd frontend && $(NPM) run generate:api-types

formats:
	cd backend && $(POETRY) run python scripts/export_formats.py

# Two backend processes on throwaway SQLite files in a temporary folder, on
# free ports of this host's private address; never the dev stack. On demand,
# not part of `make test` or CI.
e2e-peering:
	cd backend && $(POETRY) run python scripts/e2e_peering.py
