# Anchor: executive summary

**Team Beacon · Orange County Claude Impact Lab · October 17, 2026 · Challenge 1 (referral intake), built for Illumination Health + Home (IHH)**

**Anchor** helps IHH's intake team read hospital referrals faster and surer, keep hospitals informed, and answer inside the 2-hour promise.

## Who IHH is

A Santa Ana nonprofit that pairs **housing, healthcare and case management** for people experiencing homelessness. Its **recuperative care** gives people leaving the hospital a safe place to heal: people too sick for the street, but not sick enough to stay in a hospital. Studies link recuperative care to fewer hospital days and readmissions. California's Medicaid agency found a **29.2%** net cost reduction (preliminary). IHH served **2,287** people in recuperative care in 2024. More in `ABOUT-IHH.md`.

## The problem

- **Hospitals refer patients to recuperative care with referral packets.** Packets run 14 to 34 faxed pages (the Challenge 1 README rounds this to 15 to 35), often crooked, sideways or out of order, and at least one has no IHH referral form.
- **A coordinator reads each packet by hand** against IHH's criteria (155 rules). The deciding fact is often deep in the chart, not on the form.
- **IHH promises hospitals an answer within 2 hours.** Hospitals send the same referral to several providers, so a slow answer can mean a patient leaves with nowhere to go.

## What Anchor does

1. **Rule overlay:** IHH's 155 rules, tagged so a tool knows:
   - **9** rules that need a date. Dates are redacted, so the tool says "can't tell" instead of guessing.
   - **26** places where the written rules are unclear. These go to a person.
   - where the evidence usually is, and which of **27** core facts each rule depends on
2. **Verification checklist:** a fillable, printable form (5 pages, 151 fields) with a **Great / Neutral / Bad** completeness grade, a to-do list of missing items, and a Verified box for every fact.
3. **Anchor Board:**
   - a queue sorted by patient-need priority, with a 2-hour answer clock
   - a to-do list for every incomplete packet
   - a packet view with summary, missing information, medications, history and an email log
   - staff and IT guides, and accessibility built toward WCAG 2.2 AA (not yet tested with assistive-technology users)
4. **Anchor intake app:**
   - takes referrals in any common format, including fax-to-email
   - sends a receipt at 0 minutes, requests missing items at 30 and 60, and escalates at 60, 90, 110 and 120
   - **raises red flags immediately**: to the clinical reviewer at once, and to the hospital as soon as a clinician confirms, so the question is answered before the clock runs out

## Why it can be trusted

- **Every rule is cited by IHH's own ID.** Every fact must point to a page. "Unknown" and "can't tell" are real answers.
- **People decide.** The tools never approve or deny.
- **Nothing is sent, and the real packets are never published.** Messages are drafts in an outbox. With an API key, page images (pre-read) and referral details (Ask Anchor) go to the Claude API, so use only de-identified data.
- **Checked:**
  - 36 automated tests pass
  - an independent verifier moved the rule work from FAIL to PASS WITH FIXES
  - IHH's real decisions are held out for scoring only

## What is real today, and what is mocked

| Real | Mocked |
|---|---|
| Rule overlay, verification checklist, intake pipeline (local), held-out scorer | Triage board data (10 made-up packets); message sending (dry run); review of the 11 real packets (organizer check cleared; ready to resume) |

## What we need from IHH

1. The deciding facts behind a few past decisions, so the tool is right for the right reason.
2. Whether "Neutral, request items" fits how coordinators work, or whether every referral must be approve or deny within 2 hours.
3. Sign-off on message wording, the follow-up times, and the channel a pilot would use (secure email or e-fax under a business associate agreement).

**Day-one value:** coordinators can use the verification checklist today. The rule overlay and intake pipeline are ready to connect to a pilot.
