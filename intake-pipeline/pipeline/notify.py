"""Tiered hospital communication within IHH's 2-hour promise.

Every message goes through a Transport. The only working transport is OutboxTransport,
which writes a dry-run file. Real email and fax transports are deliberately not
implemented: the event rules forbid sending to real people or services. A pilot would
add an IHH-approved, HIPAA-compliant channel (secure email or Direct messaging, or an
e-fax service under a business associate agreement) here, and nowhere else.

Messages carry the referral ID only, never a patient name or other identifier.
"""
from email.message import EmailMessage
from pathlib import Path

from . import rules, store

# minute offset from receipt, tier id, audience, channel, subject, condition
TIERS = [
    (0, "T0", "hospital", "preferred", "Referral {rid} received: answer within 2 hours", "always"),
    (30, "T30", "hospital", "preferred", "Referral {rid}: {n} item(s) needed to decide", "missing"),
    (60, "T60", "hospital", "preferred", "Reminder, referral {rid}: items still needed, decision due in 60 minutes", "missing"),
    (60, "T60-INT", "coordinator", "internal", "Referral {rid} is 60 minutes old and undecided", "open"),
    (90, "T90", "coordinator_lead", "internal", "AT RISK: referral {rid} at 90 minutes. Call the hospital now", "open"),
    (110, "T110", "coordinator_lead", "internal", "10 minutes left on referral {rid}", "open"),
    (120, "T120", "supervisor", "internal", "2-hour promise missed: referral {rid}", "open"),
]

# Every internal message goes to the IHH referral intake team. The role line says who on the team should act.
INTAKE_TEAM = "IHH Referral Intake team"
AUDIENCE_LABEL = {
    "hospital": "Referring hospital case manager (contact on file)",
    "coordinator": f"{INTAKE_TEAM} (for: referral coordinator)",
    "coordinator_lead": f"{INTAKE_TEAM} (for: intake lead)",
    "clinical": f"{INTAKE_TEAM} (for: clinical reviewer)",
    "supervisor": f"{INTAKE_TEAM} (for: intake supervisor)",
}


class Transport:
    name = "base"

    def send(self, note):
        raise NotImplementedError


class OutboxTransport(Transport):
    """Writes each message as a .eml (email) or .txt (fax cover) file. Sends nothing."""
    name = "outbox (dry run)"

    def __init__(self, root=None):
        self.root = Path(root) if root else store.OUTBOX

    def send(self, note):
        folder = self.root / note["referral_id"]
        folder.mkdir(parents=True, exist_ok=True)
        stamp = note["created_at"].replace(":", "").replace("+", "_")
        if note["channel"] == "fax":
            path = folder / f"{stamp}-{note['tier']}-{note['audience']}.fax.txt"
            path.write_text(
                "DRY RUN: NOT FAXED. Prototype only.\n"
                f"To: {AUDIENCE_LABEL.get(note['audience'], note['audience'])}\n"
                f"Re: {note['subject']}\n\n{note['body']}\n")
        else:
            msg = EmailMessage()
            msg["Subject"] = "[DRY RUN] " + note["subject"]
            msg["From"] = "IHH Referral Desk (prototype) <no-reply@example.invalid>"
            msg["To"] = AUDIENCE_LABEL.get(note["audience"], note["audience"]) + " <not-sent@example.invalid>"
            msg["X-Dry-Run"] = "true: prototype, nothing was sent"
            msg["X-Tier"] = note["tier"]
            msg.set_content(note["body"])
            path = folder / f"{stamp}-{note['tier']}-{note['audience']}.eml"
            path.write_bytes(bytes(msg))
        return str(path)


class SecureEmailTransport(Transport):
    name = "secure email (pilot only)"

    def send(self, note):
        raise NotImplementedError("Not available in the prototype. A pilot needs an IHH-approved, HIPAA-compliant channel.")


class EFaxTransport(Transport):
    name = "e-fax (pilot only)"

    def send(self, note):
        raise NotImplementedError("Not available in the prototype. A pilot needs an e-fax vendor under a BAA, approved by IHH.")


