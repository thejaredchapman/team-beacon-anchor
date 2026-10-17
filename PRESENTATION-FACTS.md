# Presentation facts: Anchor (Team Beacon)

**Opening line:** "We're Team Beacon, and this is Anchor: it helps IHH's intake team answer hospital referrals faster and surer, inside the 2-hour promise."

Every number you might say, where it comes from, and how to say it. If a number isn't on this page, don't say it.

Judging weights: **Day-one impact 40%** · **Product and idea 35%** · **Clarity of the demo 25%** (event `docs/judging.md`). Finalists demo between 4:30 and 5:30 PM. Slides without a working demo don't place. Judges may hand you a referral packet your tool hasn't seen.

## About IHH (opening line)

| Say this | Source |
|---|---|
| IHH is a Santa Ana nonprofit that pairs housing, healthcare and case management for people experiencing homelessness. | `docs/background.md` (housing, healthcare); IHH website, https://illuminationhealthhome.org/, read Oct 2026 (case management) |
| Recuperative care is a safe place to heal for people too ill to recover on the street, but who don't need a hospital: a bed, meals and health monitoring. | NHCHC and DHCS, via `docs/background.md` |
| IHH served **7,282** clients in 2024, **2,287** in recuperative care. | IHH 2024 Impact Report, via `docs/background.md` |

**Careful:** IHH's website home page shows different, undated figures (6,826 and 2,329). Use the 2024 numbers and name the year.

## Facts about the problem

| Say this | Source |
|---|---|
| IHH promises hospitals an answer within **2 hours** of receiving a referral. | IHH referral form RC0725 |
| Hospitals send the same referral to several providers, so a slow answer can mean the patient leaves with nowhere to go. | Challenge 1 README |
| The 11 real packets total **282 pages**, from **14 to 34 pages** each (the Challenge 1 README rounds this to 15 to 35). They're image-only faxes: crooked, sideways, out of order, and at least one has no IHH referral form. | packets README |
| IHH approved **7** of the 11 and denied **4**. No reasons were written down. | Challenge 1 README |
| IHH's rules run to **155** rule IDs. Its two rule documents don't always agree; the internal outline wins. | `admission-criteria.json`, `.md` |
| California law requires hospitals to plan a safe discharge for patients who are homeless and to send the receiving provider their care information. That's the referral packet. | Health and Safety Code 1262.5, via `docs/background.md` |
| Orange County counted **6,321** people experiencing homelessness in January 2026; **3,065** were unsheltered. | County of Orange, via `docs/background.md` |
| Respite care patients spent **3.7** hospital days over the next year, against **8.3** with usual care (Chicago, 225 patients). | Buchanan et al., 2006 |
| California's Medicaid agency found recuperative care associated with a **29.2%** net cost reduction (preliminary). | DHCS fact sheet, October 2025 |

## Facts about Anchor

| Say this | Backed by |
|---|---|
| The rule overlay tags all **155** IHH rules: **97** given a type, **9** that need a date (the tool says "can't tell"), **26** gaps where the written rules are unclear. | `criteria-overlay/`; verifier re-check |
| The verification checklist has **27** core facts, **10** documents and **151** fillable fields, on screen or on paper. | `IHH-referral-packet-verification-checklist.pdf` |
| Grades: **Great** (all 7 core documents, a fact score of 85%+ (found = 2 points, unclear or can't tell = 1), no conflicts), **Neutral** (everything else), **Bad** (a critical alert, a missing core document, or under 60%). | Plan section 7; board |
| Priority by patient need: discharge today +3 (tomorrow +2), clock late +3 (at risk +2), unhoused +1, high care need +1, recent repeat episode +1. **P1** is 6+ points, **P2** 3–5, **P3** 2 or less. | Board, How grading works |
| The intake app reads PDF, multi-page TIFF faxes, phone photos, Word, text, email and zip, and turns faxes and photos into PDFs. | `intake-pipeline/`; tests |
| Follow-ups: receipt at **0**, requests at **30** and **60**, escalation at **60**, **90**, **110** and **120** minutes. A red flag the pre-read finds goes to the clinical reviewer **immediately**, and to the hospital once a clinician confirms; a red flag staff add goes to the intake team and hospital at once. | `pipeline/notify.py`; end-to-end run |
| **36** automated tests pass. | `cd intake-pipeline && python3 -m unittest discover -s tests -t .` |
| An independent verifier first failed our rule work, then passed it after fixes. | `verification/` (local only) |

## Say what is mocked (judges trust this)

- The triage board uses **10 made-up packets**. Real packets can't go on a published page.
- Messages are **written to an outbox, not sent**. The event forbids real sending.
- The **review of the 11 real packets** paused while an organizer checked a possible missed date in one packet. The organizer cleared it; the review can resume.
- Accessibility is built to WCAG 2.2 AA but **not yet tested with screen-reader users**.

## Don't say

- "It approves or denies referrals." A coordinator always decides.
- "It's HIPAA compliant." It's a prototype; a pilot needs an approved channel and agreements.
- Any accuracy percentage against IHH's decisions. We haven't scored them.
- Any fact about a real packet's patient. Ever.

## Three-minute demo script

0. **Before you start:** type your name in "Working as" at the top and press Save. Every action except the clock needs a name.
1. **Problem (25 s):** "A long, sideways fax. Two hours to answer. The deciding fact is often deep in the chart, not on the form."
2. **Intake (35 s):** Drop a fax email into the inbox and press **Check fax inbox**. It becomes a 3-page PDF, and the receipt is written to the outbox.
3. **Red flag (30 s):** Add a red flag. A staff-added red flag tells the intake team and the hospital immediately; one the pre-read finds goes to the clinical reviewer first and reaches the hospital only after they press Confirm. Open the hospital one: "This is not a decision."
4. **Clock (20 s):** Advance the clock: requests at 30 and 60, escalation at 90, 110 and 120.
5. **Triage Board (40 s):** Show the queue sorted by patient need. Open a Bad packet: missing information first, priority points, the to-do list with rule IDs.
6. **Trust (30 s):** Show the verification checklist, the verifier going from FAIL to PASS WITH FIXES, and one line on what's mocked.

## Questions judges may ask

| Question | Answer |
|---|---|
| Could IHH use this on day one? | Yes, the verification checklist works on paper today. The pipeline and rule overlay are ready to connect to a pilot channel IHH approves. |
| How do you stop AI mistakes? | Every fact needs a page. Date-dependent rules say "can't tell". Gaps go to a person. An independent verifier checks claims. IHH's decisions are held out. |
| What if a fax is unreadable? | The file is kept, marked "ask the hospital to resend", and added to the to-do list, so it goes out with the next hospital request. |
| What about privacy? | Referral IDs only, no names in messages. Nothing is sent. Files are stored on this computer, but with an API key the pre-read sends page images, and Ask Anchor sends referral details, to the Claude API. Use only made-up or de-identified data; a pilot needs IHH's approval for API use. |
| Why not auto-decide? | IHH's rules have gaps and judgment calls (sex offender status is case by case). People decide; the tool makes the decision faster and better informed. |
| How did you build it? | See `HOW-THIS-WAS-BUILT.md`. |
| Why "Anchor"? | It holds the referral steady: every fact anchored to its page, every hospital kept in the loop, so patients don't drift back to the street. (Say this only if asked.) |
