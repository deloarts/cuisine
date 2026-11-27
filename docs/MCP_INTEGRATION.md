# mcp integration

- [mcp integration](#mcp-integration)
  - [1 purpose and scope](#1-purpose-and-scope)
  - [2 how it fits together](#2-how-it-fits-together)
  - [3 setting it up](#3-setting-it-up)
    - [3.1 an agent with a token](#31-an-agent-with-a-token)
    - [3.2 a hosted app through OAuth](#32-a-hosted-app-through-oauth)
  - [4 what an agent can do](#4-what-an-agent-can-do)
  - [5 drafts](#5-drafts)
  - [6 security](#6-security)

## 1 purpose and scope

An AI agent such as Claude Code, Claude Desktop, ChatGPT or claude.ai can work with Cuisine on its user's behalf through MCP, the Model Context Protocol agent clients speak. Its main job is importing recipes: the agent reads a website or a PDF itself and hands Cuisine the structured recipe, which becomes a draft a person reviews and publishes. It can also search and read recipes and the ingredient catalogue.

The agent acts as the person whose token it uses, or who connected it, with that person's permissions or fewer. Nothing an agent does publishes or deletes anything.

## 2 how it fits together

The MCP surface is one more inbound adapter of the backend, next to the web, `pat` and key APIs, at `/api/v1/mcp`. It speaks the streamable HTTP transport in its stateless form. Agents that take a header authenticate with a personal access token; hosted apps that cannot (ChatGPT, claude.ai) connect through OAuth, with Cuisine as the authorization server and the web app's consent page as the place where the person approves them ([reference/auth.md section 8](reference/auth.md#8-oauth-for-hosted-ai-clients)). Each tool runs the same use case, with the same permission checks, as the matching button in the web app. The rules for tools, budgets and the call log are in [reference/mcp-tools.md](reference/mcp-tools.md).

## 3 setting it up

Both ways start with the same two steps:

1. An administrator grants `use:mcp` to the people who may connect an agent, together with `write:recipes` (and `write:ingredients`, so the agent can add missing ingredients). Putting a person into the default groups Cooks and Kitchen helpers grants all of them.
2. Agent access is on by default; the agent settings switch it off and set the budgets (120 calls a minute and 30 drafts an hour per token) and the lifetime cap of agent tokens (30 days).

### 3.1 an agent with a token

This suits agents that take a custom header: Claude Code, GitHub Copilot in VS Code, Gemini CLI, Cursor and the like.

1. The user creates a personal access token on the account page with `use:mcp`, `write:recipes` and `write:ingredients` and an expiry within 30 days. Cuisine shows the token once.
2. Claude Code connects with:

```sh
claude mcp add --transport http cuisine https://<cuisine host>/api/v1/mcp --header "Authorization: Bearer <token>"
```

Other clients take the same URL and header. The client then lists the tools and offers the `import_recipe` prompt as a command.

### 3.2 a hosted app through OAuth

This suits apps that only offer "OAuth" or "no authentication" for a custom connector: ChatGPT (developer mode), claude.ai and Claude Desktop connectors, Copilot Studio.

1. The administrator leaves "Allow apps to connect through OAuth" on in the agent settings and may list the hosts apps may return to (for example `chatgpt.com` and `claude.ai`); an empty list allows any app.
2. Cuisine must be reachable at `DOMAIN` over https, and `/api/v1/mcp`, `/api/v1/oauth/*` and `/.well-known/oauth-*` must reach the backend without a browser challenge ([OPERATIONS.md section 7](OPERATIONS.md#7-ai-agents-behind-cloudflare)).
3. In the app, the user adds a connector with the URL `https://<cuisine host>/api/v1/mcp` and OAuth as the authentication. The app registers itself with Cuisine and opens Cuisine's consent page.
4. The user signs in to Cuisine as always, checks the app's name and the host it returns to, gives the AI agents consent if it is still missing, chooses what the app may do and allows it.
5. The app holds a connection that lasts as long as an agent token may (30 days by default) and then asks the user to approve it again. It appears under Account, AI agents, Connected apps, where the user disconnects it at any time.

## 4 what an agent can do

| Question or task | Tools |
| ---------------- | ----- |
| Find and read recipes | `search_recipes`, `get_recipe`, `list_my_drafts` |
| Know the vocabulary | `list_tags`, `list_units`, `list_ingredient_categories`, `search_ingredients` |
| Import a recipe | `create_recipe_draft`, `create_ingredient`, `attach_recipe_image`, `add_recipe_translation` |

The exact arguments are what the client shows.

## 5 drafts

A recipe an agent creates is a draft visible to its owner and to `manage:recipes` only, marked as created by an agent. Ingredients the agent names but the catalogue lacks become draft ingredients, usable at once and listed for review. The person opens the draft in the web app, corrects it and publishes it. An agent may add an image or a translation to a draft, never to a published recipe.

## 6 security

- Every request authenticates on its own; a revoked token, a deactivated owner or a permission taken away stops the agent on its next call.
- An API key reaches the read tools only; drafts need a personal access token or a connected app.
- A connected app's access ends at once when the person disconnects it, signs out everywhere or withdraws the AI agents consent; a refresh token used twice ends the connection, since it must have leaked.
- The consent page shows the app's self-declared name next to the host it returns to, never follows an address the app did not register, and lets the person grant less than the app asked for.
- Food restrictions and private notes never reach an agent.
- Every tool call lands in the agent call log, which tells an agent's actions apart from its user's own; the user sees their own calls, administrators with `read:security_log` all of them.
- Recipe text in results is content written by people; the server instructions tell the agent to treat it as data, never as instructions.
