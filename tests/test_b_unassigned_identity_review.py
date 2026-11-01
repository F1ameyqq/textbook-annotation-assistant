"""Independent frozen identity and pixel-receipt faults for the 19 held rows.

These are source-local MODEL review expectations, not a human/math gold set.
Every fault repairs caller-editable hashes so rejection must inspect actual
source membership, labels, raw intervals, CPU receipts or retained pixels.
"""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from annotation.recognition.baseline import digest
from verify_identity_review_b import FIXTURE, REVIEW, verify


def resign(value):
    value["content_hash"] = digest(value["payload"])
    value["artifact_id"] = "source-material-identities-" + value["content_hash"][:24]
    return value


class UnassignedSourceIdentityReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(REVIEW.read_text(encoding="utf-8"))

    def rejected(self, value, code, fixture=FIXTURE):
        result = verify(resign(value), fixture)
        self.assertFalse(result["accepted"], result)
        self.assertIn(code, [i["code"] for i in result["issues"]], result)
        self.assertEqual(result["decision"], "HOLD")

    def row(self, value, number):
        return next(r for r in value["payload"]["source_rows"] if r["line_id"] == f"viewer-173/ocr/{number}")

    def material(self, value, mid):
        return next(m for m in value["payload"]["material_candidates"] if m["material_candidate_id"] == mid)

    def test_real_frozen_inventory_remains_19_held_rows_9_local_materials(self):
        result = verify(self.review)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["summary"]["distinct_cpu_lines_checked"], 47)
        self.assertEqual(result["summary"]["original_unassigned_rows"], 19)
        self.assertEqual(result["summary"]["source_local_material_candidates"], 9)
        self.assertEqual(result["summary"]["excluded_noncontent_rows"], 0)
        self.assertFalse(result["original_pixels_checked"])
        self.assertFalse(result["human_verified"])
        self.assertFalse(result["business_accepted"])
        self.assertEqual(result["decision"], "HOLD")

    def test_missing_row_cannot_be_hidden_by_inventory(self):
        value = copy.deepcopy(self.review)
        value["payload"]["source_rows"].pop()
        self.rejected(value, "IDENTITY_SOURCE_ROW_COVERAGE")

    def test_duplicate_row_cannot_fill_dropped_math(self):
        value = copy.deepcopy(self.review)
        value["payload"]["source_rows"][-1] = copy.deepcopy(value["payload"]["source_rows"][-2])
        self.rejected(value, "IDENTITY_DUPLICATE_SOURCE_ROW")

    def test_changed_raw_formula_remains_rejected_after_rehash(self):
        value = copy.deepcopy(self.review)
        row = self.row(value, 104)
        row["text"] = "2"
        row["text_sha256"] = __import__("hashlib").sha256(b"2").hexdigest()
        row["raw_span_memberships"][0]["text"] = "2"
        self.rejected(value, "IDENTITY_RAW_SOURCE_CHANGED")

    def test_old_fraction5_must_stay_example1_not_example2(self):
        value = copy.deepcopy(self.review)
        row = self.row(value, 86)
        row["material_candidate_ids"] = ["topic1-examples/example-2"]
        row["raw_span_memberships"][0]["material_candidate_id"] = "topic1-examples/example-2"
        self.rejected(value, "IDENTITY_ROW_OWNERSHIP_MISMATCH")

    def test_bare_example_cannot_gain_invented_number1(self):
        value = copy.deepcopy(self.review)
        material = self.material(value, "topic2-example/unnumbered-example")
        material.update(printed_number=1, printed_number_status="EXPLICIT_LOCAL_NUMBER",
            local_printed_label_model_visual="【例1】", primary_number_must_not_be_invented=False)
        self.rejected(value, "IDENTITY_PRINTED_LABEL_MISMATCH")

    def test_reading_subpart1_cannot_become_primary_question1(self):
        value = copy.deepcopy(self.review)
        material = self.material(value, "math-world/unnumbered-reading")
        material["printed_number"] = 1
        material["subparts"] = []
        self.rejected(value, "IDENTITY_PRINTED_LABEL_MISMATCH")

    def test_training_denominator3_cannot_become_question3(self):
        value = copy.deepcopy(self.review)
        row = self.row(value, 125)
        row["material_candidate_ids"] = ["topic2-training/training-3"]
        row["raw_span_memberships"][0]["material_candidate_id"] = "topic2-training/training-3"
        self.rejected(value, "IDENTITY_ROW_OWNERSHIP_MISMATCH")

    def test_mixed_1c2_cannot_merge_into_one_local_question(self):
        value = copy.deepcopy(self.review)
        row = self.row(value, 122)
        row["raw_span_memberships"] = [dict(span=[0, 5], text="1.C2.",
            material_candidate_id="topic2-training/training-1", source_role="NUMBERED_TRAINING_ANSWER")]
        self.rejected(value, "IDENTITY_RAW_SPAN_MEMBERSHIP_MISMATCH")

    def test_mixed_314_cannot_change_boundary_to_decimal(self):
        value = copy.deepcopy(self.review)
        row = self.row(value, 123)
        row["raw_span_memberships"][0].update(span=[0, 4], text="3.14")
        row["raw_span_memberships"][1].update(span=[4, 4], text="")
        self.rejected(value, "IDENTITY_RAW_SPAN_MEMBERSHIP_MISMATCH")

    def test_raw_missing_q4_dot_cannot_be_silently_hidden(self):
        value = copy.deepcopy(self.review)
        self.row(value, 123)["raw_span_memberships"][1].pop("missing_in_raw")
        self.rejected(value, "IDENTITY_RAW_MISSING_MARKER_HIDDEN")

    def test_mixed_subpart_tail_cannot_be_dropped(self):
        value = copy.deepcopy(self.review)
        self.row(value, 108)["raw_span_memberships"].pop()
        self.rejected(value, "IDENTITY_RAW_SPAN_MEMBERSHIP_MISMATCH")

    def test_diagram_b_cannot_be_excluded_or_rendered_as_body_text(self):
        value = copy.deepcopy(self.review)
        row = self.row(value, 112)
        row["classification"] = "DECORATIVE_NONCONTENT"
        row["assignment_status"] = "EXCLUDED"
        self.rejected(value, "IDENTITY_ROW_OWNERSHIP_MISMATCH")
        value = copy.deepcopy(self.review)
        self.row(value, 112)["raw_span_memberships"][0]["source_role"] = "WORKED_ANSWER_CONTINUATION"
        self.rejected(value, "IDENTITY_RAW_SPAN_ROLE_MISMATCH")

    def test_recovered6_is_real_cpu_but_not_corrected_b(self):
        denominator = self.review["payload"]["additional_cpu_evidence"]["topic2_training4_denominator6"]
        self.assertEqual([l["text"] for l in denominator], ["6", "6"])
        # This other glyph is a diagram b, misread6 in one CPU pass. Both raw
        # observations stay unchanged; neither becomes an accepted formula.
        row = self.row(self.review, 112)
        self.assertEqual(row["text"], "b")
        self.assertEqual(row["cpu_support"][0]["text"], "6")
        value = copy.deepcopy(self.review)
        self.row(value, 112)["cpu_support"][0]["text"] = "b"
        self.rejected(value, "IDENTITY_CPU_RECEIPT_CHANGED")

    def test_first_and_final_example_fractions_cannot_swap(self):
        value = copy.deepcopy(self.review)
        evidence = value["payload"]["additional_cpu_evidence"]
        evidence["topic2_example_final_fraction55_over16"] = copy.deepcopy(
            evidence["topic2_example_first_fraction55_over16"])
        self.rejected(value, "IDENTITY_COMPONENT_OWNERSHIP_MISMATCH")

    def test_denominator6_cannot_be_relabelled_as_q2_denominator3(self):
        value = copy.deepcopy(self.review)
        evidence = value["payload"]["additional_cpu_evidence"]["topic2_training4_denominator6"]
        evidence[0] = copy.deepcopy(self.row(value, 125)["cpu_support"][0])
        self.rejected(value, "IDENTITY_COMPONENT_OWNERSHIP_MISMATCH")

    def test_body_claim_cannot_cross_training_heading(self):
        value = copy.deepcopy(self.review)
        group = next(g for g in value["payload"]["groups"] if g["group_id"] == "topic2-example")
        group["proposed_activity_window"]["source_bbox"][3] = 1261
        self.rejected(value, "IDENTITY_ACTIVITY_BOUNDARY_MISMATCH")

    def test_label_anchor_cannot_move_to_other_printed_number(self):
        value = copy.deepcopy(self.review)
        material = self.material(value, "topic2-training/training-4")
        other = self.material(value, "topic2-training/training-2")
        material["anchor_pixel_region"] = copy.deepcopy(other["anchor_pixel_region"])
        self.rejected(value, "IDENTITY_ANCHOR_REGION_MISMATCH")

    def test_false_human_verification_business_or_graph_assignment_is_rejected(self):
        for field in ("human_verified", "business_accepted", "graph_assignment_performed"):
            with self.subTest(field=field):
                value = copy.deepcopy(self.review)
                value["payload"][field] = True
                self.rejected(value, "IDENTITY_FALSE_VERIFICATION")

    def test_fake_explanation_is_rejected(self):
        value = copy.deepcopy(self.review)
        self.material(value, "topic2-example/unnumbered-example")["explicit_explanation_heading_present"] = True
        self.rejected(value, "IDENTITY_FALSE_VERIFICATION")

    def test_white_crop_fails_against_retained_cpu_source_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / "fixture"
            shutil.copytree(FIXTURE, fixture)
            path = fixture / "recovery-assets/topic2-training.png"
            with Image.open(path) as image:
                white = Image.new("RGB", image.size, "white")
            white.save(path)
            self.rejected(copy.deepcopy(self.review), "IDENTITY_CROP_CHANGED", fixture)

    def test_wrong_original_hash_or_source_title_is_rejected(self):
        value = copy.deepcopy(self.review)
        value["payload"]["source"]["sha256"] = "0" * 64
        self.rejected(value, "IDENTITY_SOURCE_MISMATCH")
        value = copy.deepcopy(self.review)
        value["payload"]["groups"][0]["title_model_visual_text"] = "小专题2 勾股定理在折叠问题中的运用"
        self.rejected(value, "IDENTITY_TITLE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
