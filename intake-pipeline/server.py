"""Local web app: referral intake, pre-read, to-do list, fact checking and hospital follow-up.

Run:  python3 server.py      then open http://127.0.0.1:8765  (another port: INTAKE_PORT=8777 python3 server.py)
Binds to 127.0.0.1 only. Dry run: every message is written to outbox/, nothing is sent.
"""
import cgi
import html
import http.cookies
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from pipeline import assistant, faxmail, guidance, ingest, notify, preread, rules, store

HOST, PORT = "127.0.0.1", int(os.environ.get("INTAKE_PORT", "8765"))
con = store.connect()
ACCEPT = ".pdf,.tif,.tiff,.jpg,.jpeg,.png,.heic,.gif,.bmp,.doc,.docx,.rtf,.odt,.txt,.eml,.zip"
OWNER = {"coordinator": "Coordinator", "clinical": "Clinical reviewer"}
ROLES = ["Coordinator", "Clinical reviewer", "Intake lead", "Other"]
CURRENT = {"name": "", "role": ""}     # who is working, set per request (requests run one at a time)
STATUS_WORD = {"found": "✓ Found", "unclear": "? Unclear", "cant_tell": "⏱ Can't tell", "redacted": "■ Redacted", "missing": "✕ Missing"}
STATUS_CLS = {"found": "ok", "unclear": "warn", "cant_tell": "", "redacted": "", "missing": "bad"}

CSS = """
:root{--bg:#f6f8f9;--panel:#fff;--ink:#14222b;--muted:#4f606a;--line:#d3dde1;--accent:#0d6b67;--bad:#a4261d;--warn:#8a5300;--ok:#1d6b34;--soft:#eef4f5}
@media (prefers-color-scheme:dark){:root{--bg:#0f171b;--panel:#16232a;--ink:#e6eef1;--muted:#a6b7bf;--line:#2b3c45;--accent:#5cc2bb;--bad:#f19387;--warn:#f0b660;--ok:#86d39c;--soft:#1c2c34}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--accent)}:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
.skip{position:absolute;left:-9999px}.skip:focus{left:12px;top:12px;background:var(--panel);padding:6px 10px;border:2px solid var(--ink)}
header{background:var(--panel);border-bottom:1px solid var(--line);padding:12px max(16px,4vw)}header p{margin:2px 0 0;color:var(--muted);font-size:14px}
main{max-width:76rem;margin:0 auto;padding:20px max(16px,4vw);display:grid;gap:18px}
section,.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0}
h1{font-size:1.4rem;margin:0}h2{font-size:1.15rem;margin:0 0 8px}h3{font-size:1rem;margin:0 0 6px}
.dry{display:inline-block;border:1px dashed var(--warn);color:var(--warn);border-radius:999px;padding:1px 10px;font-size:13px}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:end}
label{display:grid;gap:4px;font-size:14px}input,select,textarea{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-height:40px}
textarea{min-height:8rem;width:100%}
button{font:inherit;min-height:40px;padding:6px 14px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--bg);cursor:pointer}
button.ghost{background:transparent;color:var(--accent)}button.red{background:var(--bad);border-color:var(--bad)}button.small{min-height:32px;padding:2px 10px;font-size:14px}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}th{white-space:nowrap}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:0 8px;font-size:13px;white-space:nowrap}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.muted{color:var(--muted)}.small{font-size:14px}
.next{border-left:4px solid var(--accent);font-size:1.05rem}
.fast{border:2px solid var(--ok)}
.two{display:grid;gap:16px;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr)}@media (max-width:900px){.two{grid-template-columns:1fr}}
.facts{list-style:none;margin:0;padding:0;display:grid;gap:4px;max-height:40rem;overflow:auto}
.fact{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--panel)}
.fact[aria-current=true]{border-color:var(--ink);box-shadow:inset 4px 0 0 var(--accent)}
.fact .k{font-weight:600}.fact .v{display:block;font-size:14px;color:var(--muted)}
.fact button.open{all:unset;cursor:pointer;text-align:left}.fact button.open:focus-visible{outline:3px solid var(--ink)}
.viewer{position:sticky;top:12px;display:grid;gap:8px;align-content:start}
.viewer img{width:100%;max-width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
.viewer pre{white-space:pre-wrap;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:10px;font-size:13px;max-height:40rem;overflow:auto}
.quote{background:var(--soft);border-left:4px solid var(--warn);padding:6px 10px;font-size:14px;margin:0}
.pages2{display:grid;gap:8px;grid-template-columns:1fr 1fr}
.kbd{font-family:ui-monospace,Menlo,monospace;font-size:.9em;border:1px solid var(--line);border-radius:4px;padding:0 5px}
pre.msg{white-space:pre-wrap;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:10px;font-size:13px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.todo{display:grid;gap:6px;padding:0;margin:0}.todo li{border:1px solid var(--line);border-radius:8px;padding:8px;list-style:none;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.todo li .t{flex:1 1 20rem}.todo form{margin:0}
ol.steps{margin:0;padding-left:1.3em;display:grid;gap:4px}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
.who{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:6px;font-size:14px}
.who form{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:0}.who input,.who select{min-height:34px;padding:2px 8px}
.who button{min-height:34px;padding:2px 12px}
.upload-btn{display:inline-flex;align-items:center;min-height:34px;padding:2px 14px;border-radius:8px;background:var(--accent);color:var(--bg);text-decoration:none;font-weight:600}
.upload-btn:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
.ask-btn{position:fixed;right:calc(16px + env(safe-area-inset-right,0px));bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:20;border-radius:999px;padding:10px 18px;box-shadow:0 4px 14px rgba(0,0,0,.18)}
.ask{position:fixed;right:calc(16px + env(safe-area-inset-right,0px));bottom:calc(72px + env(safe-area-inset-bottom,0px));z-index:21;width:min(26rem,calc(100vw - 32px));max-height:min(70vh,36rem);display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.22)}
.ask header{background:transparent;border-bottom:1px solid var(--line);padding:10px 12px;display:flex;justify-content:space-between;gap:8px;align-items:start}
.ask header h2{margin:0;font-size:1rem}.ask header p{margin:2px 0 0;font-size:12px}
.ask .log{flex:1;overflow:auto;padding:10px 12px;display:grid;gap:8px;align-content:start}
.ask .msg-u{justify-self:end;background:var(--accent);color:var(--bg);border-radius:10px 10px 2px 10px;padding:6px 10px;max-width:90%}
.ask .msg-a{justify-self:start;background:var(--soft);border-radius:10px 10px 10px 2px;padding:6px 10px;max-width:95%;white-space:pre-wrap}
.ask .tag{font-size:12px;color:var(--muted);display:block;margin-top:2px}
.ask .chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 12px 8px}.ask .chips button{min-height:32px;font-size:13px;padding:2px 10px}
.ask form{display:flex;gap:6px;padding:10px 12px;border-top:1px solid var(--line)}.ask form input{flex:1;min-width:0}
"""


