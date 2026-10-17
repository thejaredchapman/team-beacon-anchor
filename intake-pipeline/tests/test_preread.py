import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_samples  # noqa: E402
from pipeline import faxmail, ingest, notify, preread, rules, store  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        store.WORK, store.OUTBOX, store.INBOX = self.tmp / "work", self.tmp / "outbox", self.tmp / "inbox"
        self.con = store.connect(self.tmp / "t.db")
        self.out = notify.OutboxTransport(self.tmp / "outbox")
        self.answers = {}
        self.files = {}
        for spec, name in ((make_samples.P1, "fax.tiff"), (make_samples.P2, "complete.pdf"), (make_samples.P3, "resend.pdf")):
            sha, ans = make_samples.write_packet(spec, self.tmp / name)
            self.answers[sha] = ans
            self.files[name] = self.tmp / name
        (self.tmp / "answers.json").write_text(json.dumps(self.answers))
        self.reader = preread.DemoReader(self.tmp / "answers.json")
        # route every message in these tests to the temp outbox
        self._orig = notify.OutboxTransport.__init__
        tmp_out = self.tmp / "outbox"
        notify.OutboxTransport.__init__ = lambda s, root=None: setattr(s, "root", Path(root) if root else tmp_out)

    def tearDown(self):
        notify.OutboxTransport.__init__ = self._orig
        self.con.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def referral(self, name, channel="fax"):
        rid = ingest.create_referral(self.con, "Sample Hospital A", channel, [(name, self.files[name].read_bytes())])
        preread.run(self.con, rid, reader=self.reader)
        return rid

    def flags(self, rid, **where):
        rows = self.con.execute("SELECT * FROM flags WHERE referral_id=?", (rid,)).fetchall()
        return [r for r in rows if all(r[k] == v for k, v in where.items())]

    def tiers(self, rid):
        return [r["tier"] for r in self.con.execute("SELECT tier FROM notifications WHERE referral_id=? ORDER BY created_at, tier", (rid,))]


