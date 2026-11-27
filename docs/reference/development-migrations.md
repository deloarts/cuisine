# development migrations

Writing, checking and shipping Alembic migrations. The concept is in [DEVELOPMENT.md section 5](../DEVELOPMENT.md#5-database-migrations).

- [1 the chain](#1-the-chain)
- [2 writing a migration](#2-writing-a-migration)
- [3 checking it](#3-checking-it)

## 1 the chain

1. The history in `backend/alembic/versions` is a single chain with one head. Two branches that both add a migration are rebased so one follows the other.
2. A migration that shipped in a release is never edited; a fix is a new migration.
3. The backend container applies pending migrations before gunicorn starts (`docker/entrypoint.sh`); concurrent starts are safe because `alembic/env.py` holds a Postgres advisory lock while it migrates.
4. Never run `alembic upgrade` against a real database unprompted, and never point a migration test at one.

## 2 writing a migration

1. Change the models first, then autogenerate against the dev database: `ENV_FILE=../.env.dev poetry run alembic revision --autogenerate -m "<what it does>"`.
2. Read the generated file. Autogenerate misses renames (it drops and adds), server defaults and data moves; write those by hand.
3. A new non-nullable column on a table with rows needs a `server_default`, or a nullable step, a data update and a second step.
4. The app's column types render as plain SQL types (`render_item` in `env.py`), so a migration never imports application code. Keep it that way: a migration must still run when the code it was written against has changed.
5. Write a `downgrade` that undoes the `upgrade`.

## 3 checking it

1. `make migrate` applies it to the dev database; `alembic check` then reports no further changes.
2. `tests/unit/test_migrations.py` applies the history to an empty SQLite file and fails on any difference from the models.
3. CI's `backend-migrations` job runs upgrade, `alembic check` and downgrade on an empty Postgres.
