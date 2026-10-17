"""Local Anchor Board: serves ANCHOR.html on this computer and connects its "Ask the board" helper to Claude.

Run:  python3 board_server.py      then open http://127.0.0.1:8790  (another port: BOARD_PORT=8791 python3 board_server.py)
Binds to 127.0.0.1 only. The API key is read on the server (env or intake-pipeline/.env) and never sent to the browser.
Without a key the helper uses its built-in answers.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "intake-pipeline"))
from pipeline import claude  # noqa: E402

HOST, PORT = "127.0.0.1", int(os.environ.get("BOARD_PORT", "8790"))
MAX_BODY = 64 * 1024
TYPES = {".html": "text/html; charset=utf-8", ".md": "text/plain; charset=utf-8", ".py": "text/plain; charset=utf-8",
         ".json": "application/json", ".pdf": "application/pdf", ".css": "text/css", ".js": "text/javascript"}
SYSTEM = ("You are \"Ask the board\", the helper on IHH's Anchor Board. Follow the instructions in the user's message. "
          "Answer only from the guide and board data you are given. Never give medical, clinical, legal or eligibility advice.")


def allowlist():
    """Only the page, its mock fax PDFs and the files its "Everything we made" tab links to. Keys are lower-case,
    because macOS file names ignore case (WORK/ and work/ are the same folder)."""
    import build_anchor_page as page
    names = ["ANCHOR.html"] + [p for _, items in page.FILES for p, _ in items]
    names += [str(f.relative_to(HERE)) for f in (HERE / "triage-dashboard" / "faxes").glob("*.pdf")]
    out = {}
    for n in names:
        f = HERE / n
        if f.is_file() and not f.is_symlink() and f.suffix.lower() in TYPES:
            out[n.lower()] = f
    return out


ALLOWED = allowlist()


def safe_path(url_path):
    """Map a URL path to an allowlisted file, or None."""
    rel = unquote(url_path).lstrip("/") or "ANCHOR.html"
    if "\x00" in rel:
        return None
    return ALLOWED.get(rel.lower())


def clean_turns(messages):
    """Keep at most 7 plain-text turns that alternate and end on the user."""
    if not isinstance(messages, list):
        return None
    out = [{"role": m["role"], "content": m["content"][:12000]} for m in messages[-7:]
           if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out if out and out[-1]["role"] == "user" else None


def ask(messages, caller=None):
    """Returns (status, body). caller(system, turns) -> text, for tests."""
    turns = clean_turns(messages)
    if not turns:
        return 400, {"error": "bad_request"}
    call = caller or (lambda system, t: claude.call_text(claude.CHAT_MODEL, system, t, max_tokens=1000))
    try:
        return 200, {"text": call(SYSTEM, turns)}
    except claude.ReaderUnavailable:
        return 503, {"error": "unavailable"}
    except Exception:  # never crash the request or print what was asked
        return 502, {"error": "upstream_error"}


class Handler(BaseHTTPRequestHandler):
    caller = None

    def log_message(self, *a):  # keep questions out of the terminal
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _right_host(self):
        # Blocks DNS rebinding: a foreign site that points its name at 127.0.0.1 still sends its own Host
        return self.headers.get("Host") in (f"{HOST}:{self.server.server_port}", f"localhost:{self.server.server_port}")

    def _same_origin(self):
        # Another website open in the browser must not be able to use this server's key
        origin = self.headers.get("Origin")
        return origin in (f"http://{HOST}:{self.server.server_port}", f"http://localhost:{self.server.server_port}")

    def do_GET(self):
        if not self._right_host():
            return self._send(403, b"Forbidden", "text/plain")
        path = urlparse(self.path).path
        if path == "/api/ask/status":
            return self._send(200, {"available": claude.available() or Handler.caller is not None, "model": claude.CHAT_MODEL})
        p = safe_path(path)
        if not p:
            return self._send(404, b"Not found", "text/plain")
        self._send(200, p.read_bytes(), TYPES[p.suffix.lower()])

    def do_POST(self):
        if urlparse(self.path).path != "/api/ask":
            return self._send(404, {"error": "not_found"})
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if not self._right_host() or not self._same_origin() or ctype != "application/json":
            return self._send(403, {"error": "forbidden"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._send(400, {"error": "bad_request"})
        if n <= 0 or n > MAX_BODY:
            return self._send(413, {"error": "too_large"})
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, RecursionError):
            return self._send(400, {"error": "bad_request"})
        if not isinstance(body, dict):
            return self._send(400, {"error": "bad_request"})
        code, out = ask(body.get("messages"), Handler.caller)
        self._send(code, out)


def main():
    print(f"Anchor Board: http://{HOST}:{PORT}  (Ask the board: {'Claude ' + claude.CHAT_MODEL if claude.available() else 'built-in answers; set ANTHROPIC_API_KEY for Claude'})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
