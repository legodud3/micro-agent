# Coding assistant instructions

Follow these rules when changing this repo.

## First steps
- Read `README.md` before making changes.
- Read `docs/help.md` before changing user-facing behavior.
- Read `docs/plan.md` for the project shape and constraints.

## Project style
- Keep the code ultra-minimal and easy to read.
- Prefer Python standard library only.
- Keep modules small and focused:
  - `agent_harness.py` handles terminal UX and slash-command routing.
  - `config_loader.py` loads local config and prompts.
  - `openrouter_client.py` handles OpenRouter request/response helpers.
  - `tool_loop.py` runs the main model -> tool -> model loop (and optional verifier QC).
  - `agents/` contains sub-agent code and prompts (e.g. verifier/QC).
  - `tools/` contains tool definitions/executors.
- Preserve plain-language comments and docstrings.
- Add a short comment before each meaningful code block explaining what it does.
- Avoid framework/tooling churn unless explicitly requested.

## Documentation rules
- Update `README.md` when run instructions, files, flags, or commands change.
- Update `docs/help.md` whenever user-facing capabilities, slash commands, tools, limits, or config change.
- Keep `docs/help.md` accurate: `/help` uses it as the source of truth.

## Testing rules
- Run `python3 -m unittest -v` after code changes.
- Add or update stdlib `unittest` tests for new pure helpers and command behavior.

## Safety rules
- Never read or print `.env` values unless the user explicitly asks.
- Do not add secrets to docs, tests, or examples.
- Keep slash commands local; they should not be added to chat history.
