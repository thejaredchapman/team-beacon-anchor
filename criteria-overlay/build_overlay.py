"""Build a local overlay on IHH's admission criteria.

Reads the event's admission-criteria.json (never edits it) and writes:
  admission-criteria.overlay.json   additive fields per rule ID (kind, needs_date, gap, evidence, facts)
  admission-criteria.enriched.json  source rules merged with the overlay, for tools
  admission-criteria-with-ids.md    a readable list of every rule with its ID, generated from the JSON

Run:  python3 build_overlay.py
"""
import hashlib
import json
import re
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "claude-impact-lab-oc/challenges/1-referral-intake/criteria/admission-criteria.json"

# The 27 core facts from the Packet Triage plan (01-packet-triage-v2.md, section 6)
FACTS = {
    "housing": "Housing status (unhoused / at risk)",
    "admitting_diagnosis": "Admitting diagnosis / chief complaint",
    "aox4": "Alert and oriented x4",
    "cognitive_impairment": "Cognitive impairment / dementia",
    "adl_independent": "ADLs independent (hygiene, toileting)",
    "walk_100ft_transfers": "Walks 100 ft / transfers independently",
    "dme_independent": "DME used independently",
    "self_admin_meds": "Self-administers medications",
    "wounds": "Wounds: location, size, stage, who does care",
    "home_health": "Home health arranged",
    "oxygen": "Oxygen required; tank ordered",
    "iv_access": "IV access / IV antibiotics",
    "continence": "Continence; catheter; ostomy",
    "diabetes": "Diabetes; insulin; 5 glucose readings",
    "vitals_last5": "Last 5 sets of vital signs stable",
    "tb_test": "TB test / chest X-ray result",
    "mrsa_swab": "MRSA swab negative",
    "covid_swab": "COVID swab within 24 h",
    "isolation": "Isolation / active infection cleared",
    "mental_health_stable": "Mental health diagnosis; stable on meds",
    "si_hallucinations": "Suicidal ideation / command hallucinations",
    "substance_withdrawal": "Substance use; withdrawal (CIWA < 8, 72 h)",
    "aggression": "Aggressive or combative behavior",
    "sex_offender": "Registered sex offender",
    "conservatorship_fsp": "Conservatorship / FSP",
    "follow_up": "Follow-up appointments scheduled",
    "med_list_supply": "Medication list + 30-day supply",
}

# Where evidence is usually found. DOC-n are IHH's referral checklist items; the rest are page types.
DOC_TYPES = {
    "DOC-1": "IHH referral form", "DOC-2": "Face sheet / demographic page", "DOC-3": "CalOptima form / LOA / auth",
    "DOC-4": "History and physical", "DOC-5": "Progress notes", "DOC-6": "Vitals (last 24 h)", "DOC-7": "Medication list",
    "DOC-8": "PT/OT or nursing notes", "DOC-9": "Blood or wound culture", "DOC-10": "30-day medication supply",
    "labs": "Lab results", "imaging": "Imaging reports", "ekg": "EKG / ECG", "rt_notes": "Respiratory therapy notes",
    "psych_consult": "Psychiatry consult", "social_work": "Social work notes", "wound_notes": "Wound care notes",
    "mar": "Medication administration record", "orders": "Physician orders",
}

# Rules whose check depends on a date or a time window (dates are redacted in the packets)
NEEDS_DATE = {
    "MH-4": "72-hour hold after acute alcohol intoxication",
    "INF-2": "COVID swab negative within 24 hours of admission",
    "DM-3": "Insulin regimen started less than 24 hours before admission",
    "DM-4": "Follow-up within 5-7 days; no hypoglycemia in the last week",
    "CARD-1": "Blood pressure stable on oral medication for at least 24 hours",
    "CARD-6": "No IV blood pressure medicine within 24 hours",
    "INT-E2": "Wound care to arrive within 24 hours if a dressing change is due",
    "DOC-6": "Vitals from the last 24 hours",
    "RESP-3": "Oxygen tank ready the day before the client arrives",
}

