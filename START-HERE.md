# Start here: Anchor (Team Beacon)

Orange County Claude Impact Lab · Saturday, October 17, 2026 · with Illumination Health + Home (IHH)

**Team Beacon** built **Anchor**, a referral intake tool for IHH's recuperative care (Challenge 1). **Our team is working only on referral intake.** Everything below serves that challenge.

No real patient information is in any of these files or pages. The 11 real referral packets, the packet review, and the verifier reports stay on the local computer only and are never shared.

## Read these first

| Document | For | What it is |
|---|---|---|
| [EXECUTIVE-SUMMARY.md](EXECUTIVE-SUMMARY.md) · [PDF](EXECUTIVE-SUMMARY.pdf) | IHH, judges | One page: who IHH is, the problem, what we built, proof, next steps |
| [ABOUT-IHH.md](ABOUT-IHH.md) | Everyone | What IHH is, its programs, and how it benefits people and Orange County, with sources |
| [PRESENTATION-FACTS.md](PRESENTATION-FACTS.md) | Whoever presents | Every number you can say and its source; demo script; judge questions |
| [HOW-THIS-WAS-BUILT.md](HOW-THIS-WAS-BUILT.md) | Team, IHH, whoever continues | Sources, steps, tools, checks, what was paused or blocked |

## Anchor, piece by piece

| Piece | Status | Where |
|---|---|---|
| Plan (event version) | Current | [01-packet-triage-v2.md](01-packet-triage-v2.md) |
| Rule overlay: 155 IHH rule IDs with type, date-dependence (9), gaps (26), evidence and fact links; children's rules as JSON | Done; verified **PASS WITH FIXES** | [criteria-overlay/](criteria-overlay/README.md) |
| Fillable, printable verification checklist (5 pages, 151 fields, Great / Neutral / Bad grade) | Done | `../packet-review/IHH-referral-packet-verification-checklist.pdf` (local only) |
| Triage board: queue, 2-hour clock, priority, grades, what's missing, packet view, email log, staff and IT guides, accessibility | Draft on **10 made-up packets** | https://claude.ai/artifact/NVUonEKc7TRXnVU9QafCVG |
| **Intake app:** any-format upload, fax-to-email, pre-read on arrival, one-click hospital requests, side-by-side fact checking, resent pages that join the referral, fast lane, owners, keyboard flow, tiered follow-ups and immediate red flags. Dry run | Working local prototype; 38 tests pass | [intake-pipeline/](intake-pipeline/README.md) |
| Held-out scorer (opens IHH's decisions only after all 11 reviews exist) | Written, not run | `criteria-overlay/score_against_decisions.py` |
| Review of the 11 real packets | **Ready to resume**: an organizer confirmed a possible date element in one packet is fine (Oct 17) | `../packet-review/notes.md` (local only) |
| Suggestions for the organizers | Drafted, not sent | [criteria-overlay/ORGANIZER-NOTE.md](criteria-overlay/ORGANIZER-NOTE.md) |
| Verifier subagent and reports | Done | `../.claude/agents/ihh-verifier.md`, `../verification/` (local only) |

## Run things locally

```bash
cd saturday-oct17-build/intake-pipeline
python3 make_samples.py && INTAKE_PORT=8777 python3 server.py     # open http://127.0.0.1:8777
python3 -m unittest discover -s tests -v

cd ../criteria-overlay && python3 build_overlay.py && python3 build_childrens.py
cd .. && python3 make_exec_summary_pdf.py                          # rebuild the one-page PDF
```

## Open items

1. ~~Tell an organizer about a possible missed date element~~: done; the organizer confirmed it's fine. The packet review can resume.
2. **Copy the 11 packets** into `claude-impact-lab-oc/challenges/1-referral-intake/packets/` yourself. The automated copy was blocked by a safety check.
3. **Ask IHH:** the deciding facts behind a few decisions; whether "request items" fits their workflow; sign-off on message wording, tier times and the pilot channel.
4. Build the team app (tasks T1–T9 in the plan). Fill in the team README from the event template, and submit before 4:00 PM.
5. Share the triage board from its Share menu before others can open it.
