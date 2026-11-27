# Cuisine

Cuisine is a self-hosted cookbook for a household, its friends and its family. It runs as a small Docker stack behind your own domain. There is no open sign-up; an administrator creates every account.

Cuisine comes batteries-included: a fresh instance starts with 622 ingredients in German and English, each with nutrition values, allergens and diet markers, along with 140 pieces of kitchen equipment, 38 units and 58 tags. You can start writing recipes on day one instead of building a catalogue first.

## what it does

- **Recipes.** Steps with their own ingredients and equipment, sub-recipes, scaling by servings, variations that store only their differences, co-editors, a revision history and a print view. Ingredient lists, nutrition, allergens and fitting diets are derived from the steps.
- **Ingredient catalogue.** A seeded base catalogue with aliases, families, seasons, extended nutrients, 1404 food facts and nutrition prefilled from USDA FoodData Central, plus an equipment catalogue for your kitchen.
- **Personal layer.** Favourites, ratings, private cook notes, allergies, intolerances and diets, which hosts can take into account for their dinner guests.
- **Cooking and planning.** A cooking history with "on this day", households with a shared meal plan, and shopping lists that update live on every phone.
- **Sharing.** Recipe visibility per recipe, optional public recipe pages, `.cui` export and import, and pairing with other Cuisine instances to share recipes and catalogue suggestions.
- **AI agents.** An MCP server lets Claude, ChatGPT and other agents import recipes from websites or PDFs as drafts, and search and read the cookbook ([docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)).
- **Accounts and security.** Groups with freely chosen permissions, passwords with two-factor authentication, passkeys, personal access tokens, API keys and a security log.
- **Administration.** Branding, mail, webhooks, banners and notices, legal pages and consents, a log viewer, maintenance mode and backups. Photos are stored in the database as WebP without location data, so one database dump is the whole instance.

## installation

[docs/INSTALLATION.md](docs/INSTALLATION.md) sets up a new instance from the release images. [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) sets up a local development environment, and [docs/OPERATIONS.md](docs/OPERATIONS.md) covers backups, updates and recovery.

## documentation

| Guide | For |
| ----- | --- |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Architecture, conventions and how to add things |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, tests, migrations |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Deploying a new instance |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Backups, updates, recovery |
| [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) | Connecting AI agents |
| [docs/RELEASING.md](docs/RELEASING.md) | Versioning and the release flow |
| [docs/reference/](docs/reference/README.md) | The detailed rules behind each guide |
| [docs/adr/](docs/adr/README.md) | Why the code is shaped this way |

## license

Cuisine is source-available under the [DELOARTS License (DAL) 1.0.0](LICENSE.md). You may use, change and share it for noncommercial purposes. Any commercial use needs a separate commercial license from license@deloarts.com.
