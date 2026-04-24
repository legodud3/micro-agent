# TDD test plan (stdlib `unittest`, OpenRouter + Tavily)

## Assumptions
- Terminal loop lives in `agent_harness.py`.
- Loading, OpenRouter, tools, and tool loop live in small modules.
- Tests run without hitting the network (we’ll use `--dry-run` or isolate network calls).

## Test cases to write

1. **test_load_config_requires_key**
   - Given: `OPENROUTER_API_KEY` missing
   - Expect: `load_config()` raises a clear exception.

2. **test_load_system_prompt_reads_file**
   - Given: `system_prompt.txt` has 5 lines
   - Expect: `load_system_prompt()` returns a string containing all lines.

3. **test_build_messages_includes_system_first**
   - Given: empty conversation history
   - Expect: first message is `{role: "system", content: ...}`.

4. **test_build_messages_prepends_system_to_history**
   - Given: history already has prior turns
   - When: building messages
   - Expect: system prompt is first and history is preserved.

5. **test_build_request_payload_matches_openrouter_shape**
   - Expect payload has at least:
     - `model`
     - `messages`
     - `temperature`
     - `max_tokens`

6. **test_parse_assistant_text_happy_path**
   - Given: a realistic OpenRouter JSON response
   - Expect: function returns the assistant text (string).

7. **test_parse_assistant_text_handles_missing_fields**
   - Given: malformed/missing fields
   - Expect: raises a clear exception (or returns a helpful error).

8. **test_terminal_exit_commands**
   - Given: user input is `exit` or `quit`
   - Expect: loop stops (can be tested by factoring loop decision into a small function).

9. **test_build_request_payload_with_tools_sets_tools_and_tool_choice**
   - Given: a tool definition
   - Expect: payload includes `tools` and `tool_choice: auto`.

10. **test_parse_tool_calls_empty_when_missing**
   - Given: a normal assistant response
   - Expect: no tool calls.

11. **test_parse_tool_call_arguments_parses_json_string**
   - Given: tool-call arguments as JSON text
   - Expect: parsed dict.

12. **test_tavily_web_search_dry_run**
   - Given: dry-run search
   - Expect: no network call and empty results.

13. **test_run_assistant_with_tools_dry_run_trace**
   - Given: dry-run tool loop with trace on
   - Expect: trace lines print and a dry-run answer returns.

14. **test_run_assistant_with_tools_stops_at_iteration_limit**
   - Given: model keeps requesting tools
   - Expect: loop stops at `max_tool_iterations`.

## Suggested test layout
- Create `test_agent_harness.py`
- Use small pure-function tests (payload building + parsing) that don’t require network.
- Keep network call tests minimal (ideally mocked).
