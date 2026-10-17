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
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", s)          # local links: keep the text
    return s


def md(text):
    out, lines, i = [], text.splitlines(), 0
    list_stack = []

    def close_lists(to=0):
        while len(list_stack) > to:
            out.append(f"</{list_stack.pop()[0]}>")

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
                out.append(f"</{list_stack.pop()[0]}>")
            if not list_stack or list_stack[-1][1] < level:
                out.append(f"<{tag}>")
                list_stack.append((tag, level))
            out.append(f"<li>{inline(rest)}</li>")
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
    ("First check", "FAIL: one rule break and six wrong facts (test counts, out-of-date status, unreadable faxes, unchecked rule IDs, README gaps). Fixed."),
    ("Re-check", "FAIL: the earlier fixes held, but this page copied a report that described a real packet, and the privacy wording was wrong. Fixed: reports no longer copied, privacy wording corrected, sample packets rewritten from scratch."),
    ("Final check", "PASS WITH FIXES: no P0 or P1 items."),
    ("Page check", "FAIL on wording: red-flag routing, the grade score, and two source details. Fixed; small wording and accessibility items remain open."),
]


# ---------- page ----------

CSS = """
:root{--bg:#f5f7f8;--panel:#fff;--ink:#13222b;--muted:#4c5d67;--line:#d4dde1;--accent:#0d6b67;--accent-ink:#fff;--soft:#eaf3f2;--bad:#a4261d;--warn:#8a5300;--ok:#1d6b34}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f171b;--panel:#16232a;--ink:#e6eef1;--muted:#a6b7bf;--line:#2b3c45;--accent:#5cc2bb;--accent-ink:#062523;--soft:#173332;--bad:#f19387;--warn:#f0b660;--ok:#86d39c;color-scheme:dark}}
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
    b.addEventListener('click', () => show(r.p.packet_id));
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
  function show(id) {
    document.querySelectorAll('#b-queue tr').forEach((tr) => tr.setAttribute('aria-current', tr.dataset.key === id ? 'true' : 'false'));
    const r = rows.find((x) => x.p.packet_id === id), f = prof[id] || {};
    const box = document.getElementById('b-detail'); box.replaceChildren();
    const h = el('h3', { textContent: id + ' · ' + r.p.hospital, tabIndex: -1 });
    box.append(h, el('p', {}, [pill(r.pr.level, pcls(r.pr.level)), ' ', pill('Grade: ' + r.gr.g + ' (' + r.gr.pct + '%)', cls[r.gr.g]), ' ', pill(r.c, cls[r.c])]));
    box.append(el('h4', { textContent: 'Summary' }), el('p', { textContent: f.summary || '' }));
    const miss = D.alerts.filter((a) => a.packet_id === id);
    box.append(el('h4', { textContent: 'Key missing information' }), table('Do these first', ['To do', 'What', 'Page', 'Rule'], miss.map((a) => [pill(verb[a.type] || a.type, a.type === 'Critical' ? 'bad' : 'warn'), a.what, a.page, a.rule_id])));
    const P = r.pr.pts;
    box.append(el('h4', { textContent: 'Priority (by patient need)' }), table('P1 is 6+ points, P2 3-5, P3 2 or less', ['Factor', 'This packet', 'Points'],
      [['Expected discharge', f.discharge || '', '+' + P.discharge], ['Answer clock', r.c, '+' + P.clock], ['Housing', f.housing || '', '+' + P.housing], ['High care need', f.care_needs || '', '+' + P.need], ['Recent repeat episode', f.recent_episode || '', '+' + P.recent], ['Total', r.pr.level, String(r.pr.score)]]));
    box.append(el('h4', { textContent: 'Patient details (made up)' }), table('Real packets show black boxes (redacted) for name and address', ['Name', 'Address', 'Allergies', 'Blood type'], [[f.patient_name || '', f.address || '', f.allergies || '', f.blood_type || '']]));
    const fax = 'triage-dashboard/faxes/' + id + '-original-fax.pdf';
    box.append(el('h4', { textContent: 'Original fax (mock PDF)' }), el('p', {}, [el('a', { href: fax, target: '_blank', rel: 'noopener', textContent: 'Open ' + id + ' original fax (PDF, opens in a new tab)' })]));
    box.append(el('h4', { textContent: 'Email log' }), table('Times to the second; a sample log, no real messages', ['Time', 'Direction', 'Channel', 'Subject', 'Status'], D.emails.filter((e) => e.packet_id === id).map((e) => [e.time, e.direction, e.channel, e.subject, e.status])));
    box.append(el('h4', { textContent: 'The packet, page by page' }), table('', ['Pages', 'Document', 'What it shows'], D.pages.filter((p) => p.packet_id === id).map((p) => [p.page_from === p.page_to ? 'p. ' + p.page_from : 'pp. ' + p.page_from + '-' + p.page_to, p.doc_type, p.key_content])));
    box.append(el('h4', { textContent: 'Medications' }), table('', ['Medicine', 'Dose', 'How often', 'Self-gives?', 'For', 'Page'], D.meds.filter((m) => m.packet_id === id).map((m) => [m.medicine, m.dose, m.how_often, m.self_administers, m.purpose, 'p. ' + m.page])));
    box.append(el('h4', { textContent: 'Medical history and recent episodes' }), table('', ['Condition', 'Status', 'Recent?', 'Page'], D.history.filter((x) => x.packet_id === id).map((x) => [x.condition, x.status, x.recent, 'p. ' + x.page])),
      el('p', { className: 'note', textContent: 'Has this happened recently? ' + (f.recent_episode || '') + '. ' + (f.recent_note || '') }));
    h.focus();
  }
  if (rows.length) show(rows[0].p.packet_id);
})();
"""

