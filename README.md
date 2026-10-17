# Anchor

> For Illumination Health + Home's referral intake team: Anchor reads hospital referral packets, shows each fact next to the page it came from, and drafts every update to the hospital inside IHH's 2-hour promise (a person sends them through IHH's approved channel).

**Team:** Beacon
**Members:** Jared Chapman, Lei Lu, Nelson Navarrate, Alan Zhang
**Challenge:** 1 Referral intake
**Built at:** Orange County | Claude Impact Lab, October 17, 2026, with Illumination Health + Home

**Start here:** clone or download this repo, then open [`ANCHOR.html`](ANCHOR.html) in a browser (GitHub shows its source, not the page). It holds the executive summary, the Anchor Board, the intake app guide, our checks, how we built it, about IHH, presentation facts, links to every file, and the team. The board is also online: [Anchor Board](https://claude.ai/artifact/NVUonEKc7TRXnVU9QafCVG).

## The problem

An IHH intake coordinator gets hospital referral packets of 14 to 34 faxed pages, often sideways or out of order, and has to check them by hand against 155 admission rules. The deciding fact is often deep in the chart, not on the referral form. IHH promises hospitals an answer within 2 hours, and a slow answer can mean a patient leaves with nowhere to go.

## What we built

- **Anchor intake app** ([`intake-pipeline/`](intake-pipeline/README.md)): a local web app. Referrals arrive in any common format, including fax-to-email. Claude pre-reads the packet on arrival: it maps the pages, finds 27 core facts with page and quote, and checks each quote is really on its page. Staff check each fact beside its page, send the hospital one request for what's missing, and decide. Hospital messages are drafted on a tiered 2-hour ladder, and red-flag drafts are written at once. **Dry run: nothing is ever sent.**
- **Anchor Board** ([`triage-dashboard/`](triage-dashboard/)): a queue sorted by patient need with a 2-hour clock, a Great / Neutral / Bad completeness grade, a to-do list per packet, and a packet view. Built on 10 made-up sample packets. On the Board tab of `ANCHOR.html`, packet details open in a pop-up, a ☰ menu holds the grading, staff and IT guides, and the **Ask the board** helper explains grades, priority, the answer clock and what to do first for the open packet: Claude answers on claude.ai (on the viewer's own account, with their permission) or through the local `board_server.py`; built-in answers work anywhere else.
- **IHH rule overlay** ([`criteria-overlay/`](criteria-overlay/README.md)): IHH's 155 rules tagged with kind, which ones need a date (dates are redacted, so the tool says "can't tell"), 26 gaps that go to a person, and the facts each rule depends on.

The fillable verification checklist PDF described in the docs was built from IHH's public criteria and is kept with our local packet review, so it isn't in this repo.

**Demo video:** not recorded yet.

## How Claude is used

- **Building:** Claude Code (Claude Opus 5.5) planned, wrote the code and docs, and ran checks. An independent verifier subagent checked our claims against their sources, and we fixed the serious items it found before sharing. See [`HOW-THIS-WAS-BUILT.md`](HOW-THIS-WAS-BUILT.md).
- **Inside the app:** Claude Sonnet maps pages and checks quotes, Claude Opus extracts facts, and Claude Haiku runs **Ask Anchor**, a helper that answers only from the app's guide and the referral on screen. A person verifies every fact and makes every decision. Anchor never approves or denies.

## Try it

Needs Python 3.9 to 3.12, Pillow, pypdf and `pdftoppm` (poppler). Word and iPhone-photo conversion use macOS tools.

```bash
pip install pillow pypdf          # and: brew install poppler
cd intake-pipeline
python3 make_samples.py           # made-up sample faxes
INTAKE_PORT=8777 python3 server.py
# open http://127.0.0.1:8777, type your name in "Working as", press Check fax inbox
```

Optional: set `ANTHROPIC_API_KEY` in your environment (or in `intake-pipeline/.env`, which is git-ignored) to turn on the real pre-read and Ask Anchor. Without a key, the samples use built-in demo answers. No keys are in this repo.

**Anchor Board with Claude, locally:**

```bash
python3 board_server.py           # from the repo root; open http://127.0.0.1:8790
```

This serves `ANCHOR.html` and connects **Ask the board** to Claude (Haiku by default) through the server, using the same `ANTHROPIC_API_KEY`. The key stays on the server; the browser never sees it. Without a key, the helper uses its built-in answers.

Tests: `cd intake-pipeline && python3 -m unittest discover -s tests -t .`

## What is real and what is mocked

| Part | Status |
|---|---|
| Any-format intake, fax-to-email inbox (a local folder stands in for the mailbox) | working |
| Claude pre-read with quote check | working (tested on made-up samples) |
| Fact checking beside the page, to-dos with owners, fast lane, who's working | working |
| Ask Anchor helper | working (needs an API key; built-in fallback otherwise) |
| Hospital messages and 2-hour ladder | mocked: written to an outbox as DRY RUN files, never sent |
| Anchor Board | working, on 10 made-up packets |
| Scoring against IHH's real decisions | written, not run |

## Where it gets things wrong

- Dates are redacted, so rules that need a date say "can't tell" rather than checking.
- A quote the second look can't confirm counts as "unclear", so some real facts show up as unclear.
- Very messy faxes can still be misread. That is why a person verifies every fact.
- We haven't scored it against IHH's decisions, so we make no accuracy claim.
- Not yet tested with screen-reader users.

## Next steps

To pilot: an approved channel for hospital messages (secure email or eFax), IHH's approval for API use with patient data, IHH's sign-off on message wording and tier times, and scoring against IHH's held-out decisions. With one more week: run all 11 event packets, tune the pre-read on the misses, and test with intake staff.

## Data and privacy

This project uses only data from the event repo and public sources. It contains no real
patient or client information. It does not connect to any Illumination Health + Home system.
The Challenge 1 packets, our packet review, and our verifier reports are not in this repo.

## License

[MIT](LICENSE)
