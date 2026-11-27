# contributing

This guide explains how Cuisine is put together and how to add to it. It stays short enough to read in one sitting; the exact rules, checklists and edge cases live in [reference/](reference/README.md), which each section links to.

- [1 architecture in one page](#1-architecture-in-one-page)
- [2 recipes](#2-recipes)
- [3 backend conventions](#3-backend-conventions)
- [4 frontend conventions](#4-frontend-conventions)
- [5 i18n and German copy](#5-i18n-and-german-copy)
- [6 testing](#6-testing)
- [7 before you open a PR](#7-before-you-open-a-pr)
- [8 comments, docstrings and language](#8-comments-docstrings-and-language)

## 1 architecture in one page

Cuisine is one backend and one frontend in one repository, released together under one version.

The backend is a FastAPI app in hexagonal layers. Each package under `backend/src` is split the same way: `domain` holds the entities, value objects, rules and errors as plain Python; `ports` declares, as protocols, what the application needs from the outside (repositories, the token service, the mail server); `application` holds the use cases, which take ports in their constructor and never import an adapter; `adapters` implements the ports (SQLAlchemy repositories, Redis, SMTP, Pillow) and exposes the use cases over HTTP. Dependencies point inwards only. Cuisine deliberately has no bounded contexts and no import contracts on top of that ([ADR 0001](adr/0001-hexagonal-without-bounded-contexts.md)).

| Package | Holds |
| ------- | ----- |
| `src/shared_kernel` | The entity base and the UTC clock, shared by everything. |
| `src/platform` | Users, groups, permissions, sign-in, sessions, tokens, the security log, admin settings and file storage. |
| `src/cookbook` | Reserved for recipes, ingredients, collections and the shopping list. It may use Platform; Platform never imports it. |
| `src/bootstrap` | The composition root: the app factory, startup seeding, migrations and the admin CLI. |

The frontend is a Vue 3 single-page app. `src/core` holds what every page needs (the API client, the generated types, i18n, stores, the theme), `src/app/layouts` the shell, `src/shared` reusable components, and `src/features/<feature>` one folder per area with its own `views`, `components` and `api`. The rules for both halves are in [reference/architecture.md](reference/architecture.md).

## 2 recipes

The usual changes follow a fixed path. [reference/recipes.md](reference/recipes.md) has the full step lists for:

- an endpoint, from the use case to the route and the regenerated frontend types;
- a field on an existing entity, through the migration;
- a domain error and its HTTP status;
- a permission;
- a frontend feature module;
- an admin settings section.

## 3 backend conventions

### 3.1 use cases, permissions and errors

A use case is a class with its dependencies in the constructor and one method per action. It checks the domain rules, stages its writes through repositories and commits once through the unit of work, together with its security log entry. A route resolves the signed-in user, checks the permission with `require_permission`, calls one use case and maps the result to a response schema. Domain errors inherit one of the semantic bases in `platform/domain/exceptions.py`, and `exception_handlers.py` maps each base to its status, so a use case never raises an HTTP error. Details: [reference/backend-conventions.md](reference/backend-conventions.md).

### 3.2 DTOs and schemas

Pydantic lives in the adapters only. Request schemas refuse unknown fields; response schemas expose public ids (UUIDs), never the sequential database ids. A use case takes a frozen dataclass command when it needs more than a couple of arguments.

### 3.3 logging

One logger, `src.platform.infrastructure.logging.logger.log`. Never log a password, token, TOTP secret or file content.

### 3.4 persistence

SQLAlchemy 2.0 async with the psycopg 3 driver on Postgres and aiosqlite in the tests. Every schema change is an Alembic migration; the models declare constraint names through a naming convention, and app-specific column types (`UtcDateTime`, `EncryptedString`, `JsonType`) render as plain SQL types in migrations. Details: [reference/persistence.md](reference/persistence.md) and [reference/development-migrations.md](reference/development-migrations.md).

### 3.5 auth

The web session is an httponly cookie backed by a session row, so every device can be listed and signed out. Two-factor authentication, trusted devices, passkeys, personal access tokens and API keys follow the Glados design. The flows, the token scopes and the escalation guards are in [reference/auth.md](reference/auth.md).

### 3.6 file storage

Images and PDFs keep their metadata in Postgres; their bytes go to the storage provider named by `STORAGE__PROVIDER`, Postgres by default, with `local` and `seaweedfs` as options ([ADR 0002](adr/0002-file-storage-providers.md)). Images are re-encoded to WebP, which strips their metadata. Details: [reference/file-storage.md](reference/file-storage.md).

## 4 frontend conventions

TypeScript with `<script setup>`, single quotes and no semicolons, matched by hand (no prettier). Call the backend through `webApi`, which checks every path, query and body against the types generated from the OpenAPI snapshot. Use OpenVue components and the shared CSS classes of `main.scss` (`card`, `field`, `form-grid`, `panel-title`, `hint`), scoped styles for the rest, and spacing, font and colour tokens instead of literals; stylelint enforces the tokens. No Tailwind. Details: [reference/frontend-conventions.md](reference/frontend-conventions.md).

## 5 i18n and German copy

Every user-facing string exists in `en-GB.ts` and `de-AT.ts`, and `npm run check:i18n` fails when a key is missing in either. German copy uses the informal "Du" throughout. Domain messages from the backend are English and shown as they come; the frontend translates the cases it handles itself.

## 6 testing

Backend tests run on a throwaway SQLite file with in-process fakes for Redis; unit tests cover the domain rules and adapters, integration tests drive the API through httpx. Frontend specs use Vitest with jsdom and select elements by role, label, text or id, never by OpenVue's internal classes. Details: [reference/testing.md](reference/testing.md).

## 7 before you open a PR

Run `make gates` and `make test`. If a route or schema changed, `make api` regenerates the snapshot and the frontend types, and both belong in the commit. A schema change carries its migration. A user-facing change carries both locales and an entry under `[Unreleased]` in `CHANGELOG.md`.

## 8 comments, docstrings and language

The repository is written in English; German appears only in the locale files. Comments and docstrings are normal sentences with normal commas: say what the code does and why it exists, then stop. No em dashes, no dash-joined clauses, no bullet fragments, and no references to planning documents or decision ids, since code and docs must stand on their own.
