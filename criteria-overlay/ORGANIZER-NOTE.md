# Suggestions for the Challenge 1 materials (draft for organizers)

Thank you for the packets and criteria. A team found these while building. None is urgent.

## 1. Possible missed date element (resolved)

Discussed with an organizer in person on October 17; they confirmed it's fine. Kept here for the record. A README line on how to treat date-like numbers in charts would still help other teams.


## 2. `admission-criteria.json`

- 97 of 155 rules have no `kind`: the 71 by-system eligible and ineligible items, plus GEN-1 to GEN-3, DOC-1 to DOC-10, FORM-M1 to FORM-M6 and FORM-X1 to FORM-X7. Suggest `exclude` for ineligible items, `eligible_condition` for eligible ones, and `any_of`, `document`, `must` or `exclude` for the general, checklist and form-screen lists.
- Only OTH-2 and NEU-X6 carry `human_review`, but the markdown's "unclear" table lists about 15 gaps. A `gap` flag with a short note on each would let tools show the gap instead of guessing.
- Rules that depend on a date or hours (MH-4, INF-2, DM-3, DM-4, CARD-1, CARD-6, INT-E2, RESP-3, DOC-6) could carry `needs_date: true`, since dates are redacted.
- An `evidence_docs` hint per rule (MOB-1 to DOC-8, INF-1 to labs) would help tools look in the right place.
- The Ophthalmology "ineligible" list is empty. A note saying "none listed in source" avoids reading it as "nothing excludes".
- A `version` and transcription date would help if IHH revises the rules.

## 3. Markdown and children's criteria

- `admission-criteria.md` shows no rule IDs, so staff can't match it to what a tool reports. Showing IDs inline would help.
- The children's criteria have no JSON or IDs. Oppositional defiant disorder appears on both the accepted and ineligible lists.

## 4. Eval

- `decisions.json` has approve or deny only. One or two deciding facts per packet, with rule IDs, from IHH staff would let teams check that a tool is right for the right reason.
- With 11 packets (7 approved, 4 denied), suggest teams report each miss rather than a percentage.

## 5. README

- It says referrals are "15 to 35 faxed pages"; R05 is 14 pages. "14 to 34" matches the packets.
- A short "how to check your tool" section could help: never feed the decisions to the tool, score only after all reviews are saved, and time an end-to-end run on an unseen packet.

We built a local overlay with these additions (IHH's files untouched) and are happy to share it.
