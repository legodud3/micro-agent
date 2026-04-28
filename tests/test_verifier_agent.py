import unittest

from micro_agent.agents import verifier_agent as va


class TestVerifierAgentParsing(unittest.TestCase):
    def test_parse_qc_json_approve(self):
        qc = va.parse_qc_json('{"status":"approve","issues":[]}')
        self.assertEqual(qc["status"], "approve")
        self.assertEqual(qc["issues"], [])

    def test_parse_qc_json_with_markdown_blocks(self):
        markdown_json = '```json\n{"status":"approve","issues":[]}\n```'
        qc = va.parse_qc_json(markdown_json)
        self.assertEqual(qc["status"], "approve")

    def test_parse_qc_json_with_plain_code_blocks(self):
        code_json = '```\n{"status":"approve","issues":[]}\n```'
        qc = va.parse_qc_json(code_json)
        self.assertEqual(qc["status"], "approve")

    def test_parse_qc_json_reject_with_list_issues(self):
        qc = va.parse_qc_json('{"status":"reject","issues":["i1","i2"]}')
        self.assertEqual(qc["issues"], ["i1", "i2"])

    def test_parse_qc_json_reject_requires_non_empty_issues(self):
        with self.assertRaises(ValueError):
            va.parse_qc_json('{"status":"reject","issues":[]}')

    def test_parse_qc_json_approve_requires_empty_issues(self):
        with self.assertRaises(ValueError):
            va.parse_qc_json('{"status":"approve","issues":["should be empty"]}')

    def test_parse_qc_json_invalid_status(self):
        with self.assertRaises(ValueError):
            va.parse_qc_json('{"status":"maybe","issues":[]}')


if __name__ == "__main__":
    unittest.main(verbosity=2)
