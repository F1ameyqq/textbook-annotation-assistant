"""Development replay and injected faults; no website or OCR model required."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.offline import (assemble, quality_check, validate_context, scalar_issues,
                                           detect_columns, check_artifact)
from annotation.recognition.policy import classify, choice_answer_valid, option_set_valid
from offline_b import compare_reference


def read(name):
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


class OfflineRegression(unittest.TestCase):
    def setUp(self):
        self.evidence = read("ocr-evidence.json")
        self.review = read("review.json")
        self.graph = assemble(self.evidence)

    def question(self, page, number):
        return next(q for q in self.graph["payload"]["questions"] if q["asset_id"] == page and q["printed_number"] == number)

    def answer(self, question):
        return next(a for a in self.graph["payload"]["answers"] if a["answer_id"] == question["selected_answer_id"])

    def report(self):
        self.graph["revision"] += 1
        self.graph["content_hash"] = digest(self.graph["payload"])
        return quality_check(self.evidence, self.graph, self.review)["payload"]

    def codes(self):
        return {i["code"] for i in self.report()["issues"]}

    def test_real_sample_q4_read_13_without_using_history_answers(self):
        q = self.question("viewer-10", "4")
        a = self.answer(q)
        self.assertEqual(a["text"], "13")
        self.assertTrue(a["coarse_detail_agreement"])
        self.assertEqual(a["asset_id"], "viewer-173")
        self.assertFalse(self.evidence["payload"]["history_annotations_consumed"])
        self.assertIn("第4题图", [f["text"] for f in q["fragments"]])
        self.assertNotIn("ANSWER_SCALAR_FORMAT", self.codes())

    def test_q4_bad_ratio_blocks_even_when_task_says_success(self):
        self.answer(self.question("viewer-10", "4"))["text"] = "1:3"
        self.graph["payload"]["historical_task_status"] = "SUCCESS"
        report = self.report()
        self.assertEqual(report["decision"], "HOLD")
        self.assertIn("ANSWER_SCALAR_FORMAT", {i["code"] for i in report["issues"]})

    def test_q4_wrong_scalar_and_correct_scalar_are_distinguished(self):
        a = self.answer(self.question("viewer-10", "4"))
        a["text"] = "12"
        self.assertIn("ANSWER_VALUE_MISMATCH", self.codes())
        a["text"] = "13"
        self.assertNotIn("ANSWER_VALUE_MISMATCH", self.codes())
        self.assertEqual(self.report()["decision"], "HOLD")  # not an overall PASS

    def test_whole_question_omission_found_by_separate_page_census(self):
        q = self.question("viewer-10", "4")
        self.graph["payload"]["questions"].remove(q)
        self.assertIn("QUESTION_COVERAGE_MISMATCH", self.codes())

    def test_repeated_printed_one_does_not_cross_lessons(self):
        first = self.question("viewer-10", "1")
        later = self.question("viewer-14", "1")
        missing = self.question("viewer-12", "1")
        self.assertNotEqual(first["section_path"], later["section_path"])
        self.assertEqual(self.answer(first)["text"], "D")
        self.assertEqual(self.answer(later)["text"], "C")
        self.assertNotEqual(first["selected_answer_id"], later["selected_answer_id"])
        self.assertIsNone(missing["selected_answer_id"])

    def test_forged_cross_section_answer_is_blocked(self):
        q = self.question("viewer-10", "1")
        q["selected_answer_id"] = self.question("viewer-14", "1")["selected_answer_id"]
        self.assertIn("CROSS_SCOPE_ANSWER", self.codes())

    def test_ocr_zero_in_place_of_choice_c_is_not_accepted(self):
        q = self.question("viewer-10", "7")
        self.assertEqual(self.answer(q)["text"], "0")  # actual observed OCR fault
        report = self.report()
        qcodes = {i["code"] for i in report["issues"] if i["scope_id"] == q["question_id"]}
        self.assertIn("CHOICE_ANSWER_FORMAT", qcodes)
        self.assertIn("OCR_RECOGNITION_DISAGREEMENT", qcodes)

    def test_missing_option_is_not_hidden_by_high_confidence(self):
        q = self.question("viewer-10", "1")
        q["fragments"] = [f for f in q["fragments"] if f["option_label"] != "D"]
        q["confidence"] = 1.0
        self.assertIn("OPTION_SET_INCOMPLETE", self.codes())

    def test_unknown_evidence_and_foreign_book_are_blocked(self):
        q = self.question("viewer-10", "1")
        q["book_id"] = "another-book"
        q["fragments"][0]["evidence_refs"] = ["unobserved-line"]
        self.assertTrue({"QUESTION_SOURCE_MISMATCH", "UNKNOWN_FRAGMENT_EVIDENCE"} <= self.codes())

    def test_changed_payload_or_evidence_revision_rejected(self):
        altered = copy.deepcopy(self.evidence)
        altered["payload"]["pages"][0]["ocr_lines"][0]["text"] = "changed"
        with self.assertRaises(ValueError):
            assemble(altered)
        self.evidence["revision"] += 1
        with self.assertRaises(ValueError):
            quality_check(self.evidence, self.graph, self.review)

    def test_source_bound_context_rejects_other_hash_and_overlaps(self):
        source, context = read("source-descriptor.json"), read("context.json")
        validate_context(source, context)
        context["pages"]["viewer-10"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_context(source, context)
        context = read("context.json")
        context["pages"]["viewer-10"]["windows"].append(context["pages"]["viewer-10"]["windows"][0])
        with self.assertRaises(ValueError):
            validate_context(source, context)

    def test_replay_is_deterministic_and_preserves_run_identity(self):
        other = assemble(self.evidence)
        self.assertEqual(other["content_hash"], self.graph["content_hash"])
        self.assertEqual(other["artifact_id"], self.graph["artifact_id"])
        self.assertEqual(other["run_id"], self.evidence["run_id"])
        self.assertEqual(self.report()["summary"]["questions"], 34)

    def test_census_is_development_evidence_and_not_business_pass(self):
        report = self.report()
        self.assertTrue(all(p["census_matches"] for p in report["page_coverage"]))
        self.assertTrue(all(not p["business_acceptance"] for p in report["page_coverage"]))
        self.assertEqual(report["decision"], "HOLD")
        self.assertIn("BUSINESS_REVIEW_REQUIRED", {i["code"] for i in report["issues"]})

    def test_unsupported_layout_and_cross_column_are_explicit(self):
        self.assertIn("CROSS_COLUMN_CONTINUATION", self.codes())
        for page in self.evidence["payload"]["pages"]:
            page["layout"]["mode"] = "UNRESOLVED_LAYOUT"
        self.evidence["content_hash"] = digest(self.evidence["payload"])
        self.graph = assemble(self.evidence)
        self.assertIn("UNRESOLVED_LAYOUT", self.codes())

    def test_portrait_two_columns_and_crossing_text_guard(self):
        mask = np.zeros((1000, 700), dtype=bool)
        lines = []
        for x in (40, 400):
            for y in range(250, 700, 100):
                mask[y:y+10, x:x+240] = True
                lines.append({"bbox": [x,y,x+240,y+10]})
        self.assertEqual(detect_columns(mask, lines)["mode"], "two_columns")
        lines.append({"bbox": [40,750,640,780]})
        self.assertEqual(detect_columns(mask, lines)["mode"], "UNRESOLVED_LAYOUT")

    def test_reference_export_compares_only_explicit_reviewed_binding(self):
        record = read("q4-export-record.json")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reference.jsonl"
            path.write_text(json.dumps(record,ensure_ascii=False)+"\n",encoding="utf-8")
            review = copy.deepcopy(self.review)
            review["answer_checks"][0]["reference_export"]["file_sha256"] = file_digest(path)
            result = compare_reference(path, review)
            self.assertEqual(result["reviewed_bindings"], 1)
            self.assertEqual(result["comparisons"][0]["issues"], ["ANSWER_SCALAR_FORMAT"])
            record["answer"] = "13"
            path.write_text(json.dumps(record,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(ValueError):
                compare_reference(path, review)


class ConfirmedPolicyRegression(unittest.TestCase):
    def test_multiple_choice_priority_and_seven_option_pool(self):
        self.assertEqual(classify("多选", list("ABCD"), "A")["selection_mode"], "multiple")
        self.assertEqual(classify("题干", list("ABCD"), "BC")["selection_mode"], "multiple")
        seven = classify("文章 ___ ___ ___ ___ ___", list("ABCDEFG"), "ACDFG")
        self.assertEqual(seven["question_type"], "choice")
        self.assertTrue(seven["seven_to_five_candidate"])
        self.assertTrue(option_set_valid(list("ABCDEFG")))
        self.assertTrue(choice_answer_valid("ACDFG", list("ABCDEFG")))
        self.assertFalse(choice_answer_valid("0", list("ABCD")))
        self.assertFalse(choice_answer_valid("AA", list("ABCD")))

    def test_combination_options_are_stem_and_no_forced_analysis(self):
        rule = classify("公共材料与小题", list("ABCD"), shared_material=True)
        self.assertEqual(rule["question_type"], "combination")
        self.assertEqual(rule["option_role"], "stem")
        self.assertEqual(classify("请计算 ___", [])["question_type"], "fill_blank")
        self.assertEqual(classify("请证明这个结论", [])["question_type"], "open_response")
        self.assertNotIn("analysis_required", rule)

    def test_no_global_ratio_repair(self):
        self.assertEqual(scalar_issues("1:3", "13"), ["ANSWER_SCALAR_FORMAT"])
        self.assertEqual(scalar_issues(" 13 ", "13"), [])
        self.assertEqual(scalar_issues("12", "13"), ["ANSWER_VALUE_MISMATCH"])


if __name__ == "__main__":
    unittest.main()
