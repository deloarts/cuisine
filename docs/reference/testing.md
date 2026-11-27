# testing

How the two test suites are built and what a change should test. The concept is in [CONTRIBUTING.md section 6](../CONTRIBUTING.md#6-testing); running them is in [DEVELOPMENT.md section 6](../DEVELOPMENT.md#6-tests-and-gates).

- [1 backend](#1-backend)
- [2 frontend](#2-frontend)
- [3 browser smoke check](#3-browser-smoke-check)
- [4 peering end to end run](#4-peering-end-to-end-run)
- [5 what to test](#5-what-to-test)

## 1 backend

1. `tests/conftest.py` sets the environment before anything imports the app: a throwaway SQLite file per process, throwaway keys, a Redis URL that is never contacted. With `ENV_FILE` set it backs off, and the integration fixtures refuse any database but SQLite.
2. bcrypt runs at its minimum cost in tests (`_fast_bcrypt`), since verification reads the cost from the hash.
3. `tests/integration/conftest.py` drops and creates the schema before every test, builds a fresh app with the in-process login throttle, replay guard and request rate limiter, and talks to it through `httpx.ASGITransport` on `https://testserver`, so the Secure cookie is sent back like in a browser.
4. Fixtures: `client` (anonymous), `visitor` (a separate browser that never signs in, for the public recipe pages), `admin` (signed in as the system user, through `login_system`, which sets up its mandatory TOTP with a fixed secret and signs in with a code), `other_client` (a second browser), `make_user` (creates an account through the admin API). The `CSRF` header dict goes on every unsafe cookie-authenticated request.
5. WebAuthn cannot run without a browser and an authenticator, so `test_passkeys.py` swaps the verifier for a fake that checks the challenge round trip.
6. `tests/unit/test_migrations.py` applies the Alembic history to an empty SQLite file and compares the result with the models; CI also runs the history up and down on an empty Postgres.
7. The suite runs in parallel with `pytest -n auto`; each worker has its own SQLite file.
8. `tests/fixtures/` holds committed test files, such as the golden `.cui` file of each format version, which are never regenerated ([formats.md section 7](formats.md#7-schema-files-and-golden-fixtures)).

## 2 frontend

1. Vitest with jsdom; `vitest.setup.ts` stubs `matchMedia` and `ResizeObserver` for OpenVue.
2. Mount views with the real router (memory history), i18n and OpenVue; mock the `api/` module of the feature, not axios.
3. Select elements by role, label, text or id. eslint refuses OpenVue's internal `.p-*` and `.mdi-*` classes in specs.
4. Every spy is restored and every mock's history cleared before each test (`restoreMocks`, `clearMocks`).

## 3 browser smoke check

1. `npm run test:e2e` in `frontend/` runs `e2e/smoke/smoke.spec.ts` with Playwright inside the pinned `mcr.microsoft.com/playwright` image on the host network, on demand and not in CI. It signs in as the system user and the demo accounts of `make seed-dev`, visits every main page on a desktop and a phone screen, and saves a full-page screenshot of each under `test-results/smoke/<screen>/<account>/` for a person to look through.
2. A test fails on an uncaught page error or on an API answer of 400 or more, except 401 before sign-in and the answers the app expects and handles itself (an unpublished legal page, the editor of a recipe the account may not change). Console errors and text that looks like an untranslated message key are collected in `issues.json` next to the screenshots.
3. It runs against a running stack: `E2E_BASE_URL` (default `http://localhost:5173`) and `E2E_API_URL` (default `http://localhost:3000`) name it, `E2E_ADMIN_PASSWORD` is the system user's `INIT__PASSWORD`, and `E2E_ANNA_PASSWORD` and `E2E_BEN_PASSWORD` are the demo accounts' passwords (default `anna-dev-password` and `ben-dev-password`, as `make seed-dev` sets them). A production build served by `vite preview` (with `VITE_API_URL` pointing at the backend and the backend's `DOMAIN` at the preview origin) is more reliable than the dev server, whose dependency cache can serve stale modules when two dev servers share `node_modules`.
4. The system user must use TOTP, so the test enrols it through the API on the first run against a database and keeps the secret in `node_modules/.cache/e2e-system-totp-secret`; after resetting the dev database, delete that file.

## 4 peering end to end run

1. `make e2e-peering` (`backend/scripts/e2e_peering.py`) runs on demand and is not part of `make test` or CI. It starts two real backend processes, A and B, with uvicorn, each on its own throwaway SQLite file in a fresh temporary folder and on a free port, and drives them over HTTP through pairing, sharing a recipe with a variation, the accept dialog with create, map and plain decisions, an automatic update, an update held for a new ingredient, a withdrawal, an offline catch-up through "sync now", a protocol version mismatch and a revoke. It prints one line per step and exits non-zero when one fails.
2. It never touches the dev stack: the children get a clean environment without `ENV_FILE`, refuse any database but the SQLite file in their folder, and use the in-process login throttle, replay guard, rate limiter and live updates instead of Redis. The folder and both processes are removed at the end, also after a failure; `--keep` keeps the folder with the logs.
3. Peering requests go through the real target guard, which always refuses loopback, so both instances listen on the host's own private network address (found through the default route, or `--host`), which the guard accepts with the private network switch of the notification settings. Debug mode allows plain http between them.
4. The version mismatch restarts B with another protocol support window (`serve --protocol-window 2,3`, a patch of the running process only; nothing in the product reads it from the environment). A's refresh is refused and B refuses A's events with 422 until B runs with an overlapping window again, after which the queued update arrives.
5. The setup the script writes straight to the database before the start (the system user's authenticator, an instance name, user choice of visibility) is what an administrator would have done; everything the scenario checks goes through the API.

## 5 what to test

1. Every route: the happy path, the refusal without the permission, and each domain error it can answer.
2. Every security rule as its own test: lockouts, replay, escalation, CSRF, token narrowing, protected accounts.
3. Domain rules as unit tests without a database.
4. Frontend logic that can break silently: guards, stores, the login flow, helpers. Pure layout needs no spec.
