# recipes

Step lists for the common changes. The concepts are in [CONTRIBUTING.md section 2](../CONTRIBUTING.md#2-recipes).

- [1 add an endpoint](#1-add-an-endpoint)
- [2 add a field](#2-add-a-field)
- [3 add a domain error](#3-add-a-domain-error)
- [4 add a permission](#4-add-a-permission)
- [5 add a frontend feature](#5-add-a-frontend-feature)
- [6 add an admin settings field](#6-add-an-admin-settings-field)

## 1 add an endpoint

1. Write or extend the use case in `application/use_cases/<area>/`. It takes the acting user, checks the domain rules, writes through repositories, records a security event if the change concerns accounts, permissions or settings, and commits once.
2. Add a provider for it in `adapters/inbound/api/deps.py` if it is new.
3. Add request and response schemas in `adapters/inbound/api/schemas/`. Responses expose `public_id` as `id`.
4. Add the route. Resolve the user with `get_current_user` or `require_permission(...)` bound to a module-level constant (ruff's B008 refuses a call in a default), call the use case, map the result.
5. Write an integration test in `tests/integration/` for the happy path, the permission refusal and every domain error the route can answer.
6. Run `make api` and commit the regenerated `backend/openapi/openapi.json` and `frontend/src/core/api/generated/webSchema.ts`.

## 2 add a field

1. Add it to the entity, with a default if existing rows need one.
2. Add the column to the model and the mapping in the repository (the simple repositories copy fields by name).
3. Generate the migration (`DEVELOPMENT.md` section 5), read it, and give existing rows a server default if the column is not nullable.
4. Expose it in the schemas, run `make api`, and use it in the frontend through the regenerated types.

## 3 add a domain error

1. Add a class in the package's `domain/exceptions.py` that inherits the semantic base whose HTTP status it should answer with (`NotFoundError` 404, `ConflictError` 409, `InvalidInputError` 422, and so on).
2. Its message is shown to the user, so write it as a full sentence. Never put a secret or an internal id into it.
3. `exception_handlers.py` needs no change unless a new semantic base is added.

## 4 add a permission

1. Add the constant to `platform/domain/value_objects/permission.py` and to `Permission.ALL`, with a comment saying what it covers and what it does not.
2. If a token must never carry it, add it to `NEVER_GRANTABLE_TO_TOKENS` in `domain/services/permission_rules.py`.
3. Add it to `frontend/src/core/auth/permissions.ts` and a label under `permissions.` in both locale files; `npm run check:i18n` fails without the labels. Put it in one section of `frontend/src/shared/utils/permissionGroups.ts`, which the checklist beside the user and group dialogs shows by area (`permissionGroups.spec.ts` fails while a permission is in none or in two); the token dialog's `PermissionPicker.vue` lists it from `permissions.ts` directly.

## 5 add a frontend feature

1. Create `src/features/<feature>/` with `views/`, `components/` and, when needed, `api/`.
2. Add `src/features/<feature>/routes.ts`, default-exporting the feature's routes (`satisfies RouteRecordRaw[]`) with their `title` key and, when needed, their `permissions`. The router picks the file up by itself; `src/router/index.ts` is not edited.
3. A new top-level page gets its entry in `src/app/navigation.ts`, with the same permissions, which puts it into the sidebar and, when it belongs there, the phone's bottom nav.
4. Call the backend with `webApi`; alias wire types from `Schemas`.
5. Add the strings to `src/features/<feature>/locales/en-GB.ts` and `de-AT.ts` under the feature's own namespace ([frontend-conventions.md section 4](frontend-conventions.md#4-i18n)), and a spec under `__tests__/` for the logic that can break.

## 6 add an admin settings field

1. Add the field with its default to the section dataclass in `platform/domain/entities/settings.py`; the JSON storage needs no migration (`persistence.md` section 4).
2. Add its range check to `domain/services/settings_rules.py`.
3. Add it to the section's schema in `schemas/settings_schema.py` and run `make api`.
4. Add the input to the section's component in `frontend/src/features/admin-settings/components/`, with a label and a hint in both locales. A new section is registered under its tab in `features/admin-settings/adminTabs.ts`.