# Gaps in the written rules, from the "Places where the written rules are unclear" table in admission-criteria.md
GAPS = {
    "OTH-2": "Settled: case by case; offenses involving violence likely denied. Flag for the coordinator; never auto-deny.",
    "FORM-X6": "Superseded by OTH-2 (case by case).",
    "MOB-3": "Settled: wheelchair-dependent patients who transfer and use the chair independently are eligible.",
    "MOB-4": "Settled: see MOB-3.",
    "FORM-M6": "Superseded by MOB-3 and MOB-4.",
    "FORM-X3": "Superseded by MOB-3 and MOB-4.",
    "FORM-X4": "Only the tuberculosis part falls to the form (the outline is silent on TB). MRSA is covered by INF-1 and C. diff by GI-X3, so the outline governs those.",
    "FORM-X5": "Refusing detox is listed only on the form; the outline is silent, so the form's exclusion applies.",
    "RSP-E5": "'O2 baseline of 94% or greater with physician explanation': meaning in practice not stated.",
    "DM-Q3": "The A1C sentence is cut off in the source.",
    "MH-5": "'FSP' is not spelled out; likely Full Service Partnership, a county mental-health program.",
    "DM-3": "Does not say whether the 24 hours start at the first dose or when doses stop changing.",
    "END-X3": "DKA is ineligible; does not say whether resolved DKA still excludes.",
    "DM-2": "Related to END-X3: resolved DKA not addressed.",
    "GI-X3": "C. diff is ineligible; the outline does not say whether that ends when isolation lifts or when treatment finishes. The form (FORM-X4) excludes it only until cleared by a doctor or CID. Show both to the coordinator.",
    "CARD-2": "Asks for two negative troponins, but a patient admitted for a heart attack won't have them, while history of heart attack (CIR-E7) is eligible.",
    "CIR-E7": "See CARD-2: troponin rule conflicts for patients admitted for a heart attack.",
    "INF-2": "A swab negative when the referral is sent can be more than 24 hours old by arrival.",
    "INT-X2": "'Complicated large abscess' is not defined.",
    "INT-E2": "Hard-to-reach list reads 'coccyx, , back of thighs, back, perineum': an item seems missing and the sacrum is not named. Home health wording here is 'coordinated' (see OTH-3).",
    "INT-E6": "Home health wording varies: here wound care must be 'coordinated and scheduled' (see OTH-3).",
    "OTH-3": "Home health threshold wording varies across rules: established, ordered, coordinated, coordinated and scheduled.",
    "ID-3": "Home health wording varies (see OTH-3).",
    "INT-E3": "Home health wording varies (see OTH-3).",
    "INT-E7": "Home health wording varies (see OTH-3).",
    "CIR-E5": "Home health wording varies (see OTH-3).",
}

GLOBAL_NOTES = [
    "Outcomes are approve or deny; there is no stated 're-refer when ready' for a patient who will qualify in a day or two.",
    "When the referral form (FORM-*) and the outline disagree, the outline wins. Where the outline is silent, the form's exclusion applies.",
    "Dates are redacted in the packets: rules with needs_date=true should return 'can't tell' unless the packet states the timing without a date.",
    "Ophthalmology has no ineligible conditions listed in the source. Treat that as 'none listed', not 'nothing excludes'.",
]

