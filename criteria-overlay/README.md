# Criteria overlay for Packet Triage

A local layer on top of IHH's admission criteria. **IHH's files are not edited.** Everything here reads them and adds fields our tool needs.

| File | What it is |
|---|---|
| `admission-criteria.overlay.json` | Extra fields for all 155 rule IDs: `kind` (filled in for the 97 rules that had none), `needs_date` (9 rules), `gap` + `gap_note` (26 rules), `evidence` (where to look), `facts` (which of the 27 core facts it depends on) |
| `admission-criteria.enriched.json` | Source rule text merged with the overlay, one list, for tools |
| `admission-criteria-with-ids.md` | Readable rules with IDs and [date] / [gap] tags, for staff |
| `childrens-admission-criteria.json` | The children's criteria with local `KID-*` IDs (64 rules), including the ODD conflict as a gap and 4 time-dependent rules |
| `score_against_decisions.py` | The only code that opens `eval/decisions.json`. It first checks that reviews for R01 to R11 all exist, and only then opens the file |
| `build_overlay.py`, `build_childrens.py` | Rebuild the files above |
| `ORGANIZER-NOTE.md` | Suggested fixes to send to the organizers |

## How the tool uses it

Check in this order for each rule:

1. **Superseded** (`superseded_by`): skip it and use the rule it points to. FORM-X6, FORM-X3 and FORM-M6 never raise alerts on their own.
2. **Gap or human review** (`gap: true` or `human_review: true`): show the note and send it to the coordinator as a **Rule gap**. The tool never decides it, even if the rule is an exclusion (for example NEU-X6, OTH-2).
3. **Needs a date** (`needs_date: true`): return **can't tell** unless the packet states the timing without a date.
4. **Exclusion that looks true** (`kind: exclude`): raise a **Critical** alert, with the page.
5. Everything else: met, not met, or unknown.

`evidence` tells the tool which pages to check first (for example MOB-1 goes to PT/OT notes). `facts` links each rule to the 27 core facts on the verification checklist.

## Rebuild

```bash
python3 build_overlay.py      # checks every hand-listed rule ID exists in IHH's source, and that fact keys and evidence types are in the overlay's own lists
python3 build_childrens.py
```

`source_sha256` in the overlay records which version of IHH's file it was built from. If the event's JSON changes, rebuild.
