# Anchor (Team Beacon): Referral Intake for Recuperative Care (Challenge 1, revised)

> **Replaces** [01-packet-triage.md](01-packet-triage.md) and [plans/01-packet-triage-plan.md](plans/01-packet-triage-plan.md) for the event.
> Built on the official Challenge 1 folder: `claude-impact-lab-oc/challenges/1-referral-intake/`:
> - README
> - `criteria/admission-criteria.json` (rule IDs) and `.md`
> - `criteria/referral-form-and-checklist.md`
> - `criteria/childrens-admission-criteria.md`
> - `packets/README.md`
> - the event's `CLAUDE.md` and ground rules
>
> **Build window:** 9:30 AM to 4:00 PM, Saturday, October 17, 2026. Submissions are due at 4:00 PM. Judges may hand you a packet your tool has not seen.

---

## 0. Why the old plan had to change

| # | Old plan | Problem | Fix in this plan |
|---|---|---|---|
| 1 | Synthetic packets with a text layer and fake hospitals | The event gives **11 real, de-identified packets** (282 pages). They are **image-only faxes** with no text layer. Pages are crooked, sideways, upside down, or out of order | Point code at the packets folder. **Never copy packets into the team repo.** Read pages as images with Claude's vision (PDF or PNG input) |
| 2 | Extract page text with a PDF library, then string-match each quote | There is no text to extract or match | Cite page numbers. A **second Claude pass looks at the cited page image** and confirms the quote is there. Optional local OCR adds a string check. The coordinator clicks through to the page and ticks **Verified** |
| 3 | 10 invented criteria (TB in 90 days, no IV, no oxygen) | IHH's real rules differ. IV is allowed with home health. Oxygen is allowed if the hospital orders the tank. MRSA and COVID swabs are required. Walking 100 ft, AOx4, and no dementia are required | Use **IHH's rules by ID** from `admission-criteria.json`: 48 rules, plus rules by body system, the referral checklist (DOC-1 to DOC-10), and the form screen (FORM-*). **The outline wins** over the form |
| 4 | Status: Found / Missing / Unclear | Dates are blacked out, and black boxes are not missing documents | Five statuses: **Found · Unclear · Missing · Can't tell (date or time redacted) · Redacted** (a black box, never reported as missing) |
| 5 | Referral board, stages, stall math, beds | Nice later. On the day, the job is **one packet, read fast and right** | Out of scope today. Kept on the roadmap |
| 6 | 15 key fields | The real criteria need more, and the chart often contradicts the form | **27 core facts** plus the 10-document checklist, each with page citations, and a **contradiction finder** that compares form and chart |
| 7 | Golden answer key for synthetic packets | Real outcomes exist in `eval/decisions.json`: 7 approved, 4 denied, no reasons | Use decisions **only to score the tool afterward, never as input**. The tool never sees that file |
| 8 | Postgres, 22 test-first tasks | Too heavy for about 6 hours | JSON files per packet in a git-ignored `work/` folder, a small app, and 9 tasks |
| 9 | Family flag | There are no children's sample packets | Children's criteria are optional. Flag "patient under 18" and point to that document |

---

## 1. The idea in one line

**A coordinator drops in a faxed packet. In minutes they get:**
- which documents are present
- 27 key facts, each with the page it came from
- IHH's rules checked one by one with their IDs
- alerts: what's missing, what contradicts, and what can't be told
- a completeness grade: **Great / Neutral / Bad**
- a short summary and a draft request to the hospital
- a **pre-filled, fillable PDF** for a person to verify and print

**The coordinator decides. The tool never approves or denies.**

Why it matters: IHH promises hospitals an answer within **two hours**, and hospitals send the same referral to several providers.

---

## 2. Who uses it