def esc(x):
    return html.escape("" if x is None else str(x))


ASK_HTML = """
<button type="button" class="ask-btn" id="ask-open" aria-expanded="false" aria-controls="ask">Ask Anchor</button>
<section class="ask" id="ask" role="dialog" aria-modal="false" aria-labelledby="ask-title" hidden>
  <header><div><h2 id="ask-title">Ask Anchor</h2><p class="muted">Answers come only from Anchor and the referral on screen. A person decides.</p></div>
  <button type="button" class="ghost small" id="ask-close" aria-label="Close Ask Anchor">✕</button></header>
  <div class="log" id="ask-log" role="log" aria-live="polite"><div class="msg-a">Hi! Ask me what to do next, or about anything on this screen.</div></div>
  <div class="chips" role="group" aria-label="Suggested questions">
    <button type="button" class="ghost" data-q="What should I do next?">What should I do next?</button>
    <button type="button" class="ghost" data-q="What does this grade mean?">What does this grade mean?</button>
    <button type="button" class="ghost" data-q="Explain what I'm looking at.">Explain what I'm looking at</button>
  </div>
  <form id="ask-form"><label class="sr" for="ask-q">Your question</label><input id="ask-q" autocomplete="off" placeholder="Ask about this screen…"><button>Send</button></form>
</section>"""

ASK_JS = r"""
(function () {
  const btn = document.getElementById('ask-open'), panel = document.getElementById('ask'), log = document.getElementById('ask-log');
  const form = document.getElementById('ask-form'), input = document.getElementById('ask-q');
  const history = []; let lastFocus = null;
  document.addEventListener('focusin', (e) => { if (!panel.contains(e.target) && e.target !== btn) lastFocus = e.target; });
  function open() { panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); input.focus(); }
  function close() { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.focus(); }
  btn.addEventListener('click', () => (panel.hidden ? open() : close()));
  document.getElementById('ask-close').addEventListener('click', close);
  panel.addEventListener('keydown', (e) => { if (e.key === 'Escape') { e.stopPropagation(); close(); } });
  function nameOf(el) {
    if (!el) return '';
    const t = el.getAttribute('aria-label') || (el.labels && el.labels[0] && el.labels[0].textContent) || el.textContent || el.value || '';
    return t.replace(/\s+/g, ' ').trim().slice(0, 80);
  }
  function screen() {
    const mid = window.innerHeight / 2; let section = '';
    document.querySelectorAll('main h2').forEach((h) => { const r = h.closest('section') ? h.closest('section').getBoundingClientRect() : h.getBoundingClientRect(); if (r.top <= mid) section = h.textContent.trim(); });
    const fact = document.querySelector('.fact[aria-current=true] .k');
    return { page: document.title.replace(' · Anchor', ''), referral: document.body.dataset.referral || null, section, fact: fact ? fact.textContent.trim() : '', focus: nameOf(lastFocus) };
  }
  function add(cls, text, tag) {
    const d = document.createElement('div'); d.className = cls; d.textContent = text;
    if (tag) { const s = document.createElement('span'); s.className = 'tag'; s.textContent = tag; d.append(s); }
    log.append(d); log.scrollTop = log.scrollHeight; return d;
  }
  async function ask(q) {
    q = q.trim(); if (!q) return;
    add('msg-u', q); input.value = '';
    const wait = add('msg-a', 'Thinking…');
    try {
      const r = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q, history, screen: screen() }) });
      const d = await r.json();
      wait.textContent = d.answer;
      const tag = (d.mode === 'claude' ? 'Ask Anchor (Claude Haiku)' : 'Built-in guidance') + (d.note ? ' · ' + d.note : '');
      const s = document.createElement('span'); s.className = 'tag'; s.textContent = tag; wait.append(s);
      history.push({ role: 'user', content: q }, { role: 'assistant', content: d.answer });
    } catch (e) { wait.textContent = 'Ask Anchor is not reachable right now. Try again, or check "What to do next" on the page.'; }
  }
  form.addEventListener('submit', (e) => { e.preventDefault(); ask(input.value); });
  panel.querySelectorAll('[data-q]').forEach((b) => b.addEventListener('click', () => ask(b.dataset.q)));
})();
"""


def page(title, body, flash="", script="", rid=None):
    msg = f'<p role="status" class="card">{esc(flash)}</p>' if flash else '<p role="status" class="sr"></p>'
    clock = store.now(con).strftime("%H:%M:%S UTC")
    reader = preread.choose_reader()
    mode = f"Pre-read: {esc(reader.name)}" if reader else "Pre-read: off (set ANTHROPIC_API_KEY)"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Anchor</title><style>{CSS}</style></head><body{(' data-referral="' + esc(rid) + '"') if rid else ''}>
