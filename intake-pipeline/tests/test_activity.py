import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_preread import Base  # noqa: E402
from pipeline import assistant, store  # noqa: E402


class Activity(Base):
    def test_untouched_opened_worked(self):
        rid = self.referral("fax.tiff")
        self.assertEqual(store.activity_status(self.con, rid)["state"], "untouched")   # system events don't count
        store.log_activity(self.con, rid, "Dana", "opened it", kind="view", role="Coordinator")
        s = store.activity_status(self.con, rid)
        self.assertEqual((s["state"], s["last"]["actor"], s["workers"]), ("opened", "Dana", []))
        store.log_activity(self.con, rid, "Dana", "sent the request for missing items", role="Coordinator")
        store.log_activity(self.con, rid, "Dr. Okafor", "confirmed a red flag", role="Clinical reviewer")
        s = store.activity_status(self.con, rid)
        self.assertEqual(s["state"], "worked")
        self.assertEqual(s["workers"], ["Dana", "Dr. Okafor"])
        self.assertEqual(s["last"]["action"], "confirmed a red flag")

    def test_views_are_not_logged_twice_in_ten_minutes(self):
        rid = self.referral("fax.tiff")
        self.assertIsNotNone(store.log_activity(self.con, rid, "Dana", "opened it", kind="view"))
        self.assertIsNone(store.log_activity(self.con, rid, "Dana", "opened it", kind="view"))
        store.advance_clock(self.con, 11)
        self.assertIsNotNone(store.log_activity(self.con, rid, "Dana", "opened it", kind="view"))

    def test_preread_logs_itself_and_ask_anchor_knows(self):
        rid = self.referral("fax.tiff")
        sys_rows = self.con.execute("SELECT actor, kind FROM activity WHERE referral_id=?", (rid,)).fetchall()
        self.assertIn(("Anchor pre-read", "system"), [tuple(r) for r in sys_rows])
        store.log_activity(self.con, rid, "Dana", "sent the request for missing items")
        self.assertIn("worked on by: Dana", assistant.referral_text(self.con, rid))


if __name__ == "__main__":
    unittest.main()
