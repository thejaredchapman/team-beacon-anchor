"""IHH rules, the 27 core facts, grading, and the to-do list, built on the criteria overlay.

Reads ../criteria-overlay/admission-criteria.enriched.json (IHH's rule text plus local fields).
Plain code decides everything here; nothing in this file calls an AI.
"""
import json
from pathlib import Path

from . import store

OVERLAY = Path(__file__).resolve().parents[2] / "criteria-overlay" / "admission-criteria.enriched.json"
_data = json.loads(OVERLAY.read_text())
RULES = {r["id"]: r for r in _data["rules"]}
FACT_LABELS = _data["fact_keys"]
FACT_KEYS = list(FACT_LABELS)

# Plain-language hints for the reader, one per fact
FACT_HINTS = {
    "housing": "Is the patient unhoused, at risk, or without a safe place to recover? Usually the IHH form, face sheet or social work note.",
    "admitting_diagnosis": "Main reason for the hospital stay, in plain words.",
    "aox4": "Alert and oriented to person, place, time and situation. Check nursing and progress notes, not only the form.",
    "cognitive_impairment": "Any dementia, Alzheimer's or confusion. Check the face sheet diagnosis list.",
    "adl_independent": "Can bathe, dress and use the toilet without help. PT/OT or nursing notes are best.",
    "walk_100ft_transfers": "Distance walked (100 ft or more) and whether transfers are independent. PT/OT notes are best.",
    "dme_independent": "Walker, cane or wheelchair, and whether used independently.",
    "self_admin_meds": "Can the patient take their own medicines (including insulin)?",
    "wounds": "Any wounds: location, size, stage, and who will do dressing changes.",
    "home_health": "Is home health ordered or scheduled (wound care, IV, PT)?",
    "oxygen": "Oxygen needed at discharge? 'Room air' means no. If yes, is a tank ordered?",
    "iv_access": "Any IV line or IV medicine at discharge (PICC, midline, port)?",
    "continence": "Continence, catheter, colostomy or ileostomy.",
    "diabetes": "Diabetes, insulin or oral medicine, and recent glucose readings.",
    "vitals_last5": "Recent vital signs, and whether they look stable.",
    "tb_test": "TB skin test, QuantiFERON or chest X-ray result.",
    "mrsa_swab": "MRSA swab result.",
    "covid_swab": "COVID swab result. If timing needs a date, the status is cant_tell.",
    "isolation": "Is the patient on isolation, or has an active infection been cleared?",
    "mental_health_stable": "Mental health diagnosis and whether it is described as stable on medicine.",
    "si_hallucinations": "Any suicidal thoughts or command hallucinations.",
    "substance_withdrawal": "Substance use and any withdrawal risk (CIWA or COWS).",
    "aggression": "Any aggressive or combative behavior toward staff or patients.",
    "sex_offender": "Registered sex offender status, if stated.",
    "conservatorship_fsp": "Conservatorship or Full Service Partnership, if stated.",
    "follow_up": "Follow-up appointments scheduled.",
    "med_list_supply": "A current discharge medication list, and a 30-day supply.",
}

CLINICAL_FACTS = {"aox4", "cognitive_impairment", "mental_health_stable", "si_hallucinations", "substance_withdrawal", "aggression",
                  "wounds", "oxygen", "iv_access", "diabetes", "vitals_last5", "isolation", "mrsa_swab", "covid_swab", "tb_test",
                  "conservatorship_fsp"}

DOC_TYPES = {
    "fax_cover": None, "ihh_referral_form": "DOC-1", "face_sheet": "DOC-2", "calaim_authorization": "DOC-3",
    "history_physical": "DOC-4", "progress_note": "DOC-5", "vitals": "DOC-6", "medication_list": "DOC-7",
    "medication_record": "DOC-7", "pt_ot_evaluation": "DOC-8", "nursing_note": "DOC-8", "culture": "DOC-9",
    "labs": None, "imaging": None, "ekg": None, "psych_consult": None, "social_work": None, "wound_note": None,
    "physician_orders": None, "older_record": None, "blank": None, "other": None, "text": None,
}
DOC_NAMES = {r["id"]: r["text"] for r in _data["rules"] if r["id"].startswith("DOC-")}
CORE_DOCS = ["DOC-1", "DOC-2", "DOC-3", "DOC-4", "DOC-6", "DOC-7", "DOC-8"]
EXCLUDE_RULES = [{"id": r["id"], "text": r["text"]} for r in _data["rules"] if r.get("kind") == "exclude"]

STATUS_POINTS = {"found": 2, "unclear": 1, "cant_tell": 1, "missing": 0}
STATUS_ORDER = {"found": 0, "unclear": 1, "cant_tell": 2, "redacted": 3, "missing": 4}


def best_facts(con, rid):
    """One row per fact key: the best status across form and chart, with the chart preferred on ties."""
    out = {}
    for f in con.execute("SELECT * FROM facts WHERE referral_id=? ORDER BY source='form'", (rid,)):
        cur = out.get(f["key"])
        if cur is None or STATUS_ORDER.get(f["status"], 9) < STATUS_ORDER.get(cur["status"], 9):
            out[f["key"]] = f
    return out


def documents(con, rid):
    found = {}
    for p in con.execute("SELECT n, doc_type FROM pages WHERE referral_id=? ORDER BY n", (rid,)):
        doc = DOC_TYPES.get(p["doc_type"] or "other")
        if doc:
            found.setdefault(doc, []).append(p["n"])
    facts = best_facts(con, rid)
    if facts.get("med_list_supply") and facts["med_list_supply"]["status"] == "found" and "supply" in (facts["med_list_supply"]["value"] or "").lower():
        found.setdefault("DOC-10", []).append(facts["med_list_supply"]["page"])
    return found


