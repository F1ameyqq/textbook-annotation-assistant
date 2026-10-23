"""Synthetic offline evidence tests; no models, platform, or private material."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from annotation.recognition.usense_capture import CaptureReader, file_ref
from annotation.recognition.usense_candidates import assemble, check, read_json


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ocr, self.capture = self.root / "ocr", self.root / "capture"
        self.ocr.mkdir()
        self.image = self.root / "page.png"
        Image.new("RGB", (100, 100), "gray").save(self.image)
        page = {"file": file_ref(self.image), "sha256": file_ref(self.image)["sha256"], "dimensions": [100, 100]}
        self.frames = [{"rect_id": zone, "type": zone, "page_index": 2,
            "rect_bbox": "10,10,80,80", "directory_id": "lesson", "order_in_level": "4"}
            for zone in ("question", "answer")]
        self.info = {"id": "info", "file_id": "46007447", "order_in_level": 4}
        data = {"directory": {"directory_data": [{"id": "lesson", "children": [
                    {"id": "node", "order_in_level": 4}]}]}, "frames": self.frames,
                "q4_info": self.info, "q4_annotations": self.frames}
        declarations = {}
        for name, value in data.items():
            path = self.capture / (name + ".json")
            put(path, {"code": 0, "data": value})
            declarations[name] = {**file_ref(path), "status": 200}
        put(self.capture / "capture-summary.json", {"captures": declarations})
        self.manifest = self.root / "source-manifest.json"
        put(self.manifest, {"synthetic": True})
        put(self.ocr / "sources.json", {"pages": {"2": page}, "source_manifest": file_ref(self.manifest),
            "capture_directory": str(self.capture), "capture_summary": file_ref(self.capture / "capture-summary.json"),
            "readback_manifest": None})
        raw = {}
        for frame in self.frames:
            crop = self.ocr / (frame["type"] + ".png")
            with Image.open(self.image) as image:
                image.crop((10, 10, 80, 80)).save(crop)
            raw[frame["type"]] = [{"platform_frame": frame, "zone": frame["type"],
                "source": page, "crop": file_ref(crop),
                "variants": [{"joined_raw_text": "raw " + frame["type"]}]}]
        put(self.ocr / "raw.json", raw)
        self.candidate = {"schema": "LessonQuestionOCRCandidate/v1", "status": "REVIEW_REQUIRED",
            "write_allowed": False, "question_order": 4, "book_id": "46007447", "node_id": "node",
            "question_info_id": "info", "question_info": self.info, "lesson_id": "lesson",
            "platform_frames": self.frames, "raw_results": file_ref(self.ocr / "raw.json"),
            "raw_zone_text": {"question": "raw question", "choice": "", "answer": "raw answer"},
            "issues": [{"code": "SYNTHETIC_ISSUE"}]}
        put(self.ocr / "candidate.json", self.candidate)
        self.run = {"status": "REAL_LOCAL_BATCH_OCR_DONE_REVIEW_REQUIRED", "orders": [4],
            "network_disabled": True, "platform_requests": 0, "script": file_ref(self.manifest),
            "adapter": file_ref(self.manifest), "candidates": [
                {"order": 4, "candidate": file_ref(self.ocr / "candidate.json")} ]}
        put(self.ocr / "run.json", self.run)
        self.span = {"viewer_page": 2, "bbox": [12, 12, 75, 75], "purpose": "synthetic source check"}
        self.review = {"schema": "UsenseOCRSourceReview/v1", "review_kind": "MODEL_VISUAL",
            "scope": {"complete_lesson_denominator": None}, "items": [{"native_order": 4,
            "revisions": [{"field": "answer", "before": "raw answer", "after": "x² + y²",
                "reason": "visible superscripts", "evidence": [self.span]}],
            "diagrams": [self.span], "formulas": [{"field": "answer", "transcription": "x² + y²",
                "evidence": [self.span]}]}]}
        self.review_path = self.root / "review.json"

    def build(self, review=True):
        if review:
            put(self.review_path, self.review)
        return assemble(self.ocr, self.review_path if review else None, self.root / "out")

    def test_raw_and_revisions_remain_distinct_with_pixel_proof(self):
        result = self.build()
        item = result["items"][0]
        self.assertEqual(item["raw_fields"]["answer"], "raw answer")
        self.assertEqual(item["proposal_fields"]["answer"], "x² + y²")
        self.assertEqual(len(item["diagrams"]), 1)
        self.assertEqual(len(item["formulas"]), 1)
        self.assertEqual(check(self.root / "out/candidates.json")["items"], 1)
        self.assertFalse(result["write_allowed"])
        self.assertIsNone(result["human_confirmation"])

    def test_no_review_keeps_unknown_mapping_and_exact_ocr(self):
        item = self.build(False)["items"][0]
        self.assertIsNone(item["mapping"])
        self.assertEqual(item["mapping_status"], "UNKNOWN")
        self.assertEqual(item["raw_fields"], item["proposal_fields"])
        self.assertFalse(item["write_allowed"])

    def test_source_revision_requires_evidence(self):
        self.review["items"][0]["revisions"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "source evidence"):
            self.build()

    def test_answer_cannot_use_question_only_frame(self):
        self.span["bbox"] = [81, 81, 95, 95]
        with self.assertRaisesRegex(ValueError, "matching captured"):
            self.build()

    def test_wrong_role_page_rejected(self):
        self.frames[1]["type"] = "question"
        # The declared original capture is immutable; input alteration fails.
        put(self.ocr / "candidate.json", self.candidate)
        self.run["candidates"][0]["candidate"] = file_ref(self.ocr / "candidate.json")
        put(self.ocr / "run.json", self.run)
        with self.assertRaisesRegex(ValueError, "frames changed"):
            self.build()

    def test_stale_revision_predecessor_rejected(self):
        self.review["items"][0]["revisions"][0]["before"] = "other OCR"
        with self.assertRaisesRegex(ValueError, "predecessor"):
            self.build()

    def test_duplicate_review_and_out_of_scope_order_rejected(self):
        self.review["items"].append(deepcopy(self.review["items"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.build()

    def test_out_of_scope_review_rejected(self):
        self.review["items"][0]["native_order"] = 5
        with self.assertRaisesRegex(ValueError, "scopes differ"):
            self.build()

    def test_out_of_bounds_source_rejected(self):
        self.span["bbox"][2] = 101
        with self.assertRaisesRegex(ValueError, "outside page"):
            self.build()

    def test_nonfinite_bbox_rejected(self):
        self.span["bbox"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "Finite"):
            self.build()

    def test_source_image_change_rejected(self):
        Image.new("RGB", (100, 100), "white").save(self.image)
        with self.assertRaisesRegex(ValueError, "reference changed"):
            self.build()

    def test_raw_ocr_hash_change_rejected(self):
        put(self.ocr / "raw.json", {})
        with self.assertRaisesRegex(ValueError, "reference changed"):
            self.build()

    def test_same_value_revision_rejected(self):
        self.review["items"][0]["revisions"][0]["after"] = "raw answer"
        with self.assertRaisesRegex(ValueError, "changed transcription"):
            self.build()

    def test_review_cannot_establish_denominator_or_human_approval(self):
        self.review["scope"]["complete_lesson_denominator"] = 1
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.build()

    def test_human_review_kind_rejected(self):
        self.review["review_kind"] = "HUMAN"
        with self.assertRaisesRegex(ValueError, "non-human"):
            self.build()

    def test_generated_crop_tamper_rejected(self):
        result = self.build()
        crop = result["items"][0]["diagrams"][0]["evidence"][0]["crop"]["path"]
        Image.new("RGB", (63, 63), "white").save(crop)
        with self.assertRaisesRegex(ValueError, "crop changed"):
            check(self.root / "out/candidates.json")

    def test_package_acceptance_elevation_rejected(self):
        self.build()
        path = self.root / "out/candidates.json"
        value = read_json(path)
        value["write_allowed"] = True
        put(path, value)
        with self.assertRaisesRegex(ValueError, "elevated"):
            check(path)

    def test_reviewer_cannot_implicitly_migrate_native_identity(self):
        self.review["items"][0]["mapping"] = {"semantic_lesson": 2, "printed_number": 1,
            "legacy_native_order": 3, "evidence": [self.span]}
        item = self.build()["items"][0]
        self.assertEqual(item["native_order"], 4)
        self.assertEqual(item["captured_directory_id"], "lesson")
        self.assertEqual(item["mapping"]["status"], "MODEL_VISUAL_OBSERVATION_NOT_CANONICAL_MIGRATION")

    def test_exclusive_output(self):
        self.build()
        with self.assertRaises(FileExistsError):
            self.build()

    def test_cli_can_check_from_other_working_directory(self):
        self.build()
        tool = Path(__file__).resolve().parents[1] / "tools/assemble_usense_candidates.py"
        run = subprocess.run([sys.executable, str(tool), "check", "--package",
                              str(self.root / "out/candidates.json")], cwd=self.root,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(json.loads(run.stdout)["write_allowed"])


class MergedCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.merged = self.root / "merged"
        self.manifest = self.root / "manifest.json"
        rows = []
        for run_id in ("run-1", "run-2"):
            original = self.root / run_id / "frames.json"
            put(original, {"code": 0, "data": [{"synthetic": True}]})
            put(self.root / run_id / "capture-summary.json", {"captures": {
                "frames": {**file_ref(original), "status": 200}}})
            rows.append({"name": "frames", "run_id": run_id, "sha256": file_ref(original)["sha256"]})
        put(self.manifest, rows)
        self.merged.mkdir()
        (self.merged / "frames.json").write_bytes((self.root / "run-1/frames.json").read_bytes())

    def test_identical_common_responses_across_readers_allowed(self):
        reader = CaptureReader(self.merged, self.manifest)
        self.assertEqual(reader.get("frames"), [{"synthetic": True}])

    def test_conflicting_common_response_rejected(self):
        path = self.root / "run-2/frames.json"
        put(path, {"code": 0, "data": []})
        put(self.root / "run-2/capture-summary.json", {"captures": {
            "frames": {**file_ref(path), "status": 200}}})
        rows = read_json(self.manifest)
        rows[1]["sha256"] = file_ref(path)["sha256"]
        put(self.manifest, rows)
        with self.assertRaisesRegex(ValueError, "original HTTP summary"):
            CaptureReader(self.merged, self.manifest).get("frames")

    def test_changed_merged_response_rejected(self):
        put(self.merged / "frames.json", {"code": 0, "data": []})
        with self.assertRaisesRegex(ValueError, "original HTTP summary"):
            CaptureReader(self.merged, self.manifest).get("frames")

    def test_path_traversal_in_manifest_rejected(self):
        rows = read_json(self.manifest)
        rows[0]["run_id"] = "../escape"
        put(self.manifest, rows)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            CaptureReader(self.merged, self.manifest)

    def test_manifest_must_match_original_summary(self):
        rows = read_json(self.manifest)
        rows[0]["sha256"] = "0" * 64
        put(self.manifest, rows)
        with self.assertRaisesRegex(ValueError, "disagree"):
            CaptureReader(self.merged, self.manifest)

    def test_original_entity_bytes_rechecked(self):
        (self.root / "run-2/frames.json").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Merged and original"):
            CaptureReader(self.merged, self.manifest).get("frames")


if __name__ == "__main__":
    unittest.main()