<a class="skip" href="#main">Skip to content</a>
<header><h1>Anchor <span class="small muted" style="font-weight:400">· referral intake by Team Beacon</span></h1><p><span class="dry">Dry run: nothing is sent</span> · Prototype · Demo clock {clock} · {mode} ·
<a href="/">All referrals</a> · <a href="/todo">My list</a> · <a href="/how">How it works</a></p>
<div class="who"><a class="upload-btn" href="/upload">⬆ Upload</a>{who_bar()}</div></header>
<main id="main">{msg}{body}</main>{ASK_HTML}<script>{ASK_JS}</script>{script}</body></html>"""


def who_bar():
    if CURRENT["name"]:
        return (f"<span>Working as <strong>{esc(CURRENT['name'])}</strong>{(' · ' + esc(CURRENT['role'])) if CURRENT['role'] else ''}</span>"
                f"<details><summary class='small'>Change</summary>{who_form()}</details>")
    return f"<span class='warn'>Add your name so your work is recorded:</span>{who_form()}"


def who_form():
    opts = "".join(f"<option {'selected' if r == CURRENT['role'] else ''}>{r}</option>" for r in ROLES)
    return (f"<form method='post' action='/me'><label class='sr' for='me-name'>Your name</label>"
            f"<input id='me-name' name='name' maxlength='40' required placeholder='Your name' value='{esc(CURRENT['name'])}'>"
            f"<label class='sr' for='me-role'>Your role</label><select id='me-role' name='role'>{opts}</select><button class='ghost'>Save</button></form>")


def status_pill(rid):
    s = store.activity_status(con, rid)
    if s["state"] == "untouched":
        return "<span class='pill bad'><span aria-hidden='true'>✕ </span>Untouched</span>"
    last = s["last"]
    ago = "just now" if last["minutes_ago"] < 1 else f"{last['minutes_ago']} min ago"
    if s["state"] == "opened":
        return f"<span class='pill warn'><span aria-hidden='true'>! </span>Opened by {esc(last['actor'])}, {ago}</span>"
    return f"<span class='pill ok'><span aria-hidden='true'>✓ </span>Worked on</span> <span class='small muted'>last: {esc(last['actor'])}, {esc(last['action'])}, {ago}</span>"


def workers_text(rid):
    s = store.activity_status(con, rid)
    return ", ".join(s["workers"]) or "No one yet"


def clock_pill(ref):
    state = notify.clock_state(con, ref)
    cls = {"On time": "ok", "At risk": "warn", "Late": "bad", "Answered": ""}[state]
    mins = int(store.minutes_open(con, ref))
    sym = {"ok": "✓ ", "warn": "! ", "bad": "✕ "}.get(cls, "")
    return f'<span class="pill {cls}"><span aria-hidden="true">{sym}</span>{state} · {mins} min</span>'


def grade_pill(g):
    if not g["grade"]:
        return '<span class="pill">Not read yet</span>'
    cls = {"Great": "ok", "Neutral": "warn", "Bad": "bad"}[g["grade"]]
    sym = {"Great": "✓", "Neutral": "!", "Bad": "✕"}[g["grade"]]
    return f'<span class="pill {cls}" title="{esc(g["why"])}"><span aria-hidden="true">{sym} </span>{g["grade"]}</span>'


def run_row(rid):
    return con.execute("SELECT * FROM preread_runs WHERE referral_id=?", (rid,)).fetchone()


def next_step(ref, g, run):
    return guidance.next_step(con, ref, g, run)


def hidden(rid, fid=None, note=None):
    h = f"<input type='hidden' name='rid' value='{esc(rid)}'>"
    if fid:
        h += f"<input type='hidden' name='fid' value='{esc(fid)}'>"
    if note:
        h += f"<input type='hidden' name='note' value='{esc(note)}'>"
    return h


# ---------------- pages ----------------

def home(flash=""):
    refs = con.execute("SELECT * FROM referrals ORDER BY status='decided', received_at").fetchall()
    rows = []
    for r in refs:
        g = rules.grade(con, r["id"])
        run = run_row(r["id"])
        red = con.execute("SELECT COUNT(*) FROM flags WHERE referral_id=? AND type='red' AND resolved_at IS NULL", (r["id"],)).fetchone()[0]
        todo = con.execute("SELECT COUNT(*) FROM flags WHERE referral_id=? AND resolved_at IS NULL", (r["id"],)).fetchone()[0]
        red_cell = f'<span class="pill bad"><span aria-hidden="true">✕ </span>{red}</span>' if red else "0"
        fast = ' <span class="pill ok">Fast lane</span>' if g.get("fast_lane") and r["status"] == "open" else ""
        rows.append(f"<tr><th scope='row'><a href='/r/{esc(r['id'])}'>{esc(r['id'])}</a></th><td>{esc(r['hospital'])}</td><td>{clock_pill(r)}</td>"
                    f"<td>{status_pill(r['id'])}</td><td class='small'>{esc(workers_text(r['id']))}</td>"
                    f"<td>{grade_pill(g)}{fast}</td><td>{red_cell}</td><td>{todo}</td>"
                    f"<td class='small'>{esc(next_step(r, g, run))}</td></tr>")
    table = "".join(rows) or "<tr><td colspan='9'>No referrals yet. Press Upload or check the fax inbox.</td></tr>"
    return page("All referrals", f"""
<section aria-labelledby="up"><h2 id="up">Add a referral</h2>
<div class="row"><a class="upload-btn" href="/upload">⬆ Upload files</a>
<form method="post" action="/poll" class="row"><button class="ghost">Check fax inbox</button></form></div>
<p class="small muted">Faxes arrive as emails in <code>fax-inbox/</code>. A fax that mentions an open referral number is added to that referral.</p></section>
<section aria-labelledby="q"><h2 id="q">Referrals</h2><div class="tbl"><table>
<caption class="sr">Referrals with clock, who has touched them, grade, red flags, open to-dos and next step</caption>
<thead><tr><th scope="col">Referral</th><th scope="col">Hospital</th><th scope="col">2-hour clock</th><th scope="col">Status</th><th scope="col">Worked on by</th><th scope="col">Grade</th><th scope="col">Red flags</th><th scope="col">Open to-dos</th><th scope="col">Next step</th></tr></thead>
<tbody>{table}</tbody></table></div>
<form method="post" action="/advance" class="row" style="margin-top:10px"><label>Demo: move the clock forward<select name="minutes"><option>15</option><option>30</option><option>60</option></select></label><button class="ghost">Advance clock</button></form>
</section>""", flash)


def upload_page(flash=""):
    return page("Upload", f"""<section aria-labelledby="upl"><h2 id="upl">Upload a referral</h2>
<p class="small">Any common format: PDF, TIFF fax, phone photo, Word, text, email or zip. Files stay on this computer. Use made-up or de-identified documents only.</p>
<form method="post" action="/upload" enctype="multipart/form-data" style="display:grid;gap:10px;max-width:36rem">
<label for="up-hospital">Hospital<input id="up-hospital" name="hospital" required placeholder="e.g. Sample Hospital A"></label>
<label for="up-channel">How it arrived<select id="up-channel" name="channel"><option value="upload">Upload</option><option value="fax">Fax</option><option value="email">Email</option></select></label>
<label for="up-files">Files<input id="up-files" type="file" name="files" multiple required accept="{ACCEPT}"></label>
<div class="row"><button>⬆ Upload and start the pre-read</button><a href="/">Cancel</a></div></form>
<p class="small muted">To add pages to a referral that's already open, use "Add more files" on that referral's page.</p></section>""", flash)


def todo_page(owner, flash=""):
    owner = owner if owner in OWNER else ""
    q = "SELECT f.* FROM flags f JOIN referrals r ON r.id=f.referral_id WHERE f.resolved_at IS NULL AND r.status='open'"
    args = []
    if owner:
        q += " AND f.owner=?"
        args.append(owner)
    items = con.execute(q + " ORDER BY f.type='red' DESC, f.created_at", args).fetchall()
    opts = "".join(f"<option value='{k}' {'selected' if k == owner else ''}>{v}</option>" for k, v in [("", "Everyone"), *OWNER.items()])
    lis = "".join(f"<li><span class='pill {'bad' if i['type'] == 'red' else 'warn'}'>{'✕ Red flag' if i['type'] == 'red' else '! To do'}</span>"
                  f"<span class='t'>{esc(i['text'])}</span><span class='pill'>{esc(OWNER.get(i['owner'], i['owner']))}</span>"
                  f"<a href='/r/{esc(i['referral_id'])}'>{esc(i['referral_id'])}</a></li>" for i in items) or "<li>Nothing open.</li>"
    return page("My list", f"""<section><h2>My list</h2>
