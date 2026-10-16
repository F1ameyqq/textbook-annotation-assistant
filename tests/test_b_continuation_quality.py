"""Independent source expectations and injected faults for local graph quality.

The application producer creates the object under test once. Expectations below
come from immutable base entities, actual OCR, and fixed source memberships;
the quality module never imports or re-runs the producer to create a gold graph.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]

from annotation.recognition.baseline import digest
from annotation.recognition.continuation_apply import apply_continuation
from annotation.recognition.continuation_quality import audit_continuation_application
from replay_structure_b import run


class ContinuationApplicationQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inputs = run(FIXTURE)
        cls.evidence = inputs["evidence.json"]
        cls.base = inputs["question-graph-source-extension.json"]
        cls.proof = inputs["continuation-proof.json"]
        cls.review = json.loads((FIXTURE / "image-region-review.json").read_text(encoding="utf-8"))
        cls.applied = apply_continuation(cls.evidence, cls.base, cls.proof,
                                        image_review=cls.review, capture_root=FIXTURE)

    def setUp(self):
        self.derived = copy.deepcopy(self.applied)

    def answer(self):
        aid = self.proof["payload"]["from_answer_id"]
        return next(a for a in self.derived["payload"]["answers"] if a["answer_id"] == aid)

    def refresh(self):
        self.derived["content_hash"] = digest(self.derived["payload"])
        if "rollback_guard" in self.derived:
            self.derived["rollback_guard"]["expected_payload_hash"] = self.derived["content_hash"]
        self.derived["artifact_id"] = "coordinated-test-edit-" + self.derived["content_hash"][:24]

    def report(self):
        return audit_continuation_application(self.evidence, self.base, self.derived, self.proof,
                                             image_review=self.review, capture_root=FIXTURE)["payload"]

    def codes(self):
        self.refresh()
        report = self.report()
        self.assertFalse(report["accepted"], "Independent consumer accepted a coherently rehashed local edit")
        self.assertEqual(report["decision"], "HOLD")
        codes = {issue["code"] for issue in report["issues"]}
        self.assertNotIn("APPLY_ARTIFACT_INVALID", codes)
        self.assertNotIn("APPLY_DERIVED_PAYLOAD_CHANGED", codes)
        return codes

    def sync_render(self):
        self.answer()["regions"] = copy.deepcopy(self.answer()["render_regions"])

    def test_real_33_sources_15_render_regions_and_23_diagnostics_are_independently_checked(self):
        before = copy.deepcopy((self.evidence, self.base, self.derived, self.proof))
        report = self.report()
        self.assertTrue(report["accepted"], report["issues"])
        self.assertEqual(report["decision"], "HOLD")
        self.assertFalse(report["business_acceptance"])
        self.assertEqual(report["platform_actions"], [])
        answer = self.answer()
        expected_source = ["viewer-173/ocr/" + str(n) for n in (141,143,145,148,150,153,155,156)]
        expected_target = ["resource-173/ocr/" + str(n) for n in range(25)]
        self.assertEqual(answer["source_line_ids"], expected_source + expected_target)
        self.assertEqual(len(answer["fragments"]), 33)
        self.assertEqual(len(answer["render_regions"]), 15)
        self.assertEqual(len(answer["text"].splitlines()), 10)
        self.assertEqual(report["summary"]["diagnostic_fragments"], 23)
        self.assertFalse(answer["complete"])
        self.assertTrue(answer["structural_complete"])
        self.assertEqual((self.evidence, self.base, self.derived, self.proof), before)

    def test_coordinated_missing_target_fragment_and_reset_ledger_are_detected(self):
        answer = self.answer()
        missing = next(f for f in answer["fragments"] if f["evidence_refs"] == ["resource-173/ocr/0"])
        answer["fragments"].remove(missing)
        answer["source_line_ids"].remove("resource-173/ocr/0")
        answer["evidence_refs"].remove("resource-173/ocr/0")
        answer["render_regions"] = [r for r in answer["render_regions"] if missing["fragment_id"] not in r["source_fragment_ids"]]
        answer["fragment_representation"] = [r for r in answer["fragment_representation"] if r["fragment_id"] != missing["fragment_id"]]
        answer["text"] = "\n".join(r["text"] for r in answer["render_regions"] if r["content_type"] == "text")
        self.sync_render()
        ledger = self.derived["payload"]["answer_coverage"]
        original = next(r for r in self.base["payload"]["answer_coverage"] if r["line_id"] == "resource-173/ocr/0")
        index = next(i for i,r in enumerate(ledger) if r["line_id"] == "resource-173/ocr/0")
        ledger[index] = copy.deepcopy(original)
        app = self.derived["payload"]["continuation_application"]
        app["added_fragment_ids"].remove(missing["fragment_id"])
        app["render_region_ids"] = [r["region_id"] for r in answer["render_regions"]]
        self.assertIn("APPLY_TARGET_COVERAGE_MISMATCH", self.codes())

    def test_source_diagnostic_cannot_be_drawn_again_as_text(self):
        answer = self.answer()
        fragment = next(f for f in answer["fragments"] if f["evidence_refs"] == ["viewer-173/ocr/155"])
        text = next(r for r in answer["render_regions"] if r["content_type"] == "text")
        duplicate = copy.deepcopy(text)
        duplicate.update(region_id="injected-caption-text", text=fragment["text"], bbox=fragment["bbox"],
                         evidence_refs=fragment["evidence_refs"], source_fragment_ids=[fragment["fragment_id"]])
        answer["render_regions"].append(duplicate)
        self.sync_render()
        self.assertIn("APPLY_DIAGNOSTIC_RENDERED_AS_TEXT", self.codes())

    def test_caption_only_box_cannot_replace_verified_full_image(self):
        answer = self.answer()
        image = next(r for r in answer["render_regions"] if r["content_type"] == "image" and r["figure_number"] == "3")
        caption = next(f for f in answer["fragments"] if f["evidence_refs"] == ["viewer-173/ocr/155"])
        image["bbox"] = copy.deepcopy(caption["bbox"])
        self.sync_render()
        self.assertIn("APPLY_RENDER_PROJECTION_MISMATCH", self.codes())

    def test_stem_141_cannot_be_hidden_in_an_image_representation(self):
        answer = self.answer()
        stem = next(f for f in answer["fragments"] if f["evidence_refs"] == ["viewer-173/ocr/141"])
        text_region = next(r for r in answer["render_regions"] if r["source_fragment_ids"] == [stem["fragment_id"]])
        answer["render_regions"].remove(text_region)
        image = next(r for r in answer["render_regions"] if r["content_type"] == "image" and r["figure_number"] == "3")
        image["source_fragment_ids"].append(stem["fragment_id"])
        representation = next(r for r in answer["fragment_representation"] if r["fragment_id"] == stem["fragment_id"])
        representation.update(render_as_separate_region=False,represented_by_image_region=image["region_id"],render_region_id=image["region_id"])
        self.sync_render()
        self.assertIn("APPLY_RENDER_PROJECTION_MISMATCH", self.codes())

    def test_source_fragment_text_and_new_ocr_span_cannot_be_changed(self):
        self.answer()["fragments"][0]["text"] = "wrong source answer"
        self.assertIn("APPLY_SOURCE_FRAGMENT_CHANGED", self.codes())
        self.derived = copy.deepcopy(self.applied)
        fragment = next(f for f in self.answer()["fragments"] if f["evidence_refs"] == ["resource-173/ocr/0"])
        fragment["text_span"] = [0,2]
        fragment["text"] = fragment["raw_text"][:2]
        self.assertIn("APPLY_FRAGMENT_SOURCE_MISMATCH", self.codes())

    def test_duplicate_or_missing_images_cannot_be_hidden_by_rebuilt_render_alias(self):
        for mode in ("duplicate", "missing"):
            with self.subTest(mode=mode):
                self.derived = copy.deepcopy(self.applied)
                answer = self.answer()
                image = next(r for r in answer["render_regions"] if r["content_type"] == "image")
                if mode == "duplicate":
                    answer["render_regions"].append(copy.deepcopy(image))
                else:
                    answer["render_regions"].remove(image)
                self.sync_render()
                self.assertIn("APPLY_IMAGE_SET_MISMATCH", self.codes())

    def test_heading_rows_must_remain_excluded_and_original_questions_unchanged(self):
        row = next(r for r in self.derived["payload"]["answer_coverage"] if r["line_id"] == "resource-173/ocr/25")
        row.update(status="CONSUMED", answer_ids=[self.answer()["answer_id"]])
        self.assertIn("APPLY_ORIGINAL_LEDGER_CHANGED", self.codes())
        self.derived = copy.deepcopy(self.applied)
        self.derived["payload"]["questions"][0]["selected_answer_id"] = self.answer()["answer_id"]
        self.assertIn("APPLY_ORIGINAL_QUESTION_CHANGED", self.codes())

    def test_another_answer_and_unknown_payload_field_cannot_change_in_same_transition(self):
        other = next(a for a in self.derived["payload"]["answers"] if a["answer_id"] != self.answer()["answer_id"])
        other["text"] = "coordinated unrelated change"
        self.assertIn("APPLY_ORIGINAL_ANSWER_CHANGED", self.codes())
        self.derived = copy.deepcopy(self.applied)
        self.derived["payload"]["unreviewed_extra_action"] = {"submit": True}
        self.assertIn("APPLY_ORIGINAL_PAYLOAD_CHANGED", self.codes())

    def test_false_complete_and_human_acceptance_are_rejected(self):
        for field, value in (("complete", True), ("transcription_verified", True), ("human_verified", True)):
            with self.subTest(field=field):
                self.derived = copy.deepcopy(self.applied)
                self.answer()[field] = value
                self.assertIn("APPLY_FALSE_VERIFICATION", self.codes())

    def test_input_revision_and_base_archive_changes_are_rejected(self):
        self.derived["input_refs"][1]["revision"] += 1
        self.assertIn("APPLY_STALE_BINDING", self.codes())
        self.derived = copy.deepcopy(self.applied)
        self.derived["payload"]["continuation_application"]["base_graph_archive"]["revision"] += 1
        self.assertIn("APPLY_ARCHIVE_MISMATCH", self.codes())

    def test_spatial_gap_issue_cannot_be_promoted_to_resolved(self):
        answer = self.answer()
        answer["active_assembly_flags"] = []
        answer["structural_resolution"]["resolved_legacy_flags"].append("ANSWER_SPATIAL_GAP_UNRESOLVED")
        self.assertIn("APPLY_STRUCTURAL_RESOLUTION_MISMATCH", self.codes())


if __name__ == "__main__":
    unittest.main()