| Who | Needs |
|---|---|
| **Referral coordinator** (main user) | Speed; every fact cited to a page; the contradiction deep in the chart surfaced; a clear list to request |
| **Clinical reviewer** (nurse or medical director) | The rule-by-rule view with red flags first; "can't tell" items called out, never guessed |
| **Hospital case manager** (indirect) | A specific request ("PT note showing distance walked"), not "send more info" |

---

## 3. What happens, step by step

1. **Drop in a packet** (a path or an upload, kept outside git).
2. **Page map.** For each page, Claude reports:
   - document type (fax cover, IHH form, CalAIM form, face sheet, H&P, PT/OT, MAR, labs, imaging, progress note, social work)
   - orientation (rotate before reading)
   - whether it's legible
   - whether it's from an earlier stay

   The coordinator sees the packet as a table of contents, not 34 random pages.
3. **Document checklist** (DOC-1 to DOC-10): Present, Missing, or N/A, with pages.
4. **Fact extraction** by document type. The 27 facts each get a status, value, pages, and a short quote. Form answers and chart answers are kept **separately**.
5. **Contradiction finder** (code). When the form and chart disagree on a fact, raise an alert. Example: the form says no cognitive impairment, but the face sheet lists dementia. **The chart wins.**
6. **Rule check** (code, by rule ID):
   - `must` rules: met, not met, or unknown
   - `exclude` rules: flag if true
   - `document` rules: present or not
   - `conditional` rules: is the arrangement confirmed? (home health, O2 tank, follow-up)
   - `ask` rules: show the question
   - Gaps in the written rules are shown as gaps, not guessed (see the "unclear" table in the criteria file).
7. **Grade + alerts + summary + hospital request.**
8. **Verify.** The coordinator opens each cited page, ticks Verified, edits values, and prints or saves the **pre-filled verification PDF**.

---

## 4. Architecture

```
packets/R01.pdf ──(pdftoppm, 150–200 dpi)──► page PNGs (work/, git-ignored)
        │
        ▼
page map ── Claude vision: {page, doc_type, orientation, legible, prior_stay}
        │
        ▼
fact extraction ── Claude vision, per document group, strict JSON schema:
        │           {fact_key, source: form|chart, status, value, page, quote}
        ▼
quote check ── second Claude pass on that page image: "Is this text on this page? yes/no"
        │       (optional: local OCR string match)
        ▼
merge.ts ── form vs chart → contradictions; redacted vs missing; can't-tell for date rules
        ▼
rules.ts ── IHH rules by ID (admission-criteria.json + local overlay: kind, needs_date, gap, evidence, facts) → met / not met / can't tell / gap / flag
        ▼
grade.ts ── completeness score → Great / Neutral / Bad (critical contradiction → Bad)
        ▼
UI (page map, facts with click-to-page, rules, alerts, summary, request draft)
        ▼
fill_pdf.py ── pre-fills the verification checklist PDF (fillable, printable)
```

- **Criteria overlay** (`criteria-overlay/`): adds fields to IHH's 155 rule IDs without editing IHH's file.
  - `kind` is filled in for the 97 rules that had none.
  - `needs_date` marks 9 rules that become "can't tell" automatically.
  - `gap` marks 26 rules where the written rules are unclear; these go to the coordinator.
  - `evidence` says which pages to check first, and `facts` links each rule to the 27 core facts.
  - The children's rules get their own JSON with `KID-*` IDs.
- **Models:** `claude-opus-5-5` for hard extraction from messy scans; `claude-sonnet-5-5` for page mapping and quote checks.
- **Storage:** `work/<packet>/pages/*.png`, `work/<packet>/review.json`. Add `work/` and `packets/` to `.gitignore`. Nothing from packets goes into commits, screenshots in the README, or the demo video beyond what the organizer allows.
- **Keys:** `ANTHROPIC_API_KEY` in `.env`.

---

## 5. Data shapes

