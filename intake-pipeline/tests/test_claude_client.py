import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import claude  # noqa: E402


class ClientFallbacks(unittest.TestCase):
    def setUp(self):
        self.saved = claude._post
        self.calls = []

    def tearDown(self):
        claude._post = self.saved

    def test_forced_tool_answer(self):
        claude._post = lambda body, t: (self.calls.append(body), {"content": [{"type": "tool_use", "name": "x", "input": {"ok": 1}}]})[1]
        self.assertEqual(claude.call_tool("m", "s", [], "x", {"type": "object"}), {"ok": 1})
        self.assertEqual(self.calls[0]["tool_choice"], {"type": "tool", "name": "x"})

    def test_model_that_rejects_forced_tools_retries_with_auto(self):
        def post(body, t):
            self.calls.append({"tool_choice": dict(body["tool_choice"])})   # copy: the client reuses the body
            if body["tool_choice"]["type"] == "tool":
                raise claude.ReaderUnavailable('Claude API error 400: tool_choice: type "tool" and "any" are not supported for this model.')
            return {"content": [{"type": "tool_use", "name": "x", "input": {"pages": []}}]}
        claude._post = post
        self.assertEqual(claude.call_tool("m", "s", [], "x", {"type": "object"}), {"pages": []})
        self.assertEqual([c["tool_choice"]["type"] for c in self.calls], ["tool", "auto"])

    def test_json_in_text_is_accepted_as_last_resort(self):
        def post(body, t):
            if body["tool_choice"]["type"] == "tool":
                raise claude.ReaderUnavailable("tool_choice not supported")
            return {"content": [{"type": "text", "text": 'Here you go: {"results": [{"id": "f1", "present": true}]} done'}]}
        claude._post = post
        self.assertEqual(claude.call_tool("m", "s", [], "x", {})["results"][0]["present"], True)

    def test_other_errors_are_not_retried(self):
        def post(body, t):
            self.calls.append(body)
            raise claude.ReaderUnavailable("Claude API error 401: invalid key")
        claude._post = post
        with self.assertRaises(claude.ReaderUnavailable):
            claude.call_tool("m", "s", [], "x", {})
        self.assertEqual(len(self.calls), 1)

    def test_no_structure_raises(self):
        claude._post = lambda body, t: {"content": [{"type": "text", "text": "sorry"}]}
        with self.assertRaises(claude.ReaderUnavailable):
            claude.call_tool("m", "s", [], "x", {})


if __name__ == "__main__":
    unittest.main()
