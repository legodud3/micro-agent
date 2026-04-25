# Minimal Agent Harness Plan
1. Keep the repo small and stdlib-only.
2. Keep `agent_harness.py` focused on the terminal loop.
3. Put local loading in `config_loader.py`.
4. Put OpenRouter HTTP helpers in `openrouter_client.py`.
5. Put the Tavily tool in `tools/web_search.py`.
6. Put the model -> tool -> model loop in `tool_loop.py`.
7. Load `.env`, `config.json`, and `system_prompt.txt` before chat starts.
8. Keep conversation history in memory across turns.
9. Send the system prompt plus history on each model call.
10. Advertise tools to the model with OpenAI-style tool definitions.
11. Let the model decide tool use with `tool_choice: auto`.
12. Execute only known tools.
13. Append tool results back as `role: "tool"` messages.
14. Stop when the model returns a normal assistant message.
15. Cap tool iterations with `--max-tool-iterations`.
16. Add `--trace` to show observable loop steps.
17. Add `--dry-run` so the terminal flow can run without network calls.
18. Test pure helpers with stdlib `unittest`.
19. Run tests with `python3 -m unittest -v`.
20. Keep slash commands local; do not add them to chat history.
21. Use `docs/help.md` as the `/help` source of truth.
22. Follow `docs/AGENTS.md` when changing the codebase.