def _open_flags(con, rid, ftype):
    return con.execute("SELECT * FROM flags WHERE referral_id=? AND type=? AND resolved_at IS NULL ORDER BY created_at", (rid, ftype)).fetchall()


def hospital_items(con, rid):
    """Open missing items staff approved for the hospital (internal to-dos like rule gaps are never sent)."""
    return con.execute("SELECT * FROM flags WHERE referral_id=? AND type='missing' AND resolved_at IS NULL AND approved=1 AND IFNULL(source,'staff')!='internal' ORDER BY created_at", (rid,)).fetchall()


def confirmed_red(con, rid):
    return con.execute("SELECT * FROM flags WHERE referral_id=? AND type='red' AND resolved_at IS NULL AND approved=1 ORDER BY created_at", (rid,)).fetchall()


def request_sent(con, rid):
    return con.execute("SELECT COUNT(*) FROM notifications WHERE referral_id=? AND tier LIKE 'REQ-%'", (rid,)).fetchone()[0] > 0


def _body(con, ref, tier, audience, custom=None):
    rid = ref["id"]
    missing = hospital_items(con, rid)
    red = confirmed_red(con, rid) if audience == "hospital" else _open_flags(con, rid, "red")
    mins = int(store.minutes_open(con, ref))
    lines = [f"Referral: {rid}", f"From: {ref['hospital']}", f"Time since received: {mins} minutes", ""]
    if audience != "hospital":
        lines = [f"To: {AUDIENCE_LABEL.get(audience, INTAKE_TEAM)}"] + lines
    if tier == "T0":
        lines += ["Thank you. Illumination Health + Home received this referral.",
                  "A coordinator will review it and reply with a decision within 2 hours of receipt.",
                  "We may contact you for clarification or more information."]
    elif custom is not None:
        lines += [custom]
    elif tier in ("T30", "T60") or tier.startswith("REQ-"):
        if tier in ("T30", "T60") and request_sent(con, rid):
            lines += ["Reminder: we asked for these items earlier and still need them."]
        lines += ["To finish the review, please send:"] + [f"  - {f['text']}" + (f" (IHH rule {f['rule_id']})" if f["rule_id"] else "") for f in missing]
        lines += ["", "Reply by fax or secure email with the referral number above. Please do not include more patient information than needed."]
    elif tier.startswith("RED"):
        if audience == "hospital":
            lines += ["A clinical question needs your answer before we can continue:"] + [f"  - {f['text']}" for f in red]
            lines += ["", "Please call the IHH referral line or reply right away so the review can proceed.",
                      "This is not a decision. A coordinator will decide once this is answered."]
        else:
            lines += ["RED FLAG on this referral. Review now:"] + [f"  - {f['text']}" + (f" (rule {f['rule_id']})" if f["rule_id"] else "") for f in red]
            lines += ["", "The hospital has been sent a clarification request (dry run)."]
    elif tier == "DECISION":
        lines += [f"Decision recorded: {ref['decision']}.", "A coordinator will follow up with details through the usual channel."]
    else:
        lines += [f"Open items: {len(missing)} missing, {len(red)} red flag(s)."]
        if tier == "T90":
            lines += ["Call the hospital now to close the gaps."]
        if tier == "T120":
            lines += ["The 2-hour promise was missed. Log the reason and contact the hospital."]
    lines += ["", "Prototype message. Dry run only: nothing was sent."]
    return "\n".join(lines)


