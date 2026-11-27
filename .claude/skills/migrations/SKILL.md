---
name: migrations
description: Writing, changing or reviewing an Alembic migration in Cuisine. Load before creating any file under backend/alembic/versions, before running any alembic command, and whenever a model change needs a schema change.
---

# Writing a Cuisine migration

The rules live in `docs/reference/development-migrations.md` and `docs/DEVELOPMENT.md` section 5;
read both first. This skill is the order to follow, because doing the right steps in the wrong
order is what forces manual database repairs.

## Hard rules

- Never run `alembic upgrade`, `downgrade` or `stamp` against any database yourself, and never
  run `make migrate`. Ask the user to run it and wait.
- The dev backend applies every file in `alembic/versions/` on start when `MIGRATE_ON_STARTUP` is
  set, as `.env.dev.example` does, and `--reload` restarts it on every change under `backend/`.
  An unfinished migration file can be applied the moment anything is saved, so write it
  complete in one go.
- Never edit, rename, re-id or delete a migration that is on `main` or in a release. Fix forward
  with a new one.
- A migration that exists only on the current branch is extended rather than followed by a
  second one, but only after the user has downgraded every database that applied it. Never write
  a second migration on a branch that already has one without asking the user first.
- Never import from `src` in a migration (`development-migrations.md` section 2 point 4).

## Steps

1. **Change the models first**, exported from the package's `models/__init__.py`, which
   `alembic/env.py` imports through `Base`.
2. **Find the head:** `cd backend && poetry run alembic heads`. Exactly one is expected; if there
   are two, stop and tell the user. Then check whether the branch already has its own migration:
   `git diff --name-only main...HEAD -- backend/alembic/versions` plus untracked files there. If
   it has one, ask the user to downgrade the dev database to its `down_revision` and extend that
   file once they confirm.
3. **Generate the draft** as the reference describes:
   `ENV_FILE=../.env.dev poetry run alembic revision --autogenerate -m "<what it does>"`. This reads
   the dev database and writes a file but changes no database. If the user's dev backend is
   running with `MIGRATE_ON_STARTUP`, ask them to stop it first, or the draft is applied as soon
   as the next reload happens.
4. **Finish the draft before touching `backend/src` again:** fix renames that autogenerate wrote
   as drop and add, server defaults, data moves, a `server_default` or a nullable step for every
   new non-nullable column on a table with rows, explicit constraint names, and a `downgrade`
   that undoes the `upgrade`. Give the file a docstring saying what it changes, why, and what
   downgrade does.
5. **Data steps** are idempotent (a second run changes nothing), tolerant of unexpected rows
   (skip or default, never raise on data), and convert existing rows in the same revision when
   the shape or meaning of stored data changes, including new keys in stored settings.
6. **Check it:**
   - `poetry run pytest tests/unit/test_migrations.py -q` (the history on empty SQLite against
     the models);
   - the tests of the models and repositories you changed;
   - `poetry run ruff check alembic` and `poetry run ruff format --check alembic`;
   - CI's `backend-migrations` job runs upgrade, `alembic check` and downgrade on an empty
     Postgres; locally `/test ci` reproduces it on a throwaway container.
7. **Hand over:** name the file path and revision id, say it is not applied, and say that a dev
   backend with `MIGRATE_ON_STARTUP` applies it on its next start or reload. Add that before
   switching the dev database to `main` or another branch, the user downgrades it on this branch
   to the migration's `down_revision`.

## If a database was stamped without its DDL

Tell the user; do not fix it yourself. The repair they run, from `backend/`, is
`poetry run alembic downgrade <revision before it>` and then `poetry run alembic upgrade head`,
after making sure the migration body is complete.
