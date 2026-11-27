# architecture

The layer rules of the backend, where new code goes, how it is wired, and the layout of the frontend. The concept is in [CONTRIBUTING.md section 1](../CONTRIBUTING.md#1-architecture-in-one-page); why there are no bounded contexts is in [ADR 0001](../adr/0001-hexagonal-without-bounded-contexts.md).

- [1 backend layers](#1-backend-layers)
- [2 packages](#2-packages)
- [3 where new code goes](#3-where-new-code-goes)
- [4 wiring](#4-wiring)
- [5 API surfaces](#5-api-surfaces)
- [6 frontend layout](#6-frontend-layout)

## 1 backend layers

1. `domain/` holds entities (dataclasses on `shared_kernel.domain.entities.base.Entity`), value objects, pure rule functions in `services/` and the errors. It imports nothing but the standard library and `shared_kernel`. No SQLAlchemy, Pydantic or FastAPI.
2. `ports/outbound/` declares protocols for everything the application needs from outside: repositories, the unit of work, the token service, the password hasher, the mail server, the image processor, the throttle and the replay guard.
3. `application/` holds the use cases, the services several use cases share (`login_session.py`, `security_audit.py`, `login_throttle.py`) and DTOs. It imports domain and ports, never an adapter or `infrastructure`.
4. `adapters/inbound/api/` exposes the use cases over HTTP: routers, schemas, the dependency providers, auth resolution, exception handlers and middleware. `adapters/outbound/` implements the ports.
5. `infrastructure/` holds technical building blocks the adapters use: settings, the logger, the security primitives (JWT, bcrypt, TOTP, WebAuthn, Fernet), the Redis client and the gunicorn configuration.

Dependencies point inwards only: adapters → application → ports → domain. The layering is enforced by review, not by an import linter.

## 2 packages

`src/platform` holds users, groups, auth, settings, the file storage, the agent call log and the MCP server. `src/cookbook` holds recipes, ingredients, resources, the personal layer, the cooking history, the meal plan and shopping lists, in the same four layers; it may import Platform's domain, ports and the API and MCP building blocks (the session, `get_current_user`, `AgentTool`), and Platform never imports it. `src/shared_kernel` holds what both need without belonging to either. `src/bootstrap` is the composition root: it collects every package's models (`models.py`), routers and agent catalogues, and seeds the defaults. The cookbook's rules are in [cookbook.md](cookbook.md).

## 3 where new code goes

| New code | Goes to |
| -------- | ------- |
| A recipe, ingredient or shopping list concept | `src/cookbook/domain/entities/` |
| A rule that decides something | a function in `<package>/domain/services/` |
| An action a user takes | a use case in `<package>/application/use_cases/<area>/` |
| A table | a model in `<package>/adapters/outbound/persistence/models/`, exported from its `__init__.py`, which `src/bootstrap/models.py` imports so Alembic sees it |
| A repository | its protocol in `ports/outbound/repositories/`, its implementation in `adapters/outbound/persistence/repositories/` |
| An endpoint | a router in `adapters/inbound/api/v1/`, included in `bootstrap/main.py` |
| A tool for AI agents | an `AgentTool` in the package's `adapters/inbound/mcp/catalog.py` ([mcp-tools.md](mcp-tools.md)) |
| A setting read from the environment | `platform/infrastructure/config/settings.py` and `.env.example` |
| A setting an administrator changes | a field on a section in `platform/domain/entities/settings.py` |

## 4 wiring

Use cases receive their dependencies in the constructor. `adapters/inbound/api/deps.py` builds them per request from a `Platform` object, which holds every repository on the request's session, and from cached process-wide adapters (token service, hasher, verifier). The Redis-backed throttle and replay guard are separate providers (`get_login_attempts`, `get_replay_guard`), so the tests can swap them. `bootstrap/main.py` mounts the routers, the middleware and the lifespan (boot guard, dev migrations, the system user seed); no other module wires concrete classes.

## 5 API surfaces

| Prefix | Authenticates with | For |
| ------ | ------------------ | --- |
| `/api/v1/auth` | nothing, or the session to log out | the login steps |
| `/api/v1/web` | the session cookie (or bearer header) | the frontend |
| `/api/v1/public` | nothing, rate limited per address for the recipes | the login page's instance name and language, the legal pages, robots.txt, the web app manifest, and the public recipe pages ([cookbook.md](cookbook.md) section 6e) |
| `/api/v1/pat` | a personal access token in `X-Api-Key` | the user's own scripts |
| `/api/v1/key` | an API key in `X-Api-Key` | other programs, when API keys are enabled |
| `/api/peering/v1` | the invitation code (handshake) or a peer's request signature, rate limited per address | other Cuisine instances ([peering.md](peering.md)); the path carries the peering protocol version |
| `/api/v1/mcp` | a PAT or API key carrying `use:mcp` in `Authorization: Bearer` | AI agents ([mcp-tools.md](mcp-tools.md)) |
| `/api/v1/oauth` | nothing, the client's credentials or a refresh token, per endpoint | hosted AI clients registering, exchanging codes for tokens and revoking them; the consent page lives in the web app ([auth.md](auth.md) section 8) |
| `/health`, `/ready` | nothing | container health checks |

## 6 frontend layout

| Folder | Holds |
| ------ | ----- |
| `src/core/api` | the axios instances, `webApi`, the generated schema and its `Schemas` alias |
| `src/core/stores` | the signed-in user, the layout and theme, the public instance info |
| `src/core/i18n` | the i18n instance, the core locale files and the merge of the feature locale modules |
| `src/core/config` | the colour palettes and the theme presets |
| `src/app` | the navigation entries (`navigation.ts`) and the layouts: the app shell (header, sidebar, phone bottom nav), the sign-in shell and the guest shell of the public recipe pages |
| `src/shared/components` | components several features use |
| `src/features/<feature>` | `views/`, `components/`, `api/`, `locales/` and `routes.ts` of one area |
| `src/router` | the router, which collects every feature's `routes.ts`, and the guard |

A feature imports from `core` and `shared`; a feature that another feature needs exposes it through `shared` rather than being imported directly.
