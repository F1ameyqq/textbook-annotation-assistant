"""Fixed A11 actual disk-state readbacks and release failures, explicitly offline."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "fixtures" / "live_pilot"))
from helper import HERE, FakeTransport, case_root, request
from annotation.delivery.live_pilot.usense import decode_a05_history
from annotation.runtime.live_pilot.journal import Journal
from annotation.runtime.live_pilot.runner import apply


class ReadbackTests(unittest.TestCase):
    def execute(self, root, behavior):
        req = request()
        fake = FakeTransport(root/"backend",req["observation"],behavior)
        journal = Journal(root/"journal",offline=True)
        return apply(req,HERE,journal,fake), fake, journal

    def test_T7_normal_two_question_strict_readback(self):
        root = case_root(self._testMethodName)
        report, fake, journal = self.execute(root,"normal")
        self.assertEqual([q["state"] for q in report["questions"].values()],["APPLIED_OFFLINE"]*2)
        self.assertEqual(fake._load()["sends"],2)
        self.assertEqual([q["order"] for q in fake._load()["new"]],[10,11])
        self.assertTrue(report["release"]["released"])
        self.assertEqual(report["independent_acceptance"],"PENDING")
        self.assertEqual(report["submission_status"],"NOT_SUBMITTED")
        self.assertEqual(sum(e["kind"] == "READBACK" for e in journal.read()),6)

    def test_T6_response_frame_and_read_failure(self):
        base = case_root(self._testMethodName)
        for behavior in ("http_only","partial","get_timeout","truncated"):
            report, fake, journal = self.execute(base/behavior,behavior)
            self.assertEqual(report["questions"]["a11-new-alpha"]["state"],"UNKNOWN",behavior)
            self.assertEqual(report["questions"]["a11-new-beta"]["state"],"NOT_RUN",behavior)
            self.assertEqual(fake._load()["sends"],1)
            self.assertTrue(report["release"]["released"])

    def test_T7_text_and_independent_readback_rejections(self):
        base = case_root(self._testMethodName)
        for behavior in ("text_pending","text_symbol","text_answer","text_order","plan_copy","same_reopen"):
            report,fake,journal = self.execute(base/behavior,behavior)
            self.assertEqual(report["questions"]["a11-new-alpha"]["state"],"UNKNOWN",behavior)
            self.assertEqual(report["questions"]["a11-new-beta"]["state"],"NOT_RUN",behavior)
            self.assertEqual(fake._load()["sends"],1)

    def test_T4_old_state_preservation(self):
        base = case_root(self._testMethodName)
        for behavior in ("old_frame","old_text","old_directory","old_order","prewrite_drift"):
            report,fake,journal = self.execute(base/behavior,behavior)
            expected = "HOLD" if behavior == "prewrite_drift" else "UNKNOWN"
            self.assertEqual(report["questions"]["a11-new-alpha"]["state"],expected,behavior)
            self.assertEqual(report["questions"]["a11-new-beta"]["state"],"NOT_RUN")
            self.assertEqual(fake._load()["sends"],0 if behavior == "prewrite_drift" else 1)

    def test_T8_release_error_and_history_text_pending(self):
        root = case_root(self._testMethodName)
        report,fake,journal = self.execute(root,"close_error")
        self.assertEqual(report["questions"]["a11-new-alpha"]["state"],"HOLD_RELEASE")
        self.assertEqual(report["questions"]["a11-new-beta"]["state"],"NOT_RUN")
        self.assertFalse(report["release"]["released"])
        self.assertEqual(fake._load()["sends"],1)
        historical = decode_a05_history(json.loads((HERE/"a05-history.json").read_text(encoding="utf-8")))
        self.assertEqual(historical["content_status"],"CONTENT_PENDING")
        self.assertFalse(historical["live_eligible"])


if __name__ == "__main__": unittest.main()
