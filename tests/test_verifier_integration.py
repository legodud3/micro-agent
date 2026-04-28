import unittest

from micro_agent import tool_loop as tl


class TestVerifierIntegration(unittest.TestCase):
    def test_reject_appends_verifier_message_and_retries(self):
        cfg = {"model": "m", "temperature": 0.1, "max_tokens": 10}
        history = [{"role": "user", "content": "hi"}]

        # Fake OpenRouter: first draft (no tool calls), then a revised final.
        call_count = {"n": 0}

        def fake_call_openrouter(payload, api_key, base_url):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {
                    "choices": [
                        {
                            "message": {"content": "draft"}
                        }
                    ]
                }
            return {
                "choices": [
                    {
                        "message": {"content": "revised"}
                    }
                ]
            }

        real_call_openrouter = tl.call_openrouter
        real_run_verifier = tl.run_verifier
        try:
            tl.call_openrouter = fake_call_openrouter

            qc_calls = {"n": 0}

            def fake_run_verifier(*, verifier_cfg, verifier_system_prompt, main_system_prompt, history, api_key, base_url, dry_run, trace=False):
                qc_calls["n"] += 1
                if qc_calls["n"] == 1:
                    return {"status": "reject", "issues": ["issue1"]}
                return {"status": "approve", "issues": []}

            tl.run_verifier = fake_run_verifier

            out = tl.run_assistant_with_tools(
                cfg=cfg,
                system_prompt="MAIN_PROMPT",
                verifier_cfg={"model": "vm", "temperature": 0.2, "max_tokens": 50},
                verifier_system_prompt="VERIFIER_PROMPT",
                history=history,
                api_key="key",
                base_url="https://example.com",
                dry_run=False,
                trace=False,
                max_tool_iterations=2,
            )
        finally:
            tl.call_openrouter = real_call_openrouter
            tl.run_verifier = real_run_verifier

        self.assertEqual(out, "revised")
        self.assertGreaterEqual(call_count["n"], 2)

        # Expect a verifier message to be inserted.
        verifier_msgs = [m for m in history if m.get("role") == "verifier"]
        self.assertEqual(len(verifier_msgs), 1)
        self.assertIn("issue1", verifier_msgs[0]["content"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
