---
description: Run a read-only security audit of the codebase
argument-hint: [scope, e.g. backend | frontend | dependencies | a path]
---

Run a READ-ONLY security audit of the codebase (`backend/` and/or `frontend/` as relevant to
scope). Do not modify any source files. Do not commit anything. Use local tools only; never send
source code, diffs, or file contents to any external service.

This audits the whole codebase. To review only the pending changes on the current branch, use the
built-in `/security-review` skill instead; it is the lighter tool for that job.

## Scope

Arguments given: `$ARGUMENTS`

- If `$ARGUMENTS` is empty, run a full audit across `backend/`, `frontend/` and the deployment
  files (`docker-compose*.yml`, `backend/docker/`, `frontend/docker/`).
- If `$ARGUMENTS` is `backend` or `frontend`, audit only that half.
- If `$ARGUMENTS` is `dependencies`, audit dependency advisories only.
- Otherwise treat `$ARGUMENTS` as a path (e.g. `backend/src/platform/adapters/inbound/api/v1`):
  audit all applicable dimensions but restrict findings to that path.

The rules each dimension checks against are in `docs/reference/auth.md`,
`docs/reference/backend-conventions.md` section 2 and `docs/reference/file-storage.md`; read them
first.

## Dimensions

- **Authorization**: every route outside `/api/v1/auth`, `/api/v1/public` and the health checks
  must resolve an actor through `adapters/inbound/api/auth_deps.py`, and every write or sensitive
  read must check its permission with `require_permission` or `require_any_permission`. Hunt for
  routes missing either. Check that granting stays capped (`permission_rules.assert_grantable_by`)
  on every path that grants: direct grants, group permissions, group membership. Check that
  personal access tokens can never exceed their owner's permissions, that API keys only work
  when enabled, that the system user and other protected accounts cannot be edited, demoted or
  locked out by others, and that personal data (sessions, passkeys, tokens, TOTP) of one user is
  never reachable by another.
- **AuthN and sessions**: the session cookie flags (`infrastructure/security/cookies.py`), CSRF on
  every unsafe cookie-authenticated request, session rotation on login and privilege change, the
  password step and two-factor flow (no way to reach a session with only the first factor), TOTP
  replay (`replay_guard.py`), the login throttle and lockout (`login_attempts.py`), uniform login
  errors (user enumeration), passkey challenge binding (`webauthn.py`), password reset and mail
  flows, and logout clearing every store and cached item in the frontend.
- **Secrets and sensitive data**: hardcoded credentials or keys, secrets reaching logs, the
  security log or error messages (`exception_handlers.py` turns domain error messages into
  client-visible `detail` strings, so flag any that embed secrets or internal paths), encryption
  at rest of stored secrets (`secret_box.py`, ADR 0004) and whether every secret setting goes
  through it, settings responses leaking SMTP passwords or other secrets, token storage as hashes
  only (`opaque_secret.py`), sensitive data in `localStorage`, anything secret in `VITE_`
  prefixed env vars (baked into the bundle), and weak defaults in `.env.example`, migrations or
  the system user seed beyond the `INIT__*` values.
- **Injection**: raw SQL or `text()` usage, string-built `LIKE` patterns, unsafe filter or sort
  parameters interpolated into queries, command execution, path traversal.
- **File handling**: uploads (`file-storage.md`, `content_types.py`, `pillow_image_processor.py`):
  size limits enforced before the body is read in full, content type sniffed and not trusted from
  the client, image decompression bombs, metadata (EXIF location) stripped, and download headers
  (`download_headers.py`: `Content-Disposition`, `nosniff`, no inline rendering of active
  content such as SVG or HTML).
- **XSS and frontend sinks**: `v-html`, `innerHTML`, user content rendered into templates or mail
  templates, URL handling and open redirects (the login redirect target in particular).
- **SSRF**: anything that fetches a URL a user or administrator supplies (the SMTP host today, a
  recipe import later): target validation and timeouts.
- **Transport, headers, infra**: `frontend/docker/nginx.conf` (CSP, HSTS, forwarded headers and
  `trusted-proxies.sh`), `middleware/security_headers.py`, CORS, the containers' users and exposed
  ports in `docker-compose.yml`.
- **Dependencies**: in the backend, check what is actually available (`poetry run pip-audit` or
  similar) and report plainly if no such tool is installed rather than guessing at results;
  `npm audit` in the frontend.
- **Live events**: once a live channel (SSE or websocket) exists, whether events are filtered per
  user and permission before delivery or broadcast to every connected client.

## Before starting

Read the reports in earlier `.audit/security-audit-<date>/` folders first, if any exist. They
track residual items and conventions already accepted in a prior audit.

## Method

1. Fan out parallel read-only Explore subagents, one per dimension in scope. Each subagent
   searches and reads only, with no edits.
2. Before reporting any finding, verify it: it must cite a concrete `file:line`, and you must
   re-check that file:line yourself before it goes in the report. Do not report a finding you have
   not personally verified.
3. Cross-check candidate findings against earlier audit reports and drop duplicates.

## Output

Write a report to `.audit/security-audit-<today's date>/report.md` (create the folder; use
`YYYY-MM-DD`). Structure:
- Findings ranked by severity (critical, high, medium, low).
- Each finding: **Finding** (what, and a concrete attack scenario: who can do what they
  shouldn't), **Files** (file:line references), **Approach** (how it would be fixed), **Risk**,
  **Effort**.
- Describe attack scenarios in prose. Do not write working exploit payloads into the report.

Then send the user a short summary: the count of findings by severity and the report path. Do not
include the full report inline unless the user asks.

Hard constraints: this is read-only. Do not edit, create, or delete any source file. Do not run
`git add` or `git commit`. Use only local tools; never transmit code to an external service. The
only file you write is the audit report.

Use model `haiku` for the investigating subagents. Minimize token usage. Don't assume anything.