<form method="get" action="/todo" class="row"><label>Show items for<select name="owner">{opts}</select></label><button class="ghost">Show</button></form>
<p class="small muted">Clinical items (red flags, clinical conflicts, clinical facts) go to the clinical reviewer. Paperwork goes to the coordinator. Both can work at the same time.</p>
<ul class="todo">{lis}</ul></section>""", flash)


def facts_panel(rid):
    facts = {(f["key"], f["source"]): f for f in con.execute("SELECT * FROM facts WHERE referral_id=?", (rid,))}
    best = rules.best_facts(con, rid)
    conflicts = con.execute("SELECT * FROM findings WHERE referral_id=? AND kind='contradiction'", (rid,)).fetchall()
    kinds = {p["n"]: ("text" if p["image_path"].endswith(".txt") else "image") for p in con.execute("SELECT n, image_path FROM pages WHERE referral_id=?", (rid,))}
    verified = sum(1 for f in best.values() if f["verified_at"])
    items = []
    for i, key in enumerate(rules.FACT_KEYS):
        f = best.get(key)
        st = f["status"] if f else "missing"
        conflict = next((c for c in conflicts if c["fact_key"] == key), None)
        attrs = ""
        if f and f["page"]:
            attrs = f" data-page='{f['page']}' data-kind='{kinds.get(f['page'], 'image')}' data-quote='{esc(f['quote'])}' data-checked='{f['quote_checked']}'"
        if conflict:
            attrs += f" data-page2='{conflict['page2']}' data-kind2='{kinds.get(conflict['page2'], 'image')}' data-conflict='{esc(conflict['text'])}'"
        ver = ""
        if f:
            ver = (f"<form method='post' action='/fact/verify' class='verify'>{hidden(rid, f['id'])}"
                   f"<button class='small {'' if f['verified_at'] else 'ghost'}' aria-pressed='{'true' if f['verified_at'] else 'false'}'>{'✓ Verified' if f['verified_at'] else 'Verify'}</button></form>")
        src = f" · {esc(f['source'])}, p. {esc(f['page'])}" if f and f["page"] else ""
        extra = " · form and chart disagree" if conflict else ""
        items.append(f"<li class='fact' data-i='{i}'{attrs}><button type='button' class='open'><span class='k'>{esc(rules.FACT_LABELS[key])}</span> "
                     f"<span class='pill {STATUS_CLS[st]}'>{STATUS_WORD[st]}</span><span class='v'>{esc(f['value'] if f else 'Not in the packet')}{src}{extra}</span></button>{ver}</li>")
    return f"""<section aria-labelledby="s2"><h2 id="s2">2. Check the facts</h2>
<p class="small">Click a fact (or press <span class="kbd">J</span> / <span class="kbd">K</span>) to see its page beside it. Read the quote on the page, then press <span class="kbd">V</span> to mark it verified.
<span class="kbd">O</span> opens the page full size. <span class="kbd">R</span> jumps to the reply box. <strong id="vcount">{verified} of {len(rules.FACT_KEYS)}</strong> checked by a person.</p>
<div class="two"><ul class="facts" id="facts" aria-label="Facts">{''.join(items)}</ul>
<div class="viewer" id="viewer" aria-live="polite"><p class="muted">Pick a fact to see its page here.</p></div></div></section>"""


def todo_section(rid, flags, open_):
    pending_req = [f for f in flags if f["type"] == "missing" and not f["approved"] and not f["resolved_at"] and (f["source"] or "") != "internal"]
    lis = []
    for f in flags:
        if f["resolved_at"]:
            continue
        who = OWNER.get(f["owner"] or "coordinator", f["owner"])
        if f["type"] == "red":
            tag = "<span class='pill bad'>✕ Red flag</span>"
            if f["approved"]:
                act = f"<span class='pill bad'>Confirmed · hospital told</span><form method='post' action='/resolve'>{hidden(rid, f['id'], 'Resolved')}<button class='small ghost'>Mark resolved</button></form>"
            else:
                act = (f"<form method='post' action='/redconfirm'>{hidden(rid, f['id'])}<button class='small red'>Confirm (tells hospital now)</button></form>"
                       f"<form method='post' action='/resolve'>{hidden(rid, f['id'], 'Dismissed by clinical reviewer')}<button class='small ghost'>Dismiss</button></form>")
        elif (f["source"] or "") == "internal":
            tag = "<span class='pill warn'>! Settle</span>"
            act = f"<form method='post' action='/resolve'>{hidden(rid, f['id'], 'Settled')}<button class='small ghost'>Mark done</button></form>"
        elif f["approved"]:
            tag = "<span class='pill warn'>! Missing</span>"
            act = f"<span class='pill'>Requested</span><form method='post' action='/resolve'>{hidden(rid, f['id'], 'Received')}<button class='small ghost'>Received</button></form>"
        else:
            tag = "<span class='pill warn'>! Missing</span>"
            act = f"<label class='small' style='display:flex;gap:6px;align-items:center'><input type='checkbox' name='fids' value='{esc(f['id'])}' form='reqform' checked> Include in request</label>"
        src = "Suggested by the pre-read" if f["source"] in ("auto", "internal") else "Added by staff"
        rule = f" · rule {esc(f['rule_id'])}" if f["rule_id"] else ""
        lis.append(f"<li>{tag}<span class='t'>{esc(f['text'])}{rule}<br><span class='small muted'>{src}</span></span><span class='pill'>{esc(who)}</span>{act}</li>")
    done = [f for f in flags if f["resolved_at"]]
    req_btn = (f"<form id='reqform' method='post' action='/request' style='margin-top:10px'>{hidden(rid)}"
               f"<button>Send request now ({len(pending_req)} item(s))</button> <span class='small muted'>Writes one message to the hospital right away (dry run). The 30- and 60-minute messages become reminders.</span></form>") if pending_req and open_ else ""
    done_html = ("<details style='margin-top:8px'><summary>" + str(len(done)) + " done</summary><ul class='todo'>" +
                 "".join(f"<li><span class='t'>{esc(f['text'])}</span><span class='small muted'>{esc(f['resolved_note'] or 'Done')}</span></li>" for f in done) + "</ul></details>") if done else ""
    add = f"""<form method="post" action="/flag" class="row" style="margin-top:10px">{hidden(rid)}
