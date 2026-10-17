import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import faxmail, ingest, notify, store  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        store.WORK, store.OUTBOX, store.INBOX = self.tmp / "work", self.tmp / "outbox", self.tmp / "inbox"
        self.con = store.connect(self.tmp / "t.db")
        self.out = notify.OutboxTransport(self.tmp / "outbox")

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ref(self, channel="fax"):
        return ingest.create_referral(self.con, "Sample Hospital A", channel, [("note.txt", b"made-up sample note\n")])

    def tiers(self, rid):
        return [r["tier"] for r in self.con.execute("SELECT tier FROM notifications WHERE referral_id=? ORDER BY created_at, tier", (rid,))]


class DetectKind(Base):
    def test_magic_bytes(self):
        cases = {b"%PDF-1.7": "pdf", b"II*\x00rest": "tiff", b"MM\x00*rest": "tiff", b"\xff\xd8\xff\xe0": "jpeg",
                 b"\x89PNG\r\n": "png", b"GIF89a..": "gif", b"MZ\x90\x00": "blocked", b"#!/bin/sh": "blocked",
                 b"{\\rtf1 hi": "rtf", b"hello world\nplain text\n": "txt", b"\x00\x01\x02\x03\xff": "unknown"}
        for data, kind in cases.items():
            self.assertEqual(ingest.detect_kind(data), kind, data)

    def test_name_does_not_decide(self):
        self.assertEqual(ingest.detect_kind(b"%PDF-1.4", "photo.jpg"), "pdf")
        self.assertEqual(ingest.detect_kind(b"MZ\x90", "referral.pdf"), "blocked")

    def test_eml_detected(self):
        eml = b"From: a@b.example\nSubject: fax\nMIME-Version: 1.0\nContent-Type: text/plain\n\nhi\n"
        self.assertEqual(ingest.detect_kind(eml), "eml")


class Ingest(Base):
    def test_tiff_fax_becomes_pdf_and_eml_unpacks(self):
        from email.message import EmailMessage
        from PIL import Image
        import io
        buf = io.BytesIO()
        frames = [Image.new("L", (200, 260), 255) for _ in range(3)]
        frames[0].save(buf, "TIFF", save_all=True, append_images=frames[1:])
        msg = EmailMessage()
        msg["From"] = "Fax <in@fax.sample-hospital-a.example>"
        msg["Subject"] = "Fax received"
        msg.set_content("pages attached")
        msg.add_attachment(buf.getvalue(), maintype="image", subtype="tiff", filename="fax.tiff")
        store.INBOX.mkdir(parents=True)
        (store.INBOX / "f.eml").write_bytes(bytes(msg))
        rid = faxmail.poll_inbox(self.con)["new"][0]
        docs = {d["kind"]: d for d in self.con.execute("SELECT * FROM documents WHERE referral_id=?", (rid,))}
        self.assertIn("eml", docs)
        self.assertEqual(docs["tiff"]["pages"], 3)
        self.assertTrue(docs["tiff"]["normalized_path"].endswith(".pdf"))
        hosp = self.con.execute("SELECT hospital, channel FROM referrals WHERE id=?", (rid,)).fetchone()
        self.assertEqual((hosp["hospital"], hosp["channel"]), ("Sample Hospital A", "fax"))
        self.assertTrue((store.INBOX / "processed" / "f.eml").exists())

    def test_unsupported_and_blocked_are_flagged_not_run(self):
        rid = ingest.create_referral(self.con, "H", "upload", [("x.msg", b"\xd0\xcf\x11\xe0rest"), ("x.pdf", b"MZ\x90\x00")])
        st = {d["kind"]: d["status"] for d in self.con.execute("SELECT * FROM documents WHERE referral_id=?", (rid,))}
        self.assertEqual(st["msg"], "needs_resend")
        self.assertEqual(st["blocked"], "rejected")

    def test_unreadable_file_goes_into_the_next_request(self):
        rid = ingest.create_referral(self.con, "H", "upload", [("scan.msg", b"\xd0\xcf\x11\xe0rest")])
        todo = self.con.execute("SELECT * FROM flags WHERE referral_id=? AND type='missing'", (rid,)).fetchall()
        self.assertEqual(len(todo), 1)
        self.assertIn("scan.msg", todo[0]["text"])
        self.assertIsNotNone(notify.request_now(self.con, rid, transport=self.out))
        self.assertEqual(len(notify.hospital_items(self.con, rid)), 1)


