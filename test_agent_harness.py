import json
import os
import tempfile
import unittest

import agent_harness as ah


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
        history = []
        messages = ah.build_messages(system, history, "hi")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")

    def test_build_messages_appends_user_and_history_across_turns(self):
        system = "SYS"
        history = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
        ]
        messages = ah.build_messages(system, history, "u2")

        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[-1]["content"], "u2")

    def test_build_request_payload_shape(self):
        cfg = {"model": "m", "temperature": 0.1, "max_tokens": 10}
        payload = ah.build_request_payload(cfg, [{"role": "system", "content": "s"}])

        self.assertEqual(payload["model"], "m")
        self.assertIn("messages", payload)
        self.assertIn("temperature", payload)
        self.assertIn("max_tokens", payload)

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
