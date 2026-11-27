# backend conventions

The rules for use cases, permissions, errors, DTOs and schemas, and logging. The concepts are in [CONTRIBUTING.md section 3](../CONTRIBUTING.md#3-backend-conventions).

- [1 use cases](#1-use-cases)
- [2 permissions](#2-permissions)
- [3 errors](#3-errors)
- [4 DTOs and schemas](#4-dtos-and-schemas)
- [5 ids](#5-ids)
- [6 logging](#6-logging)

## 1 use cases

1. A use case is a class whose constructor takes keyword-only ports. Related actions on one aggregate may share a class (`ManageGroups.create`, `.update`, `.delete`).
2. A use case commits exactly once per action, through `IUnitOfWork.commit`, after every write and the security log entry are staged. A refusal that must be recorded (a wrong password) commits the record and then raises.
3. A use case never imports FastAPI, Pydantic, SQLAlchemy or an adapter, and never raises an HTTP error.
4. The acting user is the first argument of every action that needs one; the request's address and user agent arrive as a `RequestContext` for actions that write the security log.

## 2 permissions

1. Every signed-in user reads everything that is not personal or administrative; reading needs no permission unless the data is sensitive (settings, the security log).
2. Routes check the permission with `require_permission` or `require_any_permission`. A use case checks permissions itself only when the rule depends on the data, such as "may grant only what you hold".
3. `User.has_permission` passes everything for the system user; for everyone else it checks direct grants and group grants. There are no denials.
4. Granting is capped: a user can only grant permissions they hold, whether directly, through a group's permissions or by adding someone to a group (`permission_rules.assert_grantable_by`).
5. Permission names are `verb:object`, lower case, with the object in the plural (`write:recipes`).

## 3 errors

1. Every domain error inherits one semantic base in `platform/domain/exceptions.py`; `exception_handlers.py` maps the base to its status and returns `{"detail": <message>, "code": <class name>}`.
2. The frontend may switch on `code`, never on the message text.
3. An error that names an account never says whether the account exists (`InvalidCredentialsError` for unknown names and wrong passwords alike).
4. A unique-constraint violation at commit answers 409 through `ConstraintViolationError`; use cases still check uniqueness first, to answer with a precise message.

## 4 DTOs and schemas

1. Request schemas inherit `RequestSchema` (`extra="forbid"`), response schemas `ResponseSchema`.
2. A list default in a schema is `Field(default_factory=list)` (ruff RUF012).
3. A field that may be omitted on update is `X | None = None`, and the use case treats `None` as "leave unchanged". When `None` must also mean "clear", the schema documents the difference (the mail password: `None` keeps, `""` clears).
4. Commands between route and use case are frozen dataclasses in the use case's module or in `application/dto/`.

## 5 ids

1. Every table with its own `id` has a sequential `id` for joins and a `public_id` UUID for the API and for links (`PublicIdMixin`), whether or not a route exposes it today. Link tables with a composite primary key (recipe tags, shares, co-editors, household members, favourites, translations, aliases, conversions) have none; the public ids of the rows they link identify them. The entity generates the UUID, so it exists before the first save, and an update never writes it.
1a. Rows a save replaces as a whole (the steps of a recipe with their ingredient and equipment lines) still keep their public ids: the request names each existing row by its id, and the use case writes it again with that id ([cookbook.md section 3](cookbook.md#3-recipes-and-what-is-derived)).
1b. An import or a copy never takes over another row's public id; it gets its own and, for recipes from elsewhere, stores the source identity in separate columns ([persistence.md section 5](persistence.md#5-public-ids-the-resolver-and-the-instance-id)).
2. A path parameter is a string; repositories parse it with `parse_public_id`, so a malformed id answers 404 like an unknown one.
3. Responses translate internal ids of related rows into their public ids (`presenters.py`).

## 6 logging

1. Use `log` from `platform/infrastructure/logging/logger.py`.
2. Never log a password, token, TOTP code or secret, a session id, or file content.
3. Security-relevant events go to the security log through `SecurityAudit`, not only to stdout.
