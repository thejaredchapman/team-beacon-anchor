# Anchor: referral intake app (prototype)

**Anchor**, by Team Beacon. A local app for IHH's referral intake team. Referrals arrive in any format. Claude reads the packet straight away. Staff check the facts with each page beside it. The hospital is kept informed inside the 2-hour promise.

> **Try it online first:** the [Anchor Board](https://claude.ai/artifact/NVUonEKc7TRXnVU9QafCVG) runs in the browser on made-up sample packets, with nothing to install.

> **Dry run only.** Nothing is ever sent. Every message is written to `outbox/` as a file marked DRY RUN. Files stay on this computer.

## Start it

```bash
cd saturday-oct17-build/intake-pipeline
python3 make_samples.py                      # made-up sample faxes (and demo answers)
INTAKE_PORT=8777 python3 server.py           # open http://127.0.0.1:8777
```

- **Turn on the real pre-read and Ask Anchor:** set `ANTHROPIC_API_KEY` before starting, or put `ANTHROPIC_API_KEY=...` in `intake-pipeline/.env` (git-ignored; the app reads it on its own).
- **Without a key:** the made-up samples use built-in demo answers. Any other file opens in "review by hand" mode.

Needs **Python 3.9 to 3.12** (the server uses the `cgi` module, which Python 3.13 removed), Pillow, pypdf, and `pdftoppm` (poppler). Turning Word files and iPhone photos (HEIC) into readable pages uses macOS tools (`textutil`, `sips`), so on Windows or Linux those files are marked "ask the hospital to resend".

## Try it in 2 minutes

0. Type your name and role in **Working as** at the top and press **Save**. Every action except the demo clock needs a name, so the history shows who did what.
1. Press **Check fax inbox**. Two made-up faxes become two referrals, and both are read straight away.
2. Open the first one (graded **Bad**). At the top, **What to do next** says what to do.
3. **Step 1, To-do list:**
   - Press **Confirm** on the possible red flag. The hospital is told right away.
   - Press **Send request now** for the missing items.
4. **Step 2, Check the facts:**
   - Press **J** to move through the facts. Each page shows beside its fact.
   - Press **V** to mark a fact verified.
   - The "Cognitive impairment" fact shows **two pages side by side**, because the form and the chart disagree.
5. **Step 3:** press **Demo: hospital resends missing pages**. The new pages join this referral, and the medication list and vitals items close themselves.
6. Open the second referral. It's **Great**, so it gets the **Fast lane**: one screen to decide.

## Upload, and who's working on what

- **⬆ Upload** (top of every page): start a new referral from files. To add pages to an existing referral, use **Add more files** on its page.
- **Working as:** each person's name is saved in this browser and recorded on every action.
- **Status on the list:** **Untouched** (no one has opened it), **Opened by** (viewed only), **Worked on** (someone acted), plus a **Worked on by** column.
- **Step 6, Who has worked on it:** the full history for that referral, newest first.

## Ask Anchor (the helper)

A chat panel on every page, powered by Claude Haiku. It knows which page, section and fact you're looking at, and suggests the next step by naming the button or key.

- It answers only from Anchor's own guide and the referral on screen. It never gives medical or eligibility advice.
- If it mentions a rule ID that isn't in IHH's rules, its answer is replaced by the built-in next step.
- Without a key it shows the built-in "What to do next" instead.
- **It sends the on-screen referral's details (status, facts, to-dos, no page images) to the Claude API.** Use only made-up or de-identified data.

## The seven speed-ups

| # | What | How it helps |
|---|---|---|
| 1 | **Pre-read on arrival:** Claude maps the pages (and turns sideways ones upright), finds the 27 facts with page and quote, and a second look checks each quote is on its page | Staff check facts instead of hunting for them. An unconfirmed quote counts as "unclear", never "found" |
| 2 | **Ask the hospital now:** missing documents and facts become one request you send with one click | The hospital starts gathering pages within minutes, not at 30. The 30- and 60-minute messages become reminders |
| 3 | **Side by side:** each fact opens its page beside it; a form-vs-chart conflict shows both pages | Checking a fact takes a glance |
| 4 | **Resent pages join the referral:** a fax that mentions the referral number is added to it, only the new pages are read, and answered items close | No starting over when the hospital replies |
| 5 | **Fast lane:** all 7 core documents, a fact score of 85%+ (found = 2 points, unclear or can't tell = 1), nothing flagged | One screen to decide |
| 6 | **Owners:** clinical items (red flags, clinical conflicts, clinical facts) go to the clinical reviewer, paperwork to the coordinator. **My list** shows each person's items | Two people work at once |
| 7 | **Keyboard:** J / K move, V verifies, O opens the page, R jumps to the reply box | Fewer clicks on every referral |

## Messages

| When | To | What |
|---|---|---|
| Arrival | Hospital | Receipt, with the 2-hour promise |
| Pre-read finds a possible red flag | Intake team (clinical reviewer) | "Possible red flag: confirm now", immediately |
| A clinician confirms a red flag | Hospital and coordinator | "Clinical question, answer needed to proceed. This is not a decision.", immediately |
| A person adds a red flag | Intake team and hospital | Immediately |
| "Send request now" | Hospital | The approved missing items, each with its IHH rule |
| 30 and 60 min | Hospital | The request (or a reminder if it was already sent) |
| 60, 90, 110, 120 min | Intake team | Escalation: undecided, at risk, 10 minutes left, missed |
| Resent pages arrive | Intake team | "Hospital sent N pages; M items answered" |
| Reply box | Hospital | Your message |
| Decision | Hospital | Decision recorded; follow-ups stop |

Messages carry the referral number only, never a patient name. Internal messages go to the **IHH Referral Intake team**, with a "for:" line naming the role.

## What the pre-read never does

- **Decide.** It suggests; staff verify and decide.
- **Guess a date.** Rules that need one say "can't tell".
- **Call a black box missing.** It's a redaction.
- **Use a rule ID that isn't in IHH's rules.** Made-up IDs are dropped.
- **Send a request staff haven't approved.** A possible red flag reaches the hospital only after a clinician confirms it.

## Formats it accepts

| Format | What happens to it |
|---|---|
| PDF | Kept as is |
| Multi-page TIFF faxes and photos (including iPhone HEIC) | Turned into PDF |
| Word, RTF and ODT | Turned into text |
| Emails (including fax-to-email) and zip files | Unpacked |
| Anything unreadable, or over 50 MB | Marked "ask the hospital to resend" and added to the to-do list, so it goes out with the next request |
| Programs | Rejected |

## Folders (all git-ignored)

- `work/`: files, page images and `pipeline.db`
- `outbox/`: dry-run messages
- `fax-inbox/`: stand-in for the fax-to-email mailbox
- `samples/`: made-up samples and demo answers

## Tests

```bash
python3 -m unittest discover -s tests -t . -v      # 48 tests
```

The tests cover:
- format detection and fax unpacking
- the full message ladder
- the pre-read on made-up packets: page map, grade, possible red flag, conflict, owners
- sending the request now, then reminders
- confirming a red flag
- resent pages closing items
- the fast lane and manual mode
- safety: unconfirmed quotes never count as found, and made-up rule IDs are dropped (from the pre-read, Ask Anchor, and staff-typed to-dos)
- unreadable and oversize files going into the next hospital request
- Ask Anchor: answers only from context, built-in fallback, rule-ID guard
- who's working: Untouched / Opened / Worked on, and the history
- the Claude client: models that refuse a forced tool fall back safely

## Using it with the real packets

The pre-read sends page images to the Claude API. Use only the de-identified event packets, and keep everything on this computer. Never commit `work/`. A real pilot needs IHH's approval for any API use with patient data, plus an approved channel for sending messages.