<label>Add<select name="type"><option value="missing">Missing item</option><option value="red">Red flag (tells hospital now)</option></select></label>
<label>What<input name="text" required size="36" placeholder="e.g. PT note showing distance walked"></label>
<label>Rule ID (optional)<input name="rule_id" size="8" placeholder="MOB-2"></label><button class="ghost">Add</button></form>""" if open_ else ""
    return f"""<section aria-labelledby="s1"><h2 id="s1">1. To-do list</h2>
<p class="small muted">Each item has an owner. Clinical items go to the clinical reviewer and paperwork to the coordinator, so both can work at once. <a href="/todo">See everyone's list</a>.</p>
<ul class="todo">{''.join(lis) or '<li>Nothing open.</li>'}</ul>{req_btn}{done_html}{add}</section>"""


def detail(rid, flash=""):
    r = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone()
    if not r:
        return page("Not found", "<p>No such referral.</p>")
    g = rules.grade(con, rid)
    run = run_row(rid)
    open_ = r["status"] == "open"
    flags = con.execute("SELECT * FROM flags WHERE referral_id=? ORDER BY resolved_at IS NOT NULL, type='red' DESC, created_at", (rid,)).fetchall()
    notes = con.execute("SELECT * FROM notifications WHERE referral_id=? ORDER BY created_at", (rid,)).fetchall()
    pages = con.execute("SELECT * FROM pages WHERE referral_id=? ORDER BY n", (rid,)).fetchall()
    docs = con.execute("SELECT * FROM documents WHERE referral_id=? ORDER BY added_at", (rid,)).fetchall()
    run_txt = (f"{run['status']} · {run['step']}" + (f" · {run['error']}" if run["error"] else "")) if run else "not started"
    acts = con.execute("SELECT * FROM activity WHERE referral_id=? ORDER BY at DESC LIMIT 60", (rid,)).fetchall()
    kind_word = {"work": "", "view": "opened it", "system": ""}
    act_rows = "".join(f"<tr><td>{esc(a['at'][11:19])}</td><td>{esc(a['actor'])}{(' · ' + esc(a['role'])) if a['role'] else ''}</td>"
                       f"<td>{esc(a['action'] if a['kind'] != 'view' else kind_word['view'])}</td></tr>" for a in acts)
    activity_sec = f"""<section aria-labelledby="s6"><h2 id="s6">6. Who has worked on it</h2>
<p>{status_pill(rid)}</p><p class="small">Worked on by: <strong>{esc(workers_text(rid))}</strong></p>
<div class="tbl"><table><caption class="sr">Activity history, newest first</caption><thead><tr><th scope="col">Time</th><th scope="col">Who</th><th scope="col">What</th></tr></thead>
<tbody>{act_rows or '<tr><td colspan=3>No activity yet.</td></tr>'}</tbody></table></div></section>"""

    fast = ""
    if g.get("fast_lane") and open_:
        doc_list = ", ".join(sorted(rules.documents(con, rid)))
        fast = f"""<section class="fast" aria-labelledby="fl"><h2 id="fl">Fast lane</h2>
<p>All 7 core documents are here ({esc(doc_list)}), {g['pct']}% of facts were found and confirmed on their pages, and nothing is flagged.</p>
<p class="small muted">Still glance at the facts in step 2. You decide; the tool never approves or denies.</p>
<form method="post" action="/decide" class="row">{hidden(rid)}
<button name="decision" value="Approved">Approve</button><button class="ghost" name="decision" value="Denied">Deny</button>
<a href="#s2">Check the facts first</a></form></section>"""

    page_rows = "".join(f"<tr><td>p. {p['n']}</td><td>{esc((p['doc_type'] or 'not mapped').replace('_', ' '))}</td><td>{('turned ' + str(p['rotation']) + '°') if p['rotation'] else ''}</td>"
                        f"<td>{'older stay' if p['prior_stay'] else ''}{' · hard to read' if p['legible'] == 0 else ''}{' · resent' if p['added_by'] == 'resend' else ''}</td>"
                        f"<td><a href='/page/{esc(rid)}/{p['n']}' target='_blank' rel='noopener'>Open<span class='sr'> page {p['n']} (new tab)</span></a></td></tr>" for p in pages)
    docs_found = rules.documents(con, rid)
    checklist = "".join(f"<li>{'✓' if d in docs_found else '✕'} {esc(rules.DOC_NAMES.get(d, d))}{(' (p. ' + ', '.join(map(str, docs_found[d])) + ')') if d in docs_found else ' (not in packet)'}</li>"
                        for d in [f"DOC-{i}" for i in range(1, 11)])
    files_html = "".join(f"<li>{esc(d['filename'])} · {esc(d['kind'].upper())} · {esc(d['status'].replace('_', ' '))}{(' · ' + esc(d['note'])) if d['note'] else ''}{' · resent' if d['via'] == 'resend' else ''}</li>" for d in docs)
    more = f"""<form method="post" action="/add" enctype="multipart/form-data" class="row">{hidden(rid)}<label>Add more files<input type="file" name="files" multiple required accept="{ACCEPT}"></label><button class="ghost">Add</button></form>
<form method="post" action="/demo-resend" class="row" style="margin-top:6px">{hidden(rid)}<button class="ghost small">Demo: hospital resends missing pages</button></form>""" if open_ else ""
    pages_sec = f"""<section aria-labelledby="s3"><h2 id="s3">3. What arrived</h2>
<div class="two"><div><h3>IHH document checklist</h3><ul class="small" style="padding-left:1.1em">{checklist}</ul></div>
<div class="tbl"><table><caption class="sr">Page map</caption><thead><tr><th scope="col">Page</th><th scope="col">Document</th><th scope="col">Turned</th><th scope="col">Notes</th><th scope="col"><span class="sr">Open</span></th></tr></thead>
<tbody>{page_rows or '<tr><td colspan=5>No pages mapped yet.</td></tr>'}</tbody></table></div></div>
<details><summary>Files received ({len(docs)})</summary><ul class="small">{files_html}</ul></details>{more}</section>"""

    nrows = "".join(f"<tr><td>{esc(n['created_at'][11:19])}</td><td>{esc(n['tier'])}</td><td>{esc(notify.AUDIENCE_LABEL.get(n['audience'], n['audience']))}</td>"
                    f"<td>{esc(n['subject'])}</td><td><a href='/msg/{esc(n['id'])}'>View</a></td></tr>" for n in notes)
    reply_default = f"Referral: {rid}\n\n\n\nIHH Referral Intake team\n(Prototype draft. Not sent.)"
    reply = f"""<form method="post" action="/reply" style="display:grid;gap:8px;margin-top:10px">{hidden(rid)}