def grade(con, rid):
    """Completeness grade (never an eligibility decision)."""
    facts = best_facts(con, rid)
    if not facts:
        return {"grade": None, "pct": None, "why": "Not read yet", "fast_lane": False}
    pts = poss = 0
    for key in FACT_KEYS:
        f = facts.get(key)
        st = f["status"] if f else "missing"
        if st == "redacted":
            continue
        pts += STATUS_POINTS.get(st, 0)
        poss += 2
    pct = round(100 * pts / poss) if poss else 0
    docs = documents(con, rid)
    missing_core = [d for d in CORE_DOCS if d not in docs]
    critical = con.execute("SELECT COUNT(*) FROM flags WHERE referral_id=? AND type='red' AND resolved_at IS NULL", (rid,)).fetchone()[0]
    conflicts = con.execute("SELECT COUNT(*) FROM findings WHERE referral_id=? AND kind='contradiction'", (rid,)).fetchone()[0]
    open_conflicts = con.execute("SELECT COUNT(*) FROM flags WHERE referral_id=? AND fact_key LIKE 'conflict:%' AND resolved_at IS NULL", (rid,)).fetchone()[0]
    if critical:
        g, why = "Bad", "A possible red flag needs clinical review"
    elif missing_core:
        g, why = "Bad", "Core document missing: " + ", ".join(missing_core)
    elif pct < 60:
        g, why = "Bad", f"Only {pct}% of facts found"
    elif pct >= 85 and open_conflicts == 0:
        g, why = "Great", f"{pct}% of facts found, all core documents, no conflicts"
    else:
        g, why = "Neutral", f"{pct}% of facts found" + (f", {open_conflicts} conflict(s) to settle" if open_conflicts else "")
    return {"grade": g, "pct": pct, "why": why, "fast_lane": g == "Great" and critical == 0 and open_conflicts == 0,
            "missing_core": missing_core, "conflicts": conflicts}


def cant_tell(con, rid):
    """Rules that need a date (redacted), shown only when the packet touches their facts."""
    facts = best_facts(con, rid)
    out = []
    for r in RULES.values():
        if r.get("needs_date") and any(facts.get(k) and facts[k]["status"] in ("found", "unclear", "cant_tell") for k in r.get("facts", [])):
            out.append(r)
    return out


def _add_todo(con, rid, ftype, text, owner, source, rule_id=None, fact_key=None, approved=0):
    exists = con.execute("SELECT 1 FROM flags WHERE referral_id=? AND IFNULL(fact_key,'')=IFNULL(?, '') AND IFNULL(rule_id,'')=IFNULL(?, '') AND text=?",
                         (rid, fact_key, rule_id, text)).fetchone()
    if exists:
        return None
    fid = store.new_id("flag")
    con.execute("INSERT INTO flags (id, referral_id, type, text, rule_id, created_at, owner, source, approved, fact_key) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (fid, rid, ftype, text, rule_id, store.iso(store.now(con)), owner, source, approved, fact_key))
    return fid


def build_todos(con, rid):
    """Turn the pre-read into a to-do list with an owner on each item. Hospital requests still need staff approval."""
    created = {"requests": 0, "possible_red_flags": [], "internal": 0}
    docs = documents(con, rid)
    for d in CORE_DOCS:
        if d not in docs and _add_todo(con, rid, "missing", f"Send: {DOC_NAMES.get(d, d)}", "coordinator", "auto", rule_id=d):
            created["requests"] += 1
    facts = best_facts(con, rid)
    for key in FACT_KEYS:
        f = facts.get(key)
        if f is None or f["status"] == "missing":
            rule = next((r["id"] for r in RULES.values() if key in r.get("facts", []) and r.get("kind") in ("must", "document", "exclude")), None)
            owner = "clinical" if key in CLINICAL_FACTS else "coordinator"
            if _add_todo(con, rid, "missing", f"Send or confirm: {FACT_LABELS[key]}", owner, "auto", rule_id=rule, fact_key=key):
                created["requests"] += 1
    for fd in con.execute("SELECT * FROM findings WHERE referral_id=?", (rid,)).fetchall():
        rule = RULES.get(fd["rule_id"] or "")
        if fd["kind"] == "red_flag":
            if not rule:
                continue  # a rule ID that doesn't exist is dropped; the reader is told to use IHH's IDs only
            if rule.get("superseded_by") or rule.get("gap") or rule.get("human_review"):
                if _add_todo(con, rid, "missing", f"Coordinator decides (rule gap): {fd['text']}", "coordinator", "internal", rule_id=fd["rule_id"], fact_key=f"gap:{fd['id']}", approved=1):
                    created["internal"] += 1
            else:
                label = "Possible red flag" + ("" if fd["quote_checked"] else " (quote not confirmed: check the page)")
                fid = _add_todo(con, rid, "red", f"{label}: {fd['text']}", "clinical", "auto", rule_id=fd["rule_id"], fact_key=f"red:{fd['id']}")
                if fid:
                    created["possible_red_flags"].append(fid)
        elif fd["kind"] == "contradiction":
            owner = "clinical" if (fd["fact_key"] or "") in CLINICAL_FACTS else "coordinator"
            if _add_todo(con, rid, "missing", f"Settle: {fd['text']}", owner, "internal", fact_key=f"conflict:{fd['id']}", approved=1):
                created["internal"] += 1
    con.commit()
    return created
