---
name: frontend
description: Any work in frontend/, or a full-stack Cuisine change that touches the UI. Load before editing Vue components, stores, the API client or generated types, and whenever a backend API change needs a matching frontend update.
---

# Cuisine frontend conventions

Every frontend rule is documented in `docs/reference/` (`docs/CONTRIBUTING.md` sections 4 and 5
explain the concepts). Read the parts that apply before writing code:

- Folder layout: `architecture.md` section 6. New feature module: `recipes.md` section 5. New
  admin settings field: `recipes.md` section 6; read the existing settings tabs in
  `src/features/admin-settings/` first.
- Code style, API calls and types, styling and the look (OpenVue, scoped CSS, `.p-dark`), i18n
  and informal German, stores and the session: `frontend-conventions.md`.
- Testing (real router, mocking the feature's `api/` module, no `.p-*` or `.mdi-*` selectors):
  `testing.md` section 2.
- Why OpenVue: `docs/adr/0005-openvue-ui-library.md`.

After a backend API change, the generated types in `src/core/api/generated/webSchema.ts` go
stale: run `make api` from the repo root (it exports the snapshot and regenerates the types; no
backend needs to run). Never edit `webSchema.ts` or `components.d.ts` by hand.

Every new label goes into both `de-AT.ts` and `en-GB.ts`, with German in informal "Du".

## Before calling it done

Run the frontend gates and the specs you touched, as listed in `CLAUDE.md`, or `/test frontend`.
Never run prettier; match the single-quote, no-semicolon style by hand. If an existing test looks
wrong given your change, say so and ask before touching it.
