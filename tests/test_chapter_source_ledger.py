import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


path = Path(__file__).resolve().parents[1] / "tools/build_chapter_source_ledger.py"
spec = importlib.util.spec_from_file_location("chapter_ledger", path)
ledger_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger_module)


class ChapterSourceLedgerTests(unittest.TestCase):
    def fixture(self):
        return {"authentication": {"private": "DO-NOT-EXPORT"}, "target": {
            "book_id": "46007447",
            "raw_directory_tree_projection": [{"id": "root", "label": "chapter", "children": [
                {"id": "lesson", "label": "lesson", "children": [
                    {"id": "lesson-nine", "isQuestion": True, "label": "9"}]},
                {"id": "reflection", "label": "reflection", "children": []}]}],
            "questions": [{"id": "lesson-nine", "directory_id": "lesson", "frames": [],
                           "content": {"status": "UNKNOWN", "reason": "NOT_FETCHED", "text": None}}],
        }}

    def build(self, state):
        return ledger_module.build_ledger(state, "root", "reflection")

    def test_empty_reflection_is_unknown_and_first_in_acquisition_queue(self):
        state = self.fixture()
        original = copy.deepcopy(state)
        result = self.build(state)
        self.assertEqual(result["acquisition_queue"][0]["directory_node_id_candidate"], "reflection")
        reflected = next(r for r in result["sections"] if r["directory_node_id_candidate"] == "reflection")
        self.assertEqual(reflected["status"], "QUESTION_MEMBERSHIP_UNOBSERVED_NOT_PROVEN_EMPTY")
        self.assertIsNone(reflected["question_denominator"])
        self.assertFalse(result["source_range_complete"])
        self.assertEqual(state, original)
        self.assertNotIn("DO-NOT-EXPORT", json.dumps(result))

    def test_another_directory_label_nine_never_supplies_reflection_identity(self):
        result = self.build(self.fixture())
        self.assertEqual(result["q9_reflection"]["other_directory_label_9_ids_rejected_as_substitutes"], ["lesson-nine"])
        self.assertIsNone(result["q9_reflection"]["question_id"])
        question = result["sections"][1]["questions"][0]
        self.assertIsNone(question["printed_question_number"])
        self.assertIsNone(question["canonical_question_id"])

    def test_conflicting_membership_rejects_instead_of_joining_same_id(self):
        state = self.fixture()
        state["target"]["questions"][0]["directory_id"] = "reflection"
        with self.assertRaisesRegex(ValueError, "DIRECTORY_MEMBERSHIP_CONFLICT"):
            self.build(state)

    def test_duplicate_tree_node_rejects(self):
        state = self.fixture()
        state["target"]["raw_directory_tree_projection"][0]["children"][1]["id"] = "lesson"
        with self.assertRaisesRegex(ValueError, "DUPLICATE_TREE_NODE_ID"):
            self.build(state)

    def test_wrong_source_hash_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "wrong.json"
            source.write_text(json.dumps(self.fixture()), encoding="utf-8")
            output = Path(directory) / "output"
            with self.assertRaisesRegex(ValueError, "ARCHIVED_STATE_HASH_MISMATCH"):
                ledger_module.run(source, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