class Tiers(Base):
    def test_receipt_on_arrival(self):
        rid = self.ref()
        notify.tick(self.con, self.out)
        self.assertEqual(self.tiers(rid), ["T0"])

    def test_requests_only_when_items_missing(self):
        rid = self.ref()
        notify.tick(self.con, self.out)
        store.advance_clock(self.con, 31)
        notify.tick(self.con, self.out)
        self.assertNotIn("T30", self.tiers(rid))
        notify.add_flag(self.con, rid, "missing", "PT note showing distance walked", "MOB-2", self.out)
        notify.tick(self.con, self.out)
        self.assertIn("T30", self.tiers(rid))

    def test_full_ladder_and_no_duplicates(self):
        rid = self.ref()
        notify.add_flag(self.con, rid, "missing", "Medication list", "DOC-7", self.out)
        for _ in range(9):
            store.advance_clock(self.con, 15)
            notify.tick(self.con, self.out)
            notify.tick(self.con, self.out)
        t = self.tiers(rid)
        for tier in ("T0", "T30", "T60", "T60-INT", "T90", "T110", "T120"):
            self.assertEqual(t.count(tier), 1, tier)

    def test_staff_rule_ids_must_be_real(self):
        rid = self.ref()
        with self.assertRaises(ValueError):
            notify.add_flag(self.con, rid, "missing", "Something", "ZZZ-1", self.out)
        notify.add_flag(self.con, rid, "missing", "PT note", "mob-2", self.out)
        self.assertEqual(self.con.execute("SELECT rule_id FROM flags WHERE referral_id=?", (rid,)).fetchone()[0], "MOB-2")
        self.assertNotIn("ZZZ-1", "".join(p.read_text() for p in self.tmp.rglob("*") if p.is_file() and p.suffix in (".eml", ".txt")))

    def test_red_flag_notifies_immediately(self):
        rid = self.ref()
        _, sent = notify.add_flag(self.con, rid, "red", "Face sheet lists a diagnosis the form leaves unticked", "NEU-X5", self.out)
        self.assertEqual(sorted(n["audience"] for n in sent), ["clinical", "coordinator", "hospital"])
        hospital = [n for n in sent if n["audience"] == "hospital"][0]
        self.assertEqual(hospital["channel"], "fax")
        self.assertIn("not a decision", hospital["body"].lower())
        self.assertTrue(Path(hospital["outbox_path"]).read_text().startswith("DRY RUN"))

    def test_decision_stops_tiers(self):
        rid = self.ref("email")
        notify.add_flag(self.con, rid, "missing", "Vitals", "DOC-6", self.out)
        notify.tick(self.con, self.out)
        notify.decide(self.con, rid, "Approved", self.out)
        store.advance_clock(self.con, 200)
        notify.tick(self.con, self.out)
        self.assertEqual(sorted(self.tiers(rid)), ["DECISION", "T0"])

    def test_messages_never_send_and_carry_no_name(self):
        rid = self.ref("email")
        notify.tick(self.con, self.out)
        n = self.con.execute("SELECT * FROM notifications WHERE referral_id=?", (rid,)).fetchone()
        text = Path(n["outbox_path"]).read_text()
        self.assertIn("X-Dry-Run", text)
        self.assertIn("[DRY RUN]", text)
        self.assertIn("not-sent@example.invalid", text)
        with self.assertRaises(NotImplementedError):
            notify.SecureEmailTransport().send({})
        with self.assertRaises(NotImplementedError):
            notify.EFaxTransport().send({})

    def test_blocked_transport_is_recorded(self):
        rid = self.ref()
        notify.tick(self.con, notify.EFaxTransport())
        st = self.con.execute("SELECT status FROM notifications WHERE referral_id=?", (rid,)).fetchone()["status"]
        self.assertTrue(st.startswith("blocked"))


if __name__ == "__main__":
    unittest.main()