<h3>Reply to the hospital</h3><label>Subject<input name="subject" id="reply-subject" value="Referral {esc(rid)}: "></label>
<label>Message<textarea name="text" id="reply-text">{esc(reply_default)}</textarea></label>
<div class="row"><button>Save reply to outbox (dry run)</button><span class="small muted">Referral number only; no patient names.</span></div></form>""" if open_ else ""
    msgs = f"""<section aria-labelledby="s4"><h2 id="s4">4. Messages</h2>
<div class="tbl"><table><caption class="sr">Messages written to the outbox</caption><thead><tr><th scope="col">Time</th><th scope="col">Type</th><th scope="col">To</th><th scope="col">Subject</th><th scope="col"><span class="sr">Open</span></th></tr></thead>
<tbody>{nrows or '<tr><td colspan=5>None yet</td></tr>'}</tbody></table></div>{reply}</section>"""

    decide = f"""<section aria-labelledby="s5"><h2 id="s5">5. Decide</h2>
<form method="post" action="/decide" class="row">{hidden(rid)}
<label>Decision<select name="decision"><option>Approved</option><option>Denied</option><option>Withdrawn by hospital</option></select></label>
<button class="ghost">Record decision and stop follow-ups</button></form><p class="small muted">A person decides. The tool never approves or denies.</p></section>""" if open_ else ""

    rerun = f'<form method="post" action="/preread" class="row">{hidden(rid)}<button class="ghost small">Run pre-read again</button></form>' if open_ else ""
    head = f"""<section><h2>{esc(rid)} · {esc(r['hospital'])}</h2>
<p>{clock_pill(r)} {grade_pill(g)} {('<span class="pill ok">Fast lane</span>' if g.get('fast_lane') and open_ else '')}
<span class="small muted">· arrived by {esc(r['channel'])} · grade: {esc(g['why'])} · pre-read: {esc(run_txt)}</span></p>
<p>{status_pill(rid)} <span class="small muted">· worked on by {esc(workers_text(rid))} · <a href="#s6">history</a></span></p>{rerun}</section>
<section class="next" aria-labelledby="nx"><h2 id="nx">What to do next</h2><p>{esc(next_step(r, g, run))}</p></section>"""
    body = head + fast + todo_section(rid, flags, open_) + facts_panel(rid) + pages_sec + msgs + decide + activity_sec
    return page(rid, body, flash, script=f"<script>{DETAIL_JS.replace('__RID__', json.dumps(rid))}</script>", rid=rid)


DETAIL_JS = r"""
(function () {
  const rid = __RID__;
  const list = document.getElementById('facts'); if (!list) return;
  const items = [...list.querySelectorAll('.fact')];
  const viewer = document.getElementById('viewer');
  const status = document.querySelector('[role=status]');
  let cur = -1;
  function pageEl(n, kind, label) {
    const wrap = document.createElement('div');
    const cap = document.createElement('p'); cap.className = 'small'; cap.textContent = label + ', page ' + n; wrap.append(cap);
    if (kind === 'text') {
      const pre = document.createElement('pre'); pre.textContent = 'Loading…';
      fetch('/page/' + encodeURIComponent(rid) + '/' + n).then(r => r.text()).then(t => { pre.textContent = t; });
      wrap.append(pre);
    } else {
      const img = document.createElement('img'); img.src = '/page/' + encodeURIComponent(rid) + '/' + n; img.alt = 'Scanned page ' + n + ' of the referral packet'; wrap.append(img);
    }
    return wrap;
  }
  function show(i) {
    if (i < 0 || i >= items.length) return;
    items.forEach((el, j) => el.setAttribute('aria-current', j === i ? 'true' : 'false'));
    cur = i; const el = items[i]; el.querySelector('button.open').focus();
    viewer.replaceChildren();
    const title = document.createElement('h3'); title.textContent = el.querySelector('.k').textContent; viewer.append(title);
    if (!el.dataset.page) { const p = document.createElement('p'); p.textContent = 'Not found in the packet. It is on the to-do list.'; viewer.append(p); return; }
    const q = document.createElement('p'); q.className = 'quote';
    q.textContent = 'Look for: "' + el.dataset.quote + '"' + (el.dataset.checked === '1' ? '  (a second look confirmed it is on this page)' : '  (not confirmed: read carefully)');
    viewer.append(q);
    if (el.dataset.page2) {
      const c = document.createElement('p'); c.className = 'quote'; c.textContent = 'Form and chart disagree: ' + el.dataset.conflict; viewer.append(c);
      const two = document.createElement('div'); two.className = 'pages2';
      two.append(pageEl(el.dataset.page, el.dataset.kind, 'This page'), pageEl(el.dataset.page2, el.dataset.kind2, 'Other page'));
      viewer.append(two);
    } else viewer.append(pageEl(el.dataset.page, el.dataset.kind, 'Source'));
  }
  items.forEach((el, i) => el.querySelector('button.open').addEventListener('click', () => show(i)));
  function verify(form) {
    const btn = form.querySelector('button');
    fetch('/fact/verify', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json' }, body: new URLSearchParams(new FormData(form)) })
      .then(r => r.json()).then(d => {
        btn.textContent = d.verified ? '✓ Verified' : 'Verify'; btn.setAttribute('aria-pressed', d.verified ? 'true' : 'false'); btn.classList.toggle('ghost', !d.verified);
        document.getElementById('vcount').textContent = d.count + ' of ' + d.total;
        if (status) status.textContent = (d.verified ? 'Marked verified. ' : 'Unmarked. ') + d.count + ' of ' + d.total + ' checked.';
      });
  }
  document.querySelectorAll('form.verify').forEach(f => f.addEventListener('submit', (e) => { e.preventDefault(); verify(f); }));
  document.addEventListener('keydown', (e) => {
    const t = e.target; if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
    if (t && t.closest && t.closest('#ask')) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === 'j') { e.preventDefault(); show(Math.min(items.length - 1, cur + 1)); }
    else if (k === 'k') { e.preventDefault(); show(Math.max(0, cur - 1)); }
    else if (k === 'v' && cur >= 0) { const f = items[cur].querySelector('form.verify'); if (f) { e.preventDefault(); verify(f); } }
    else if (k === 'o' && cur >= 0 && items[cur].dataset.page) { e.preventDefault(); window.open('/page/' + encodeURIComponent(rid) + '/' + items[cur].dataset.page, '_blank', 'noopener'); }
    else if (k === 'r') { const s = document.getElementById('reply-text'); if (s) { e.preventDefault(); s.focus(); } }
  });
})();
"""


def how():
    tiers = "".join(f"<li><strong>{t[0]} min</strong> · {esc(notify.AUDIENCE_LABEL[t[2]])}: {esc(t[4].format(rid='REF-…', n='N'))}</li>" for t in notify.TIERS)
    return page("How it works", f"""
