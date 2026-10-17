"""Fax-to-email intake.

Most e-fax services turn an incoming fax into an email with the pages attached as PDF or TIFF.
In the prototype, a folder (fax-inbox/) stands in for that mailbox: drop .eml files in it and
poll_inbox() turns each one into a referral. A real mailbox connection is not implemented.
"""
import re
import shutil

from . import ingest, store

# Maps a sender's email domain to a hospital name. Placeholder domains only.
SENDER_DOMAINS = {
    "fax.sample-hospital-a.example": "Sample Hospital A",
    "fax.sample-hospital-b.example": "Sample Hospital B",
    "sample-hospital-c.example": "Sample Hospital C",
}


def hospital_for(sender_domain):
    return SENDER_DOMAINS.get(sender_domain, f"Unknown sender ({sender_domain})")


REF_PATTERN = re.compile(r"\bREF-[0-9a-f]{8}\b")


def find_referral_id(con, msg, filename):
    """A resend mentions the referral number in the subject, body or file name. Returns an open referral id or None."""
    text = " ".join([str(msg.get("Subject", "")), filename])
    body = msg.get_body(preferencelist=("plain",))
    if body is not None:
        text += " " + body.get_content()[:5000]
    for rid in REF_PATTERN.findall(text):
        row = con.execute("SELECT id FROM referrals WHERE id=? AND status='open'", (rid,)).fetchone()
        if row:
            return row["id"]
    return None


def poll_inbox(con, inbox=None, on_new=None, on_resend=None):
    """Turn each .eml in the inbox into a referral, or attach it to an open referral it names.

    on_new(rid) and on_resend(rid, doc_ids) let the caller start the pre-read.
    Returns {"new": [rids], "resent": [rids]}.
    """
    import email
    from email import policy
    inbox = inbox or store.INBOX
    inbox.mkdir(parents=True, exist_ok=True)
    done = inbox / "processed"
    done.mkdir(exist_ok=True)
    result = {"new": [], "resent": []}
    for path in sorted(inbox.glob("*.eml")):
        data = path.read_bytes()
        msg = email.message_from_bytes(data, policy=policy.default)
        rid = find_referral_id(con, msg, path.name)
        if rid:
            docs = ingest.add_file(con, rid, path.name, data, via="resend")
            result["resent"].append(rid)
            if on_resend:
                on_resend(rid, [d["id"] for d in docs])
        else:
            sender = str(msg.get("From", ""))
            domain = sender.split("@")[-1].strip("> ").lower() if "@" in sender else "unknown"
            rid = ingest.create_referral(con, hospital_for(domain), "fax", [(path.name, data)])
            result["new"].append(rid)
            if on_new:
                on_new(rid)
        shutil.move(str(path), str(done / path.name))
    return result


class IMAPMailbox:
    """Pilot only. Reading a real mailbox needs IHH approval and a HIPAA-compliant setup."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Not available in the prototype. Use the fax-inbox folder.")
