# Minimal OpenRouter Chat Agent (Python, no tools)

## Files
- `agent_harness.py` — terminal chat loop + OpenRouter call (with `web_search` tool)
- `config.json` — model selection + generation params
- `system_prompt.txt` — the system prompt
- `.env.example` — copy to `.env` and set API keys
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

Tool safety:
- `--max-tool-iterations N` (default 5)

## Tests
- `python3 -m unittest -v`
