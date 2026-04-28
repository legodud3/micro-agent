# micro-agent v0.2 help

This document is the source of truth for the `/help` command.

## What micro-agent is
micro-agent is a small terminal chat agent that:
- sends normal chat messages to OpenRouter
- lets the model call approved tools when needed
- runs a separate “verifier QC” sub-agent after the main draft is done (and may ask the main agent to revise)
- currently supports one model tool: `web_search`

## Slash commands
Slash commands are handled locally by the terminal app. They are not added to chat history and do not persist as a mode.

### `/`
Lists available slash commands.

### `/tool`
Lists the tools the model can call, with a one-line description for each tool.

### `/model`
Lists 10–15 live OpenRouter text/coding/agentic models. You can set the active model via:
- `/model set <id>`
- `/model <id>`
This writes the choice to `config.json` so it persists until changed.

### `/help`
Prints this `docs/help.md` file.

### `exit` / `quit` / `/exit` / `/quit`
Quits the chat.

## Model tools
### `web_search`
Searches the public web for up-to-date information using Tavily.

The tool returns a small normalized list of search results with:
- `title`
- `url`
- `snippet`

Search snippets are truncated to keep tool results compact.

## Configuration
### `.env`
Required environment variables:
- `OPENROUTER_API_KEY` — required for model calls
- `TAVILY_API_KEY` — required for `web_search`

Optional environment variables:
- `MICRO_AGENT_LOCATION` (or `LOCATION`) — a short location hint (city/region/country) that will be included in every user prompt.

### `config.json`
Controls:
- `base_url`
- `micro_agent` (the main model + generation params)
- `verifier` (the QC/verifier model + params)

The verifier uses its model/params to judge the main agent’s latest draft and returns JSON:
- `status`: `approve` or `reject`
- `issues`: `[]` when approved, otherwise a list of issues.

Its instruction file lives at `micro_agent/agents/verifier_system_prompt.txt`.

## CLI flags
### `--dry-run`
Runs the terminal flow without model or Tavily network calls.

### `--trace`
Prints model/tool loop trace lines.

### `--max-tool-iterations N`
Sets the safety cap for model/tool iterations per normal user message.
Default: `50`.

This cap includes both:
- the main agent’s tool-call iterations, and
- any “main agent revise” rounds triggered by verifier rejection.

## What micro-agent cannot do yet
micro-agent does not currently have model tools for:
- reading arbitrary local files
- editing files
- running shell commands
- searching the local repo
- persistent planning or long-term memory

The only local file used for self-help is `docs/help.md`.

## Developer note
Coding assistants working on this repo should follow the repo’s `AGENTS.md` and keep this file updated whenever user-facing behavior changes.