<section><h2>How a referral moves, step by step</h2><ol class="steps">
<li><strong>It arrives</strong> by upload, fax (an email with the pages attached) or email, in any common format.</li>
<li><strong>The pre-read starts at once.</strong> Claude maps the pages, finds the 27 facts with page and quote, and a second look checks each quote is really on its page. Anything it can't confirm counts as unclear, not found.</li>
<li><strong>The to-do list fills in.</strong> Missing documents and facts become a request you send with one click. Possible red flags go straight to the clinical reviewer.</li>
<li><strong>You check the facts</strong> with each page beside its fact. Keyboard: J and K to move, V to verify, O to open the page, R to reply.</li>
<li><strong>The hospital resends pages?</strong> A fax that mentions the referral number joins the same referral. Only the new pages are read, and answered items close themselves.</li>
<li><strong>Complete packets get the fast lane:</strong> one screen to decide.</li>
<li><strong>A person decides.</strong> That stops all follow-ups and drafts the decision notice.</li></ol></section>
<section><h2>Messages to the hospital and the team</h2><ul>
<li><strong>Red flag:</strong> a possible red flag from the pre-read goes to the intake team (clinical reviewer) immediately. When a clinician confirms it, the hospital is told immediately. A red flag a person adds tells everyone at once.</li>
<li><strong>Missing items:</strong> sent when you press "Send request now". If nobody has, the 30-minute message sends the approved items.</li>
<li>Then on a timer:<ul>{tiers}</ul></li></ul>
<p class="small muted">Dry run only: every message is a file in <code>outbox/</code>. Messages carry the referral number, never a patient name.</p></section>
<section><h2>What the pre-read never does</h2><ul>
<li>Decide. It suggests; staff verify and decide.</li><li>Guess a date. Rules that need one say "can't tell".</li>
<li>Count a black box as missing. It's a redaction.</li><li>Use a rule ID that isn't in IHH's rules. Unknown IDs are dropped.</li>
<li>Send the hospital a request staff haven't approved.</li></ul></section>""")


# ---------------- request handling ----------------

