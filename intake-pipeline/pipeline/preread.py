"""Pre-read a referral the moment it arrives.

1. Render every page to an image (rotated upright later if the page map says so).
2. Page map: what each page is, whether it's sideways, legible, or from an older stay.
3. Facts: the 27 core facts with page and quote, form and chart kept apart; possible red flags
   using IHH rule IDs only; places where the form and chart disagree.
4. Quote check: a second look at each cited page confirms the quote is really there.
5. Rules and to-do list (plain code in rules.py).

Readers: ClaudeReader (needs ANTHROPIC_API_KEY), DemoReader (built-in answers for the made-up
samples), or none (manual mode). The AI suggests; staff verify and decide.
"""
import hashlib
import json
import subprocess
import threading
from pathlib import Path

from . import claude, notify, rules, store

PAGE_DPI = 110


class Reader:
    name = "none"

    def page_map(self, pages):
        raise NotImplementedError

    def extract(self, pages, page_map):
        raise NotImplementedError

    def check_quotes(self, items):
        raise NotImplementedError


# ---------------- Claude ----------------

SYSTEM = ("You read de-identified hospital referral packets for Illumination Health + Home's recuperative care intake. "
          "Black boxes are redactions for privacy: never report them as missing, never guess what they hid. "
          "Dates are redacted, so anything that needs a date or a number of hours is 'cant_tell'. "
          "If the packet does not say, the answer is 'missing'. Never invent values, page numbers or quotes. "
          "Quotes must be copied exactly from the page, short (under 20 words), and contain no names, dates or numbers that identify anyone.")

PAGE_SCHEMA = {"type": "object", "required": ["pages"], "properties": {"pages": {"type": "array", "items": {
    "type": "object", "required": ["page", "doc_type", "rotation", "legible", "prior_stay"],
    "properties": {"page": {"type": "integer"}, "doc_type": {"type": "string", "enum": list(rules.DOC_TYPES)},
                   "rotation": {"type": "integer", "enum": [0, 90, 180, 270]}, "legible": {"type": "boolean"},
                   "prior_stay": {"type": "boolean"}}}}}}

FACT_SCHEMA = {"type": "object", "required": ["facts", "red_flags", "contradictions"], "properties": {
    "facts": {"type": "array", "items": {"type": "object", "required": ["key", "source", "status"], "properties": {
        "key": {"type": "string", "enum": rules.FACT_KEYS}, "source": {"type": "string", "enum": ["form", "chart"]},
        "status": {"type": "string", "enum": ["found", "unclear", "cant_tell", "redacted", "missing"]},
        "value": {"type": "string"}, "page": {"type": "integer"}, "quote": {"type": "string"}}}},
    "red_flags": {"type": "array", "items": {"type": "object", "required": ["rule_id", "text", "page", "quote"], "properties": {
        "rule_id": {"type": "string"}, "text": {"type": "string"}, "page": {"type": "integer"}, "quote": {"type": "string"}}}},
    "contradictions": {"type": "array", "items": {"type": "object", "required": ["fact_key", "text", "page", "quote", "page2", "quote2"], "properties": {
        "fact_key": {"type": "string", "enum": rules.FACT_KEYS}, "text": {"type": "string"}, "page": {"type": "integer"},
        "quote": {"type": "string"}, "page2": {"type": "integer"}, "quote2": {"type": "string"}}}}}}

CHECK_SCHEMA = {"type": "object", "required": ["results"], "properties": {"results": {"type": "array", "items": {
    "type": "object", "required": ["id", "present"], "properties": {"id": {"type": "string"}, "present": {"type": "boolean"}}}}}}


def _page_blocks(pages):
    blocks = []
    for p in pages:
        if str(p["image_path"]).endswith(".txt"):
            blocks.append(claude.text_block(f"--- Page {p['n']} (text file) ---\n" + Path(p["image_path"]).read_text(errors="replace")[:20000]))
        else:
            blocks += [claude.text_block(f"--- Page {p['n']} ---"), claude.image_block(p["image_path"])]
    return blocks


