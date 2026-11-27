# Cuisine Frontend

See the root [CLAUDE.md](../CLAUDE.md) for what to run, the Don't list, and where every rule is
documented.

## Frontend-specific

- Conventions: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md) sections 4 and 5; the rules are in
  [docs/reference/frontend-conventions.md](../docs/reference/frontend-conventions.md) and
  [docs/reference/testing.md](../docs/reference/testing.md).
- Call the backend through `webApi` (`src/core/api/webRequest.ts`), which checks paths, queries
  and bodies against the generated schema; the login steps go through `authApi`
  (`src/core/api/auth.ts`). Wire types alias `Schemas['X']`, never a hand-written interface.
- Every user-facing string lives in both `src/core/i18n/locales/en-GB.ts` and `de-AT.ts`
  (informal "Du"); `npm run check:i18n` enforces parity.
- Style OpenVue through `src/assets/styles/_openvue.scss`, a `--p-*` variable or a class of your
  own, never its internal `.p-*` classes in a component.