def start_preread(rid, only_doc_ids=None):
    preread.run_in_background(con, rid, only_doc_ids)


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, to, cookie=None):
        self.send_response(303)
        self.send_header("Location", to)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass

    def _who(self):
        c = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        raw = c["anchor_user"].value if "anchor_user" in c else ""
        name, _, role = unquote(raw).partition("|")
        CURRENT["name"], CURRENT["role"] = name.strip()[:40], (role if role in ROLES else "")

    def do_GET(self):
        with store._lock:              # one request at a time on the shared connection
            self._who()
            return self._get()

    def do_POST(self):
        if urlparse(self.path).path == "/chat":
            return self._chat()
        with store._lock:
            self._who()
            return self._post()

    def _chat(self):
        """Ask Anchor. Uses its own database connection so a slow answer never blocks the rest of the app."""
        try:
            length = min(int(self.headers.get("Content-Length", 0) or 0), 64000)
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return self._send(json.dumps({"answer": "I couldn't read that question.", "mode": "built-in", "note": None}), 400, "application/json")
        own = store.connect()
        try:
            out = assistant.answer(own, data.get("question"), data.get("history"), data.get("screen"))
        finally:
            own.close()
        return self._send(json.dumps(out), ctype="application/json")

    def _get(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        flash = q.get("m", [""])[0]
        if u.path == "/":
            return self._send(home(flash))
        if u.path == "/todo":
            return self._send(todo_page(q.get("owner", [""])[0], flash))
        if u.path == "/how":
            return self._send(how())
        if u.path == "/upload":
            return self._send(upload_page(flash))
        if u.path.startswith("/r/"):
            rid = u.path[3:]
            if CURRENT["name"] and con.execute("SELECT 1 FROM referrals WHERE id=?", (rid,)).fetchone():
                store.log_activity(con, rid, CURRENT["name"], "opened it", kind="view", role=CURRENT["role"])
            return self._send(detail(rid, flash))
        if u.path.startswith("/page/"):
            parts = u.path.split("/")
            if len(parts) == 4 and parts[3].isdigit():
                row = con.execute("SELECT image_path FROM pages WHERE referral_id=? AND n=?", (parts[2], int(parts[3]))).fetchone()
                if row:
                    path = Path(row["image_path"]).resolve()
                    if store.WORK.resolve() in path.parents and path.exists():
                        if path.suffix == ".txt":
                            return self._send(path.read_text(errors="replace"), ctype="text/plain; charset=utf-8")
                        return self._send(path.read_bytes(), ctype="image/png" if path.suffix == ".png" else "image/jpeg")
            return self._send("Page not found", 404, "text/plain; charset=utf-8")
        if u.path.startswith("/msg/"):
            n = con.execute("SELECT * FROM notifications WHERE id=?", (u.path[5:],)).fetchone()
            if not n:
                return self._send(page("Not found", "<p>No such message.</p>"), 404)
            text = Path(n["outbox_path"]).read_text(errors="replace") if n["outbox_path"] and Path(n["outbox_path"]).exists() else n["body"]
            return self._send(page(n["subject"], f"<section><h2>{esc(n['subject'])}</h2><p><span class='dry'>Dry run: not sent</span> · {esc(n['tier'])}</p><pre class='msg'>{esc(text)}</pre><p><a href='/r/{esc(n['referral_id'])}'>Back to {esc(n['referral_id'])}</a></p></section>"))
        self._send(page("Not found", "<p>Page not found.</p>"), 404)

    def _post(self):
        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("multipart/form-data"):
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype})
            get = lambda k, d="": form.getvalue(k, d)
            getall = lambda k: form.getlist(k)
            items = form["files"] if "files" in form else []
            items = items if isinstance(items, list) else [items]
            files = [(i.filename, i.file.read()) for i in items if getattr(i, "filename", None)]
        else:
            length = int(self.headers.get("Content-Length", 0) or 0)
            data = parse_qs(self.rfile.read(length).decode("utf-8"))
            get = lambda k, d="": data.get(k, [d])[0]
            getall = lambda k: data.get(k, [])
            files = []
        p = urlparse(self.path).path
        back = lambda rid, m: self._redirect(f"/r/{rid}?m={quote(m)}")
        if p == "/me":
            name, role = get("name").strip()[:40], get("role")
            role = role if role in ROLES else ""
            ref = self.headers.get("Referer", "/")
            to = urlparse(ref).path if urlparse(ref).path.startswith("/") else "/"
            cookie = f"anchor_user={quote(name + '|' + role)}; Path=/; SameSite=Lax; Max-Age=86400"
            return self._redirect(to + "?m=" + quote(f"Working as {name}. Your actions will be recorded." if name else "Name cleared."), cookie)
        if p not in ("/advance",) and not CURRENT["name"]:
            to = "/r/" + get("rid") if get("rid") else ("/upload" if p == "/upload" else "/")
            return self._redirect(to + "?m=" + quote("Add your name at the top first, so the team can see who worked on what."))
        who, role = CURRENT["name"], CURRENT["role"]
        act = lambda rid, what: store.log_activity(con, rid, who, what, role=role)
        if p == "/upload":
            if not files:
                return self._redirect("/upload?m=" + quote("Choose at least one file to upload."))
            rid = ingest.create_referral(con, get("hospital").strip(), get("channel", "upload"), files)
            act(rid, f"uploaded {len(files)} file(s)")
            notify.tick(con)
            start_preread(rid)
            return back(rid, f"Received {len(files)} file(s). The pre-read has started; reload in a moment.")
        if p == "/add":
            rid = get("rid")
            ids = []
            for name, data_ in files:
                ids += [d["id"] for d in ingest.add_file(con, rid, name, data_, via="resend")]
            act(rid, f"added {len(files)} file(s)")
            start_preread(rid, ids)
            return back(rid, f"Added {len(files)} file(s). Reading the new pages.")
        if p == "/poll":
            res = faxmail.poll_inbox(con, on_new=start_preread, on_resend=start_preread)
            for rid_ in res["new"]:
                store.log_activity(con, rid_, "Fax inbox", f"arrived by fax (inbox checked by {who})", kind="system")
            for rid_ in res["resent"]:
                store.log_activity(con, rid_, "Fax inbox", f"hospital resent pages (inbox checked by {who})", kind="system")
            notify.tick(con)
            return self._redirect("/?m=" + quote(f"Fax inbox checked: {len(res['new'])} new referral(s), {len(res['resent'])} resend(s) added to open referrals."))
        if p == "/demo-resend":
            rid = get("rid")
            import make_samples
            if not (store.ROOT / "samples" / "sample-resend.pdf").exists():
                return back(rid, "Run make_samples.py first.")
            make_samples.make_resend(rid, store.INBOX)
            act(rid, "ran the demo resend")
            res = faxmail.poll_inbox(con, on_new=start_preread, on_resend=start_preread)
            return back(rid, f"The hospital resent pages ({len(res['resent'])} fax). Reading only the new pages; reload in a moment.")
        if p == "/preread":
            rid = get("rid")
            act(rid, "ran the pre-read again")
            start_preread(rid)
            return back(rid, "Pre-read started. Reload in a moment.")
        if p == "/fact/verify":
            rid, fid = get("rid"), get("fid")
            f = con.execute("SELECT * FROM facts WHERE id=? AND referral_id=?", (fid, rid)).fetchone()
            if f:
                if f["verified_at"]:
                    con.execute("UPDATE facts SET verified_at=NULL, verified_by=NULL WHERE id=?", (fid,))
                    act(rid, f"unmarked {rules.FACT_LABELS.get(f['key'], f['key'])}")
                else:
                    con.execute("UPDATE facts SET verified_at=?, verified_by=? WHERE id=?", (store.iso(store.now(con)), who, fid))
                    act(rid, f"verified {rules.FACT_LABELS.get(f['key'], f['key'])}")
                con.commit()
            best = rules.best_facts(con, rid)
            count = sum(1 for x in best.values() if x["verified_at"])
            if "application/json" in self.headers.get("Accept", ""):
                v = con.execute("SELECT verified_at FROM facts WHERE id=?", (fid,)).fetchone()
                return self._send(json.dumps({"verified": bool(v and v["verified_at"]), "count": count, "total": len(rules.FACT_KEYS)}), ctype="application/json")
            return back(rid, f"{count} of {len(rules.FACT_KEYS)} facts checked.")
        if p == "/request":
            rid = get("rid")
            n = notify.request_now(con, rid, getall("fids") or None)
            if n:
                act(rid, "sent the request for missing items")
            return back(rid, "Request written to the outbox (dry run). The 30- and 60-minute messages will be reminders." if n else "Nothing selected to request.")
        if p == "/redconfirm":
            sent = notify.confirm_red(con, get("fid"))
            act(get("rid"), "confirmed a red flag")
            return back(get("rid"), f"Red flag confirmed. {len(sent)} message(s) written right away, including the hospital.")
        if p == "/flag":
            rid = get("rid")
            try:
                _, sent = notify.add_flag(con, rid, get("type"), get("text"), get("rule_id"))
            except ValueError as e:
                return back(rid, f"Not added: {e}. Leave the rule ID blank or check it in the criteria.")
            act(rid, "added a red flag" if get("type") == "red" else "added a missing item")
            notify.tick(con)
            return back(rid, f"Red flag recorded. {len(sent)} immediate message(s) written." if get("type") == "red" else "Missing item added. Send it with the next request.")
        if p == "/resolve":
            note = get("note") or "Done"
            notify.resolve_flag(con, get("fid"), f"{note} ({who})")
            act(get("rid"), f"closed a to-do ({note.lower()})")
            return back(get("rid"), "Updated.")
        if p == "/reply":
            n = notify.reply(con, get("rid"), get("subject"), get("text"))
            if n:
                act(get("rid"), "replied to the hospital")
            return back(get("rid"), "Reply saved to the outbox (dry run)." if n else "Could not save the reply.")
        if p == "/decide":
            notify.decide(con, get("rid"), get("decision"))
            act(get("rid"), f"recorded the decision: {get('decision')}")
            return back(get("rid"), "Decision recorded. Follow-ups stopped; decision notice written to the outbox.")
        if p == "/advance":
            store.advance_clock(con, float(get("minutes", "15")))
            sent = notify.tick(con)
            return self._redirect("/?m=" + quote(f"Clock moved forward. {len(sent)} follow-up message(s) written."))
        self._send(page("Not found", "<p>Unknown action.</p>"), 404)


def ticker():
    while True:
        try:
            with store._lock:
                notify.tick(con)
        except Exception as e:  # keep the demo running; show the problem in the terminal
            print("tick error:", e)
        time.sleep(20)


if __name__ == "__main__":
    for d in (store.WORK, store.OUTBOX, store.INBOX):
        d.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=ticker, daemon=True).start()
    reader = preread.choose_reader()
    print(f"Referral intake running at http://{HOST}:{PORT}  (dry run: nothing is sent)")
    print("Pre-read:", reader.name if reader else "off. Set ANTHROPIC_API_KEY, or run make_samples.py for demo answers.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
