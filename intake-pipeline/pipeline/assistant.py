""""Ask Anchor": a Claude Haiku helper that answers only from Anchor's own guide and the referral on screen.

It knows where the person is (page, section, the fact they're looking at) and suggests the next action.
It never gives medical advice, never decides eligibility, and never invents facts. Without an API key
it falls back to Anchor's built-in "what to do next" rule.
"""
import re

from . import claude, guidance, notify, rules, store

GUIDE = """ANCHOR GUIDE (the only general knowledge you may use)
Anchor is Team Beacon's referral intake prototype for Illumination Health + Home (IHH) recuperative care. Dry run: nothing is ever sent.
Pages: "All referrals" (list, Check fax inbox, Advance clock demo), "Upload" (button at the top of every page), "My list" (to-dos by owner), "How it works", and each referral's page.
Who's working: staff add their name at the top ("Working as"); every action is recorded. Status: Untouched (no one has opened it), Opened by (viewed only), Worked on (someone acted), with "Worked on by" names and a history in step 6.
A referral page has: What to do next; Fast lane (only for complete packets); 1. To-do list; 2. Check the facts; 3. What arrived; 4. Messages; 5. Decide; 6. Who has worked on it.
Pre-read: Claude maps the pages, finds 27 facts with page and quote, then a second look checks each quote is on its page. Unconfirmed quotes count as "unclear", never "found".
Statuses: Found (with a page), Unclear, Can't tell (the rule needs a date, and dates are redacted), Redacted (a black box: privacy, never "missing"), Missing (not in the packet).
Grade (completeness, never eligibility): Great = all 7 core documents (IHH form, face sheet, CalAIM authorization, H&P, vitals, medication list, PT/OT or nursing notes), a fact score of 85%+ (found = 2 points, unclear or can't tell = 1), no open conflicts. Bad = possible red flag, a core document missing, or under 60%. Neutral = everything else.
Fast lane = Great and nothing flagged: one screen to Approve or Deny. A person always decides; Anchor never approves or denies.
To-do list: each item has an owner. Clinical reviewer gets red flags, clinical conflicts and clinical facts; Coordinator gets paperwork.
Possible red flag (from the pre-read): goes to the intake team at once; press "Confirm (tells hospital now)" or "Dismiss". Confirming tells the hospital immediately; it is a request for clarification, not a decision.
Missing items: tick "Include in request", then "Send request now". The 30- and 60-minute messages become reminders.
"Settle" items: the form and chart disagree. Open the fact in step 2 to see both pages; the chart wins over the form. Then "Mark done".
Check the facts: click a fact (or J/K) to see its page beside it; V marks verified; O opens the page full size; R jumps to the reply box.
Resent pages: a fax that mentions the referral number joins the same referral; only new pages are read; answered items close themselves. Demo button: "Demo: hospital resends missing pages".
Messages: receipt at arrival; request/reminders at 30 and 60 minutes; intake team escalations at 60, 90, 110, 120 minutes; replies via "Save reply to outbox (dry run)". Messages carry the referral number only, never a patient name.
2-hour promise: IHH answers hospitals within 2 hours. Clock: On time under 90 minutes, At risk 90-120, Late over 120.
Rules: IHH's rules have IDs (for example NEU-X5 dementia, MOB-2 PT/OT notes). Gaps in the written rules go to the coordinator to decide."""

SYSTEM = """You are "Ask Anchor", the in-app helper for IHH's referral intake staff.
Answer ONLY from the ANCHOR GUIDE and the SCREEN and REFERRAL sections you are given. If the answer is not there, say you can only help with Anchor and this referral, and suggest asking the intake lead or clinical reviewer.
Never give medical, clinical, legal or eligibility advice, and never say whether a patient qualifies. A person decides; you explain the tool and the next step.
Never invent facts, page numbers, rule IDs, phone numbers or quotes. Use only rule IDs and pages that appear in the context.
Be brief: 1 to 4 short sentences, plain words. When useful, end with "Next:" and one action, naming the exact button or key on screen.
Never repeat or ask for patient names or identifiers."""

RULE_ID = re.compile(r"\b(?:[A-Z]{2,5}-(?:[A-Z]{1,2})?\d{1,2}|DOC-\d{1,2})\b")
NOT_RULES = {"COVID-19", "SARS-2", "HIV-1", "HIV-2", "ICD-10", "ICD-9", "TYPE-1", "TYPE-2"}


def screen_text(screen):
    s = screen or {}
    parts = [f"Page: {s.get('page') or 'unknown'}"]
    if s.get("section"):
        parts.append(f"Section in view: {s['section']}")
    if s.get("fact"):
        parts.append(f"Fact being viewed: {s['fact']}")
    if s.get("focus"):
        parts.append(f"Focused control: {s['focus']}")
    return "SCREEN\n" + "\n".join(parts)