def _queue(con, ref, tier, audience, channel, subject, transport, dedupe_key, custom=None):
    if con.execute("SELECT 1 FROM notifications WHERE dedupe_key=?", (dedupe_key,)).fetchone():
        return None
    if channel == "preferred":
        channel = "fax" if ref["channel"] == "fax" else "email"
    note = {
        "id": store.new_id("msg"), "referral_id": ref["id"], "tier": tier, "audience": audience, "channel": channel,
        "subject": subject, "body": _body(con, ref, tier, audience, custom), "created_at": store.iso(store.now(con)),
        "status": "queued", "outbox_path": None, "dedupe_key": dedupe_key,
    }
    try:
        note["outbox_path"] = transport.send(note)
        note["status"] = "dry_run_written"
    except NotImplementedError as e:
        note["status"] = "blocked: " + str(e)
    con.execute("INSERT INTO notifications VALUES (:id,:referral_id,:tier,:audience,:channel,:subject,:body,:created_at,:status,:outbox_path,:dedupe_key)", note)
    con.commit()
    return note


def tick(con, transport=None):
    """Send every tier that is due for every open referral. Safe to call often."""
    transport = transport or OutboxTransport()
    sent = []
    with store._lock:
        for ref in con.execute("SELECT * FROM referrals WHERE status='open'").fetchall():
            mins = store.minutes_open(con, ref)
            n_missing = len(hospital_items(con, ref["id"]))
            for offset, tier, audience, channel, subject, cond in TIERS:
                if mins < offset:
                    continue
                if cond == "missing" and n_missing == 0:
                    continue
                subj = subject.format(rid=ref["id"], n=n_missing)
                if tier in ("T30", "T60") and request_sent(con, ref["id"]):
                    subj = f"Reminder, referral {ref['id']}: {n_missing} item(s) still needed"
                n = _queue(con, ref, tier, audience, channel, subj, transport, f"{ref['id']}:{tier}")
                if n:
                    sent.append(n)
    return sent


def add_flag(con, rid, ftype, text, rule_id=None, transport=None):
    """Record a red flag or missing item. A red flag notifies immediately, without waiting for a tier."""
    transport = transport or OutboxTransport()
    rule_id = (rule_id or "").strip().upper() or None
    if rule_id and rule_id not in rules.RULES:
        raise ValueError(f"{rule_id} is not one of IHH's rule IDs")
    with store._lock:
        fid = store.new_id("flag")
        con.execute("INSERT INTO flags (id, referral_id, type, text, rule_id, created_at, owner, source, approved) VALUES (?,?,?,?,?,?,?,?,1)", (fid, rid, ftype, text.strip(), (rule_id or "").strip() or None, store.iso(store.now(con)), "clinical" if ftype == "red" else "coordinator", "staff"))
        con.commit()
        out = []
        if ftype == "red":
            ref = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone()
            if ref and ref["status"] == "open":
                for audience, channel in (("coordinator", "internal"), ("clinical", "internal"), ("hospital", "preferred")):
                    subj = f"RED FLAG on referral {rid}: clinical question" if audience != "hospital" else f"Referral {rid}: urgent clarification needed to proceed"
                    n = _queue(con, ref, f"RED-{audience.upper()}", audience, channel, subj, transport, f"{rid}:RED:{fid}:{audience}")
                    if n:
                        out.append(n)
        return fid, out


def request_now(con, rid, flag_ids=None, transport=None):
    """Approve the listed (or all suggested) items and send the request to the hospital right away."""
    transport = transport or OutboxTransport()
    with store._lock:
        if flag_ids is None:
            con.execute("UPDATE flags SET approved=1 WHERE referral_id=? AND type='missing' AND resolved_at IS NULL AND IFNULL(source,'staff')!='internal'", (rid,))
        else:
            for fid in flag_ids:
                con.execute("UPDATE flags SET approved=1 WHERE id=? AND referral_id=?", (fid, rid))
        con.commit()
        items = hospital_items(con, rid)
        if not items:
            return None
        ref = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone()
        n = con.execute("SELECT COUNT(*) FROM notifications WHERE referral_id=? AND tier LIKE 'REQ-%'", (rid,)).fetchone()[0] + 1
        return _queue(con, ref, f"REQ-{n}", "hospital", "preferred", f"Referral {rid}: {len(items)} item(s) needed to decide", transport, f"{rid}:REQ-{n}")


