import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_preread import Base  # noqa: E402
from pipeline import assistant, claude, preread  # noqa: E402


class AskAnchor(Base):
    def setUp(self):
        super().setUp()
        self.rid = self.referral("fax.tiff")
        self.screen = {"page": self.rid, "referral": self.rid, "section": "2. Check the facts", "fact": "Cognitive impairment / dementia"}

    def test_context_has_screen_and_referral_state(self):
        text = assistant.screen_text(self.screen) + "\n" + assistant.referral_text(self.con, self.rid)
        for needle in ("Section in view: 2. Check the facts", "Fact being viewed: Cognitive impairment", "Grade: Bad",
                       "red flag, not yet confirmed", "rule NEU-X5", "Conflict:", "DOC-7 missing"):
            self.assertIn(needle, text)

    def test_falls_back_to_built_in_next_step_without_a_key(self):
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            out = assistant.answer(self.con, "What should I do next?", screen=self.screen)
        finally:
            if saved:
                os.environ["ANTHROPIC_API_KEY"] = saved
        self.assertEqual(out["mode"], "built-in")
        self.assertIn("possible red flag", out["answer"])
        self.assertIn("ANTHROPIC_API_KEY", out["note"])

    def test_grounded_answer_passes_and_gets_context(self):
        seen = {}

        def fake(system, msgs):
            seen["system"], seen["msgs"] = system, msgs
            return "The form says no cognitive impairment but the face sheet lists dementia (rule NEU-X5). Next: press \"Confirm (tells hospital now)\" or \"Dismiss\"."
        out = assistant.answer(self.con, "Why is this flagged?", history=[{"role": "assistant", "content": "hi"}, {"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}],
                               screen=self.screen, caller=fake)
        self.assertEqual(out["mode"], "claude")
        self.assertIn("Never give medical", seen["system"])
        self.assertEqual(seen["msgs"][0]["role"], "user")          # history starts on a user turn
        self.assertIn("ANCHOR GUIDE", seen["msgs"][-1]["content"])
        self.assertIn("Grade: Bad", seen["msgs"][-1]["content"])

    def test_made_up_rule_id_is_rejected(self):
        out = assistant.answer(self.con, "Which rule?", screen=self.screen, caller=lambda s, m: "This breaks rule ZZZ-42.")
        self.assertEqual(out["mode"], "built-in")
        self.assertIn("not in Anchor's rules", out["note"])

    def test_common_terms_are_not_mistaken_for_rules(self):
        out = assistant.answer(self.con, "COVID?", screen=self.screen, caller=lambda s, m: "The COVID-19 swab timing can't be checked because dates are redacted.")
        self.assertEqual(out["mode"], "claude")

    def test_no_referral_on_screen(self):
        out = assistant.answer(self.con, "What now?", screen={"page": "All referrals"}, caller=lambda s, m: "Open a referral from the list.")
        self.assertEqual(out["answer"], "Open a referral from the list.")
        self.assertIn("No referral open on screen", assistant.referral_text(self.con, None))


if __name__ == "__main__":
    unittest.main()