class ClaudeReader(Reader):
    name = "Claude"

    def page_map(self, pages):
        out = []
        for i in range(0, len(pages), 12):
            chunk = pages[i:i + 12]
            ans = claude.call_tool(claude.PAGE_MODEL, SYSTEM, _page_blocks(chunk) + [claude.text_block(
                "For each page above, say what kind of document it is, how many degrees clockwise it must be rotated to read upright, "
                "whether it is legible, and whether it looks like a record from an earlier hospital stay.")], "page_map", PAGE_SCHEMA, 4000)
            out += ans["pages"]
        return out

    def extract(self, pages, page_map):
        guide = "\n".join(f"- {k}: {rules.FACT_HINTS[k]}" for k in rules.FACT_KEYS)
        excl = "\n".join(f"- {r['id']}: {r['text']}" for r in rules.EXCLUDE_RULES)
        pm = "\n".join(f"p{p['page']}: {p['doc_type']}" for p in page_map)
        prompt = (f"Page map:\n{pm}\n\nFind these 27 facts. Report what the IHH referral form or the health plan's authorization form (CalOptima form/LOA/AUTH) says as source 'form', "
                  f"and what the rest of the chart says as source 'chart'. Give the page and an exact short quote for anything found.\n{guide}\n\n"
                  f"Possible red flags: only if the chart shows one of these IHH exclusion rules may be true. Use these rule IDs exactly; never invent one.\n{excl}\n\n"
                  "Contradictions: where the form and the chart disagree on a fact, give both pages and both quotes.")
        return claude.call_tool(claude.FACT_MODEL, SYSTEM, _page_blocks(pages) + [claude.text_block(prompt)], "packet_facts", FACT_SCHEMA, 12000)

    def check_quotes(self, items):
        by_page = {}
        for it in items:
            by_page.setdefault(it["page_path"], []).append(it)
        results = {}
        for path, its in by_page.items():
            listing = "\n".join(f"{it['id']}: \"{it['quote']}\"" for it in its)
            block = claude.text_block(Path(path).read_text(errors="replace")[:20000]) if path.endswith(".txt") else claude.image_block(path)
            ans = claude.call_tool(claude.PAGE_MODEL, SYSTEM, [block, claude.text_block(
                "For each quote, answer whether this exact text (allowing only for scan noise) appears on this page.\n" + listing)],
                "quote_check", CHECK_SCHEMA, 2000)
            for r in ans["results"]:
                results[r["id"]] = bool(r["present"])
        return results


# ---------------- Demo (made-up samples only) ----------------

class DemoReader(Reader):
    """Built-in answers for the made-up sample files, keyed by file hash. Real files get nothing."""
    name = "Demo answers (made-up samples)"

    def __init__(self, answers_path):
        self.answers = json.loads(Path(answers_path).read_text()) if Path(answers_path).exists() else {}

    def _for_pages(self, pages):
        return [self.answers.get(p["sha256"], {}).get(str(p["doc_page"])) for p in pages]

    def page_map(self, pages):
        out = []
        for p, a in zip(pages, self._for_pages(pages)):
            out.append({"page": p["n"], "doc_type": (a or {}).get("doc_type", "other"), "rotation": 0, "legible": True, "prior_stay": False})
        return out

    def extract(self, pages, page_map):
        res = {"facts": [], "red_flags": [], "contradictions": []}
        for p, a in zip(pages, self._for_pages(pages)):
            for f in (a or {}).get("facts", []):
                res["facts"].append({**f, "page": p["n"]})
            for r in (a or {}).get("red_flags", []):
                res["red_flags"].append({**r, "page": p["n"]})
            for c in (a or {}).get("contradictions", []):
                other = next((q["n"] for q in pages if q["sha256"] == p["sha256"] and q["doc_page"] == c["doc_page2"]), p["n"])
                res["contradictions"].append({**{k: v for k, v in c.items() if k != "doc_page2"}, "page": p["n"], "page2": other})
        return res

    def check_quotes(self, items):
        return {it["id"]: True for it in items}


def choose_reader():
    if claude.available():
        return ClaudeReader()
    demo = store.ROOT / "samples" / "demo-answers.json"
    if demo.exists():
        return DemoReader(demo)
    return None


# ---------------- pipeline ----------------

