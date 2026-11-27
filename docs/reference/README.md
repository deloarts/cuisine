# reference

The detailed rule tier of the documentation. The guides one level up explain what a part of Cuisine is and how to do the common tasks; the files here hold what a change has to get exactly right: checklists, invariants, edge cases and the reasoning behind a single rule.

Every fact lives in one place. A guide explains a concept and links here for the rules; a reference file states the rules and links back instead of explaining the concept again. Neither copies what the code already says: column lists, enum values and signatures go stale, so a document names the module that holds them. Rules a tool checks (ruff, mypy, eslint, stylelint, `npm run check:i18n`) are named, not restated.

A reference file covers one topic, opens with a paragraph naming its guide, and numbers its sections so comments can point at `docs/reference/<file>.md section N`.

| File | Covers | Guide |
| ---- | ------ | ----- |
| [architecture.md](architecture.md) | Layers, packages, where new code goes, wiring, the frontend layout. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 1 |
| [cookbook.md](cookbook.md) | Languages, permissions, derived ingredients and nutrition, the private personal layer, cooking history, meal plan, shopping lists and live updates, the nutrition lookup, seeds. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 1 |
| [formats.md](formats.md) | The exchange formats `cuisine-recipes` and `cuisine-catalogue`: versions, the additive-only rule, the upgrade chain, schema files and golden fixtures. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 1 |
| [peering.md](peering.md) | Pairing with other Cuisine instances: invitations, the handshake, version negotiation, request signatures, the peering surface, revoke, the per-peer switches, peer channels with catch-up and restores, and the recipe kind. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 1 |
| [mcp-tools.md](mcp-tools.md) | Writing MCP tools, read and draft tools, agent authentication, budgets and the call log. | [MCP_INTEGRATION.md](../MCP_INTEGRATION.md) |
| [recipes.md](recipes.md) | Step lists for an endpoint, a field, a domain error, a permission, a frontend feature and a settings section. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 2 |
| [backend-conventions.md](backend-conventions.md) | Use cases, permissions, errors, DTOs and schemas, logging. | [CONTRIBUTING.md](../CONTRIBUTING.md) sections 3.1 to 3.3 |
| [persistence.md](persistence.md) | Models, column types, repositories, the unit of work, settings storage, public ids, the resolver and the instance id. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 3.4 |
| [auth.md](auth.md) | Sessions, CSRF, the login steps, TOTP, passkeys, tokens, escalation guards, the security log. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 3.5 |
| [file-storage.md](file-storage.md) | Accepted types, image re-encoding, limits, download headers, ETags, the storage providers and moving between them. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 3.6 |
| [admin-area.md](admin-area.md) | Host and storage readings, branding and display settings, webhooks, the banner, in-app notices. | [OPERATIONS.md](../OPERATIONS.md) |
| [frontend-conventions.md](frontend-conventions.md) | Code style, API calls and types, styling and the look, i18n, stores. | [CONTRIBUTING.md](../CONTRIBUTING.md) sections 4 and 5 |
| [testing.md](testing.md) | Backend fixtures and fakes, frontend specs, what to test. | [CONTRIBUTING.md](../CONTRIBUTING.md) section 6 |
| [development-migrations.md](development-migrations.md) | Writing, checking and shipping migrations. | [DEVELOPMENT.md](../DEVELOPMENT.md) section 5 |
| [releasing-ci.md](releasing-ci.md) | CI jobs, the release workflow with its smoke test, GHCR retention and the release scripts. | [RELEASING.md](../RELEASING.md) |
| [releasing-github-setup.md](releasing-github-setup.md) | Pull request and actions settings, the rulesets with their required checks, code security, packages. | [RELEASING.md](../RELEASING.md) |
