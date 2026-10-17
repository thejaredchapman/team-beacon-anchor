import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import board_server  # noqa: E402


class LocalBoard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seen = []
        board_server.Handler.caller = lambda system, turns: cls.seen.append(turns) or "Sample-04 is Bad. Next: Clinical review."
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), board_server.Handler)
        cls.port = cls.srv.server_port
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        board_server.Handler.caller = None

    def get(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def post(self, body, origin=None, ctype="application/json"):
        headers = {"Content-Type": ctype, "Origin": origin or f"http://127.0.0.1:{self.port}"}
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/ask", data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_serves_the_board(self):
        code, body = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn(b"Ask the board", body)

    def test_never_serves_secrets_or_working_files(self):
        for path in ("/intake-pipeline/.env", "/.env", "/../CLAUDE.md", "/%2e%2e/CLAUDE.md", "/intake-pipeline/work/pipeline.db",
                     "/intake-pipeline/outbox/x.eml", "/intake-pipeline/pipeline/__pycache__/x.pyc", "/nope.html",
                     "/intake-pipeline/WORK/x.pdf", "/intake-pipeline/Work/x.pdf", "/intake-pipeline/SAMPLES/sample-complete.pdf",
                     "/intake-pipeline/.ENV", "/INTAKE-PIPELINE/.env", "/intake-pipeline/samples/sample-complete.pdf", "/a%00.html"):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_serves_linked_files_in_any_case(self):
        self.assertEqual(self.get("/triage-dashboard/faxes/Sample-01-original-fax.pdf")[0], 200)
        self.assertEqual(self.get("/intake-pipeline/README.md")[0], 200)

    def test_foreign_host_is_refused(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/", headers={"Host": "evil.example"})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 403)

    def test_malformed_requests_do_not_crash(self):
        self.assertEqual(self.post(["not", "a", "dict"])[0], 400)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/ask", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.port}", "Content-Length": "abc"})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 400)

    def test_status_never_includes_the_key(self):
        code, body = self.get("/api/ask/status")
        self.assertEqual(code, 200)
        self.assertEqual(set(json.loads(body)), {"available", "model"})

    def test_ask_passes_turns_to_claude(self):
        code, out = self.post({"messages": [{"role": "user", "content": "What does the grade mean?"}]})
        self.assertEqual(code, 200)
        self.assertIn("Next:", out["text"])
        self.assertEqual(self.seen[-1][-1]["content"], "What does the grade mean?")

    def test_other_websites_are_refused(self):
        self.assertEqual(self.post({"messages": [{"role": "user", "content": "hi"}]}, origin="https://evil.example")[0], 403)
        self.assertEqual(self.post({"messages": [{"role": "user", "content": "hi"}]}, ctype="text/plain")[0], 403)
        self.assertEqual(self.post({"messages": [{"role": "user", "content": "hi"}]}, ctype="application/jsonx")[0], 403)
        self.assertEqual(self.post({"messages": [{"role": "user", "content": "hi"}]}, origin="null")[0], 403)

    def test_bad_turns_are_rejected(self):
        self.assertEqual(self.post({"messages": [{"role": "assistant", "content": "only me"}]})[0], 400)
        self.assertEqual(self.post({"messages": "nope"})[0], 400)

    def test_no_key_means_built_in_answers(self):
        def unavailable(system, turns):
            raise board_server.claude.ReaderUnavailable("no key")
        self.assertEqual(board_server.ask([{"role": "user", "content": "hi"}], unavailable), (503, {"error": "unavailable"}))


if __name__ == "__main__":
    unittest.main()
