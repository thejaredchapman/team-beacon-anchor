# How Anchor was built

Team Beacon's build story for **Anchor**, our referral intake tool for IHH: what we started from, what we read, the order of work, the tools, how we checked it, and what we chose not to do. Written so IHH or another team can pick it up.

**Scope:** Challenge 1, referral intake.

## The starting point

We began with a Packet Triage design and build plan written before the event. It was thorough, but written for a generic setting, with synthetic data and invented rules.

## Step by step

### 1. Learn who IHH is
- We read six pages of IHH's public website: home, Get Help Now, housing services, healthcare services, about, and contact.
- We noted IHH's programs, its Orange County service area, its published intake routes, and some inconsistencies on the site (board chair names, rating figures).
- We re-aimed the plan at IHH: its roles, its locations and its recuperative care intake.

### 2. Read the event's Challenge 1 materials, carefully
- We read IHH's admission criteria (155 rule IDs), the referral form, and the packets README.
- We began reading the 11 real de-identified packets.
- The event rules say to stop and tell an organizer about any possible missed identifier. **We stopped** and flagged it. An organizer later confirmed it is fine, so the review can resume.
- While paused, we built a **fillable, printable verification checklist** (5 pages, 151 fields) from the public criteria only. It includes a field map showing which facts both forms ask, which only one form asks, and which only the chart can answer.
- We rewrote the plan for the real conditions:
  - image-only faxes
  - IHH's rule IDs
  - five statuses: Found, Unclear, Missing, Can't tell, Redacted
  - a completeness grade of Great, Neutral or Bad
  - IHH's decisions held out from the tool

  → `01-packet-triage-v2.md`

### 3. Build the Anchor Board (on made-up samples)
- The real packets can't go on a published page, so we wrote 10 clearly labeled made-up sample packets.
- The board shows:
  - a queue with a 2-hour answer clock
  - grades, with a to-do list for every incomplete packet
  - a priority based on patient need (P1 Urgent, P2 High, P3 Routine)
  - a click-through packet view: summary, missing information, priority points, patient details, a mock fax PDF, an email log, page map, medications, and history with recent episodes
  - staff and IT guides in plain words
- **Accessibility:** we added a WCAG 2.2 AA layer:
  - keyboard tabs and skip links
  - focus that survives redraws
  - captions and row headers on tables
  - announcements for screen readers
  - a symbol and a word with every color
  - high-contrast mode, reduced motion, and larger tap targets

### 4. Add an independent checker
- We wrote an **`ihh-verifier` subagent**. It breaks work into claims, checks each one against its primary source, enforces 12 hard rules, and writes a prioritized correction plan.
- We built a **criteria overlay** adding the fields a tool needs to all 155 rule IDs: type of rule, date-dependent rules, gaps in the written rules, where evidence lives, and links to the 27 core facts. It also turns the children's criteria into JSON.
- **The verifier's first run said FAIL:**
  - two wrong claims in the organizer note
  - wrong fact links on ID-2 and ID-3
  - seven smaller issues
- We fixed the main items. **The second run said PASS WITH FIXES**, after rebuilding the files independently and getting byte-identical results.

### 5. Build the intake and follow-up pipeline
- A local web app that accepts PDF, multi-page TIFF faxes, photos (including iPhone HEIC), Word, text, email and zip.
- It identifies files by their contents, never runs them, and turns faxes and photos into PDFs.
- **Fax-to-email** runs through an inbox folder that stands in for the mailbox.
- **Tiered follow-ups inside the 2-hour promise:**
  - receipt at 0 minutes
  - requests for missing items at 30 and 60
  - escalation at 60, 90, 110 and 120
  - immediate red-flag messages: a flag staff add goes to the intake team and the hospital at once; a flag the pre-read finds goes to the clinical reviewer at once, and to the hospital once a clinician confirms it
- **Every internal message goes to the IHH Referral Intake team.** A "for:" line says which role should act.
- **Dry run only:** every message is a file in `outbox/`.
- 48 unit tests pass (`cd intake-pipeline && python3 -m unittest discover -s tests -t .`), and a full end-to-end run produced every tier in order.

## Tools

| Tool | Used for |
|---|---|
| Claude Code (Claude Opus 5.5) | Planning, writing, code, data checks, coordinating the work |
| A web-reading helper agent | Reading IHH's website |
| claude.ai pages (artifacts) | The Anchor Board |
| Claude API (Sonnet, Opus, Haiku) | The intake app's pre-read and the Ask Anchor helper |
| Verifier subagent | Independent claim-by-claim checks |
| Python: reportlab, pypdf, Pillow, sqlite3 | PDFs, fax conversion, the pipeline |
| macOS `sips`, `textutil`; `pdftoppm` | Photo and Word conversion; previews |
| Node | Syntax checks and running the board's scoring code on samples |

## How we kept it honest

- **Sources first.** Every rule comes from IHH's criteria by ID. "Unknown" is a real answer.
- **The math was run, not trusted:**
  - the grading and priority code was run on the samples
  - the overlay was rebuilt and compared
  - the pipeline has tests
- **Made-up data is labeled** everywhere it appears.
- **An independent verifier** checked the overlay, and we fixed what it found.
- **We reported our own mistakes:**
  - an invented rule ID in an early draft was replaced with the real one (NEU-X5)
  - a quote bug that would have broken the board was fixed before publishing
  - wrong rule IDs in the sample alerts were corrected against the criteria file

## What we chose not to do, or couldn't

- **No real sending.** Email and fax senders are stubs that refuse to run, as the event rules require.
- **No real packets on any published page.** The board uses made-up samples. Real packets stay local.
- **No peeking at IHH's decisions.** Only a scorer opens that file, and only after all reviews exist.
- **The packet review paused** until an organizer cleared a question about one packet (cleared Oct 17; not yet resumed).
- **The automated packet copy was blocked** by a safety check. The user copies the files by hand.
- **Not done:** the team's own app (the remaining tasks in the plan), automatic links from the triage tool into the pipeline, fluent review of the Spanish, and testing with screen-reader users.

## If you pick this up

1. Start at [START-HERE.md](START-HERE.md).
2. Run the verifier on anything before sharing it.
3. Ask IHH the open questions listed in START-HERE.
4. Build on Anchor's tools against `criteria-overlay/admission-criteria.enriched.json`. Write `review.json` files the board and pipeline can read.
