"""Source-bound split-heading composition; real observations and injected faults."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from annotation.recognition.baseline import digest
from annotation.recognition.boundary import build_boundary_candidate, validate_boundary
from annotation.recognition.offline import assemble
from verify_continuation_b import load_continuation_fixture, prepare_continuation


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


REVIEW = {"kind": "EXPLICIT_SOURCE_REVIEW", "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW",
          "reason": "Reviewed source heading occupies one dedicated semantic window; preserve all OCR components."}


def real_candidate(evidence, **changes):
    args = {"asset_id": "resource-173", "source_bbox": [160, 440, 464, 464],
            "line_spans": [{"line_id": "resource-173/ocr/25", "text_span": [0, 4]},
                           {"line_id": "resource-173/ocr/26", "text_span": [0, 8]}],
            "review_basis": REVIEW}
    args.update(changes)
    return build_boundary_candidate(evidence, **args)


class RealSplitHeadingRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / "tests/fixtures/book46007447"
        original = json.loads((directory / "ocr-evidence.json").read_text(encoding="utf-8"))
        fixture, _ = load_continuation_fixture(directory / "continuation-evidence.json")
        cls.original = prepare_continuation(original, assemble(original), fixture)["evidence"]

    def setUp(self):
        self.evidence = copy.deepcopy(self.original)

    def report(self, candidate=None):
        return validate_boundary(self.evidence, candidate or real_candidate(self.evidence))["payload"]

    def codes(self, candidate=None):
        report = self.report(candidate)
        self.assertFalse(report["accepted"])
        self.assertIsNone(report["boundary"])
        self.assertEqual(report["decision"], "HOLD")
        return {issue["code"] for issue in report["issues"]}

    def test_real_two_components_compose_by_geometry_and_preserve_sources(self):
        before = copy.deepcopy(self.evidence)
        candidate = real_candidate(self.evidence)
        self.assertEqual([m["raw_text"] for m in candidate["payload"]["members"]],
                         ["勾股定理", "回顾与思考（一）"])
        report = self.report(candidate)
        self.assertTrue(report["accepted"], report["issues"])
        boundary = report["boundary"]
        self.assertEqual(boundary["text"], "回顾与思考（一） 勾股定理")
        self.assertEqual(boundary["line_ids"], ["resource-173/ocr/26", "resource-173/ocr/25"])
        self.assertEqual(boundary["source_bbox"], [160, 440, 464, 464])
        self.assertEqual(boundary["bbox_union"], [160.5, 441.0, 463.0, 463.0])
        self.assertEqual(boundary["asset"]["sha256"], "8380f9a1872c830b1cf4fba12fa00e3b6d9c50ddaed357587de7333086e9cdbf")
        self.assertEqual(boundary["evidence_ref"]["revision"], self.evidence["revision"])
        self.assertEqual(boundary["verification_status"], "UNVERIFIED")
        self.assertEqual(boundary["platform_actions"], [])
        self.assertFalse(boundary["business_acceptance"])
        self.assertEqual(self.evidence, before)

    def test_committed_source_review_matches_real_fragments_and_drives_candidate(self):
        review = json.loads((ROOT / "tests/fixtures/book46007447/boundary-review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["content_hash"], digest(review["payload"]))
        data = review["payload"]
        page = next(p for p in self.evidence["payload"]["pages"] if p["asset_id"] == data["asset"]["asset_id"])
        self.assertEqual(data["asset"]["sha256"], page["source"]["sha256"])
        lines = {line["line_id"]: line for line in page["ocr_lines"]}
        for member in data["members"]:
            self.assertEqual(member["raw_text"], lines[member["line_id"]]["text"])
            self.assertEqual(member["bbox"], lines[member["line_id"]]["bbox"])
        candidate = build_boundary_candidate(self.evidence, asset_id=data["asset"]["asset_id"],
            line_spans=data["line_spans"], source_bbox=data["source_bbox"], review_basis=data["review_basis"])
        report = self.report(candidate)
        self.assertTrue(report["accepted"], report["issues"])
        self.assertEqual(report["boundary"]["text"], data["expected_title"])

    def test_dropped_component_is_detected_even_with_shrunken_region_and_fresh_candidate(self):
        candidate = real_candidate(self.evidence,
            line_spans=[{"line_id": "resource-173/ocr/26", "text_span": [0, 8]}],
            source_bbox=[160, 440, 338, 464])
        codes = self.codes(candidate)
        self.assertIn("BOUNDARY_MEMBER_COVERAGE_MISMATCH", codes)
        self.assertIn("BOUNDARY_TITLE_CONTEXT_MISMATCH", codes)

    def test_body_and_diagram_labels_cannot_be_captured_by_heading_region(self):
        candidate = real_candidate(self.evidence, source_bbox=[160, 432, 464, 464])
        codes = self.codes(candidate)
        self.assertIn("BOUNDARY_SOURCE_BBOX_OUTSIDE_WINDOW", codes)
        self.assertIn("BOUNDARY_OVERLAPS_NONMEMBER_CONTENT", codes)

    def test_out_of_image_region_and_truncated_member_are_rejected(self):
        self.assertIn("BOUNDARY_SOURCE_BBOX_INVALID", self.codes(real_candidate(self.evidence, source_bbox=[-1,440,464,464])))
        self.assertIn("BOUNDARY_SOURCE_BBOX_TRUNCATES_MEMBER", self.codes(real_candidate(self.evidence, source_bbox=[160,440,450,464])))

    def test_changed_text_or_raw_snapshot_cannot_rewrite_heading(self):
        for field, value in [("text", "勾股a理"), ("raw_text", "勾股a理"), ("raw_text_sha256", "0" * 64)]:
            with self.subTest(field=field):
                candidate = real_candidate(self.evidence)
                candidate["payload"]["members"][0][field] = value
                rehash(candidate)
                self.assertIn("BOUNDARY_TEXT_SOURCE_MISMATCH", self.codes(candidate))

    def test_partial_text_span_cannot_drop_original_ocr_content(self):
        candidate = real_candidate(self.evidence,
            line_spans=[{"line_id": "resource-173/ocr/25", "text_span": [0, 4]},
                        {"line_id": "resource-173/ocr/26", "text_span": [0, 5]}])
        self.assertIn("BOUNDARY_PARTIAL_OCR_ELEMENT_UNSUPPORTED", self.codes(candidate))

    def test_invalid_character_spans_are_rejected(self):
        for span in ([-1,4], [0,5], [4,0], [0,4.0]):
            with self.subTest(span=span):
                candidate = real_candidate(self.evidence,
                    line_spans=[{"line_id": "resource-173/ocr/25", "text_span": span},
                                {"line_id": "resource-173/ocr/26", "text_span": [0,8]}])
                self.assertIn("BOUNDARY_TEXT_SPAN_INVALID", self.codes(candidate))

    def test_stale_evidence_revision_and_asset_hash_are_rejected(self):
        candidate = real_candidate(self.evidence)
        self.evidence["revision"] += 1
        self.assertIn("BOUNDARY_STALE_OR_FOREIGN_EVIDENCE", self.codes(candidate))
        self.evidence = copy.deepcopy(self.original)
        page = next(p for p in self.evidence["payload"]["pages"] if p["asset_id"] == "resource-173")
        page["source"]["sha256"] = "0" * 64
        rehash(self.evidence)
        self.assertIn("BOUNDARY_ASSET_BINDING_MISMATCH", self.codes(candidate))

    def test_forged_reading_order_and_geometry_are_rejected(self):
        candidate = real_candidate(self.evidence)
        candidate["payload"]["reading_order"].reverse()
        candidate["payload"]["assembled_text"] = "勾股定理 回顾与思考（一）"
        rehash(candidate)
        self.assertIn("BOUNDARY_COMPOSITION_MISMATCH", self.codes(candidate))
        candidate = real_candidate(self.evidence)
        candidate["payload"]["members"][0]["bbox"] = [1, 1, 2, 2]
        rehash(candidate)
        self.assertIn("BOUNDARY_MEMBER_GEOMETRY_MISMATCH", self.codes(candidate))

    def test_duplicate_or_missing_member_is_explicit(self):
        candidate = real_candidate(self.evidence)
        candidate["payload"]["members"].append(copy.deepcopy(candidate["payload"]["members"][0]))
        rehash(candidate)
        self.assertIn("BOUNDARY_MEMBER_REUSED", self.codes(candidate))
        candidate = real_candidate(self.evidence,
            line_spans=[{"line_id": "never-observed", "text_span": [0, 4]}])
        self.assertIn("BOUNDARY_WINDOW_BINDING_MISMATCH", self.codes(candidate))

    def test_cross_page_title_fragment_is_rejected(self):
        original = next(p for p in self.evidence["payload"]["pages"] if p["asset_id"] == "resource-173")
        foreign = copy.deepcopy(original)
        foreign["asset_id"], foreign["source"]["asset_id"] = "other-page", "other-page"
        foreign["source"]["sha256"] = "d" * 64
        foreign["ocr_lines"] = [copy.deepcopy(original["ocr_lines"][-1])]
        foreign["ocr_lines"][0]["line_id"] = "other-page/ocr/title"
        self.evidence["payload"]["pages"].append(foreign)
        rehash(self.evidence)
        candidate = real_candidate(self.evidence,
            line_spans=[{"line_id": "resource-173/ocr/25", "text_span": [0, 4]},
                        {"line_id": "other-page/ocr/title", "text_span": [0, 8]}])
        self.assertIn("BOUNDARY_MEMBER_SCOPE_MISMATCH", self.codes(candidate))

    def test_cross_column_fragment_and_inconsistent_window_are_rejected(self):
        page = next(p for p in self.evidence["payload"]["pages"] if p["asset_id"] == "resource-173")
        member = page["ocr_lines"][-1]
        member["location"]["column"] = 1
        member["bbox"] = [650,443,826,463]
        rehash(self.evidence)
        self.assertIn("BOUNDARY_MEMBER_SCOPE_MISMATCH", self.codes())
        self.evidence = copy.deepcopy(self.original)
        self.evidence["payload"]["context"]["pages"]["resource-173"]["windows"][1]["path"] = ["Another title"]
        rehash(self.evidence)
        self.assertIn("BOUNDARY_MEMBER_SCOPE_MISMATCH", self.codes())

    def test_old_candidate_payload_tamper_is_rejected_without_rehash(self):
        candidate = real_candidate(self.evidence)
        candidate["payload"]["source_bbox"][0] = 0
        self.assertIn("BOUNDARY_CANDIDATE_INVALID", self.codes(candidate))

    def test_caller_label_cannot_promote_model_review_to_human_acceptance(self):
        candidate = real_candidate(self.evidence, review_basis={**REVIEW, "reference_quality": "HUMAN_REVIEWED"})
        self.assertIn("BOUNDARY_HUMAN_REVIEW_RECEIPT_UNSUPPORTED", self.codes(candidate))
        page = next(p for p in self.evidence["payload"]["pages"] if p["asset_id"] == "resource-173")
        page["source"]["reference_quality"] = "SYNTHETIC_TEST"
        rehash(self.evidence)
        self.assertIn("BOUNDARY_REFERENCE_QUALITY_PROMOTION", self.codes())


class GenericHeadingRegression(unittest.TestCase):
    """Constructed second heading confirms composition is not a book-specific regex."""
    def test_other_two_fragment_heading_composes_from_a_reviewed_window(self):
        path = ["Synthetic chapter", "第2课时 勾股定理"]
        lines = [
            {"line_id": "synthetic/title/left", "text": "第2课时", "bbox": [60,120,170,140]},
            {"line_id": "synthetic/title/right", "text": "勾股定理", "bbox": [190,121,330,141]}]
        for line in lines:
            line["location"] = {"column": 0, "window_index": 0, "section_path": path}
        evidence = rehash({"schema_version": "b-evidence-trial/0.3", "artifact_id": "synthetic-boundary-evidence",
            "revision": 1, "book_id": "synthetic-book", "scope_id": "synthetic-heading", "run_id": "synthetic-run",
            "payload": {"pages": [{"asset_id": "synthetic", "source": {"asset_id": "synthetic",
                "sha256": "a" * 64, "width": 1000, "height": 800}, "layout": {"cut_x": 500}, "ocr_lines": lines}],
                "context": {"pages": {"synthetic": {"windows": [{"column": 0, "y_range": [100,150], "path": path}]}}}}})
        candidate = build_boundary_candidate(evidence, asset_id="synthetic", source_bbox=[58,118,332,143],
            line_spans=[{"line_id": line["line_id"], "text_span": [0,4]} for line in reversed(lines)],
            review_basis={**REVIEW, "reference_quality": "SYNTHETIC_TEST"})
        report = validate_boundary(evidence, candidate)["payload"]
        self.assertTrue(report["accepted"], report["issues"])
        self.assertEqual(report["boundary"]["text"], "第2课时 勾股定理")
        self.assertEqual(report["boundary"]["reference_quality"], "SYNTHETIC_TEST")
        lines[1]["bbox"] = [150,120,310,140]
        rehash(evidence)
        candidate = build_boundary_candidate(evidence, asset_id="synthetic", source_bbox=[58,118,332,143],
            line_spans=[{"line_id": line["line_id"], "text_span": [0,4]} for line in lines],
            review_basis={**REVIEW, "reference_quality": "SYNTHETIC_TEST"})
        failed = validate_boundary(evidence, candidate)["payload"]
        self.assertFalse(failed["accepted"])
        self.assertIn("BOUNDARY_MEMBERS_OVERLAP", {issue["code"] for issue in failed["issues"]})


if __name__ == "__main__":
    unittest.main()
