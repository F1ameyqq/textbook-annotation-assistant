"""Independent source-region faults; labels alone cannot prove a whole diagram.

The fixed ink witnesses were visually reviewed from original pages. They are
development references, never held-out accuracy, human gold, or a site plan.
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
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]

from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.image_regions import (
    build_image_regions, validate_image_regions, load_capture, subimage, rgb_hash,
    ref,
)
from annotation.recognition.offline import assemble
from verify_continuation_b import load_continuation_fixture, prepare_continuation


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


class ImageRegionRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = json.loads((FIXTURE / "ocr-evidence.json").read_text(encoding="utf-8"))
        continuation, _ = load_continuation_fixture(FIXTURE / "continuation-evidence.json")
        cls.original = prepare_continuation(base, assemble(base), continuation)["evidence"]
        cls.original_review = json.loads((FIXTURE / "image-region-review.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.evidence = copy.deepcopy(self.original)
        self.review = copy.deepcopy(self.original_review)
        self.regions = build_image_regions(self.evidence, self.review, FIXTURE)

    def region(self, number):
        return next(r for r in self.regions["payload"]["regions"] if r["figure_number"] == str(number))

    def report(self, root=FIXTURE):
        return validate_image_regions(self.evidence, self.regions, self.review, root)["payload"]

    def codes(self, root=FIXTURE):
        result = self.report(root)
        self.assertFalse(result["accepted"], "Consumer accepted the injected image-region fault")
        self.assertEqual(result["decision"], "HOLD")
        self.assertEqual(result["validated_regions"], [])
        self.assertFalse(result["business_acceptance"])
        return {i["code"] for i in result["issues"]}

    def change_bbox(self, number, bbox):
        region = self.region(number)
        descriptor = next(d for d in self.review["payload"]["captures"] if d["asset_id"] == region["asset_id"])
        image = load_capture(FIXTURE, descriptor)
        region["bbox"] = bbox
        region["crop_rgb_sha256"] = rgb_hash(subimage(image, descriptor, bbox))
        rehash(self.regions)

    def rebind_review(self):
        rehash(self.review)
        self.regions["input_refs"] = [ref(self.evidence), ref(self.review)]
        self.regions["payload"]["review_ref"] = ref(self.review)
        rehash(self.regions)

    def copy_captures(self, root):
        for descriptor in self.review["payload"]["captures"]:
            target = root / descriptor["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(FIXTURE / descriptor["path"], target)

    def test_five_real_regions_keep_pixels_identity_and_unverified_semantics(self):
        before = copy.deepcopy(self.evidence)
        result = self.report()
        self.assertTrue(result["accepted"], result["issues"])
        self.assertEqual(result["structural_status"], "PIXEL_REGION_VALIDATED")
        self.assertEqual(result["semantic_status"], "UNVERIFIED_SEMANTICS")
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["business_acceptance"])
        self.assertEqual({r["figure_number"] for r in result["validated_regions"]}, set("34567"))
        # All witnesses include actual linework and missing-OCR labels; these
        # counts were independently checked against original source pixels.
        counts = {r["figure_number"]: r["ink_witness"]["ink_pixels"] for r in self.review["payload"]["regions"]}
        self.assertEqual(counts, {"3": 886, "4": 809, "5": 1083, "6": 1149, "7": 1144})
        for region in result["validated_regions"]:
            self.assertEqual(region["content_type"], "image")
            self.assertEqual(region["role"], "answer")
            self.assertEqual(region["printed_number"], "9")
            self.assertEqual(region["verification_status"], "UNVERIFIED")
            self.assertEqual(region["reference_quality"], "MODEL_VISUAL_DEVELOPMENT_REVIEW")
            if region["asset_id"] == "resource-173":
                self.assertLess(region["bbox"][3], 442)
        # In particular, no builder/checker removes or clips the Q9 stem /141.
        self.assertEqual(self.evidence, before)

    def test_caption_only_box_is_rejected_despite_correct_caption_pixels(self):
        self.change_bbox(5, [167, 418, 202, 441])
        self.assertIn("IMAGE_REGION_INK_TRUNCATED", self.codes())

    def test_single_missing_non_ocr_source_pixel_cannot_pass_label_coverage(self):
        # Figure 3's extreme x711 signal has no required OCR element. Moving
        # the left edge to712 still contains every declared diagnostic label.
        self.change_bbox(3, [712, 1417, 834, 1539])
        self.assertIn("IMAGE_REGION_INK_TRUNCATED", self.codes())

    def test_cropped_top_vertex_label_d_is_detected(self):
        old = self.region(5)["bbox"]
        self.change_bbox(5, [old[0], 260, old[2], old[3]])
        self.assertIn("IMAGE_REGION_INK_TRUNCATED", self.codes())

    def test_dropping_a_complete_figure_is_not_hidden_by_other_captions(self):
        self.regions["payload"]["regions"].remove(self.region(6))
        rehash(self.regions)
        self.assertIn("IMAGE_REGION_SET_INCOMPLETE", self.codes())

    def test_wrong_caption_identity_cannot_relabel_another_image(self):
        self.region(5)["caption_ref"] = "resource-173/ocr/22"
        rehash(self.regions)
        self.assertIn("IMAGE_REGION_OWNERSHIP_MISMATCH", self.codes())

    def test_diagram_cannot_extend_into_next_section_title(self):
        old = self.region(5)["bbox"]
        self.change_bbox(5, [old[0], old[1], old[2], 466])
        self.assertIn("IMAGE_REGION_OUTSIDE_REVIEW_SCOPE", self.codes())

    def test_pixel_hash_and_source_hash_mutations_are_reported(self):
        self.region(5)["crop_rgb_sha256"] = "0" * 64
        rehash(self.regions)
        self.assertIn("IMAGE_REGION_PIXEL_MISMATCH", self.codes())
        self.setUp()
        self.region(5)["source_sha256"] = "0" * 64
        rehash(self.regions)
        self.assertIn("IMAGE_REGION_SOURCE_MISMATCH", self.codes())

    def test_old_evidence_revision_is_not_reusable(self):
        self.evidence["revision"] += 1
        self.assertIn("IMAGE_REGION_STALE_BINDING", self.codes())

    def test_label_set_and_text_only_role_cannot_replace_image(self):
        self.region(7)["diagnostic_ocr_refs"] = ["resource-173/ocr/23"]
        rehash(self.regions)
        self.assertIn("IMAGE_REGION_LABEL_SET_MISMATCH", self.codes())
        self.setUp()
        self.region(7)["content_type"] = "text"
        rehash(self.regions)
        self.assertIn("IMAGE_REGION_SOURCE_MISMATCH", self.codes())

    def test_human_or_business_claims_cannot_be_added_to_model_regions(self):
        for field, value in [("reference_quality", "HUMAN_REVIEWED"),
                             ("verification_status", "VERIFIED"),
                             ("semantic_status", "VERIFIED"), ("business_acceptance", True)]:
            with self.subTest(field=field):
                self.setUp()
                self.region(5)[field] = value
                rehash(self.regions)
                self.assertIn("IMAGE_REGION_FALSE_VERIFICATION", self.codes())

    def test_model_source_review_cannot_be_upgraded_to_human_gold(self):
        self.review["payload"]["reference_quality"] = "HUMAN_REVIEWED"
        self.rebind_review()
        self.assertIn("IMAGE_REGION_SOURCE_INVALID", self.codes())

    def test_replaced_capture_bytes_fail_even_before_region_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_captures(root)
            descriptor = self.review["payload"]["captures"][1]
            image = Image.open(root / descriptor["path"]).convert("RGB")
            image.putpixel((100, 200), tuple(255 - channel for channel in image.getpixel((100, 200))))
            image.save(root / descriptor["path"])
            self.assertIn("IMAGE_REGION_SOURCE_INVALID", self.codes(root))

    def test_blank_capture_with_fresh_file_hash_cannot_erase_frozen_witness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_captures(root)
            descriptor = self.review["payload"]["captures"][1]
            image = Image.new("RGB", (485, 398), "white")
            image.save(root / descriptor["path"])
            descriptor["sha256"] = file_digest(root / descriptor["path"])
            descriptor["rgb_sha256"] = rgb_hash(image)
            self.rebind_review()
            # The consumer must return an explicit rejected check, not crash
            # when a formerly nonempty witness becomes empty.
            self.codes(root)

    def test_artifact_header_book_and_scope_must_match_bound_source(self):
        for field in ("book_id", "scope_id"):
            with self.subTest(field=field):
                self.setUp()
                self.regions[field] = "another-" + field
                self.codes()

    def test_review_scope_must_match_bound_evidence(self):
        self.review["scope_id"] = "another-scope"
        self.rebind_review()
        self.codes()

    def test_capture_source_dimensions_must_match_original_descriptor(self):
        self.review["payload"]["captures"][0]["source_size"] = [2000, 2000]
        self.rebind_review()
        self.codes()

    def test_structural_evidence_never_authorizes_platform_actions(self):
        self.regions["payload"]["platform_actions"] = [{"operation": "DRAW_AND_SUBMIT"}]
        rehash(self.regions)
        self.codes()


if __name__ == "__main__":
    unittest.main()