def render_pages(con, rid, only_doc_ids=None):
    """Render normalized PDFs (and text files) into numbered pages. Returns the new page rows."""
    folder = store.WORK / rid / "pages"
    folder.mkdir(parents=True, exist_ok=True)
    start = (con.execute("SELECT MAX(n) FROM pages WHERE referral_id=?", (rid,)).fetchone()[0] or 0) + 1
    new = []
    docs = con.execute("SELECT * FROM documents WHERE referral_id=? AND status='ready' AND normalized_path IS NOT NULL ORDER BY added_at", (rid,)).fetchall()
    for d in docs:
        if only_doc_ids is not None and d["id"] not in only_doc_ids:
            continue
        if con.execute("SELECT 1 FROM pages WHERE referral_id=? AND document_id=?", (rid, d["id"])).fetchone():
            continue
        src = Path(d["normalized_path"])
        if src.suffix.lower() == ".pdf":
            prefix = folder / d["id"]
            subprocess.run(["pdftoppm", "-r", str(PAGE_DPI), "-jpeg", "-jpegopt", "quality=70", str(src), str(prefix)], check=False, capture_output=True)
            imgs = sorted(folder.glob(f"{d['id']}-*.jpg"))
        elif src.suffix.lower() == ".txt" and d["kind"] != "eml":
            imgs = [src]
        else:
            imgs = []
        for i, img in enumerate(imgs, 1):
            con.execute("INSERT INTO pages (referral_id, n, document_id, image_path, added_by) VALUES (?,?,?,?,?)",
                        (rid, start, d["id"], str(img), d["via"] or "arrival"))
            new.append({"n": start, "image_path": str(img), "sha256": d["sha256"], "doc_page": i, "document_id": d["id"]})
            start += 1
    con.commit()
    return new


def _rotate(path, degrees):
    if degrees and not str(path).endswith(".txt"):
        from PIL import Image
        with Image.open(path) as im:
            im.rotate(-degrees, expand=True).save(path, quality=70)


def _set_run(con, rid, **kw):
    cur = con.execute("SELECT * FROM preread_runs WHERE referral_id=?", (rid,)).fetchone()
    row = dict(cur) if cur else {"referral_id": rid, "status": "", "step": "", "reader": "", "started_at": None, "finished_at": None, "error": None}
    row.update(kw)
    con.execute("INSERT OR REPLACE INTO preread_runs VALUES (:referral_id,:status,:step,:reader,:started_at,:finished_at,:error)", row)
    con.commit()