TABS_JS = r"""
(function () {
  const tabs = [...document.querySelectorAll('.tabs [role=tab]')];
  function show(id) {
    tabs.forEach((t) => { const on = t.getAttribute('aria-controls') === id; t.setAttribute('aria-selected', String(on)); t.tabIndex = on ? 0 : -1; });
    document.querySelectorAll('main > section[role=tabpanel]').forEach((s) => { s.hidden = s.id !== id; });
    history.replaceState(null, '', '#' + id);
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
    e.preventDefault(); const id = a.dataset.tab; show(id); window.scrollTo(0, 0); document.getElementById('tab-' + id).focus();
  }));
  const start = location.hash.slice(1);
  show(tabs.some((t) => t.getAttribute('aria-controls') === start) ? start : 'overview');
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
        ("ANCHOR.html", "This page"), ("build_anchor_page.py", "Builds this page"), ("make_exec_summary_pdf.py", "Builds the executive summary PDF")]),
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
        ("intake-pipeline/tests/test_activity.py", "Who's working and the history"), ("intake-pipeline/tests/test_claude_client.py", "Claude client fallback")]),
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
<p>Links open the files from the <code>saturday-oct17-build</code> folder, so they work when this page is opened from that folder. Online: <a href="https://claude.ai/artifact/NVUonEKc7TRXnVU9QafCVG" target="_blank" rel="noopener">Anchor Board</a>.</p>
{groups}
<p class="note">Not linked on purpose: <code>packet-review/</code> (work on the real packets stays local), and the app's <code>work/</code>, <code>outbox/</code> and <code>.env</code>.</p></div>"""


def built_by():
    people = sorted(TEAM, key=lambda t: (t[1].lower(), t[0].lower()))
    cards = "".join(f'<li class="panel"><strong>{html.escape(f + " " + l)}</strong><br><a href="{html.escape(u)}" target="_blank" rel="noopener">'
                    f'LinkedIn profile<span class="sr-only"> for {html.escape(f + " " + l)} (opens in a new tab)</span></a></li>' for f, l, u in people)
    return f"""<div class="prose"><h2>Built by</h2><p>Team Beacon built Anchor at the OC Claude Impact Lab on October 17, 2026, for Illumination Health + Home. Listed by last name.</p>
<ul class="team">{cards}</ul></div>"""