def referral_text(con, rid):
    r = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone() if rid else None
    if not r:
        open_n = con.execute("SELECT COUNT(*) FROM referrals WHERE status='open'").fetchone()[0]
        return f"REFERRAL\nNo referral open on screen. Open referrals in the list: {open_n}."
    g = rules.grade(con, rid)
    run = con.execute("SELECT status, step FROM preread_runs WHERE referral_id=?", (rid,)).fetchone()
    lines = [f"REFERRAL {rid} from {r['hospital']} (arrived by {r['channel']}). Status: {r['status']}" + (f", decision {r['decision']}" if r["decision"] else ""),
             f"Clock: {notify.clock_state(con, r)}, {int(store.minutes_open(con, r))} minutes since arrival.",
             f"Grade: {g['grade'] or 'not read yet'} ({g['why']}). Fast lane: {'yes' if g.get('fast_lane') else 'no'}.",
             f"Pre-read: {run['status'] + ' - ' + run['step'] if run else 'not started'}."]
    act = store.activity_status(con, rid)
    if act["state"] == "untouched":
        lines.append("Activity: untouched (no staff has opened or worked on it yet).")
    else:
        lines.append(f"Activity: {act['state']}; last by {act['last']['actor']} ({act['last']['action']}, {act['last']['minutes_ago']} min ago); worked on by: {', '.join(act['workers']) or 'no one yet'}.")
    docs = rules.documents(con, rid)
    lines.append("Core documents: " + "; ".join(f"{d} {'present' if d in docs else 'missing'}" for d in rules.CORE_DOCS))
    flags = con.execute("SELECT * FROM flags WHERE referral_id=? AND resolved_at IS NULL ORDER BY type='red' DESC, created_at", (rid,)).fetchall()
    if flags:
        lines.append("Open to-dos:")
        for f in flags[:25]:
            state = "red flag, " + ("confirmed" if f["approved"] else "not yet confirmed") if f["type"] == "red" else (
                "internal, settle" if (f["source"] or "") == "internal" else ("requested" if f["approved"] else "suggested, not yet requested"))
            lines.append(f"- [{state}; owner {f['owner']}] {f['text']}" + (f" (rule {f['rule_id']})" if f["rule_id"] else ""))
    else:
        lines.append("Open to-dos: none.")
    best = rules.best_facts(con, rid)
    counts = {}
    for k in rules.FACT_KEYS:
        st = best[k]["status"] if k in best else "missing"
        counts[st] = counts.get(st, 0) + 1
    verified = sum(1 for f in best.values() if f["verified_at"])
    lines.append("Facts: " + ", ".join(f"{v} {k}" for k, v in counts.items()) + f"; {verified} of {len(rules.FACT_KEYS)} verified by a person.")
    for k in rules.FACT_KEYS:
        f = best.get(k)
        if f:
            lines.append(f"- {rules.FACT_LABELS[k]}: {f['status']}" + (f", p. {f['page']}" if f["page"] else "") + (", quote confirmed" if f["quote_checked"] else "") + (", verified" if f["verified_at"] else ""))
    for c in con.execute("SELECT * FROM findings WHERE referral_id=? AND kind='contradiction'", (rid,)):
        lines.append(f"Conflict: {c['text']} (pages {c['page']} and {c['page2']})")
    ct = [r_["id"] for r_ in rules.cant_tell(con, rid)]
    if ct:
        lines.append("Rules that can't be checked because dates are redacted: " + ", ".join(ct))
    msgs = [n["tier"] for n in con.execute("SELECT tier FROM notifications WHERE referral_id=? ORDER BY created_at", (rid,))]
    lines.append("Messages so far: " + (", ".join(msgs) if msgs else "none"))
    return "\n".join(lines)


def fallback(con, rid):
    """Built-in guidance used when Claude isn't available."""
    r = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone() if rid else None
    if not r:
        return "Open a referral from the list to see what to do next, or press \"Check fax inbox\" to bring in new faxes."
    return guidance.next_step(con, r)


def answer(con, question, history=None, screen=None, caller=None):
    """Returns {"answer": str, "mode": "claude"|"built-in", "note": str|None}."""
    question = (question or "").strip()[:800]
    rid = (screen or {}).get("referral")
    if not question:
        return {"answer": "Ask me about this screen or what to do next.", "mode": "built-in", "note": None}
    context = "\n\n".join([GUIDE, screen_text(screen), referral_text(con, rid)])
    msgs = []
    for turn in (history or [])[-6:]:
        if turn.get("role") in ("user", "assistant") and isinstance(turn.get("content"), str):
            msgs.append({"role": turn["role"], "content": turn["content"][:1200]})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    msgs.append({"role": "user", "content": f"{context}\n\nQUESTION: {question}"})
    call = caller or (lambda system, m: claude.call_text(claude.CHAT_MODEL, system, m, max_tokens=400))
    try:
        text = call(SYSTEM, msgs)
    except claude.ReaderUnavailable as e:
        return {"answer": fallback(con, rid), "mode": "built-in", "note": "Ask Anchor needs ANTHROPIC_API_KEY. Showing the built-in next step instead." if not claude.available() else str(e)[:200]}
    # Grounding guard: any rule ID not in IHH's rules means the answer can't be trusted
    bad = [x for x in RULE_ID.findall(text) if x not in rules.RULES and x not in NOT_RULES]
    if bad or not text:
        return {"answer": fallback(con, rid), "mode": "built-in", "note": "That answer mentioned something not in Anchor's rules, so here is the built-in next step instead."}
    return {"answer": text, "mode": "claude", "note": None}
