"""Accept referral documents in many formats and normalize them for review.

Supported: PDF, TIFF (multi-page fax), JPEG, PNG, HEIC, GIF/BMP, DOCX/DOC/RTF/ODT, TXT,
EML (fax-to-email or emailed referrals; attachments are extracted), ZIP (one level).
Unsupported files are stored and flagged so staff can ask the hospital to resend.
Nothing is executed; files are identified by their first bytes, not their names.
"""
import email
import hashlib
import io
import re
import shutil
import subprocess
import zipfile
from email import policy
from pathlib import Path

from . import rules, store

MAX_BYTES = 50 * 1024 * 1024
BLOCKED = (b"MZ", b"\x7fELF", b"#!", b"\xca\xfe\xba\xbe", b"\xcf\xfa\xed\xfe")


def detect_kind(data, filename=""):
    """Identify a file by its first bytes. Returns a short kind string."""
    head = data[:64]
    name = filename.lower()
    if any(head.startswith(b) for b in BLOCKED):
        return "blocked"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"II*\x00") or head.startswith(b"MM\x00*"):
        return "tiff"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG"):
        return "png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head.startswith(b"BM"):
        return "bmp"
    if head[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftypheif"):
        return "heic"
    if head.startswith(b"{\\rtf"):
        return "rtf"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "msg" if name.endswith(".msg") else "doc"
    if head.startswith(b"PK\x03\x04"):
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except zipfile.BadZipFile:
            return "unknown"
        if "word/document.xml" in names:
            return "docx"
        if "content.xml" in names and "mimetype" in names:
            return "odt"
        return "zip"
    text = data[:4096].decode("utf-8", errors="ignore")
    if re.search(r"^(Received|From|MIME-Version|Return-Path|Subject):", text, re.M) and re.search(r"^Content-Type:", text, re.M | re.I):
        return "eml"
    if text and sum(c.isprintable() or c in "\r\n\t" for c in text) / max(len(text), 1) > 0.95:
        return "txt"
    return "unknown"


def safe_name(name):
    base = Path(name or "file").name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:80] or "file"