# Default evidence and facts by ID prefix; specific IDs override below.
PREFIX = {
    "GEN": (["DOC-1", "DOC-2", "social_work"], ["housing"]),
    "ADL": (["DOC-8", "DOC-1", "DOC-3"], ["adl_independent"]),
    "MOB": (["DOC-8"], ["walk_100ft_transfers", "dme_independent"]),
    "MH": (["DOC-4", "DOC-5", "psych_consult"], ["mental_health_stable"]),
    "COG": (["DOC-4", "DOC-5", "DOC-3"], ["aox4", "cognitive_impairment"]),
    "OTH": (["DOC-4", "DOC-5"], []),
    "EOL": (["DOC-1", "DOC-5"], ["home_health"]),
    "INF": (["labs"], []),
    "DM": (["labs", "mar", "DOC-4", "DOC-7"], ["diabetes"]),
    "ID": (["DOC-6", "DOC-9", "DOC-4"], ["vitals_last5", "isolation"]),
    "RESP": (["imaging", "DOC-6", "rt_notes"], ["oxygen", "vitals_last5"]),
    "CARD": (["DOC-6", "labs", "ekg"], ["vitals_last5"]),
    "INT": (["wound_notes", "DOC-4", "DOC-3"], ["wounds", "home_health"]),
    "OPH": (["DOC-4", "DOC-2"], ["admitting_diagnosis"]),
    "RSP": (["DOC-4", "imaging", "DOC-6"], ["admitting_diagnosis", "oxygen"]),
    "MSK": (["DOC-4", "imaging", "DOC-8"], ["admitting_diagnosis", "walk_100ft_transfers"]),
    "GI": (["DOC-4", "labs"], ["admitting_diagnosis"]),
    "END": (["DOC-4", "labs"], ["admitting_diagnosis", "diabetes"]),
    "GU": (["DOC-4", "DOC-8"], ["admitting_diagnosis", "continence"]),
    "CIR": (["DOC-4", "DOC-6", "ekg"], ["admitting_diagnosis", "vitals_last5"]),
    "NEU": (["DOC-4", "DOC-2", "DOC-5"], ["admitting_diagnosis"]),
    "FORM": (["DOC-1"], []),
    "DOC": ([], []),
}
OVERRIDE = {
    "ID-2": (["mar", "DOC-8", "DOC-5"], ["self_admin_meds"]),
    "CARD-4": (["DOC-7", "mar", "DOC-4", "labs"], ["self_admin_meds"]), "CARD-6": (["mar", "orders", "DOC-6"], ["vitals_last5"]), "ID-3": (["orders", "DOC-5", "DOC-3"], ["iv_access", "home_health"]),
    "MH-2": (None, ["si_hallucinations"]), "MH-3": (None, ["si_hallucinations"]),
    "MH-4": (["DOC-4", "DOC-5", "labs"], ["substance_withdrawal"]), "MH-5": (["DOC-4", "social_work", "psych_consult"], ["conservatorship_fsp"]),
    "COG-1": (["DOC-1", "DOC-3", "DOC-8", "DOC-5"], ["self_admin_meds"]),
    "OTH-1": (["DOC-5", "DOC-8", "social_work"], ["aggression"]), "OTH-2": (["DOC-1", "DOC-3", "social_work"], ["sex_offender"]),
    "OTH-3": (["orders", "DOC-5", "DOC-3"], ["iv_access", "home_health"]), "OTH-4": (["DOC-4", "DOC-5", "DOC-9"], ["isolation"]),
    "INF-1": (["labs"], ["mrsa_swab"]), "INF-2": (["labs"], ["covid_swab"]),
    "INT-E3": (None, ["iv_access", "home_health"]), "INT-E5": (None, ["wounds", "follow_up"]),
    "NEU-X5": (["DOC-2", "DOC-4", "DOC-5"], ["cognitive_impairment"]),
    "GU-E5": (None, ["continence", "follow_up"]),
    "FORM-M1": (None, ["housing"]), "FORM-M2": (["DOC-4", "DOC-5"], ["mental_health_stable", "vitals_last5"]),
    "FORM-M3": (["DOC-4", "DOC-5", "DOC-3"], ["aox4"]), "FORM-M4": (["DOC-8"], ["adl_independent"]),
    "FORM-M5": (None, ["self_admin_meds"]), "FORM-M6": (["DOC-8"], ["walk_100ft_transfers", "dme_independent"]),
    "FORM-X1": (["DOC-2", "DOC-4"], ["cognitive_impairment"]), "FORM-X2": (["DOC-8"], ["adl_independent"]),
    "FORM-X3": (["DOC-8"], ["walk_100ft_transfers", "dme_independent"]), "FORM-X4": (["labs", "DOC-9", "imaging"], ["tb_test", "mrsa_swab", "isolation"]),
    "FORM-X5": (["DOC-4", "DOC-5"], ["substance_withdrawal"]), "FORM-X6": (["DOC-1"], ["sex_offender"]), "FORM-X7": (["DOC-5", "DOC-8"], ["aggression"]),
    "DOC-6": (None, ["vitals_last5"]), "DOC-7": (None, ["med_list_supply"]), "DOC-10": (None, ["med_list_supply"]),
    "DOC-8": (None, ["walk_100ft_transfers", "adl_independent"]),
}


def collect(src):
    """Yield (rule, section, inferred_kind) for every rule with an id, in document order."""
    for g in src["general"]["any_of"]:
        yield g, "General admission criteria (any one)", "any_of"
    for r in src["rules"]:
        yield r, r["section"], None
    for s in src["by_system"]:
        for r in s.get("eligible", []):
            yield r, f"{s['system']}: eligible", "eligible_condition"
        for r in s.get("ineligible", []):
            yield r, f"{s['system']}: ineligible", "exclude"
    for r in src["referral_checklist"]["items"]:
        yield r, "Referral checklist", "document"
    for r in src["referral_form_screen"]["must_meet_all"]:
        yield r, "Referral form: must meet all", "must"
    for r in src["referral_form_screen"]["not_eligible_if"]:
        yield r, "Referral form: not eligible if", "exclude"