```jsonc
// page map entry
{ "page": 4, "doc_type": "face_sheet", "orientation": 0, "legible": true, "prior_stay": false }

// fact (one per source; form and chart kept apart). Made-up example, not from a real packet
{ "key": "cognitive_impairment", "source": "chart", "status": "found",
  "value": "Dementia listed among diagnoses", "pages": [4], "quote": "<text copied from that page>",
  "quote_checked": true }

// rule result
{ "rule_id": "NEU-X5", "kind": "exclude", "status": "flag",
  "facts": ["cognitive_impairment"], "note": "Dementia is listed on the face sheet; the referral form does not mention it." }

// review
{ "packet": "Sample-01", "docs": {...}, "facts": [...], "rules": [...],
  "alerts": { "critical": [], "missing": [], "contradictions": [], "cant_tell": [], "rule_gaps": [] },
  "score": { "points": 0, "possible": 0, "pct": 0 }, "grade": "great|neutral|bad", "summary": {...} }
```

Fact statuses: `found` · `unclear` · `missing` · `cant_tell` (needs a redacted date or time) · `redacted` (black box).

---

## 6. The 27 core facts (same list as the verification PDF)

| Group | Facts |
|---|---|
| Who and why | Housing status · Admitting diagnosis |
| Cognition and function | AOx4 · Cognitive impairment or dementia · ADLs independent · Walks 100 ft and transfers independently · DME used independently · Self-administers medications |
| Care needs | Wounds (location, size, stage, who does care) · Home health arranged · Oxygen required and tank ordered · IV access or IV antibiotics · Continence, catheter, ostomy · Diabetes, insulin, 5 glucose readings |
| Stability and infection | Last 5 vital signs stable · TB test or chest X-ray · MRSA swab negative · COVID swab within 24 h · Isolation or active infection cleared |
| Behavioral | Mental health diagnosis, stable on meds · Suicidal ideation or command hallucinations · Substance use and withdrawal (CIWA < 8, 72 h) · Aggressive or combative behavior · Registered sex offender (case by case) · Conservatorship or FSP |
| Discharge readiness | Follow-up appointments scheduled · Medication list and 30-day supply |

**Field map** (which form asks what), from the CalAIM authorization form seen in packets and the IHH form RC0725:
- **Both forms ask:** housing, diagnosis, TB, wounds, O2, continence, ADLs, ambulation, diabetes, anticoagulants, substance use, mental health, cognitive impairment, sex offender, self-administered meds, and others (18 in all).
- **IHH form only:** homeless 1+ year or 4 episodes, current withdrawals, hallucinations, non-compliant or forgetful, communicable disease, length of stay authorized, attached-documents boxes.
- **CalAIM form only:** pathway, PCP and follow-ups, home health services, oriented to person/place/time/situation, tube feeding, fractures and surgery, walking distance, IV antibiotic frequency, isolation, meds through end of month, refills.
- **Chart only (no form asks):** last 5 vitals, MRSA, COVID swab, PT/OT distance and transfers, glucose x5, troponins and EKG, chest imaging, cultures, CIWA and 72 h hold, aggression, conservatorship, O2 tank delivery.

---

## 7. Grading (packet completeness, not eligibility)

