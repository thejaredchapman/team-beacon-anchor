"""Score finished packet reviews against IHH's real decisions, after the fact.

This is the ONLY code that should open eval/decisions.json. The review tool never reads it.
It refuses to run until every packet has a saved review, so decisions can't leak into reviewing.

Each review is work/<packet>/review.json with at least:
  {"packet": "R01", "readiness": "ready" | "needs_info" | "red_flags", "grade": "great" | "neutral" | "bad",
   "red_flag_rules": ["NEU-X5", ...]}

Run:  python3 score_against_decisions.py --work ../../packet-review/work
"""
import argparse
import json
from pathlib import Path

DECISIONS = Path(__file__).resolve().parents[2] / "claude-impact-lab-oc/challenges/1-referral-intake/eval/decisions.json"


def norm(decision):
    d = str(decision).strip().lower()
    if d.startswith("approv") or d.startswith("accept"):
        return "approved"
    if d.startswith("den") or d.startswith("declin") or d.startswith("reject"):
        return "denied"
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, help="folder holding <packet>/review.json")
    args = ap.parse_args()
    work = Path(args.work)

    # Check every review exists BEFORE opening the decisions file.
    wanted = [f"R{i:02d}" for i in range(1, 12)]
    reviews = {}
    for pid in wanted:
        f = work / pid / "review.json"
        if not f.exists():
            raise SystemExit(f"Not scoring: no saved review for {pid}. Finish all {len(wanted)} reviews first, so decisions can't influence reviewing.")
        reviews[pid] = json.loads(f.read_text())

    decisions = json.loads(DECISIONS.read_text())["packets"]
    extra = sorted({p["packet_id"] for p in decisions} - set(wanted))
    if extra:
        raise SystemExit(f"decisions.json lists packets this script doesn't expect: {extra}. Update the fixed list.")

    rows, agree = [], 0
    for p in decisions:
        pid, truth = p["packet_id"], norm(p["decision"])
        r = reviews[pid]
        flagged = r.get("readiness") == "red_flags"
        # Agreement: red flags should line up with denials; ready or needs-info with approvals.
        ok = (truth == "denied" and flagged) or (truth == "approved" and not flagged)
        agree += ok
        rows.append((pid, truth, r.get("readiness", "?"), r.get("grade", "?"), ", ".join(r.get("red_flag_rules", [])) or "-", "yes" if ok else "MISS"))

    print(f"{'Packet':<7} {'IHH':<9} {'Tool readiness':<15} {'Grade':<8} {'Red-flag rules':<28} Agree")
    for row in rows:
        print(f"{row[0]:<7} {row[1]:<9} {row[2]:<15} {row[3]:<8} {row[4]:<28} {row[5]}")
    print(f"\nAgreement: {agree} of {len(rows)}. With only {len(rows)} packets, each one moves this by about {round(100 / len(rows))} points; review every MISS by hand.")
    print("A match can still be right for the wrong reason: ask IHH staff for the deciding facts and compare to red_flag_rules.")


if __name__ == "__main__":
    main()
