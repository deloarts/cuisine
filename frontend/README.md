# Cuisine frontend

Vue 3 + TypeScript frontend for [Cuisine](../README.md): OpenVue 1, Pinia, vue-router, vue-i18n,
Vite and Vitest.

```bash
cd frontend
npm ci
npm run dev                 # http://localhost:5173, talks to the backend on :3000
npm run ci                  # type-check, lint, unit tests, i18n parity, API types
npm run generate:api-types  # after a backend route or schema changed
```

See the [root README](../README.md) for the full-stack quick start and [docs/](../docs/) for the
conventions.
