---
name: architecture
description: Before changing code, understand where it belongs in Cuisine's architecture and keep the dependency direction. Load when adding features, moving code, starting the cookbook package, or wiring new components.
---

# Cuisine architecture

The architecture is documented in `docs/`; read it instead of guessing. `docs/CONTRIBUTING.md`
section 1 has the overview. The rules are in `docs/reference/architecture.md`: the backend layers
and what each may import (section 1), the packages and which may import which (section 2), the
table of where new code goes (section 3), wiring (section 4), the API surfaces (section 5) and the
frontend layout (section 6). `docs/reference/recipes.md` holds the step lists for common changes.
The reasons are in `docs/adr/`, starting with
`0001-hexagonal-without-bounded-contexts.md`.

## Before you add code

1. Name the layer the code belongs to (backend: domain, ports, application, adapters,
   infrastructure; frontend: core, shared, features, app) and the package (`platform`,
   `cookbook`, `shared_kernel`).
2. Check that every new import points inward (backend adapters → application → ports → domain;
   frontend features → shared → core). `cookbook` may import Platform's domain and ports, never
   the reverse. If an import points outward, stop and restructure.
3. Check that `domain/` and `shared_kernel/` stay free of SQLAlchemy, Pydantic and FastAPI.
4. Check whether an existing abstraction already covers it (a domain service, a port, a shared
   component, a store).
5. Concrete classes are wired only in `adapters/inbound/api/deps.py` and `bootstrap/main.py`.

No import linter enforces the layering, so review every new import yourself. After a structural
change (moved file, new cross-layer import, new package) run mypy from `backend/` and
`npm run lint:check` and `npm run type-check` from `frontend/`.