class PreRead(Base):
    def test_incomplete_packet_is_mapped_graded_and_listed(self):
        rid = self.referral("fax.tiff")
        types = [p["doc_type"] for p in self.con.execute("SELECT doc_type FROM pages WHERE referral_id=? ORDER BY n", (rid,))]
        self.assertEqual(types, ["ihh_referral_form", "face_sheet", "pt_ot_evaluation"])
        g = rules.grade(self.con, rid)
        self.assertEqual(g["grade"], "Bad")
        self.assertFalse(g["fast_lane"])
        # possible red flag: clinical owner, not yet approved, intake team alerted, hospital not yet told
        red = self.flags(rid, type="red")
        self.assertEqual(len(red), 1)
        self.assertEqual((red[0]["owner"], red[0]["approved"], red[0]["rule_id"]), ("clinical", 0, "NEU-X5"))
        self.assertIn("RED-POSSIBLE", self.tiers(rid))
        self.assertNotIn("RED-HOSPITAL", self.tiers(rid))
        # form-vs-chart conflict becomes an internal "Settle" item for the clinical reviewer
        settle = [f for f in self.flags(rid) if (f["fact_key"] or "").startswith("conflict:")]
        self.assertEqual(len(settle), 1)
        self.assertEqual(settle[0]["owner"], "clinical")
        # missing documents and facts are suggested but not sent until staff approve
        self.assertTrue(any(f["rule_id"] == "DOC-7" for f in self.flags(rid, source="auto")))
        self.assertEqual(notify.hospital_items(self.con, rid), [])

    def test_owners_split_clinical_and_paperwork(self):
        rid = self.referral("fax.tiff")
        by_key = {f["fact_key"]: f["owner"] for f in self.flags(rid) if f["fact_key"] in rules.FACT_KEYS}
        self.assertEqual(by_key["mrsa_swab"], "clinical")
        self.assertEqual(by_key["follow_up"], "coordinator")

    def test_send_request_now_then_reminders(self):
        rid = self.referral("fax.tiff")
        notify.tick(self.con)
        n = notify.request_now(self.con, rid)
        self.assertEqual(n["tier"], "REQ-1")
        self.assertIn("To finish the review", n["body"])
        self.assertNotIn("rule gap", n["body"].lower())
        store.advance_clock(self.con, 31)
        sent = notify.tick(self.con)
        t30 = [s for s in sent if s["tier"] == "T30"][0]
        self.assertTrue(t30["subject"].startswith("Reminder"))
        self.assertIn("still need", t30["body"])

    def test_confirm_red_flag_tells_hospital_now(self):
        rid = self.referral("fax.tiff")
        fid = self.flags(rid, type="red")[0]["id"]
        sent = notify.confirm_red(self.con, fid)
        hosp = [s for s in sent if s["audience"] == "hospital"][0]
        self.assertEqual(hosp["channel"], "fax")
        self.assertIn("not a decision", hosp["body"].lower())

    def test_resend_attaches_and_closes_answered_items(self):
        rid = self.referral("fax.tiff")
        open_before = {f["fact_key"] or f["rule_id"] for f in self.flags(rid) if not f["resolved_at"]}
        self.assertTrue({"med_list_supply", "vitals_last5", "DOC-6", "DOC-7"} <= open_before)
        store.INBOX.mkdir(parents=True, exist_ok=True)
        eml = make_samples.fax_email("fax.sample-hospital-a.example", f"Re: Referral {rid} - missing items", "pages attached", self.files["resend.pdf"])
        (store.INBOX / "r.eml").write_bytes(eml)
        res = faxmail.poll_inbox(self.con, on_resend=lambda r, ids: preread.run(self.con, r, reader=self.reader, only_doc_ids=ids))
        self.assertEqual(res, {"new": [], "resent": [rid]})
        closed = {f["fact_key"] or f["rule_id"]: f["resolved_note"] for f in self.flags(rid) if f["resolved_at"]}
        for k in ("med_list_supply", "vitals_last5", "DOC-6", "DOC-7"):
            self.assertIn(k, closed)
        self.assertTrue(any(t.startswith("RESEND-") for t in self.tiers(rid)))
        resent = self.con.execute("SELECT image_path FROM pages WHERE referral_id=? AND added_by='resend'", (rid,)).fetchall()
        self.assertEqual(sum(1 for r in resent if r["image_path"].endswith(".jpg")), 2)   # the 2 faxed pages
        self.assertEqual(sum(1 for r in resent if r["image_path"].endswith(".txt")), 1)   # the email's cover note

    def test_complete_packet_gets_fast_lane(self):
        rid = self.referral("complete.pdf")
        g = rules.grade(self.con, rid)
        self.assertEqual(g["grade"], "Great")
        self.assertTrue(g["fast_lane"])
        self.assertEqual(self.flags(rid, type="red"), [])
        cant = [r["id"] for r in rules.cant_tell(self.con, rid)]
        self.assertIn("INF-2", cant)   # COVID swab timing needs a redacted date

    def test_manual_mode_without_reader(self):
        rid = ingest.create_referral(self.con, "H", "upload", [("fax.tiff", self.files["fax.tiff"].read_bytes())])
        saved = preread.choose_reader
        preread.choose_reader = lambda: None
        try:
            out = preread.run(self.con, rid)
        finally:
            preread.choose_reader = saved
        self.assertEqual(out["status"], "manual")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM pages WHERE referral_id=?", (rid,)).fetchone()[0], 3)


class Safety(Base):
    def test_unconfirmed_quotes_and_made_up_rule_ids(self):
        class Shaky(preread.DemoReader):
            def extract(self, pages, page_map):
                res = super().extract(pages, page_map)
                res["red_flags"].append({"rule_id": "FAKE-99", "text": "invented rule", "page": pages[0]["n"], "quote": "x"})
                return res

            def check_quotes(self, items):
                return {it["id"]: False for it in items}

        rid = ingest.create_referral(self.con, "H", "fax", [("fax.tiff", self.files["fax.tiff"].read_bytes())])
        preread.run(self.con, rid, reader=Shaky(self.tmp / "answers.json"))
        statuses = {f["status"] for f in self.con.execute("SELECT status FROM facts WHERE referral_id=?", (rid,))}
        self.assertNotIn("found", statuses)          # nothing counts as found without a confirmed quote
        rules_flagged = {f["rule_id"] for f in self.flags(rid, type="red")}
        self.assertNotIn("FAKE-99", rules_flagged)   # made-up rule IDs are dropped
        red = self.flags(rid, type="red")[0]
        self.assertIn("not confirmed", red["text"])


if __name__ == "__main__":
    unittest.main()