| Grade | Rule |
|---|---|
| **Great** | DOC-1, 2, 3, 4, 6, 7, 8 present, **and** a fact score of 85% or more (Found = 2 points, Unclear or Can't tell = 1), **and** no unexplained contradiction. Decide within 2 hours |
| **Neutral** | Core documents present, but score is 60–84%, or one contradiction a phone call can settle. Request specific items |
| **Bad** | No IHH form, H&P, or PT/OT notes, **or** score under 60%, **or** any critical contradiction. Call the hospital before deciding |

**Score:** Found = 2 points, Unclear or Can't tell = 1, Missing = 0, divided by 2 x the facts that apply. **Redacted doesn't count against the packet.**

---

## 8. Alerts

| Type | Examples | Shown as |
|---|---|---|
| **Critical** | An `exclude` rule looks true (dementia, active infection not cleared, suicidal ideation, aggression, isolation); a `must` rule clearly not met | Red, at the top, with rule ID and page |
| **Missing documents** | No PT/OT notes, no H&P, no medication list, no IHH form (some packets have none) | Amber, with the exact request text |
| **Missing facts** | No TB result, no MRSA swab, walking distance not stated, AOx not documented | Amber, with where it should be |
| **Contradictions** | Form says X, chart says Y (cognition, ADLs, living situation, age, O2) | Amber or red, both pages side by side |
| **Can't tell** | Insulin started under 24 h ago; 72 h after alcohol; COVID swab within 24 h | Grey: "Dates are redacted in this packet" |
| **Rule gaps** | Sex offender (case by case); wheelchair users; resolved DKA; C. diff timing | Blue: "The written rules don't settle this. Coordinator decides." |

---

## 9. Quality control

- **Every fact has a page.** No page means it's not shown as Found.
- **Second look:** a separate pass confirms each quote is on its page image. If not, the fact drops to Unclear.
- **Form and chart kept apart**, so contradictions can't be averaged away.
- **People verify:** the UI and PDF have a Verified box per fact; the grade shows "x of 27 verified."
- **Scoring against IHH's real decisions** (`eval/decisions.json`, held out; only `criteria-overlay/score_against_decisions.py` opens it, and it refuses to run until all 11 reviews are saved): after reviewing all 11 packets, compare the tool's **red flags vs. ready** split to approve/deny. Report agreement and every miss honestly. **Never** feed the decisions to the model or tune prompts to them packet by packet.
- **Unseen packet test:** time one end-to-end run on a packet the team hasn't looked at, as judges may do.

---

## 10. Privacy and rules (non-negotiable)

- Packets stay in `challenges/1-referral-intake/packets/` or a local folder. **Never commit, post, or paste them**, and never put page images in the README.
- **If any page shows an identifier that was missed, stop and tell an organizer.** Don't copy, search, or try to identify anyone.
- Black box = removed for privacy, never "missing."
- Don't read `eval/decisions.json` while reviewing a packet.
- No connection to IHH systems. The hospital request is a **draft**; nothing is sent.

---

## 11. Accessibility (WCAG 2.2 AA)

- The page viewer has keyboard controls (next, previous, rotate, zoom) and announces "page 14 of 34, face sheet."
- Status uses an icon and a word, never color alone (✓ Found, ? Unclear, ✕ Missing, ⏱ Can't tell, ■ Redacted).
- The PDF has real form fields with tooltips, a logical tab order, and print-friendly contrast.

---

## 12. Build plan (about 6 hours, 4 people)

| Task | Owner | What | Done when |
|---|---|---|---|
| **T1** | B | Render pages (`pdftoppm`), page map with Claude (type, orientation, legible) | R01 shows a correct table of contents |
| **T2** | B | Fact extraction prompt + JSON schema, form and chart kept separate | 27 facts with pages for R01 and R02 |
| **T3** | B | Quote check (second pass) + optional OCR | Wrong quotes drop to Unclear |
| **T4** | A | Load `criteria-overlay/admission-criteria.enriched.json` → `rules.ts` (uses `needs_date`, `gap`, `evidence`, `facts`) | Every rule ID shows a status; date rules say can't tell; gaps go to the coordinator |
| **T5** | A | Merge: contradictions, redacted vs. missing, can't tell | Known contradiction raised as an alert |
| **T6** | A | Grade + alerts + summary + hospital request draft | Grade and alerts render for 3 packets |
| **T7** | C | UI: page map, facts with click-to-page, rule list, alerts, Verified boxes | A coordinator can verify R01 end to end |
| **T8** | D | `fill_pdf.py`: pre-fill the verification checklist PDF from `review.json` | Printable, fillable PDF per packet |
| **T9** | D | Eval: run all 11, compare to held-out decisions, write README sections (mocked parts, where it's wrong) | Agreement table + honest misses |

| Time | Milestone |
|---|---|
| 9:30 | Repo from template, `.gitignore` for `work/` and `packets/`, download packets, T1 starts |
| 11:00 | Page map works on 2 packets; rules file loaded |
| 12:30 | **Check-in:** R01 end to end, ugly but cited |
| 2:30 | All 11 packets reviewed; PDF pre-fill works |
| 3:15 | Eval table, unseen-packet timing, accessibility pass |
| 3:45 | **Freeze, push, submit before 4:00** |

If you fall behind, cut the UI polish first, then OCR. **Never cut** page citations, the contradiction finder, or the "can't tell" status.

---

## 13. Demo script (3 minutes)

1. **The problem (20 s):** "A long, sideways fax. Two hours to answer. The fact that decides it is deep in the chart, not on the form."
2. **Run a packet (60 s):** the page map appears, then the documents checklist, then facts with page cites.
3. **The catch (40 s):** a red alert says the form and the chart disagree. Click it, and both pages open side by side.
4. **Honesty (20 s):** "Can't tell: dates are redacted." "Rule gap: the written rules don't settle this."
5. **Hand-off (20 s):** Grade: Bad. A draft hospital request lists 3 specific items. Print the pre-filled verification PDF.
6. **Trust (20 s):** the eval table against IHH's real decisions, misses included.

---

## 14. Status: what's done (Oct 17)

| Piece | Status | Where |
|---|---|---|
| This revised plan | Done | This file |
| Field map: common vs. separate fields across the IHH form, CalAIM form, and chart | Done | Section 6; PDF page 5 |
| Grading rubric (Great / Neutral / Bad) and alert types | Done | Sections 7–8 |
| **Blank fillable, printable verification checklist PDF** (5 pages, 151 fields) | Done | `packet-review/IHH-referral-packet-verification-checklist.pdf` (generator: `make_checklist.py`) |
| Packet-by-packet review of R01–R11 (grades, summaries, alerts, pre-filled PDFs) | **Ready to resume**: a possible missed date element was reported to an organizer, who confirmed it is fine | `packet-review/notes.md` (local only) |
| **Anchor Board** (draft dashboard): queue with 2-hour answer clock, grades, alerts, "what's needed to complete" per packet, grading guide, staff guide, IT guide | Done, on **made-up sample packets only** | [Dashboard](https://claude.ai/artifact/NVUonEKc7TRXnVU9QafCVG); data in `triage-dashboard/` |
| **Criteria overlay**: kinds for 97 untyped rules, 9 date-dependent rules, 26 gaps, evidence and fact links for all 155 IDs; children's criteria as JSON (64 `KID-*` rules); rules with IDs as markdown | Done | `criteria-overlay/` |
| Held-out scorer (`score_against_decisions.py`) | Written, not run (no reviews yet) | `criteria-overlay/` |
| Suggestions for the organizers | Drafted, not sent | `criteria-overlay/ORGANIZER-NOTE.md` |
| Packets copied into `challenges/1-referral-intake/packets/` | **To do (by you)**; the automated copy was blocked | — |
| **Intake app** (any-format upload, fax-to-email, tiered follow-ups, immediate red flags) **plus seven speed-ups**: pre-read on arrival with quote check; ask the hospital now; side-by-side fact check; resent pages join the referral; fast lane; clinical vs. coordinator owners; keyboard flow. Dry run only | Working local prototype; 48 tests pass; end-to-end run on made-up samples | `intake-pipeline/` |
| Team app (T1–T9) | Not started | Team repo |

---

## 15. Questions for IHH staff

1. Which three facts most often decide a denial in practice?
2. When the form and chart disagree, do coordinators call the hospital first, or decide from the chart?
3. Is "Neutral, request items" a real outcome for you, or is every referral approve/deny within two hours?
4. How do you handle a packet with no IHH referral form?
5. Would a pre-filled verification sheet fit how coordinators work today (paper, screen, both)?
