# TDD test plan (stdlib `unittest`, OpenRouter, no tools)

## Assumptions
- Code lives in `agent_harness.py`.
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

4. **test_build_messages_appends_user_and_history_across_turns**
   - Given: history already has one prior user+assistant turn
   - When: building messages for a new user input
   - Expect: newest user message is appended and prior turns are preserved.

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

## Suggested test layout
- Create `test_agent_harness.py`
- Use small pure-function tests (payload building + parsing) that don’t require network.
- Keep network call tests minimal (ideally mocked).
