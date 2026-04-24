import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

import agent_harness as ah
import tool_loop as tl


class TestAgentHarness(unittest.TestCase):
    def test_load_config_requires_key(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_path = os.path.join(td, "config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

            with self.assertRaises(ValueError):
                ah.load_config(cfg_path)

    def test_load_system_prompt_reads_file(self):
        with tempfile.TemporaryDirectory() as td:
            prompt_path = os.path.join(td, "system_prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("l1\nl2\nl3\nl4\nl5\n")

            text = ah.load_system_prompt(prompt_path)
            self.assertIn("l1", text)
            self.assertIn("l5", text)

    def test_build_messages_includes_system_first(self):
        system = "SYS"
        history = [{"role": "user", "content": "hi"}]
        messages = ah.build_messages(system, history)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")

    def test_build_messages_prepends_system_to_history(self):
        system = "SYS"
        history = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]
        messages = ah.build_messages(system, history)

        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[-1]["content"], "u2")

    def test_build_request_payload_shape(self):
        cfg = {"model": "m", "temperature": 0.1, "max_tokens": 10}
        payload = ah.build_request_payload(cfg, [{"role": "system", "content": "s"}])

        self.assertEqual(payload["model"], "m")
        self.assertIn("messages", payload)
        self.assertIn("temperature", payload)
        self.assertIn("max_tokens", payload)

    def test_build_request_payload_with_tools_sets_tools_and_tool_choice(self):
        cfg = {"model": "m", "temperature": 0.1, "max_tokens": 10}
        tools = [
            {
                "type": "function",
                "function": {"name": "web_search"},
            }
        ]
        payload = ah.build_request_payload(
            cfg,
            [{"role": "system", "content": "s"}],
            tools=tools,
        )
        self.assertEqual(payload["tools"], tools)
        self.assertEqual(payload["tool_choice"], "auto")

    def test_parse_tool_calls_empty_when_missing(self):
        resp = {"choices": [{"message": {"content": "hi"}}]}
        self.assertEqual(ah.parse_tool_calls(resp), [])

    def test_parse_tool_call_arguments_parses_json_string(self):
        tool_call = {
            "function": {"arguments": '{"query":"cats","max_results":3}'}
        }
        args = ah.parse_tool_call_arguments(tool_call)
        self.assertEqual(args["query"], "cats")
        self.assertEqual(args["max_results"], 3)

    def test_tavily_web_search_dry_run(self):
        res = ah.tavily_web_search("cats", max_results=10, dry_run=True)
        self.assertEqual(res["query"], "cats")
        self.assertEqual(res["results"], [])

    def test_run_assistant_with_tools_dry_run_trace(self):
        cfg = {"model": "m", "temperature": 0.1, "max_tokens": 10}
        history = [{"role": "user", "content": "hi"}]
        out = StringIO()

        with redirect_stdout(out):
            text = ah.run_assistant_with_tools(
                cfg=cfg,
                system_prompt="SYS",
                history=history,
                api_key=None,
                base_url="https://example.com",
                dry_run=True,
                trace=True,
            )

        self.assertIn("dry-run", text)
        self.assertIn("[trace] iteration 1: calling model", out.getvalue())

    def test_run_assistant_with_tools_stops_at_iteration_limit(self):
        cfg = {"model": "m", "temperature": 0.1, "max_tokens": 10}
        history = [{"role": "user", "content": "search forever"}]

        def fake_call_openrouter(payload, api_key, base_url):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "web_search",
                                        "arguments": '{"query":"cats","max_results":1}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }

        real_call_openrouter = tl.call_openrouter
        real_tavily_web_search = tl.tavily_web_search
        try:
            tl.call_openrouter = fake_call_openrouter
            tl.tavily_web_search = lambda query, max_results=5, dry_run=False: {
                "query": query,
                "results": [],
            }

            text = ah.run_assistant_with_tools(
                cfg=cfg,
                system_prompt="SYS",
                history=history,
                api_key="key",
                base_url="https://example.com",
                dry_run=False,
                max_tool_iterations=2,
            )
        finally:
            tl.call_openrouter = real_call_openrouter
            tl.tavily_web_search = real_tavily_web_search

        self.assertIn("iteration limit", text)
        self.assertEqual(history[-1]["role"], "assistant")

    def test_run_assistant_with_tools_returns_openrouter_error(self):
        cfg = {"model": "m", "temperature": 0.1, "max_tokens": 10}
        history = [{"role": "user", "content": "hi"}]

        def fake_call_openrouter(payload, api_key, base_url):
            return {"error": {"message": "Provider returned error", "code": 502}}

        real_call_openrouter = tl.call_openrouter
        try:
            tl.call_openrouter = fake_call_openrouter
            text = ah.run_assistant_with_tools(
                cfg=cfg,
                system_prompt="SYS",
                history=history,
                api_key="key",
                base_url="https://example.com",
                dry_run=False,
            )
        finally:
            tl.call_openrouter = real_call_openrouter

        self.assertIn("OpenRouter returned an error", text)
        self.assertIn("502", text)

    def test_parse_assistant_text_happy_path(self):
        resp = {
            "choices": [
                {"message": {"content": "hello there"}}
            ]
        }
        self.assertEqual(ah.parse_assistant_text(resp), "hello there")

    def test_parse_assistant_text_handles_missing_fields(self):
        with self.assertRaises(ValueError):
            ah.parse_assistant_text({"choices": []})

    def test_validate_chat_response_handles_openrouter_error(self):
        with self.assertRaisesRegex(ValueError, "OpenRouter error"):
            ah.validate_chat_response({"error": {"message": "rate limited"}})

    def test_validate_chat_response_handles_empty_choices(self):
        with self.assertRaisesRegex(ValueError, "no choices"):
            ah.validate_chat_response({"choices": []})

    def test_should_exit(self):
        self.assertTrue(ah.should_exit("exit"))
        self.assertTrue(ah.should_exit("  Quit  "))
        self.assertFalse(ah.should_exit("hello"))

    def test_parse_env_file_sets_env(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = os.path.join(td, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# comment\nOPENROUTER_API_KEY=abc123\n")

            # Avoid polluting real env; set a known different value then change.
            os.environ.pop("OPENROUTER_API_KEY", None)

            ah.parse_env_file(env_path)
            self.assertEqual(os.environ.get("OPENROUTER_API_KEY"), "abc123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
