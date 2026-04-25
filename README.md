# micro-agent v0.2

## Files
- `agent_harness.py` — terminal chat loop
- `config_loader.py` — `.env`, config, and system prompt loading
- `openrouter_client.py` — OpenRouter request/response helpers
- `tool_loop.py` — model -> tool -> model loop
- `tools/web_search.py` — Tavily `web_search` tool
- `config.json` — model selection + generation params
- `system_prompt.txt` — the system prompt
- `.env.example` — copy to `.env` and set API keys
- `docs/help.md` — source of truth for `/help`
- `docs/learnings.md` — personal learning notes by coding session
- `docs/AGENTS.md` — instructions for coding assistants changing this repo
- `test_agent_harness.py` — stdlib `unittest` tests

## Run
1. Copy env example:
   - `cp .env.example .env`
2. Fill in:
   - `OPENROUTER_API_KEY`
   - `TAVILY_API_KEY`
3. (Optional) edit `config.json` to change the model.
4. Start:
   - `python3 agent_harness.py`
5. To avoid network calls (useful for testing):
   - `python3 agent_harness.py --dry-run`
6. To see model/tool iterations:
   - `python3 agent_harness.py --trace`
   - safe test version: `python3 agent_harness.py --dry-run --trace`

Tool safety:
- `--max-tool-iterations N` (default 5)

## Slash commands
- `/` — list slash commands
- `/tool` — list tools the model can call
- `/model` — list 10–15 live OpenRouter text/coding/agentic models
- `/model set <id>` — set active model and persist to config.json
- `/help` — print `docs/help.md`
- `/exit` or `/quit` — quit the chat

## Tests
- `python3 -m unittest -v`