def main():
    raw = SRC.read_bytes()
    src = json.loads(raw)
    rules, enriched, sections = {}, [], {}
    for r, section, inferred in collect(src):
        rid = r["id"]
        prefix = re.match(r"[A-Z]+", rid).group(0)
        ev, facts = PREFIX.get(prefix, ([], []))
        o_ev, o_facts = OVERRIDE.get(rid, (None, None))
        kind = r.get("kind") or inferred
        entry = {
            "kind": kind,
            "kind_source": "source" if r.get("kind") else "overlay",
            "needs_date": rid in NEEDS_DATE,
            "gap": rid in GAPS,
            "evidence": o_ev if o_ev is not None else ev,
            "facts": o_facts if o_facts is not None else facts,
        }
        if rid in NEEDS_DATE:
            entry["date_note"] = NEEDS_DATE[rid]
        if rid in GAPS:
            entry["gap_note"] = GAPS[rid]
        for k in ("human_review", "superseded_by"):
            if k in r:
                entry[k] = r[k]
        rules[rid] = entry
        enriched.append({"id": rid, "section": section, "text": r["text"], **entry})
        sections.setdefault(section, []).append((rid, r["text"], entry))

    # Validation: every overlay ID exists in the source, and every hand-listed ID is real
    listed = set(NEEDS_DATE) | set(GAPS) | set(OVERRIDE)
    missing = sorted(listed - set(rules))
    bad_facts = sorted({f for e in rules.values() for f in e["facts"]} - set(FACTS))
    bad_docs = sorted({d for e in rules.values() for d in e["evidence"]} - set(DOC_TYPES))
    assert not missing, f"IDs not in source: {missing}"
    assert not bad_facts, f"unknown fact keys: {bad_facts}"
    assert not bad_docs, f"unknown evidence types: {bad_docs}"
    assert all(e["kind"] for e in rules.values()), "a rule has no kind"

    meta = {
        "about": "Local overlay on IHH's admission criteria for the Packet Triage tool. Adds fields only; rule text stays in the source file. Not an IHH document.",
        "source_file": "claude-impact-lab-oc/challenges/1-referral-intake/criteria/admission-criteria.json",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "built_on": date.today().isoformat(),
        "fields": {
            "kind": "must | exclude | document | conditional | ask | note | eligible_condition | any_of. 'kind_source: overlay' means the source had no kind and the overlay inferred it from the list the rule sits in.",
            "needs_date": "True if the check depends on a date or time window. Dates are redacted, so return 'can't tell' unless timing is stated without a date.",
            "gap": "True if IHH's written rules leave this unclear or a settled conflict applies. Show gap_note to the coordinator; never decide silently.",
            "evidence": "Where the evidence usually is (DOC-n from IHH's referral checklist, or a page type).",
            "facts": "Which of the 27 core facts the rule depends on.",
        },
        "fact_keys": FACTS,
        "evidence_types": DOC_TYPES,
        "global_notes": GLOBAL_NOTES,
    }
    (HERE / "admission-criteria.overlay.json").write_text(json.dumps({**meta, "rules": rules}, indent=1, ensure_ascii=False))
    (HERE / "admission-criteria.enriched.json").write_text(json.dumps({**meta, "rules": enriched}, indent=1, ensure_ascii=False))

    md = [
        "# IHH admission criteria with rule IDs (generated)",
        "",
        "Generated from `admission-criteria.json` by `build_overlay.py`. Rule text is IHH's wording. "
        "Tags come from the local overlay, not from IHH: **[date]** = needs a date (redacted in packets, so usually \"can't tell\"), "
        "**[gap]** = the written rules leave this unclear. If this page and IHH staff disagree, IHH staff are right.",
        "",
        "**Which wins:** " + src["precedence"],
        "",
    ]
    for section, items in sections.items():
        md += [f"## {section}", ""]
        for rid, text, e in items:
            tags = []
            if e["kind"]:
                tags.append(f"`{e['kind']}`")
            if e["needs_date"]:
                tags.append("**[date]**")
            if e["gap"]:
                tags.append("**[gap]**")
            line = f"- **{rid}** {text} " + " ".join(tags)
            if e["gap"]:
                line += f"\n  - Gap: {e['gap_note']}"
            md.append(line)
        md.append("")
    md += ["## Notes", ""] + [f"- {n}" for n in GLOBAL_NOTES] + [""]
    (HERE / "admission-criteria-with-ids.md").write_text("\n".join(md))

    kinds = {}
    for e in rules.values():
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"rules: {len(rules)} | kinds: {kinds} | needs_date: {sum(e['needs_date'] for e in rules.values())} | gaps: {sum(e['gap'] for e in rules.values())}")
    print(f"kind inferred by overlay: {sum(e['kind_source'] == 'overlay' for e in rules.values())} | rules with no evidence hint: {[k for k, e in rules.items() if not e['evidence'] and not k.startswith('DOC')]}")


if __name__ == "__main__":
    main()