def run(con, rid, reader=None, only_doc_ids=None):
    """Pre-read a referral (or only newly added documents). Safe to call again."""
    reader = reader if reader is not None else choose_reader()
    with store._lock:
        new_pages = render_pages(con, rid, only_doc_ids)
    if reader is None:
        _set_run(con, rid, status="manual", step="No reader: set ANTHROPIC_API_KEY to turn on the pre-read. Review by hand.", reader="none",
                 started_at=store.iso(store.now(con)), finished_at=store.iso(store.now(con)))
        return {"status": "manual"}
    _set_run(con, rid, status="running", step="Reading pages", reader=reader.name, started_at=store.iso(store.now(con)), error=None)
    try:
        sha = {r["id"]: r["sha256"] for r in con.execute("SELECT id, sha256 FROM documents WHERE referral_id=?", (rid,))}
        pages = new_pages
        if not pages:
            _set_run(con, rid, status="done", step="No new pages", finished_at=store.iso(store.now(con)))
            return {"status": "done", "new_pages": 0}
        _set_run(con, rid, step=f"Mapping {len(pages)} page(s)")
        pmap = reader.page_map(pages)
        with store._lock:
            for pm in pmap:
                p = next((x for x in pages if x["n"] == pm["page"]), None)
                if not p:
                    continue
                _rotate(p["image_path"], pm.get("rotation", 0))
                con.execute("UPDATE pages SET doc_type=?, rotation=?, legible=?, prior_stay=? WHERE referral_id=? AND n=?",
                            (pm["doc_type"], pm.get("rotation", 0), int(bool(pm.get("legible", True))), int(bool(pm.get("prior_stay", False))), rid, p["n"]))
            con.commit()
        _set_run(con, rid, step="Finding the 27 facts")
        found = reader.extract(pages, pmap)
        page_path = {p["n"]: p["image_path"] for p in con.execute("SELECT n, image_path FROM pages WHERE referral_id=?", (rid,))}
        # Quote check: every cited quote gets a second look at its page
        items = []
        for i, f in enumerate(found.get("facts", [])):
            if f.get("status") == "found" and f.get("quote") and f.get("page") in page_path:
                items.append({"id": f"f{i}", "quote": f["quote"], "page_path": page_path[f["page"]]})
        for i, r in enumerate(found.get("red_flags", [])):
            if r.get("page") in page_path:
                items.append({"id": f"r{i}", "quote": r["quote"], "page_path": page_path[r["page"]]})
        for i, c in enumerate(found.get("contradictions", [])):
            if c.get("page") in page_path:
                items.append({"id": f"c{i}a", "quote": c["quote"], "page_path": page_path[c["page"]]})
            if c.get("page2") in page_path:
                items.append({"id": f"c{i}b", "quote": c["quote2"], "page_path": page_path[c["page2"]]})
        _set_run(con, rid, step=f"Double-checking {len(items)} quote(s)")
        ok = reader.check_quotes(items) if items else {}
        now = store.iso(store.now(con))
        resolved = []
        with store._lock:
            for i, f in enumerate(found.get("facts", [])):
                checked = int(ok.get(f"f{i}", False))
                status = f["status"]
                if status == "found" and not checked:
                    status = "unclear"          # a quote we couldn't confirm is not counted as found
                cur = con.execute("SELECT * FROM facts WHERE referral_id=? AND key=? AND source=?", (rid, f["key"], f["source"])).fetchone()
                if cur and rules.STATUS_ORDER.get(cur["status"], 9) <= rules.STATUS_ORDER.get(status, 9):
                    continue                    # keep what we already have unless the new read is better
                con.execute("INSERT OR REPLACE INTO facts (id, referral_id, key, source, status, value, page, quote, quote_checked, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (cur["id"] if cur else store.new_id("fact"), rid, f["key"], f["source"], status, f.get("value"), f.get("page"), f.get("quote"), checked, now))
                if status == "found":
                    for fl in con.execute("SELECT id FROM flags WHERE referral_id=? AND fact_key=? AND resolved_at IS NULL", (rid, f["key"])).fetchall():
                        con.execute("UPDATE flags SET resolved_at=?, resolved_note=? WHERE id=?", (now, f"Answered by new pages (p. {f.get('page')})", fl["id"]))
                        resolved.append(fl["id"])
            for i, r in enumerate(found.get("red_flags", [])):
                if r["rule_id"] not in rules.RULES:
                    continue
                con.execute("INSERT INTO findings (id, referral_id, kind, rule_id, text, page, quote, quote_checked, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                            (store.new_id("fd"), rid, "red_flag", r["rule_id"], r["text"], r.get("page"), r.get("quote"), int(ok.get(f"r{i}", False)), now))
            for i, c in enumerate(found.get("contradictions", [])):
                both = int(ok.get(f"c{i}a", False) and ok.get(f"c{i}b", False))
                con.execute("INSERT INTO findings (id, referral_id, kind, fact_key, text, page, quote, page2, quote2, quote_checked, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (store.new_id("fd"), rid, "contradiction", c["fact_key"], c["text"], c.get("page"), c.get("quote"), c.get("page2"), c.get("quote2"), both, now))
            con.commit()
            # A resent page can also deliver a missing document: close those to-dos too
            docs_now = rules.documents(con, rid)
            for fl in con.execute("SELECT id, rule_id FROM flags WHERE referral_id=? AND resolved_at IS NULL AND fact_key IS NULL AND rule_id LIKE 'DOC-%'", (rid,)).fetchall():
                if fl["rule_id"] in docs_now:
                    con.execute("UPDATE flags SET resolved_at=?, resolved_note=? WHERE id=?", (now, f"Document arrived (p. {docs_now[fl['rule_id']][0]})", fl["id"]))
                    resolved.append(fl["id"])
            con.commit()
            todo = rules.build_todos(con, rid)
        # Possible red flags go to the intake team at once; the hospital is told when a clinician confirms.
        for fid in todo["possible_red_flags"]:
            notify.alert_possible_red_flag(con, rid, fid)
        if resolved:
            notify.note_resend(con, rid, len(new_pages), len(resolved))
        _set_run(con, rid, status="done", step="Done", finished_at=store.iso(store.now(con)))
        store.log_activity(con, rid, "Anchor pre-read", f"read {len(new_pages)} page(s); {todo['requests']} missing item(s) suggested; {len(resolved)} answered", kind="system")
        return {"status": "done", "new_pages": len(new_pages), "todo": todo, "resolved": len(resolved)}
    except claude.ReaderUnavailable as e:
        _set_run(con, rid, status="error", step="Could not finish the pre-read. Review by hand.", error=str(e)[:300], finished_at=store.iso(store.now(con)))
        return {"status": "error", "error": str(e)}


def run_in_background(con, rid, only_doc_ids=None):
    """Run the pre-read on its own database connection so the web pages stay responsive."""
    def work():
        own = store.connect()
        try:
            run(own, rid, only_doc_ids=only_doc_ids)
        finally:
            own.close()
    threading.Thread(target=work, daemon=True).start()


def sha_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
