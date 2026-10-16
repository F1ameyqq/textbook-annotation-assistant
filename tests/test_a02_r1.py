"""R1 regressions for full multi-book history, preserving same-book safety gates."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location("a02_r1_" + name, ROOT / "examples/a02/R1" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


scenarios = module("scenarios")
identity = module("identity")


class A02R1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def test_full_foreign_unknown_diagnostic_then_ready_and_reverse_roles(self):
        for book, foreign in (("book-alpha", "book-beta"), ("book-beta", "book-alpha")):
            with self.subTest(book=book):
                result = scenarios.crossbook(ROOT, self.output / book, book, foreign)
                self.assertTrue(result["foreign_unknown_retained"])
                self.assertFalse(result["pause_after_history"])
                self.assertEqual(result["target_frames"], 9)

    def test_conclusive_history_with_foreign_unknown_is_not_a_pause(self):
        for fault in ("applied", "not_applied"):
            with self.subTest(fault=fault):
                result = scenarios.crossbook(ROOT, self.output / fault, mode=fault)
                self.assertFalse(result["pause_after_history"])

    def test_two_actual_unknown_books_each_remain_paused(self):
        result = scenarios.two_books(ROOT, self.output / "two-unknown")
        self.assertTrue(result["first_paused"])
        self.assertTrue(result["second_paused"])

    def test_applied_or_absent_book_does_not_clear_other_unknown(self):
        for fault in ("applied", "not_applied"):
            with self.subTest(fault=fault):
                result = scenarios.two_books(ROOT, self.output / fault, second_fault=fault)
                self.assertTrue(result["first_paused"])
                self.assertFalse(result["second_paused"])

    def test_standalone_other_book_remains_independent(self):
        result = scenarios.two_books(ROOT, self.output / "standalone", second_fault="applied", mixed=False)
        self.assertFalse(result["second_paused"])

    def test_same_book_omitted_history_identity_changes_and_all_old_plan_replays(self):
        result = scenarios.same_book_and_replay(ROOT, self.output / "safety")
        self.assertEqual(result["lost_response"]["bypass_count"], 4)
        self.assertEqual(result["applied"]["replay_error"], "REPLAY_FORBIDDEN")
        self.assertEqual(result["not_applied"]["replay_error"], "REPLAY_FORBIDDEN")
        self.assertEqual(result["lost_response"]["replay_error"], "BOOK_WRITE_PAUSED")

    def test_own_unknown_in_complete_history_pauses_without_pending_intent(self):
        result = scenarios.same_book_history_only(ROOT, self.output / "history-only")
        self.assertTrue(result["own_historical_unknown_pause"])
        self.assertEqual(result["pending_intents_created"], 0)

    def test_export_subdirectory_cannot_borrow_enclosing_git_head(self):
        # This is a path inside the real repository, but is not its Git top-level.
        result = identity.git_identity(ROOT / "examples/a02/R1")
        self.assertIsNone(result["checkout_commit"])
        self.assertIn("unknown", result["status"])
        if (ROOT / ".git").exists():
            self.assertIsNotNone(identity.git_identity(ROOT)["checkout_commit"])
        else:
            self.assertIsNone(identity.git_identity(ROOT)["checkout_commit"])


if __name__ == "__main__":
    unittest.main()
