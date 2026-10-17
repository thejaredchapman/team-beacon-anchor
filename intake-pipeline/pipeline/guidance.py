"""The built-in "what to do next" rule, shared by the referral page and Ask Anchor."""
from . import rules


def next_step(con, ref, g=None, run=None):
    rid = ref["id"]
    g = g or rules.grade(con, rid)
    run = run if run is not None else con.execute("SELECT * FROM preread_runs WHERE referral_id=?", (rid,)).fetchone()
    if ref["status"] != "open":
        return f"Done. Decision recorded: {ref['decision']}."
    if run and run["status"] == "running":
        return f"Reading the packet: {run['step']}. Reload this page in a moment."
    if con.execute("SELECT 1 FROM flags WHERE referral_id=? AND type='red' AND approved=0 AND resolved_at IS NULL", (rid,)).fetchone():
        return "Clinical reviewer: check the possible red flag and confirm or dismiss it (step 1)."
    pending = con.execute("SELECT COUNT(*) FROM flags WHERE referral_id=? AND type='missing' AND approved=0 AND resolved_at IS NULL AND IFNULL(source,'')!='internal'", (rid,)).fetchone()[0]
    if pending:
        return f"Coordinator: send the request for {pending} missing item(s) now, so the hospital starts gathering them (step 1)."
    if g.get("fast_lane"):
        return "Fast lane: everything is here and nothing is flagged. Glance at the facts and decide on one screen."
    if run and run["status"] in ("manual", "error"):
        return "Review by hand: check the pages, add missing items, then decide."
    return "Check the facts against their pages (step 2), settle anything open, then decide (step 5)."