def alert_possible_red_flag(con, rid, fid, transport=None):
    """The pre-read found a possible red flag: tell the intake team (clinical reviewer) at once."""
    transport = transport or OutboxTransport()
    ref = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone()
    fl = con.execute("SELECT * FROM flags WHERE id=?", (fid,)).fetchone()
    body = f"The pre-read found a possible red flag:\n  - {fl['text']}" + (f" (rule {fl['rule_id']})" if fl["rule_id"] else "") + \
        "\n\nOpen the referral, check the page, then confirm or dismiss it. Confirming notifies the hospital immediately."
    return _queue(con, ref, "RED-POSSIBLE", "clinical", "internal", f"Possible red flag on referral {rid}: confirm now", transport, f"{rid}:REDPOSS:{fid}", custom=body)


def confirm_red(con, fid, transport=None):
    """A clinician confirmed a red flag: notify the hospital (and the coordinator) immediately."""
    transport = transport or OutboxTransport()
    with store._lock:
        con.execute("UPDATE flags SET approved=1 WHERE id=?", (fid,))
        con.commit()
        fl = con.execute("SELECT * FROM flags WHERE id=?", (fid,)).fetchone()
        ref = con.execute("SELECT * FROM referrals WHERE id=?", (fl["referral_id"],)).fetchone()
        out = []
        for audience, channel in (("coordinator", "internal"), ("hospital", "preferred")):
            subj = f"RED FLAG confirmed on referral {ref['id']}" if audience != "hospital" else f"Referral {ref['id']}: urgent clarification needed to proceed"
            n = _queue(con, ref, f"RED-{audience.upper()}", audience, channel, subj, transport, f"{ref['id']}:RED:{fid}:{audience}")
            if n:
                out.append(n)
        return out


def note_resend(con, rid, pages, resolved, transport=None):
    transport = transport or OutboxTransport()
    ref = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone()
    k = con.execute("SELECT COUNT(*) FROM notifications WHERE referral_id=? AND tier LIKE 'RESEND-%'", (rid,)).fetchone()[0] + 1
    return _queue(con, ref, f"RESEND-{k}", "coordinator", "internal", f"Referral {rid}: hospital sent {pages} more page(s); {resolved} item(s) answered",
                  transport, f"{rid}:RESEND-{k}", custom=f"The hospital sent {pages} more page(s). The pre-read answered {resolved} open item(s). Check them and continue.")


def reply(con, rid, subject, text, transport=None):
    """Staff reply to the hospital, written to the outbox (dry run)."""
    transport = transport or OutboxTransport()
    ref = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone()
    k = con.execute("SELECT COUNT(*) FROM notifications WHERE referral_id=? AND tier LIKE 'REPLY-%'", (rid,)).fetchone()[0] + 1
    return _queue(con, ref, f"REPLY-{k}", "hospital", "preferred", subject.strip() or f"Referral {rid}", transport, f"{rid}:REPLY-{k}", custom=text.strip())


def resolve_flag(con, fid, note=None):
    con.execute("UPDATE flags SET resolved_at=?, resolved_note=? WHERE id=?", (store.iso(store.now(con)), note, fid))
    con.commit()


def decide(con, rid, decision, transport=None):
    """Record the coordinator's decision, stop the tiers, and draft the decision notice."""
    transport = transport or OutboxTransport()
    with store._lock:
        con.execute("UPDATE referrals SET status='decided', decided_at=?, decision=? WHERE id=?", (store.iso(store.now(con)), decision, rid))
        con.commit()
        ref = con.execute("SELECT * FROM referrals WHERE id=?", (rid,)).fetchone()
        return _queue(con, ref, "DECISION", "hospital", "preferred", f"Referral {rid}: decision", transport, f"{rid}:DECISION")


def clock_state(con, ref):
    """On time / At risk / Late, using the same thresholds as the Packet Triage Board."""
    if ref["status"] != "open":
        return "Answered"
    m = store.minutes_open(con, ref)
    return "On time" if m <= 90 else ("At risk" if m <= 120 else "Late")
