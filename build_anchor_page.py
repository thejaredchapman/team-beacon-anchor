"""Build ANCHOR.html: one self-contained page with everything about Anchor (Team Beacon).

Tabs: Overview (executive summary) · Board (made-up sample packets, click a packet for details) ·
Intake app · Checks (tests and verifier) · How it was built · About IHH · Presentation facts.
Re-run after any document changes:  python3 build_anchor_page.py
"""
import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "ANCHOR.html"
DASH = HERE / "triage-dashboard"


# ---------- tiny markdown to HTML (headings, lists, tables, code, bold, links) ----------

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1<span class="sr-only"> (opens in a new tab)</span></a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", s)          # local links: keep the text
    return s


def md(text):
    out, lines, i = [], text.splitlines(), 0
    list_stack = []

    def close_lists(to=0):
        while len(list_stack) > to:
            out.append(f"</li></{list_stack.pop()[0]}>")

    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            close_lists()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
            i += 1
            continue
        if ln.startswith("|"):
            close_lists()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                head, body = rows[0], rows[1:]
                out.append('<div class="tbl"><table><thead><tr>' + "".join(f'<th scope="col">{inline(c)}</th>' for c in head) + "</tr></thead><tbody>" +
                           "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", ln)
        if m:
            indent, marker, rest = len(m.group(1)), m.group(2), m.group(3)
            tag = "ol" if marker[0].isdigit() else "ul"
            level = indent // 2 + 1
            while list_stack and list_stack[-1][1] > level:
                out.append(f"</li></{list_stack.pop()[0]}>")
            if list_stack and list_stack[-1][1] == level:
                out.append("</li>")
            else:
                out.append(f"<{tag}>")
                list_stack.append((tag, level))
            out.append(f"<li>{inline(rest)}")
            i += 1
            continue
        if ln.strip() and list_stack and ln.startswith("   "):
            out.append(f"<p class='cont'>{inline(ln.strip())}</p>")
            i += 1
            continue
        close_lists()
        h = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if h:
            lvl = min(len(h.group(1)) + 1, 5)
            out.append(f"<h{lvl}>{inline(h.group(2))}</h{lvl}>")
        elif ln.startswith(">"):
            out.append(f"<blockquote>{inline(ln.lstrip('> '))}</blockquote>")
        elif ln.strip() in ("---", "***"):
            out.append("<hr>")
        elif ln.strip():
            para = [ln.strip()]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||\s*([-*]|\d+\.)\s|>|```|---)", lines[i + 1]):
                i += 1
                para.append(lines[i].strip())
            out.append(f"<p>{inline(' '.join(para))}</p>")
        i += 1
    close_lists()
    return "\n".join(out)


def doc(name):
    p = HERE / name
    return md(p.read_text()) if p.exists() else f"<p>{html.escape(name)} not found.</p>"


# ---------- live facts: tests and verifier ----------

def test_summary():
    r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=HERE / "intake-pipeline",
                       capture_output=True, text=True, timeout=600)
    tail = (r.stderr or r.stdout).strip().splitlines()
    ran = next((l for l in tail if l.startswith("Ran ")), "Ran ? tests")
    ok = "OK" in tail[-1] if tail else False
    return {"ran": ran, "ok": ok, "when": datetime.now().strftime("%Y-%m-%d %H:%M")}


# The verifier's reports stay local (they may describe real packets), so this page shows only their outcome.
VERIFY_STATUS = [
    ("First check", "FAIL: one rule break and six wrong facts (test counts, out-of-date status, unreadable faxes, unchecked rule IDs, README gaps). The main fixes were made."),
    ("Re-check", "FAIL: the earlier fixes held, but this page copied a report that described a real packet, and the privacy wording was wrong. Fixed: reports no longer copied, privacy wording corrected, sample packets rewritten from scratch."),
    ("Final check", "PASS WITH FIXES: no P0 or P1 items."),
    ("Boards and local server check", "FAIL: the local server served some blocked files when asked in a different letter case. Fixed (allowlist and host check); the re-check passed with fixes."),
    ("Page check", "FAIL on wording: red-flag routing, the grade score, and two source details. Fixed, along with the smaller wording and accessibility items."),
]


# ---------- page ----------

CSS = """
:root{--bg:#f5f7f8;--panel:#fff;--ink:#13222b;--muted:#4c5d67;--line:#d4dde1;--accent:#0d6b67;--accent-ink:#fff;--soft:#eaf3f2;--bad:#a4261d;--warn:#8a5300;--ok:#1d6b34}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f171b;--panel:#16232a;--ink:#e6eef1;--muted:#a6b7bf;--line:#2b3c45;--accent:#5cc2bb;--accent-ink:#062523;--soft:#173332;--bad:#f19387;--warn:#f0b660;--ok:#86d39c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f171b;--panel:#16232a;--ink:#e6eef1;--muted:#a6b7bf;--line:#2b3c45;--accent:#5cc2bb;--accent-ink:#062523;--soft:#173332;--bad:#f19387;--warn:#f0b660;--ok:#86d39c;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--accent)}:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
.skip{position:absolute;left:-9999px}.skip:focus{left:12px;top:12px;background:var(--panel);padding:6px 10px;border:2px solid var(--ink);z-index:9}
header.top{background:var(--panel);border-bottom:1px solid var(--line);padding:14px max(16px,4vw) 0}
header.top h1{margin:0;font-size:1.6rem}header.top p{margin:2px 0 10px;color:var(--muted)}
.tabs{display:flex;flex-wrap:wrap;gap:2px}.tabs button{all:unset;cursor:pointer;padding:10px 14px;min-height:24px;border-bottom:3px solid transparent;color:var(--muted)}
.tabs button[aria-selected=true]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}.tabs button:focus-visible{outline:3px solid var(--ink)}
main{max-width:78rem;margin:0 auto;padding:20px max(16px,4vw) 60px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px;min-width:0}
.prose{max-width:72ch}.prose h2{font-size:1.5rem;margin:.2em 0 .4em}.prose h3{font-size:1.2rem;margin:1.2em 0 .4em}.prose h4{margin:1em 0 .3em}
.prose li{margin:2px 0}.prose p.cont{margin:.2em 0 .2em 1.3em}
blockquote{margin:.6em 0;padding:8px 12px;border-left:4px solid var(--accent);background:var(--soft)}
.tbl{overflow-x:auto;margin:.6em 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}th{background:var(--soft)}
pre{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:10px;overflow-x:auto;font-size:13px}code{font-size:.92em}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:0 8px;font-size:13px;white-space:nowrap}
.pill.ok{color:var(--ok)}.pill.warn{color:var(--warn)}.pill.bad{color:var(--bad)}.pill.p1{color:var(--bad);border-color:var(--bad)}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))}
.tile .n{font-size:1.9rem;font-weight:700;line-height:1.1}.tile .l{font-size:14px;color:var(--muted)}
.two{display:grid;gap:16px;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}@media (max-width:860px){.two{grid-template-columns:1fr}}
.stack{display:grid;gap:16px}
button.link{all:unset;cursor:pointer;color:var(--accent);text-decoration:underline;font-weight:600}button.link:focus-visible{outline:3px solid var(--ink)}
tr[aria-current=true] td,tr[aria-current=true] th{background:var(--soft)}
.note{font-size:14px;color:var(--muted)}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;border:1px dashed var(--warn);color:var(--warn);font-size:13px}
.ok-txt{color:var(--ok)}.bad-txt{color:var(--bad)}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
.team{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}.team li{margin:0}
.chat{margin-top:16px}.chat-log{max-height:340px;overflow:auto;display:flex;flex-direction:column;gap:8px;margin:8px 0}.chat-log:empty{display:none}
.msg{padding:8px 12px;border-radius:10px;border:1px solid var(--line);max-width:46rem;white-space:pre-wrap}.msg.user{align-self:flex-end;background:var(--soft)}.msg.bot{background:var(--panel)}
.msg .who{display:block;font-size:12px;color:var(--muted);font-weight:600}.chips{display:flex;flex-wrap:wrap;gap:6px}.chips button{font:inherit;font-size:14px;padding:6px 10px;border-radius:999px;border:1px solid var(--muted);background:var(--panel);color:var(--ink);cursor:pointer;min-height:32px}
.row{display:flex;gap:8px;flex-wrap:wrap}.row input{flex:1 1 220px;font:inherit;padding:8px 10px;border:1px solid var(--muted);border-radius:8px;background:var(--panel);color:var(--ink);min-height:40px}
.row button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--accent-ink);cursor:pointer;min-height:40px}#ask-stop{background:var(--panel);color:var(--ink)}
header.top{position:relative}.menu-wrap{position:absolute;right:max(16px,4vw);top:14px;z-index:5}
.menu-btn{font:inherit;min-height:44px;padding:8px 14px;border-radius:8px;border:1px solid var(--muted);background:var(--panel);color:var(--ink);cursor:pointer}
.menu{position:absolute;right:0;top:calc(100% + 6px);margin:0;padding:6px;list-style:none;min-width:230px;background:var(--panel);border:1px solid var(--muted);border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.18)}
.menu button{all:unset;box-sizing:border-box;display:block;width:100%;min-height:44px;padding:10px 12px;border-radius:6px;cursor:pointer;color:var(--ink)}.menu button:hover,.menu button:focus-visible{background:var(--soft);outline:2px solid var(--ink)}
header.top h1{padding-right:120px}
dialog#b-dialog{width:min(920px,calc(100vw - 24px));max-height:calc(100vh - 32px);padding:0;border:1px solid var(--muted);border-radius:12px;background:var(--panel);color:var(--ink)}
dialog#b-dialog::backdrop{background:rgba(0,0,0,.45)}#b-detail{padding:4px 18px 18px}
.dlg-bar{position:sticky;top:0;display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 18px;background:var(--panel);border-bottom:1px solid var(--line);z-index:1}
.ghost{font:inherit;min-height:44px;padding:8px 14px;border-radius:8px;border:1px solid var(--muted);background:var(--panel);color:var(--ink);cursor:pointer}
.kbd{display:inline-block;padding:0 6px;border:1px solid var(--muted);border-radius:4px;font-size:.9em}
.chips button[aria-disabled=true],.row button[aria-disabled=true]{opacity:.6;cursor:progress}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.foot{max-width:1100px;margin:24px auto;padding:0 16px;color:var(--muted);font-size:14px}
@media print{.tabs,.skip{display:none}section[hidden]{display:block!important}}
"""

BOARD_JS = r"""
(function () {
  const D = window.ANCHOR_DATA;
  const el = (t, p, k) => { const e = Object.assign(document.createElement(t), p || {}); (k || []).forEach((x) => e.append(x)); return e; };
  const pill = (text, cls) => el('span', { className: 'pill ' + (cls || ''), textContent: text });
  function grade(p) {
    const pct = Math.round(100 * (2 * p.facts_found + p.facts_unclear + p.facts_cant_tell) / (2 * p.facts_applicable));
    let g = 'Neutral', why = 'Score 60-84% or conflicts to settle';
    if (p.critical_alerts > 0) { g = 'Bad'; why = 'Critical alert'; }
    else if (p.required_docs_present < 7) { g = 'Bad'; why = 'Core document missing'; }
    else if (pct < 60) { g = 'Bad'; why = 'Score under 60%'; }
    else if (pct >= 85 && p.contradictions === 0) { g = 'Great'; why = '85%+ and no conflicts'; }
    return { pct, g, why };
  }
  function clock(p) { return p.status === 'Decided' ? 'Answered' : (p.minutes_open <= 90 ? 'On time' : (p.minutes_open <= 120 ? 'At risk' : 'Late')); }
  function priority(p, prof) {
    const c = clock(p);
    const pts = { discharge: prof.discharge === 'Today' ? 3 : (prof.discharge === 'Tomorrow' ? 2 : 0), clock: c === 'Late' ? 3 : (c === 'At risk' ? 2 : 0),
      housing: prof.housing === 'Unhoused' ? 1 : 0, need: Number(prof.high_need) === 1 ? 1 : 0, recent: prof.recent_episode === 'Yes' ? 1 : 0 };
    const score = pts.discharge + pts.clock + pts.housing + pts.need + pts.recent;
    const level = p.status === 'Decided' ? 'Done' : (score >= 6 ? 'P1 Urgent' : (score >= 3 ? 'P2 High' : 'P3 Routine'));
    return { pts, score, level };
  }
  const cls = { Great: 'ok', Neutral: 'warn', Bad: 'bad', 'On time': 'ok', 'At risk': 'warn', Late: 'bad', Answered: '' };
  const pcls = (l) => l.startsWith('P1') ? 'p1' : (l.startsWith('P2') ? 'warn' : '');
  const prof = Object.fromEntries(D.profiles.map((x) => [x.packet_id, x]));
  const rows = D.packets.map((p) => ({ p, gr: grade(p), c: clock(p), pr: priority(p, prof[p.packet_id] || {}) }))
    .sort((a, b) => ((b.pr.level === 'Done' ? -1 : b.pr.score) - (a.pr.level === 'Done' ? -1 : a.pr.score)) || (b.p.minutes_open - a.p.minutes_open));
  const counts = { Great: 0, Neutral: 0, Bad: 0 }; rows.forEach((r) => counts[r.gr.g]++);
  const waiting = rows.filter((r) => r.p.status !== 'Decided').length, risk = rows.filter((r) => r.c === 'At risk' || r.c === 'Late').length;
  document.getElementById('b-tiles').replaceChildren(...[['Packets waiting', waiting, ''], ['At risk or late', risk, 'bad-txt'], ['Great', counts.Great, 'ok-txt'], ['Neutral', counts.Neutral, ''], ['Bad', counts.Bad, 'bad-txt']]
    .map(([l, n, c]) => el('div', { className: 'panel tile' }, [el('div', { className: 'n ' + c, textContent: String(n) }), el('div', { className: 'l', textContent: l })])));
  const tb = document.getElementById('b-queue');
  tb.replaceChildren(...rows.map((r) => {
    const b = el('button', { type: 'button', className: 'link', textContent: r.p.packet_id }); b.setAttribute('aria-label', 'Open details for ' + r.p.packet_id);
    b.addEventListener('click', () => show(r.p.packet_id, b));
    const tr = el('tr'); tr.dataset.key = r.p.packet_id;
    tr.append(el('th', { scope: 'row' }, [b]), el('td', {}, [pill(r.pr.level, pcls(r.pr.level))]), el('td', {}, [pill(r.c + (r.c === 'Answered' ? '' : ' · ' + r.p.minutes_open + ' min'), cls[r.c])]),
      el('td', {}, [pill(r.gr.g, cls[r.gr.g])]), el('td', { textContent: r.gr.pct + '%' }), el('td', { textContent: String(D.alerts.filter((a) => a.packet_id === r.p.packet_id).length) }));
    return tr;
  }));
  const verb = { 'Critical': 'Clinical review', 'Missing document': 'Get', 'Missing fact': 'Find', 'Contradiction': 'Settle', "Can't tell": 'Confirm with hospital', 'Rule gap': 'Coordinator decides' };
  function table(caption, heads, data) {
    return el('div', { className: 'tbl' }, [el('table', {}, [el('caption', { className: 'note', textContent: caption }), el('thead', {}, [el('tr', {}, heads.map((h) => el('th', { scope: 'col', textContent: h })))]),
      el('tbody', {}, data.length ? data.map((r) => el('tr', {}, r.map((c) => el('td', {}, [typeof c === 'string' ? document.createTextNode(c) : c])))) : [el('tr', {}, [el('td', { colSpan: heads.length, textContent: 'None.' })])])])]);
  }
  const dlg = document.getElementById('b-dialog'); let opener = null;
  function select(id) {
    window.ANCHOR_BOARD.current = id;
    document.querySelectorAll('#b-queue tr').forEach((tr) => tr.setAttribute('aria-current', tr.dataset.key === id ? 'true' : 'false'));
    if (window.ANCHOR_BOARD.onSelect) window.ANCHOR_BOARD.onSelect(id);
  }
  // Packet details open in a pop-up; Esc or Close returns focus to the packet that opened it
  function show(id, from) {
    select(id); opener = from || null;
    const r = rows.find((x) => x.p.packet_id === id), f = prof[id] || {};
    const box = document.getElementById('b-detail'); box.replaceChildren();
    const h = el('h2', { id: 'b-dialog-title', textContent: id + ' · ' + r.p.hospital, tabIndex: -1 });
    box.append(h, el('p', {}, [pill(r.pr.level, pcls(r.pr.level)), ' ', pill('Grade: ' + r.gr.g + ' (' + r.gr.pct + '%)', cls[r.gr.g]), ' ', pill(r.c, cls[r.c])]));
    box.append(el('h3', { textContent: 'Summary' }), el('p', { textContent: f.summary || '' }));
    const miss = D.alerts.filter((a) => a.packet_id === id);
    box.append(el('h3', { textContent: 'Key missing information' }), table('Do these first', ['To do', 'What', 'Page', 'Rule'], miss.map((a) => [pill(verb[a.type] || a.type, a.type === 'Critical' ? 'bad' : 'warn'), a.what, a.page, a.rule_id])));
    const P = r.pr.pts;
    box.append(el('h3', { textContent: 'Priority (by patient need)' }), table('P1 is 6+ points, P2 3-5, P3 2 or less', ['Factor', 'This packet', 'Points'],
      [['Expected discharge', f.discharge || '', '+' + P.discharge], ['Answer clock', r.c, '+' + P.clock], ['Housing', f.housing || '', '+' + P.housing], ['High care need', f.care_needs || '', '+' + P.need], ['Recent repeat episode', f.recent_episode || '', '+' + P.recent], ['Total', r.pr.level, String(r.pr.score)]]));
    box.append(el('h3', { textContent: 'Patient details (made up)' }), table('Real packets show black boxes (redacted) for name and address', ['Name', 'Address', 'Allergies', 'Blood type'], [[f.patient_name || '', f.address || '', f.allergies || '', f.blood_type || '']]));
    const fax = 'triage-dashboard/faxes/' + id + '-original-fax.pdf';
    box.append(el('h3', { textContent: 'Original fax (mock PDF)' }), el('p', {}, [el('a', { href: fax, target: '_blank', rel: 'noopener', textContent: 'Open ' + id + ' mock fax (one page per section, PDF, opens in a new tab)' })]));
    box.append(el('h3', { textContent: 'Email log' }), table('Made-up log, times to the second. The tool itself sends nothing.', ['Time', 'Direction', 'Channel', 'Subject', 'Status'], D.emails.filter((e) => e.packet_id === id).map((e) => [e.time, e.direction, e.channel, e.subject, e.status])));
    box.append(el('h3', { textContent: 'The packet, page by page' }), table('', ['Pages', 'Document', 'What it shows'], D.pages.filter((p) => p.packet_id === id).map((p) => [p.page_from === p.page_to ? 'p. ' + p.page_from : 'pp. ' + p.page_from + '-' + p.page_to, p.doc_type, p.key_content])));
    box.append(el('h3', { textContent: 'Medications' }), table('', ['Medicine', 'Dose', 'How often', 'Self-gives?', 'For', 'Page'], D.meds.filter((m) => m.packet_id === id).map((m) => [m.medicine, m.dose, m.how_often, m.self_administers, m.purpose, 'p. ' + m.page])));
    box.append(el('h3', { textContent: 'Medical history and recent episodes' }), table('', ['Condition', 'Status', 'Recent?', 'Page'], D.history.filter((x) => x.packet_id === id).map((x) => [x.condition, x.status, x.recent, 'p. ' + x.page])),
      el('p', { className: 'note', textContent: 'Has this happened recently? ' + (f.recent_episode || '') + '. ' + (f.recent_note || '') }));
    if (dlg.showModal) { if (!dlg.open) dlg.showModal(); } else dlg.setAttribute('open', '');
    document.getElementById('b-dialog').scrollTop = 0; h.focus();
  }
  function closeDialog() { if (dlg.close) dlg.close(); else dlg.removeAttribute('open'); }
  dlg.addEventListener('close', () => { if (opener) opener.focus(); });
  document.getElementById('b-dialog-close').addEventListener('click', closeDialog);
  dlg.addEventListener('click', (e) => { if (e.target === dlg) closeDialog(); });
  window.ANCHOR_BOARD = { rows, prof, verb, current: null, show };
  if (rows.length) select(rows[0].p.packet_id);
})();
"""

ASK_JS = r"""
(function () {
  const B = window.ANCHOR_BOARD, RULES = new Set(window.ANCHOR_RULE_IDS || []);
  if (!B) return;
  const $ = (id) => document.getElementById(id);
  const log = $('ask-log'), form = $('ask-form'), q = $('ask-q'), send = $('ask-send'), stop = $('ask-stop'), mode = $('ask-mode'), cur = $('ask-current');
  // Any rule-like ID with one of IHH's prefixes, in any case or spacing (DOC 12, doc-12, DOC-1a), must be a real rule
  const PREFIXES = [...new Set([...RULES].map((r) => r.split('-')[0]))].sort((a, b) => b.length - a.length);
  const RULE_RE = new RegExp('\\b(' + PREFIXES.join('|') + ')[-\\s]?([A-Z]{0,2}\\d{1,3}[A-Z]?)\\b', 'gi');
  const ANY_ID = /\b[A-Z]{2,5}-[A-Z]{0,2}\d{1,3}[A-Z]?\b/g;   // made-up prefixes too (ZZZ-9)
  const NOT_RULES = new Set(['COVID-19', 'ICD-10', 'ICD-9', 'HIV-1', 'HIV-2', 'TYPE-1', 'TYPE-2', 'SARS-2']);
  // Any wording that reads as an admission decision. Over-catching is fine: the built-in answer shows instead
  const DECIDES = /\bqualif(y|ies|ied|ying)\b|\b(in)?eligible\b|\bshould (not )?be (accepted|admitted|denied|approved|rejected|declined)\b|\bcan(not|'t)? be (admitted|accepted)\b|\bmeets? (all )?(of )?(the |IHH'?s? )?(admission )?criteria\b|\b(approve|deny|accept|admit|reject) (this|the) (patient|referral|packet)\b|\b(is|are|was|be|been) (approved|denied|accepted|admitted|rejected)\b|\b(should|must|will|can|could) (not )?(admit|accept|approve|deny|reject)\b|\b(meets?|satisf(y|ies)) (every|each|all)\b|^\s*(accept|admit|approve|deny|reject)\b/im;
  const GUIDE = [
    'ANCHOR BOARD GUIDE. Team Beacon prototype for Illumination Health + Home (IHH) recuperative care referral intake. All packets on this board are MADE UP. The board sends no messages to hospitals.',
    'Queue: sorted by priority (patient need), then time waiting. Clicking a packet opens its details in a pop-up: summary, key missing information, priority points, made-up patient details, mock fax PDF, email log, page map, medications, history.',
    'Grade is completeness, never eligibility. Fact score = (2 x found + unclear + can\'t tell) / (2 x facts that apply). Great = all 7 core documents, score 85%+, no conflicts. Bad = a critical alert, a missing core document, or score under 60%. Neutral = everything else.',
    'Priority points: discharge today +3 (tomorrow +2); answer clock Late +3 (At risk +2); unhoused +1; high care need +1; recent repeat episode +1. P1 Urgent is 6+, P2 High 3-5, P3 Routine 2 or less. Decided packets are Done.',
    'Answer clock (IHH answers hospitals within 2 hours): On time up to 90 minutes, At risk from 91 to 120, Late after 120.',
    'To-do verbs: Critical = Clinical review; Missing document = Get; Missing fact = Find; Contradiction = Settle (open both pages and decide which is right; Anchor\'s default is to trust the chart over the form, a team choice, not an IHH rule); Can\'t tell = Confirm with hospital (dates are redacted); Rule gap = Coordinator decides.',
    'Black boxes in real packets mean redacted for privacy, never missing. A person always decides; the board never approves or denies.'
  ].join('\n');
  function packetText(id) {
    const r = B.rows.find((x) => x.p.packet_id === id); if (!r) return 'No packet selected.';
    const f = B.prof[id] || {}, D = window.ANCHOR_DATA, P = r.pr.pts;
    const al = D.alerts.filter((a) => a.packet_id === id).map((a) => '- ' + (B.verb[a.type] || a.type) + ': ' + a.what + ' (rule ' + a.rule_id + ', ' + a.page + ')');
    return ['SELECTED PACKET ' + id + ' from ' + r.p.hospital + ' (made up). Status: ' + r.p.status + '.',
      'Grade: ' + r.gr.g + ', fact score ' + r.gr.pct + '% (' + r.gr.why + '). Core documents present: ' + r.p.required_docs_present + ' of 7' + (r.p.missing_docs ? ', missing: ' + r.p.missing_docs : '') + '.',
      'Facts: ' + r.p.facts_found + ' found, ' + r.p.facts_unclear + ' unclear, ' + r.p.facts_cant_tell + ' can\'t tell, ' + r.p.facts_missing + ' missing, of ' + r.p.facts_applicable + ' that apply.',
      'Priority: ' + r.pr.level + ', ' + r.pr.score + ' points (discharge ' + (f.discharge || '?') + ' +' + P.discharge + ', clock ' + r.c + ' +' + P.clock + ', housing ' + (f.housing || '?') + ' +' + P.housing + ', high care need +' + P.need + ', recent repeat episode ' + (f.recent_episode || '?') + ' +' + P.recent + ').',
      'Answer clock: ' + r.c + ', ' + r.p.minutes_open + ' minutes open.', 'Summary: ' + (f.summary || ''), 'To-dos:', ...(al.length ? al : ['- none'])].join('\n');
  }
  function queueText() { return 'QUEUE: ' + B.rows.map((r) => r.p.packet_id + ' ' + r.pr.level + ' ' + r.gr.g + ' ' + r.c).join('; '); }
  // Built-in answers: used when Claude is not available here, and as the safe fallback
  function builtin(text) {
    const t = text.toLowerCase(), id = B.current, r = B.rows.find((x) => x.p.packet_id === id), D = window.ANCHOR_DATA;
    const al = r ? D.alerts.filter((a) => a.packet_id === id) : [];
    const order = ['Critical', 'Contradiction', 'Missing document', 'Missing fact', "Can't tell", 'Rule gap'];
    if (/qualif|eligib|accept|admit|approve|deny|denied|reject/.test(t)) return 'I can\'t say whether a patient qualifies. A person at IHH decides. I can explain the grade, the priority, or the to-do list for ' + (id || 'the selected packet') + '.';
    if (/first|next|do now|to.?do|missing|need/.test(t) && r) {
      if (!al.length) return id + ' has nothing open. ' + (r.gr.g === 'Great' ? 'It is Great: everything needed is there, so a person can decide.' : 'Check the grade, then decide.');
      const s = al.slice().sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type));
      return 'For ' + id + ', in this order:\n' + s.map((a, i) => (i + 1) + '. ' + (B.verb[a.type] || a.type) + ': ' + a.what + ' (' + a.page + ', rule ' + a.rule_id + ')').join('\n') + '\nNext: start with item 1 (' + (B.verb[s[0].type] || s[0].type).toLowerCase() + ').';
    }
    if (/grade|great|neutral|bad|score|percent|%/.test(t)) return 'The grade is about completeness, never eligibility. Fact score = (2 x found + unclear + can\'t tell) / (2 x facts that apply). Great: all 7 core documents, 85%+, no conflicts. Bad: a critical alert, a missing core document, or under 60%. Neutral: everything else.' + (r ? '\n' + id + ' is ' + r.gr.g + ' at ' + r.gr.pct + '% (' + r.gr.why + ').' : '');
    if (/priorit|p1|p2|p3|urgent|points|order|sort/.test(t)) return 'Priority is by patient need: discharge today +3 (tomorrow +2), clock Late +3 (At risk +2), unhoused +1, high care need +1, recent repeat episode +1. P1 is 6+, P2 is 3-5, P3 is 2 or less.' + (r ? '\n' + id + ' is ' + r.pr.level + ' with ' + r.pr.score + ' points.' : '');
    if (/clock|time|late|risk|2.?hour|minute/.test(t)) return 'IHH promises hospitals an answer within 2 hours. The clock is On time up to 90 minutes, At risk from 91 to 120, and Late after 120.' + (r ? '\n' + id + ' is ' + r.c + ' at ' + r.p.minutes_open + ' minutes.' : '');
    if (/fast.?lane/.test(t)) return 'In the intake app, a Great packet with nothing flagged gets the fast lane: one screen for a person to decide. Anchor never decides.';
    if (/red flag|critical|exclu/.test(t)) return 'A critical alert means a rule that would exclude the patient looks true. Someone clinical should read that page first. It is a question to check, not a decision.';
    if (/settle|conflict|contradict|disagree/.test(t)) return 'A contradiction means the form and the chart disagree. Open both pages and decide which is right. Anchor\'s default is to trust the chart over the form; that is a team choice, not an IHH rule.';
    if (/can.?t tell|date|redact|black/.test(t)) return 'Dates are redacted in the packets, so rules that need a date say "can\'t tell". Confirm those with the hospital. A black box means redacted for privacy, never missing.';
    if (/real|privacy|patient|data|fake|made.?up/.test(t)) return 'Every packet on this board is made up, and the board sends no messages to hospitals. When Claude answers, your question and this made-up board data go to Claude.';
    if (/fax|pdf|email|log/.test(t)) return 'Each packet has a mock fax PDF (one page per section) and an email log. The log is made up; the board sends nothing.';
    return 'I can explain the grade, the priority, the answer clock, the to-do list, or what to do first for ' + (id ? id : 'the selected packet') + '. Try one of the suggested questions.';
  }
  function add(role, text) {
    const m = document.createElement('div'); m.className = 'msg ' + role;
    const w = document.createElement('span'); w.className = 'who'; w.textContent = role === 'user' ? 'You' : 'Anchor';
    const b = document.createElement('span'); b.textContent = text; m.append(w, b); log.append(m); log.scrollTop = log.scrollHeight; return b;
  }
  const turns = []; let sample = null, local = false, ctl = null, busy = false;
  const OFF = new Set(['not_granted', 'sampling_disabled', 'not_declared', 'capability_disabled', 'capability_removed', 'session_expired']);
  function setMode() {
    mode.textContent = sample ? 'Answers by Claude, using your own Claude account; your first question asks your permission. Your question and this made-up board data go to Claude.'
      : local ? 'Answers by Claude through the local board server on this computer. Your question and this made-up board data go to Claude.' : 'Built-in answers (Claude is not available on this copy of the page).';
  }
  function setCurrent() { cur.textContent = B.current ? 'Selected packet: ' + B.current + '.' : ''; }
  B.onSelect = setCurrent; setCurrent();
  async function localAsk(msgs, signal) {
    const r = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: msgs }), signal });
    if (!r.ok) throw { code: r.status === 503 ? 'unavailable' : 'upstream_error' };
    return (await r.json()).text || '';
  }
  setMode();
  if (window.claude && typeof window.claude.use === 'function') {
    window.claude.use('sample').then((fn) => { sample = fn || null; setMode(); }).catch(() => {});
  } else if (/^https?:$/.test(location.protocol)) {
    fetch('/api/ask/status').then((r) => (r.ok ? r.json() : null)).then((j) => { local = !!(j && j.available); setMode(); }).catch(() => {});
  }
  // Returns the text if it is safe to show, else null
  function guarded(text) {
    const ids = [...(text || '').matchAll(RULE_RE)].map((m) => m[1].toUpperCase() + '-' + m[2].toUpperCase())
      .concat(((text || '').match(ANY_ID) || []).filter((x) => !NOT_RULES.has(x)));
    if (ids.some((x) => !RULES.has(x))) return null;
    if (DECIDES.test(text || '')) return null;
    return text;
  }
  const NOTE = '\n(Claude\'s answer did not pass Anchor\'s checks, so here is the built-in answer.)';
  function setBusy(on) {
    busy = on; log.setAttribute('aria-busy', String(on)); send.setAttribute('aria-disabled', String(on));
    document.querySelectorAll('#ask-chips button').forEach((b) => b.setAttribute('aria-disabled', String(on)));
  }
  async function ask(question) {
    if (busy || !question.trim()) return;
    setBusy(true); add('user', question);
    const out = add('bot', 'Thinking...');
    if (!sample && !local) { out.textContent = builtin(question); turns.push({ role: 'user', content: question }, { role: 'assistant', content: out.textContent }); setBusy(false); return; }
    const context = GUIDE + '\n\n' + queueText() + '\n\n' + packetText(B.current);
    const instr = 'You are "Ask the board", the helper on IHH\'s Anchor Board. Answer ONLY from the guide and board data below. If the answer is not there, say you can only help with this board. Never give medical, clinical, legal or eligibility advice and never say whether a patient qualifies; a person decides. Never invent facts, pages, rule IDs or numbers; use only those in the data. Plain words, 1 to 4 short sentences, no markdown. When useful, end with "Next:" and one action.\n\n' + context;
    const msgs = turns.slice(-6).concat([{ role: 'user', content: instr + '\n\nQUESTION: ' + question }]);
    ctl = new AbortController(); stop.hidden = false;
    // While streaming, only show text that already passes the checks
    const onText = ({ text }) => { const ok = guarded(text); out.textContent = ok === null ? 'Thinking...' : ok; };
    try {
      const text = sample ? (await sample(msgs, { modelTier: 'quick', cache: false, signal: ctl.signal, onText })).text : await localAsk(msgs, ctl.signal);
      const ok = guarded(text || '');
      out.textContent = ok || builtin(question) + NOTE;
      turns.push({ role: 'user', content: question }, { role: 'assistant', content: out.textContent });
    } catch (e) {
      const code = e && e.code;
      if (code === 'cancelled' || (e && e.name === 'AbortError')) { const ok = guarded(e.text || ''); out.textContent = ok ? ok + ' (stopped)' : 'Stopped.'; }
      else if (OFF.has(code) || code === 'unavailable') { sample = null; local = false; setMode(); out.textContent = builtin(question); }
      else if (code === 'rate_limited') { out.textContent = 'Claude is busy right now. Here is the built-in answer:\n' + builtin(question); }
      else { out.textContent = builtin(question); }
    } finally { setBusy(false); stop.hidden = true; ctl = null; }
  }
  form.addEventListener('submit', (e) => { e.preventDefault(); if (busy) return; const v = q.value; q.value = ''; ask(v); });
  stop.addEventListener('click', () => { if (ctl) ctl.abort(); });
  ['What should I do first for this packet?', 'What does the grade mean?', 'Why is this packet this priority?', 'What does the answer clock mean?']
    .forEach((t) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = t; b.addEventListener('click', () => { if (!busy) ask(t); }); $('ask-chips').append(b); });
})();
"""

TABS_JS = r"""
(function () {
  const tabs = [...document.querySelectorAll('.tabs [role=tab]')];
  const panels = () => document.querySelectorAll('main > section');
  // Show a tab panel or a menu panel; only real tabs get selected
  function show(id, focusPanel) {
    if (!document.getElementById(id)) id = 'overview';
    const isTab = tabs.some((t) => t.getAttribute('aria-controls') === id);
    tabs.forEach((t, i) => { const on = t.getAttribute('aria-controls') === id; t.setAttribute('aria-selected', String(on)); t.tabIndex = on || (!isTab && i === 0) ? 0 : -1; });
    panels().forEach((s) => { s.hidden = s.id !== id; });
    try { history.replaceState(null, '', '#' + id); } catch (e) { /* sandboxed frames may refuse; tabs still work */ }
    if (focusPanel) { const p = document.getElementById(id); window.scrollTo(0, 0); (p.querySelector('h2') ? (p.querySelector('h2').tabIndex = -1, p.querySelector('h2')) : p).focus(); }
  }
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => show(t.getAttribute('aria-controls')));
    t.addEventListener('keydown', (e) => {
      let j = null;
      if (e.key === 'ArrowRight') j = (i + 1) % tabs.length; else if (e.key === 'ArrowLeft') j = (i + tabs.length - 1) % tabs.length;
      else if (e.key === 'Home') j = 0; else if (e.key === 'End') j = tabs.length - 1;
      if (j !== null) { e.preventDefault(); tabs[j].focus(); tabs[j].click(); }
    });
  });
  document.querySelectorAll('a[data-tab]').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault(); const id = a.dataset.tab, tab = document.getElementById('tab-' + id);
    show(id, !tab); if (tab) { window.scrollTo(0, 0); tab.focus(); }
  }));
  // Menu button (menu pattern): Enter/Space/ArrowDown opens, arrows move, Esc or Tab closes
  const btn = document.getElementById('menu-btn'), list = document.getElementById('menu-list'), items = [...list.querySelectorAll('[role=menuitem]')];
  function openMenu(k) { list.hidden = false; btn.setAttribute('aria-expanded', 'true'); items[k || 0].focus(); }
  function closeMenu(refocus) { list.hidden = true; btn.setAttribute('aria-expanded', 'false'); if (refocus) btn.focus(); }
  btn.addEventListener('click', () => (list.hidden ? openMenu(0) : closeMenu(true)));
  btn.addEventListener('keydown', (e) => { if (e.key === 'ArrowDown') { e.preventDefault(); openMenu(0); } else if (e.key === 'ArrowUp') { e.preventDefault(); openMenu(items.length - 1); } });
  items.forEach((it, i) => {
    it.addEventListener('click', () => { closeMenu(false); show(it.dataset.open, true); });
    it.addEventListener('keydown', (e) => {
      let j = null;
      if (e.key === 'ArrowDown') j = (i + 1) % items.length; else if (e.key === 'ArrowUp') j = (i + items.length - 1) % items.length;
      else if (e.key === 'Home') j = 0; else if (e.key === 'End') j = items.length - 1;
      else if (e.key === 'Escape') { e.preventDefault(); closeMenu(true); return; } else if (e.key === 'Tab') { closeMenu(false); return; }
      if (j !== null) { e.preventDefault(); items[j].focus(); }
    });
  });
  document.addEventListener('click', (e) => { if (!list.hidden && !e.target.closest('.menu-wrap')) closeMenu(false); });
  show(location.hash.slice(1) || 'overview');
})();
"""


BOARD_URL = "https://claude.ai/artifact/NVUonEKc7TRXnVU9QafCVG"

# Team Beacon, shown sorted by last name.
TEAM = [
    ("Alan", "Zhang", "https://www.linkedin.com/in/alan-z/"),
    ("Nelson", "Navarrate", "https://www.linkedin.com/in/navnelson/"),
    ("Lei", "Lu", "https://www.linkedin.com/in/8leilu8/"),
    ("Jared", "Chapman", "https://www.linkedin.com/in/thejaredchapman/"),
]


# Every file Team Beacon made for Anchor, grouped. Paths are relative to this page.
FILES = [
    ("Start here and share", [
        ("START-HERE.md", "Map of everything, and what to share with whom"),
        ("EXECUTIVE-SUMMARY.md", "One-page executive summary"), ("EXECUTIVE-SUMMARY.pdf", "The same, as a printable PDF"),
        ("PRESENTATION-FACTS.md", "Sourced facts, demo script and judge Q&A"), ("HOW-THIS-WAS-BUILT.md", "Sources, steps, tools and checks"),
        ("ABOUT-IHH.md", "What IHH is and how it helps people and the community"), ("01-packet-triage-v2.md", "The referral intake plan"),
        ("ANCHOR.html", "This page"), ("build_anchor_page.py", "Builds this page"), ("board_server.py", "Runs this page locally with Claude behind Ask the board"), ("make_exec_summary_pdf.py", "Builds the executive summary PDF")]),
    ("Intake app", [
        ("intake-pipeline/README.md", "How to run and use the app"), ("intake-pipeline/server.py", "The app (local web server)"),
        ("intake-pipeline/make_samples.py", "Makes the made-up sample faxes"),
        ("intake-pipeline/pipeline/ingest.py", "Any-format upload and fax unpacking"), ("intake-pipeline/pipeline/faxmail.py", "Fax-to-email inbox"),
        ("intake-pipeline/pipeline/preread.py", "Claude pre-read with quote check"), ("intake-pipeline/pipeline/rules.py", "Grade, documents and to-dos from IHH's rules"),
        ("intake-pipeline/pipeline/notify.py", "2-hour message ladder and red flags (dry run)"), ("intake-pipeline/pipeline/guidance.py", "\"What to do next\""),
        ("intake-pipeline/pipeline/assistant.py", "Ask Anchor helper"), ("intake-pipeline/pipeline/claude.py", "Claude API client"),
        ("intake-pipeline/pipeline/store.py", "Database, demo clock and activity history")]),
    ("Tests", [
        ("intake-pipeline/tests/test_pipeline.py", "Formats, message ladder, red flags, unreadable files, rule IDs"),
        ("intake-pipeline/tests/test_preread.py", "Pre-read, grade, owners, resends, fast lane"), ("intake-pipeline/tests/test_assistant.py", "Ask Anchor"),
        ("intake-pipeline/tests/test_activity.py", "Who's working and the history"), ("intake-pipeline/tests/test_board_server.py", "Local board server: safe files, same-origin only, Claude call"), ("intake-pipeline/tests/test_claude_client.py", "Claude client fallback")]),
    ("IHH rules overlay", [
        ("criteria-overlay/README.md", "What the overlay adds"), ("criteria-overlay/admission-criteria.enriched.json", "All 155 rules with kind, dates, gaps, evidence, facts"),
        ("criteria-overlay/admission-criteria.overlay.json", "The overlay on its own"), ("criteria-overlay/admission-criteria-with-ids.md", "The criteria with rule IDs, readable"),
        ("criteria-overlay/childrens-admission-criteria.json", "Children's criteria (64 KID rules)"), ("criteria-overlay/build_overlay.py", "Builds the overlay"),
        ("criteria-overlay/build_childrens.py", "Builds the children's file"), ("criteria-overlay/score_against_decisions.py", "Held-out scorer"),
        ("criteria-overlay/ORGANIZER-NOTE.md", "Suggestions for the organizers")]),
    ("Anchor Board (made-up samples)", [
        ("triage-dashboard/index.html", "The board page"), ("triage-dashboard/make_faxes.py", "Makes the mock fax PDFs"),
        ("triage-dashboard/faxes/", "Mock fax PDFs"), ("triage-dashboard/sample-packets.json", "Sample packets"),
        ("triage-dashboard/sample-alerts.json", "Alerts"), ("triage-dashboard/sample-email-log.json", "Email log"),
        ("triage-dashboard/sample-meds.json", "Medications"), ("triage-dashboard/sample-history.json", "Medical history"),
        ("triage-dashboard/sample-pages.json", "Page maps"), ("triage-dashboard/sample-profiles.json", "Made-up patient details")]),
]


def everything():
    groups = "".join(f"<h3>{html.escape(g)}</h3><ul>" + "".join(
        f'<li><a href="{html.escape(p)}"><code>{html.escape(p)}</code></a>: {html.escape(d)}</li>' for p, d in items if (HERE / p).exists()) + "</ul>" for g, items in FILES)
    return f"""<div class="prose"><h2>Everything we made</h2>
<p>Links open the files from the <code>saturday-oct17-build</code> folder, so they work when this page is opened from that folder. Online: <a href="https://claude.ai/artifact/NVUonEKc7TRXnVU9QafCVG" target="_blank" rel="noopener">Anchor Board<span class="sr-only"> (opens in a new tab)</span></a>.</p>
{groups}
<p class="note">Not linked on purpose: <code>packet-review/</code> (work on the real packets stays local), and the app's <code>work/</code>, <code>outbox/</code> and <code>.env</code>.</p></div>"""


LOCAL_BOARD_URL = "http://127.0.0.1:8790/#board"

# The menu on the right of the header: guides and credits that aren't everyday tabs
MENU = [("grading", "How grading works"), ("staff", "Staff guide"), ("it", "IT guide"), ("built", "How it was built"), ("by", "Built by")]


def grading_guide():
    return """<div class="prose"><h2 id="grading-h">How grading works</h2>
<p>The grade says <strong>how complete and consistent a packet is</strong>. It never says whether the patient qualifies. A person always decides.</p>
<h3>Step 1: score the 27 facts</h3>
<ul><li><strong>Found</strong> (with a page): 2 points</li><li><strong>Unclear</strong>, or <strong>Can't tell</strong> (the rule needs a date, and dates are blacked out): 1 point</li>
<li><strong>Missing</strong>: 0 points</li><li><strong>Redacted</strong> (a black box): not counted. A black box is privacy, not a gap.</li></ul>
<p>Fact score = points ÷ (2 × facts that apply), shown as a percent.</p>
<h3>Step 2: pick the grade</h3>
<ul><li><strong>Great:</strong> all 7 core documents (IHH form, face sheet, CalOptima form/LOA/authorization (DOC-3), H&amp;P, vitals, medication list, PT/OT or nursing notes), a fact score of 85% or more, and no conflicts. Ready for a person to decide.</li>
<li><strong>Bad:</strong> any critical alert (a rule that would exclude the patient looks true), a missing core document, or a score under 60%. Call the hospital before deciding.</li>
<li><strong>Neutral:</strong> everything else. Request the specific items.</li></ul>
<h3>When a packet is incomplete</h3>
<p>A Neutral or Bad packet comes with a to-do list. Each item starts with what to do:</p>
<ul><li><strong>Clinical review:</strong> someone clinical reads the page before anything else.</li><li><strong>Get:</strong> ask the hospital for a missing document.</li>
<li><strong>Find:</strong> the document is there but the fact isn't. Look again or ask.</li><li><strong>Settle:</strong> the form and the chart disagree. Open both pages and decide which is right. Anchor's default is to trust the chart over the form; that is a team choice, not an IHH rule.</li>
<li><strong>Confirm with hospital:</strong> the rule needs a date we can't see.</li><li><strong>Coordinator decides:</strong> IHH's written rules don't settle it.</li></ul>
<h3>Priority: who to look at first</h3>
<p>Priority is about the patient's need, not completeness: discharge today +3 (tomorrow +2), answer clock Late +3 (At risk +2), unhoused +1, high care need +1, recent repeat episode +1. <strong>P1 Urgent</strong> is 6 or more points, <strong>P2 High</strong> 3 to 5, <strong>P3 Routine</strong> 2 or less. Answered packets show <strong>Done</strong>.</p>
<h3>The answer clock</h3>
<p>IHH promises hospitals an answer within 2 hours. <strong>On time</strong> is up to 90 minutes, <strong>At risk</strong> is 91 to 120, and <strong>Late</strong> is after 120. Answered packets show <strong>Answered</strong>.</p></div>"""


def staff_guide():
    return """<div class="prose"><h2 id="staff-h">Staff guide: using the board</h2>
<p>For referral coordinators and nurses. Every packet on this board is made up.</p>
<h3>1. Start with the queue</h3><p>On the <strong>Board</strong> tab, work from the top: the queue is sorted by <strong>priority</strong> (P1 Urgent first), then by time waiting. Watch the <strong>answer clock</strong>.</p>
<h3>2. Open a packet</h3><p>Click a packet name. Its details open in a pop-up: summary, key missing information, priority with its points, made-up patient details, the mock fax PDF, the email log, the packet page by page, medications, and medical history. Press <span class="kbd">Esc</span> or <strong>Close</strong> to go back to the queue.</p>
<h3>3. Look at the grade, then the to-dos</h3><ul><li><strong>Great:</strong> everything needed is there; a person can decide.</li><li><strong>Neutral:</strong> ask the hospital for the listed items.</li><li><strong>Bad:</strong> read the critical alerts first, then call the hospital.</li></ul>
<h3>4. Check the page yourself</h3><p>Each alert names its page. Read that page before relying on it. A tool can misread a crooked fax.</p>
<h3>5. Ask the board</h3><p>Below the queue, <strong>Ask the board</strong> explains grades, priority and what to do first for the selected packet: the one you last opened, or the top of the queue until you open one. It never says whether a patient qualifies.</p>
<h3>6. Decide</h3><p>You decide. Anchor never approves or denies. The board sends no messages; in the intake app, messages are dry-run drafts.</p>
<h3>Keyboard</h3><ul><li><span class="kbd">Tab</span> moves between controls; the first stop is "Skip to content".</li><li>On the tabs, <span class="kbd">←</span> <span class="kbd">→</span> switch tabs; <span class="kbd">Home</span> and <span class="kbd">End</span> jump to the first or last.</li>
<li>In the queue, each packet name is a button. <span class="kbd">Enter</span> opens its pop-up; <span class="kbd">Esc</span> closes it and returns you to the same packet.</li>
<li>The <strong>☰ Menu</strong> button (top right) opens the guides. <span class="kbd">↑</span> <span class="kbd">↓</span> move through it; <span class="kbd">Esc</span> closes it.</li></ul>
<h3>Remember</h3><ul><li>A black box is privacy, not a missing document.</li><li>"Can't tell" means the rule needs a date we can't see. Ask the hospital if it matters.</li><li>Sex offender status is case by case (rule OTH-2). Never auto-deny.</li><li>Never type names or record numbers into notes.</li></ul></div>"""


def it_guide():
    return """<div class="prose"><h2 id="it-h">IT guide: how this page works</h2>
<p>For whoever sets it up and keeps it running.</p>
<h3>What it is</h3><p>One self-contained HTML file, <code>ANCHOR.html</code>, built by <code>build_anchor_page.py</code> from the team's docs and the made-up sample files in <code>triage-dashboard/</code>. Rebuild with <code>python3 build_anchor_page.py</code>; it also runs the tests and shows the result on the Checks tab.</p>
<h3>Ask the board, three ways</h3><ul><li><strong>On claude.ai:</strong> the page asks Claude through the artifact's <code>sample</code> capability, on the viewer's own account, after they allow it.</li>
<li><strong>Locally with Claude:</strong> run <code>python3 board_server.py</code> and open <code>http://127.0.0.1:8790</code>. If a key is set (in the environment or <code>intake-pipeline/.env</code>), the server calls Claude Haiku by default. The key never reaches the browser. The server binds to 127.0.0.1, refuses requests for any other host name and questions from any other page, and serves only an allowlist: this page, its mock fax PDFs and the files listed under Everything we made.</li>
<li><strong>Anywhere else:</strong> built-in answers from the same rules.</li></ul>
<p>Every Claude answer is checked before it shows: an answer that names a rule ID that isn't one of IHH's 155, or uses common wording that reads as an admission decision ("qualifies", "eligible", "should be approved"), is replaced with the built-in answer. The check catches common phrasings, not every possible one; a person still decides.</p>
<h3>Data the board needs</h3><p><strong>Packets:</strong> <code>packet_id, hospital, received, minutes_open, status, pages, required_docs_present, docs_present, facts_applicable, facts_found, facts_unclear, facts_cant_tell, facts_missing, facts_verified, critical_alerts, contradictions, minutes_to_ready, missing_docs</code></p>
<p><strong>Alerts:</strong> <code>alert_id, packet_id, type, what, rule_id, page</code>. <strong>Profiles</strong>, <strong>pages</strong>, <strong>medications</strong>, <strong>history</strong> and the <strong>email log</strong> are in the matching <code>sample-*.json</code> files.</p>
<h3>Rules that don't bend</h3><ul><li>No real patient details on any published page. Real packets stay on a staff computer.</li><li>Never connect to IHH's live systems in the prototype.</li><li>The board sends nothing; the intake app writes dry-run drafts only.</li><li>API keys go in environment variables or the git-ignored <code>.env</code>, never in code.</li></ul>
<h3>Accessibility</h3><p>Built toward WCAG 2.2 AA: tabs follow the ARIA tabs pattern, the menu works by keyboard, packet details use a native dialog that returns focus, tables have captions and headers, links that open a new tab say so, colors come from light and dark tokens, and the page shows every section if JavaScript is off. <strong>Not yet tested</strong> with screen-reader users or a formal audit.</p></div>"""


def built_by():
    people = sorted(TEAM, key=lambda t: (t[1].lower(), t[0].lower()))
    cards = "".join(f'<li class="panel"><strong>{html.escape(f + " " + l)}</strong><br><a href="{html.escape(u)}" target="_blank" rel="noopener">'
                    f'LinkedIn profile<span class="sr-only"> for {html.escape(f + " " + l)} (opens in a new tab)</span></a></li>' for f, l, u in people)
    return f"""<div class="prose"><h2 id="by-h">Built by</h2><p>Team Beacon built Anchor at the OC Claude Impact Lab on October 17, 2026, for Illumination Health + Home. Listed by last name.</p>
<ul class="team">{cards}</ul></div>"""


def main():
    data = {k: json.loads((DASH / f"sample-{f}.json").read_text()) for k, f in
            [("packets", "packets"), ("alerts", "alerts"), ("profiles", "profiles"), ("pages", "pages"), ("meds", "meds"), ("history", "history"), ("emails", "email-log")]}
    tests = test_summary()
    rule_ids = [r["id"] for r in json.loads((HERE / "criteria-overlay" / "admission-criteria.enriched.json").read_text())["rules"]]
    tabs = [("overview", "Overview"), ("board", "Board"), ("app", "Intake app"), ("checks", "Checks"), ("ihh", "About IHH"), ("facts", "Presentation facts"), ("files", "Everything we made")]
    nav = "".join(f'<button type="button" role="tab" id="tab-{i}" aria-controls="{i}" aria-selected="false" tabindex="-1">{t}</button>' for i, t in tabs)
    test_line = f"<strong class='{'ok-txt' if tests['ok'] else 'bad-txt'}'>{html.escape(tests['ran'])} · {'all passing' if tests['ok'] else 'FAILURES'}</strong> (run {tests['when']})"
    checks = f"""<div class="prose"><h2>Checks</h2>
<h3>Automated tests</h3><p>{test_line}</p>
<p>Run them yourself: <code>cd saturday-oct17-build/intake-pipeline &amp;&amp; python3 -m unittest discover -s tests -t . -v</code></p>
<ul><li>Format detection, fax unpacking, blocked and unsupported files</li><li>The 2-hour message ladder, no duplicates, decisions stop follow-ups, nothing is sent</li>
<li>Pre-read on made-up packets: page map, grade, possible red flag, form-vs-chart conflict, owners</li><li>Send request now, then reminders; confirm red flag tells the hospital</li>
<li>Resent pages join the referral and close answered items; fast lane; manual mode</li><li>Safety: unconfirmed quotes never count as found; made-up rule IDs are dropped</li>
<li>Ask Anchor: answers only from context, built-in fallback, rule-ID guard</li><li>Who's working: Untouched / Opened / Worked on, and the activity history</li>
<li>Claude client: models that reject forced tools fall back safely</li></ul>
<h3>Real Claude pre-read (made-up sample, 3-page fax)</h3>
<p>Ran in about 23 seconds. Every page was identified, the facts were found with quotes confirmed on their pages, the form-vs-chart conflict was caught, and the dementia exclusions were raised as possible red flags (NEU-X5, FORM-X1). Grade: Bad, as expected.</p>
<h3>Independent verifier</h3><p>The <code>ihh-verifier</code> checks the page's claims against their sources. Its full reports stay on the team's computer.</p>
<ul>{"".join(f"<li><strong>{html.escape(k)}:</strong> {html.escape(v)}</li>" for k, v in VERIFY_STATUS)}</ul></div>"""
    sections = {
        "overview": f'<div class="prose">{doc("EXECUTIVE-SUMMARY.md")}</div>',
        "board": f"""<h2>Anchor Board</h2><p class="note"><span class="badge">Made-up sample packets. No real referral data.</span> Sorted by priority (patient need), then time waiting. Click a packet to open its details in a pop-up.</p>
<div class="grid" id="b-tiles"></div>
<div class="panel" style="margin-top:16px"><h3>The queue</h3><div class="tbl"><table><caption class="note">Packets by priority</caption>
<thead><tr><th scope="col">Packet</th><th scope="col">Priority</th><th scope="col">Answer clock</th><th scope="col">Grade</th><th scope="col">Score</th><th scope="col">Open items</th></tr></thead><tbody id="b-queue"></tbody></table></div>
<p class="note">Grade: Great = all 7 core documents, a fact score of 85%+ (found = 2 points, unclear or can't tell = 1), no conflicts. Bad = critical alert, missing core document, or under 60%. Neutral = everything else. The grade is completeness, never eligibility.</p></div>
<dialog id="b-dialog" aria-labelledby="b-dialog-title"><div class="dlg-bar"><span class="note">Packet details · made-up sample</span><button type="button" id="b-dialog-close" class="ghost">Close<span class="sr-only"> packet details</span></button></div>
<div class="stack" id="b-detail"></div></dialog>
<section class="panel chat" aria-labelledby="ask-h"><h3 id="ask-h">Ask the board</h3>
<p class="note">Questions about this board and the packet you have open: what a grade means, why a packet is P1, what to do first. It explains the tool; it never gives medical advice or decides eligibility. <span id="ask-current"></span> <span id="ask-mode">Built-in answers.</span></p>
<div class="chips" id="ask-chips"></div>
<div id="ask-log" class="chat-log" role="log" aria-live="polite" aria-label="Conversation"></div>
<form id="ask-form" class="row"><label for="ask-q" class="sr-only">Your question</label><input id="ask-q" autocomplete="off" maxlength="500" placeholder="Ask about the open packet or the board">
<button type="submit" id="ask-send">Ask</button><button type="button" id="ask-stop" hidden>Stop</button></form></section>""",
        "app": f'''<div class="prose"><p class="panel"><strong>Try the Anchor Board with its chatbot:</strong> <a href="{LOCAL_BOARD_URL}" target="_blank" rel="noopener">open the local Anchor Board<span class="sr-only"> (opens in a new tab)</span></a>. Start it first with <code>python3 board_server.py</code> in the <code>saturday-oct17-build</code> folder; Ask the board then answers with Claude, using the key in <code>intake-pipeline/.env</code>. The full intake app below also runs on your own computer.</p>
{doc("intake-pipeline/README.md")}</div>''',
        "checks": checks,
        "built": '<div class="prose">' + doc("HOW-THIS-WAS-BUILT.md").replace("<h2>How Anchor was built</h2>", '<h2 id="built-h">How Anchor was built</h2>', 1) + "</div>",
        "grading": grading_guide(), "staff": staff_guide(), "it": it_guide(),
        "ihh": f'<div class="prose">{doc("ABOUT-IHH.md")}</div>',
        "facts": f'<div class="prose">{doc("PRESENTATION-FACTS.md")}</div>',
        "files": everything(),
        "by": built_by(),
    }
    body = "".join(f'<section id="{i}" role="tabpanel" aria-labelledby="tab-{i}" tabindex="0" class="panel">{sections[i]}</section>' for i, _ in tabs)
    body += "".join(f'<section id="{i}" class="panel menu-panel" role="region" aria-labelledby="{i}-h" tabindex="-1">{sections[i]}</section>' for i, _ in MENU)
    menu = "".join(f'<li role="none"><button type="button" role="menuitem" tabindex="-1" data-open="{i}">{html.escape(t)}</button></li>' for i, t in MENU)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anchor</title><style>{CSS}</style></head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="menu-wrap"><button type="button" id="menu-btn" class="menu-btn" aria-label="Menu" aria-haspopup="menu" aria-expanded="false" aria-controls="menu-list"><span aria-hidden="true">☰</span> Menu</button>
<ul id="menu-list" class="menu" role="menu" aria-labelledby="menu-btn" hidden>{menu}</ul></div>
<h1>Anchor</h1><p>Referral intake for Illumination Health + Home · Team Beacon · OC Claude Impact Lab, October 17, 2026 · prototype, dry run, no real patient data</p>
<nav class="tabs" role="tablist" aria-label="Anchor sections">{nav}</nav></header>
<main id="main">{body}</main>
<footer class="foot"><p>Anchor · Team Beacon · <a href="#files" data-tab="files">Everything we made</a> · <a href="#built" data-tab="built">How it was built</a> · <a href="#by" data-tab="by">Built by</a></p></footer>
<script>window.ANCHOR_DATA = {json.dumps(data)}; window.ANCHOR_RULE_IDS = {json.dumps(rule_ids)};</script>
<script>{TABS_JS}</script><script>{BOARD_JS}</script><script>{ASK_JS}</script>
</body></html>"""
    OUT.write_text(page)
    print(f"wrote {OUT.name}: {len(page) // 1024} KB · tests: {tests['ran']} {'OK' if tests['ok'] else 'FAILED'}")


if __name__ == "__main__":
    main()