def pdf_pages(path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def images_to_pdf(src_path, out_path):
    """TIFF (all frames), JPEG, PNG, GIF, BMP -> one PDF. Returns page count."""
    from PIL import Image, ImageSequence
    with Image.open(src_path) as im:
        frames = [f.convert("RGB") for f in ImageSequence.Iterator(im)]
    frames[0].save(out_path, "PDF", save_all=True, append_images=frames[1:], resolution=200)
    return len(frames)


def convert(kind, src, out_dir):
    """Return (normalized_path, pages, status, note)."""
    if kind == "pdf":
        return src, pdf_pages(src), "ready", None
    if kind in ("tiff", "jpeg", "png", "gif", "bmp"):
        out = out_dir / (src.stem + ".pdf")
        return out, images_to_pdf(src, out), "ready", f"{kind.upper()} converted to PDF"
    if kind == "heic":
        jpg = out_dir / (src.stem + ".jpg")
        r = subprocess.run(["sips", "-s", "format", "jpeg", str(src), "--out", str(jpg)], capture_output=True)
        if r.returncode != 0 or not jpg.exists():
            return None, None, "needs_resend", "HEIC photo could not be converted; ask for a PDF"
        out = out_dir / (src.stem + ".pdf")
        return out, images_to_pdf(jpg, out), "ready", "HEIC photo converted to PDF"
    if kind in ("docx", "doc", "rtf", "odt"):
        out = out_dir / (src.stem + ".txt")
        r = subprocess.run(["textutil", "-convert", "txt", str(src), "-output", str(out)], capture_output=True)
        if r.returncode != 0 or not out.exists():
            return None, None, "needs_resend", f"{kind.upper()} text could not be read; ask for a PDF"
        return out, None, "ready", f"Text extracted from {kind.upper()}; check the original for tables and checkboxes"
    if kind == "txt":
        return src, None, "ready", "Plain text"
    if kind == "msg":
        return None, None, "needs_resend", "Outlook .msg is not supported; ask the hospital to send PDF or forward as email"
    if kind == "blocked":
        return None, None, "rejected", "Program file rejected for safety"
    return None, None, "needs_resend", "Unknown format; ask the hospital to resend as PDF"


def add_file(con, referral_id, filename, data, depth=0, via="arrival"):
    """Store one file, normalize it, record it. Expands EML and ZIP. Returns list of document rows."""
    if len(data) > MAX_BYTES:
        return [_record(con, referral_id, via, filename, "too_large", data, None, None, None, "rejected", "Over 50 MB; ask for a smaller file")]
    kind = detect_kind(data, filename)
    folder = store.WORK / referral_id
    (folder / "original").mkdir(parents=True, exist_ok=True)
    (folder / "normalized").mkdir(parents=True, exist_ok=True)
    original = folder / "original" / f"{store.new_id('f')}-{safe_name(filename)}"
    original.write_bytes(data)
    docs = []
    if kind == "eml" and depth < 2:
        msg = email.message_from_bytes(data, policy=policy.default)
        sender = str(msg.get("From", ""))
        domain = sender.split("@")[-1].strip("> ").lower() if "@" in sender else "unknown"
        docs.append(_record(con, referral_id, via, filename, "eml", data, original, None, None, "ready",
                            f"Email from {domain}; attachments extracted below"))
        found = False
        for part in msg.iter_attachments():
            payload = part.get_content() if isinstance(part.get_content(), bytes) else part.get_payload(decode=True)
            if payload:
                found = True
                docs += add_file(con, referral_id, part.get_filename() or "attachment", payload, depth + 1, via)
        body = msg.get_body(preferencelist=("plain",))
        if body is not None:
            text = body.get_content()
            if text.strip():
                docs += add_file(con, referral_id, "email-body.txt", text.encode("utf-8"), depth + 1, via)
        if not found:
            docs[0] = _update_note(con, docs[0], "Email had no attachments; the referral may be incomplete")
        return docs
    if kind == "zip" and depth < 1:
        docs.append(_record(con, referral_id, via, filename, "zip", data, original, None, None, "ready", "Archive; contents extracted below"))
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist()[:50]:
                if info.is_dir() or info.file_size > MAX_BYTES:
                    continue
                docs += add_file(con, referral_id, info.filename, z.read(info), depth + 1, via)
        return docs
    norm, pages, status, note = convert(kind, original, folder / "normalized")
    docs.append(_record(con, referral_id, via, filename, kind, data, original, norm, pages, status, note))
    if status == "needs_resend":
        # Put the unreadable file on the to-do list so it goes out with the next hospital request
        rules._add_todo(con, referral_id, "missing", f"Resend {safe_name(filename)} as a PDF ({note})", "coordinator", "auto")
        con.commit()
    return docs


def _record(con, referral_id, via, filename, kind, data, original, norm, pages, status, note):
    row = {
        "id": store.new_id("doc"), "referral_id": referral_id, "filename": safe_name(filename), "kind": kind,
        "sha256": hashlib.sha256(data).hexdigest(), "pages": pages,
        "original_path": str(original) if original else "", "normalized_path": str(norm) if norm else None,
        "status": status, "note": note, "added_at": store.iso(store.now(con)), "via": via,
    }
    con.execute("INSERT INTO documents (id, referral_id, filename, kind, sha256, pages, original_path, normalized_path, status, note, added_at, via) VALUES (:id,:referral_id,:filename,:kind,:sha256,:pages,:original_path,:normalized_path,:status,:note,:added_at,:via)", row)
    con.commit()
    return row


def _update_note(con, row, note):
    con.execute("UPDATE documents SET note=? WHERE id=?", (note, row["id"]))
    con.commit()
    row["note"] = note
    return row


def create_referral(con, hospital, channel, files):
    """files: list of (filename, bytes). Returns referral id. Duplicate files (same hash) are noted."""
    rid = store.new_id("REF")
    con.execute("INSERT INTO referrals(id, hospital, channel, received_at) VALUES (?,?,?,?)",
                (rid, hospital or "Unknown hospital", channel, store.iso(store.now(con))))
    con.commit()
    for name, data in files:
        add_file(con, rid, name, data)
    dupes = con.execute("SELECT sha256, COUNT(*) n FROM documents WHERE referral_id=? GROUP BY sha256 HAVING n>1", (rid,)).fetchall()
    if dupes:
        con.execute("UPDATE referrals SET note=? WHERE id=?", (f"{len(dupes)} duplicate file(s) received", rid))
        con.commit()
    return rid


def remove_referral_files(referral_id):
    shutil.rmtree(store.WORK / referral_id, ignore_errors=True)
