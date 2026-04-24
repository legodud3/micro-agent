# Minimal OpenRouter Chat Agent (Python, no tools)

## Files
- `agent_harness.py` — terminal chat loop + OpenRouter call
- `config.json` — model selection + generation params
- `system_prompt.txt` — the system prompt (5 lines)
- `.env` — openrouter api key
- `test_agent_harness.py` — stdlib `unittest` tests

## Run
1. (Optional) edit `config.json` to change the model.
2. Start:
   - `python3 agent_harness.py`
3. To avoid network calls (useful for testing the UI):
   - `python3 agent_harness.py --dry-run`

## Tests
- `python3 -m unittest -v`
