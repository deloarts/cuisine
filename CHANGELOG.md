# changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-11-27

The first release.

### Added

- Recipes with steps that name their ingredients and equipment, sub-recipes, variations, revisions and co-editors; ingredient lists, nutrition, allergens and diets derived from the steps and scaled with the servings.
- German and English throughout, for the interface and for recipe and catalogue text.
- An ingredient catalogue with nutrition, unit conversions and the 14 EU allergens, seeded with about 670 base ingredients from USDA FoodData Central.
- Favourites, ratings, private notes, allergies, intolerances and diets with warnings, and dinner guests.
- Households with a shared meal plan, a cooking calendar, meal plan suggestions and live shared shopping lists.
- Recipe visibility from private to public, set per recipe with an admin default.
- Recipe exchange as `.cui` files and a catalogue file for moving data between instances.
- Peering: pair two Cuisine instances to share recipes as read-only mirrors.
- An MCP surface for AI agents, with tokens or OAuth, to search recipes and import them from websites and PDFs as drafts.
- Accounts managed by administrators, groups as permission bundles, mandatory two-factor authentication, passkeys, access tokens and a security log.
- An admin area with branding, mail, webhooks, banners and notices, legal pages with consents, feature switches, retention, maintenance mode and readings of the host, storage and backups.
- File storage in Postgres, on a local volume or in SeaweedFS.
- Installs as an app on Android and iOS.
- A Docker Compose stack of prebuilt images for linux/amd64 and linux/arm64 (Raspberry Pi), with Postgres, Redis, nightly database dumps and an optional Cloudflare Tunnel.
