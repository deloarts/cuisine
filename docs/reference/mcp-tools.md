# mcp tools

The rules for offering a tool or a prompt to AI agents through the MCP surface, and for authenticating, limiting and logging agent calls. The concept is in [MCP_INTEGRATION.md](../MCP_INTEGRATION.md).

- [1 where tools live](#1-where-tools-live)
- [2 writing a tool](#2-writing-a-tool)
- [3 read tools and draft tools](#3-read-tools-and-draft-tools)
- [4 authentication, budgets and the call log](#4-authentication-budgets-and-the-call-log)
- [5 testing a tool](#5-testing-a-tool)

## 1 where tools live

1. The building blocks (`AgentTool`, `ToolInput`, `DraftToolInput`, `ToolOutput`, `AgentPrompt`, `AgentCatalog`, `ref`) are in `src/platform/adapters/inbound/mcp/tools.py`. The server (`server.py`) and the dependency resolver (`resolve.py`) belong to Platform.
2. The cookbook offers its tools as `COOKBOOK_AGENT_CATALOG` in `src/cookbook/adapters/inbound/mcp/catalog.py`. `src/bootstrap/main.py` hands the catalogues to `create_agent_app` and mounts the app at `/api/v1/mcp`, so Platform never names the cookbook. A tool or prompt name used twice fails at startup.

## 2 writing a tool

1. A tool has a snake case name, a title, a description written for a model, an input model and an async handler `(ctx, args) -> ToolOutput`.
2. The input model subclasses `ToolInput`, which refuses unknown arguments. A list tool takes a `limit` with a small default.
3. The handler builds its use case with `await ctx.use_case(<factory>)`, the factory the matching web route takes through `Depends`, and calls it with `ctx.actor` first. The resolver walks the factory's `Depends` tree on the call's session and applies the app's dependency overrides; a factory that reads the request cannot be resolved.
4. A permission a route checks outside its use case goes into the tool's `requires`, so a tool never checks less than its route and a token never sees a tool it cannot use.
5. The handler raises the use cases' domain errors; the server turns them into an error result the agent reads and can correct, never a protocol error.
6. A result stays below 200,000 characters; a larger one answers with a hint to narrow the query.
6a. A tool that takes `locale` answers in the token user's UI language when the agent names none, as the web surface does (`_locale` in `catalog.py`), so a recipe's own text and the catalogue names around it come in one language.
7. Every tool sees only the recipes the token's user can see ([cookbook.md section 6b](cookbook.md#6b-recipe-visibility)); a private recipe of someone else is unknown to an agent as it is in the web app.
7a. Mirrors of recipes paired instances share with this one ([cookbook.md section 6f](cookbook.md#6f-sharing-with-paired-instances-and-mirrors)) are read only for agents as for people. The read tools include the mirrors the user can see with their attribution: `search_recipes` names `from_instance` and `source_author` (null for a local recipe), and `get_recipe` returns `mirror` and `mirror_details` (source instance, author name, `source_url`, plain-text lines) and, with `include_variations`, marks variations that came from the source as `mirrored`, with the author's name there. Every tool that writes refuses a mirror with the error `MirrorReadOnlyError`, which the agent reads as a correctable result. No tool imports `.cui` files.
8. A result never contains food restrictions, the warnings derived from them or the dinner guest flag (`get_recipe` drops `warnings`, `has_warning`, `unsuitable_for_guests` and `variation_fits_guests`), and no private cook note. No tool takes guests.

## 3 read tools and draft tools

1. A read tool (`ToolKind.READ`, the default) never writes.
2. A draft tool (`ToolKind.DRAFT`) only creates records that wait for a person: a recipe draft or a draft ingredient. It may add an image or a translation to a draft the caller may edit, never to a published recipe, and a language's names to a draft ingredient the caller may edit (`add_ingredient_translation`), never to a catalogue ingredient. It never publishes or deletes.
3. A draft tool's input subclasses `DraftToolInput`, whose optional `idempotency_key` makes the server answer a repeated call with the first call's records. The call log keeps the first answer of such a call (`agent_calls.result`), and the repeat returns it unchanged with `replayed: true` added; a call logged before answers were kept is answered with `replayed` and its `created` refs only.
4. A draft tool returns the references of every record it created in `ToolOutput.created_refs`, built with `ref(kind, public_id)`.
5. `create_ingredient` takes allergens and diet markers, so the recipes using the ingredient derive the diets they fit; `search_ingredients` returns both. It also takes the extended nutrients per 100 g by catalogue key (`extended_nutrition_per_100g`, any other key is an error) and the season months.
6. `get_recipe` with `include_variations` adds the recipe's variations the caller may see (private ones only the caller's own), each with its name, note, locale, author name, staleness, rating and the changes that still apply ([cookbook.md section 3f](cookbook.md#3f-variations-co-editors-and-copies)). Variations, co-editors and copies have no draft tools.
7. `create_recipe_draft` takes step ingredients by catalogue id, by name or as a sub-recipe (`sub_recipe_id` from `search_recipes`, amount in its yield unit or servings); a name no ingredient carries in any language becomes a draft ingredient in the recipe's original language, which needs `write:ingredients`. Units are named by code, tags by id or name. Each step may list its equipment by id or by name or alias (`equipment`, with an optional count and note); a name the catalogue lacks becomes a draft equipment item, listed under `created_equipment`. Step text may mention the step's own lines and equipment by id (`@[Name](ingredient:<id>)`, `@[Name](recipe:<id>)`, `@[Name](equipment:<id>)`) or, for ingredients and equipment, by name (`@[Zwiebeln](ingredient)`, `@[Topf](equipment)`): a named mention matches one line or item of its own step by name, plural or alias in any language or by the name the agent gave, failing that by the end or a whole word of one of those names ("flour" for "plain flour", "Zucker" for "Kristallzucker"), so it also reaches an ingredient the same call creates, and is saved as a mention by id (`mentions.resolve_named_mentions`). A named mention that matches none or several answers a correctable error naming the step. An optional top-level `ingredients` takes the recipe's declared ingredient list in the same shape as step ingredients, and `add_recipe_translation` takes its notes as `ingredient_notes`; `get_recipe` returns the merged list.
8. The tool description, the step text's field description, the server instructions and the `import_recipe` prompt all ask for each ingredient on the step that uses it and a mention where the text names it, with one worked example in the tool description. The answer carries `hints`, advice for the next draft since an agent cannot change this one: no step lists its ingredients while the declared list does, a step whose text mentions none of its ingredients, and ingredients created as drafts without allergens or markers (so the recipe claims no diet until a person checks them), each named with its id so `add_ingredient_translation` can name it in the other languages.
9. Agents always add every content language (de-AT and en-GB): the server instructions, the `import_recipe` prompt and the descriptions of `create_recipe_draft`, `add_recipe_translation`, `create_ingredient` and `add_ingredient_translation` say so. The answers of `create_recipe_draft` and `add_recipe_translation` carry a hint naming each language the draft still lacks (`_translation_hint`), and those of `create_ingredient` and `add_ingredient_translation` one naming each language the ingredient has no name in, until none is missing. `add_ingredient_translation` sets one language's name, plural and optionally its aliases (replacing that language's aliases), checking the names are free as any edit does (`ManageIngredients.add_translation`). A translated step text may mention the step's stored lines and items by name in its own language (`@[onions](ingredient)`), resolved like the named mentions of item 7 against every name, plural and alias of each line.

## 4 authentication, budgets and the call log

1. Every request authenticates on its own with `Authorization: Bearer <token>`, a personal access token, an API key or the access token of an app connected through OAuth (`AuthenticateAgent`, [auth.md section 8](auth.md#8-oauth-for-hosted-ai-clients)). The token must carry `use:mcp`; a PAT and an OAuth grant act as their owner narrowed to the permissions they carry, an API key as its service account and only while API key authentication is on. A refused request answers with a `WWW-Authenticate` challenge that names the Protected Resource Metadata.
2. Agent access can be switched off in the agent settings (`/settings/agents`); every agent request then answers 403.
3. A token carrying `use:mcp` must expire within the agent settings' `token_max_lifetime_days` (30 by default), on top of the general token cap.
4. Each token may make `calls_per_minute` calls and, with a PAT or an OAuth grant, `drafts_per_hour` successful draft calls; an API key never creates drafts. For an OAuth app the budget belongs to the grant, not to its hourly access token. A spent budget answers with a refused result.
5. Every call, refused or failed ones included, is appended to the agent call log (`agent_calls`) on a separate session, with the arguments cut to 4,000 characters. A user reads their own calls at `/users/me/agent-calls`; holders of `read:security_log` read every call at `/agent-calls`.

## 5 testing a tool

1. `tests/integration/test_mcp.py` calls the surface over HTTP like a client: one JSON-RPC message per POST with `Accept: application/json, text/event-stream` and the bearer token, minting the token through the PAT route.
2. Test every tool's happy path, its permission (the tool missing from `tools/list` without it), and the errors the agent should be able to correct.
