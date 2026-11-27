# 0001 hexagonal layers without bounded contexts

- Status: accepted
- Date: 2026-11-21

## context

Cuisine is built on the blueprint of Glados, a manufacturing system whose backend is a modular monolith of seven bounded contexts with import contracts between them, a read side, a transactional outbox and event workers. That structure pays for itself in a large domain worked on by several people over years. Cuisine is a cookbook for a household and its friends and family: one small domain (recipes, ingredients, meal plans, shopping lists, households) next to the platform concerns (accounts, sign-in, settings, files). Copying the full modularity would mean more packages, contracts and wiring than code.

## decision

The backend keeps Glados's hexagonal layers inside each package (domain, ports, application, adapters) and its dependency rule (inward only), its async I/O, its use case and repository shapes, and its conventions. It drops the bounded contexts: there is one `platform` package for users, auth, settings and files, one `cookbook` package for the recipe domain, a `shared_kernel`, and `bootstrap` as the composition root. There are no import-linter contracts, no read side and no general event bus. The one place that needs reliable delivery, webhooks, writes its deliveries in the same transaction as the change and sends them from a small background worker; it is a narrow outbox for that purpose only. `cookbook` may use Platform; Platform never imports `cookbook`.

## consequences

New code has an obvious home and few files, and Glados's documentation and habits still apply layer by layer. The layer rule is kept by review instead of a tool, so a stray import is caught later. Live updates for the shopping list go through Redis pub/sub to server-sent events rather than through an outbox, and the MCP surface is one more inbound adapter next to the web API; if the cookbook ever grows into several independent areas, splitting it into bounded contexts with contracts is a later decision with its own ADR.
