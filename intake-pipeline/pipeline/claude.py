"""Minimal Claude API client (standard library only) that forces a JSON answer through a tool.

Reads ANTHROPIC_API_KEY from the environment. Never logs the key or page content.
"""
import base64
import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def _load_env_file():
    """Read ANTHROPIC_API_KEY (and model overrides) from intake-pipeline/.env if not already set. The file is git-ignored."""
    if os.environ.get("ANTHROPIC_API_KEY") or not os.path.exists(_ENV_FILE):
        return
    for line in open(_ENV_FILE, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip().replace("export ", ""), v.strip().strip('"').strip("'")
        if k in ("ANTHROPIC_API_KEY", "INTAKE_PAGE_MODEL", "INTAKE_FACT_MODEL", "INTAKE_CHAT_MODEL") and v:
            os.environ.setdefault(k, v)


_load_env_file()
PAGE_MODEL = os.environ.get("INTAKE_PAGE_MODEL", "claude-sonnet-5-5")    # page map, quote checks
FACT_MODEL = os.environ.get("INTAKE_FACT_MODEL", "claude-opus-5-5")      # fact extraction from messy faxes
CHAT_MODEL = os.environ.get("INTAKE_CHAT_MODEL", "claude-haiku-5-5")     # the "Ask Anchor" helper


class ReaderUnavailable(Exception):
    """No API key, or the API could not be reached."""


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def image_block(path):
    data = base64.standard_b64encode(open(path, "rb").read()).decode("ascii")
    media = "image/png" if str(path).lower().endswith(".png") else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def text_block(text):
    return {"type": "text", "text": text}


def _post(body, timeout):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ReaderUnavailable("Set ANTHROPIC_API_KEY to turn this on.")
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ReaderUnavailable(f"Claude API error {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except urllib.error.URLError as e:
        raise ReaderUnavailable(f"Could not reach the Claude API: {e.reason}")


def call_text(model, system, messages, max_tokens=600, timeout=60):
    """Plain chat call. messages: [{"role": "user"|"assistant", "content": str}], ending with a user turn."""
    out = _post({"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}, timeout)
    return "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text").strip()


def _extract_json(text):
    """Pull the first JSON object out of a text answer (used when a model can't be forced to call the tool)."""
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None


def call_tool(model, system, blocks, tool_name, schema, max_tokens=8000, timeout=300):
    """Ask for a structured answer. Forces the tool when the model allows it; otherwise lets the model choose and
    falls back to JSON in the text. Raises ReaderUnavailable if no valid structure comes back."""
    tools = [{"name": tool_name, "description": "Return the answer in this exact structure.", "input_schema": schema}]
    body = {"model": model, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": blocks}], "tools": tools,
            "tool_choice": {"type": "tool", "name": tool_name}}
    try:
        out = _post(body, timeout)
    except ReaderUnavailable as e:
        if "tool_choice" not in str(e):
            raise
        # Some models don't allow forcing a tool. Ask nicely instead, and accept JSON in text as a fallback.
        body["tool_choice"] = {"type": "auto"}
        body["messages"] = [{"role": "user", "content": blocks + [{"type": "text", "text":
                            f"Answer by calling the {tool_name} tool. If you cannot, reply with only the JSON object for it."}]}]
        out = _post(body, timeout)
    for block in out.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == tool_name:
            return block["input"]
    text = "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")
    data = _extract_json(text)
    if isinstance(data, dict):
        return data
    raise ReaderUnavailable("Claude did not return a structured answer.")
