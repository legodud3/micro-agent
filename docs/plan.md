# Simplest Agent Harness Plan (OpenRouter, Python, no tools)
1. Keep folders minimal: all code + files in project root (no `src/`, no `prompts/`).
2. Create `agent_harness.py` (terminal chat loop + OpenRouter call).
3. Create `config.json` for model id + simple settings (temperature, max_tokens).
4. Create `.env.example` with `OPENROUTER_API_KEY=`; real `.env` stays local.
5. Create `system_prompt.txt` with exactly 5 lines.
6. Use TDD: write tests first with Python stdlib `unittest` (no extra deps).
7. In `tests.md`, list test cases and the expected behavior (payload, parsing, state).
8. Implement `load_config()` to read `config.json` + env var for the API key.
9. Implement `load_system_prompt()` to read the 5-line file as a single string.
10. Implement `build_messages()` to combine system prompt + prior turns + newest user message.
11. Persist conversation history **across turns** in memory (not just for one turn).
12. Implement `build_request_payload()` to match OpenRouter Chat Completions format.
13. Implement `parse_assistant_text()` to safely extract the assistant reply from JSON.
14. Implement a simple `available_tools()`/tool calls? (NONE for now) → omit tool logic entirely.
15. In the terminal loop, support `exit`/`quit` to stop cleanly.
16. Implement `call_openrouter()` using stdlib `urllib.request` and `Authorization: Bearer ...`.
17. Add only minimal error handling: missing key/config, non-200 HTTP, bad response shape.
18. Add a `--dry-run` option (tests can avoid network) or isolate network call behind a function.
19. Ensure tests cover: system prompt always first, history grows each turn, parsing works.
20. Run tests with `python -m unittest -v`.
21. Implement code until tests are green (keep code small, modular, and readable).
22. Add ELI5-style comments above each modular function block.
23. Skip lint/format/libraries for now.
24. Run harness with `python agent_harness.py`.
25. Manually test one-turn and multi-turn conversation to confirm continuity.
26. Confirm payload includes: model, messages, temperature, max_tokens.
27. Confirm system prompt is included every request as message role `system`.
28. Keep only the required files: `agent_harness.py`, `config.json`, `.env.example`, `system_prompt.txt`.
29. Document setup in `README.md` (copy `.env.example` → `.env`, set model in `config.json`).
30. Deliver working harness + `tests.md` + test code (if you want, in `test_agent_harness.py`).