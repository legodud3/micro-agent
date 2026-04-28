# micro-agent v0.2

## Files
- `agent_harness.py` — thin CLI wrapper (implementation in `micro_agent/`)
- `micro_agent/` — package with the agent implementation
  - `micro_agent/agent_harness.py` — terminal chat loop + local slash commands
  - `micro_agent/config_loader.py` — `.env`, config, and system prompt loading
  - `micro_agent/openrouter_client.py` — OpenRouter request/response helpers
  - `micro_agent/tool_loop.py` — main model -> tool -> model loop (+ verifier QC)
  - `micro_agent/agents/verifier_agent.py` — verifier/QC sub-agent
  - `micro_agent/agents/verifier_system_prompt.md` — verifier prompt text
  - `micro_agent/tools/web_search.py` — Tavily `web_search` tool
- `micro_agent/config.json` — config for `micro_agent` and `verifier`
- `micro_agent/system_prompt.md` — main agent system prompt
- `.env.example` — copy to `.env` and set API keys
- `docs/help.md` — source of truth for `/help`
- `docs/learnings.md` — personal learning notes by coding session
- `AGENTS.md` — instructions for coding assistants changing this repo
- `test_agent_harness.py`, `test_verifier_agent.py`, `test_verifier_integration.py` — stdlib `unittest` tests

## Run
1. Copy env example:
   - `cp .env.example .env`
2. Fill in:
   - `OPENROUTER_API_KEY`
   - `TAVILY_API_KEY`
3. (Optional) edit `config.json` to change the main model and/or verifier model.
4. Start:
   - `python3 agent_harness.py`
5. To avoid network calls (useful for testing):
   - `python3 agent_harness.py --dry-run`
6. To see model/tool iterations:
   - `python3 agent_harness.py --trace`
   - safe test version: `python3 agent_harness.py --dry-run --trace`

Tool safety (also limits verifier retries):
- `--max-tool-iterations N` (default 50)

## Slash commands
- `/` — list slash commands
- `/tool` — list tools the model can call
- `/model` — list 10–15 live OpenRouter text/coding/agentic models
- `/model set <id>` — set active model and persist to config.json
- `/help` — print `docs/help.md`
- `/exit` or `/quit` — quit the chat

## Tests
- `python3 -m unittest -v`