def main():
    data = {k: json.loads((DASH / f"sample-{f}.json").read_text()) for k, f in
            [("packets", "packets"), ("alerts", "alerts"), ("profiles", "profiles"), ("pages", "pages"), ("meds", "meds"), ("history", "history"), ("emails", "email-log")]}
    tests = test_summary()
    tabs = [("overview", "Overview"), ("board", "Board"), ("app", "Intake app"), ("checks", "Checks"), ("built", "How it was built"), ("ihh", "About IHH"), ("facts", "Presentation facts"), ("files", "Everything we made"), ("by", "Built by")]
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
<h3>Independent verifier</h3><p>The <code>ihh-verifier</code> checks every claim against its source. Its full reports stay on the team's computer.</p>
<ul>{"".join(f"<li><strong>{html.escape(k)}:</strong> {html.escape(v)}</li>" for k, v in VERIFY_STATUS)}</ul></div>"""
    sections = {
        "overview": f'<div class="prose">{doc("EXECUTIVE-SUMMARY.md")}</div>',
        "board": f"""<h2>Anchor Board</h2><p class="note"><span class="badge">Made-up sample packets. No real referral data.</span> Sorted by priority (patient need), then time waiting. Click a packet for its details.</p>
<div class="grid" id="b-tiles"></div>
<div class="two" style="margin-top:16px"><div class="panel"><h3>The queue</h3><div class="tbl"><table><caption class="note">Packets by priority</caption>
<thead><tr><th scope="col">Packet</th><th scope="col">Priority</th><th scope="col">Answer clock</th><th scope="col">Grade</th><th scope="col">Score</th><th scope="col">Open items</th></tr></thead><tbody id="b-queue"></tbody></table></div>
<p class="note">Grade: Great = all 7 core documents, a fact score of 85%+ (found = 2 points, unclear or can't tell = 1), no conflicts. Bad = critical alert, missing core document, or under 60%. Neutral = everything else. The grade is completeness, never eligibility.</p></div>
<div class="panel stack" id="b-detail" aria-live="polite"></div></div>""",
        "app": f'''<div class="prose"><p class="panel"><strong>Try Anchor online:</strong> <a href="{BOARD_URL}" target="_blank" rel="noopener">open the Anchor Board<span class="sr-only"> (opens in a new tab)</span></a>. It runs in the browser on made-up sample packets, with nothing to install. The full intake app below runs on your own computer.</p>
{doc("intake-pipeline/README.md")}</div>''',
        "checks": checks,
        "built": f'<div class="prose">{doc("HOW-THIS-WAS-BUILT.md")}</div>',
        "ihh": f'<div class="prose">{doc("ABOUT-IHH.md")}</div>',
        "facts": f'<div class="prose">{doc("PRESENTATION-FACTS.md")}</div>',
        "files": everything(),
        "by": built_by(),
    }
    body = "".join(f'<section id="{i}" role="tabpanel" aria-labelledby="tab-{i}" tabindex="0" hidden class="panel">{sections[i]}</section>' for i, _ in tabs)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anchor</title><style>{CSS}</style></head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><h1>Anchor</h1><p>Referral intake for Illumination Health + Home · Team Beacon · OC Claude Impact Lab, October 17, 2026 · prototype, dry run, no real patient data</p>
<nav class="tabs" role="tablist" aria-label="Anchor sections">{nav}</nav></header>
<main id="main">{body}</main>
<footer class="foot"><p>Anchor · Team Beacon · <a href="#files" data-tab="files">Everything we made</a> · <a href="#by" data-tab="by">Built by</a></p></footer>
<script>window.ANCHOR_DATA = {json.dumps(data)};</script>
<script>{TABS_JS}</script><script>{BOARD_JS}</script>
</body></html>"""
    OUT.write_text(page)
    print(f"wrote {OUT.name}: {len(page) // 1024} KB · tests: {tests['ran']} {'OK' if tests['ok'] else 'FAILED'}")


if __name__ == "__main__":
    main()
