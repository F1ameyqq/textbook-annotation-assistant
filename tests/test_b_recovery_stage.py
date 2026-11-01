"""Exact recovery migration, with real source pixels and synthetic OCR receipts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.offline import artifact, assemble, quality_check
from annotation.recognition.recovery_apply import derive_evidence, reference
from annotation.recognition.recovery_stage import POLICY, load_recovery_package, recover_evidence, build_recovery_review


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def make_recovery_fixture(directory):
    """Two generated images, one genuinely replaced raw row, no engine calls."""
    root = Path(directory)
    assets = []
    for i, aid in enumerate(("question", "answer")):
        image = Image.new("RGB", (700, 400), "white")
        ImageDraw.Draw(image).text((35, 42), "1.4" if i else "1. 2+2?", fill="black")
        path = root / (aid+".png")
        image.save(path)
        assets.append({"asset_id": aid, "path": path.name, "sha256": file_digest(path), "width": 700,
                       "height": 400, "reading_order": i, "reference_quality": "SYNTHETIC_TEST"})
    source = {"schema_version": "b-source-trial/0.1", "artifact_id": "synthetic-source", "book_id": "synthetic-book",
              "scope_id": "two-source-assets", "assets": assets}
    context = {"schema_version": "b-context-trial/0.1", "artifact_id": "synthetic-context", "book_id": source["book_id"],
               "scope_id": source["scope_id"], "pages": {a["asset_id"]: {"sha256": a["sha256"], "role": a["asset_id"],
                   "windows": [{"column": 0, "y_range": [20, 380], "path": ["Synthetic section"]}]} for a in assets}}
    location = {"column": 0, "window_index": 0, "section_path": ["Synthetic section"]}
    pages = []
    for asset in assets:
        aid = asset["asset_id"]
        line = {"line_id": aid+"/ocr/0", "text": "1.求2+2的值。" if aid == "question" else "1.3", "score": .9,
                "bbox": [30, 40, 300, 60] if aid == "question" else [30, 40, 100, 60], "location": copy.deepcopy(location)}
        detail = []
        if aid == "answer":
            detail = [{**copy.deepcopy(line), "line_id": aid+"/ocr/0/detail/0", "parent_line_id": line["line_id"]}]
        pages.append({"asset_id": aid, "source": asset, "page_role": aid, "layout": {"mode": "two_columns", "cut_x": 350},
                      "ocr_lines": [line], "answer_detail_lines": detail, "unscoped_line_ids": []})
    base = artifact("b-evidence-trial/0.2", "EvidenceBundleTrial", source,
                    {"pages": pages, "context": context, "history_annotations_consumed": False, "quality_decision": "NOT_EVALUATED"},
                    [], {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST"})
    box = [25, 35, 110, 70]
    crop_path = root / "answer-crop.png"
    with Image.open(root / "answer.png") as image:
        crop = image.convert("RGB").crop(box)
    crop.save(crop_path)
    line_id = "recovery/fix-answer/scale1/0"
    replacement = {"line_id": line_id, "text": "1.4", "score": .95, "bbox": box, "polygon": None,
                   "asset_id": "answer", "location": copy.deepcopy(location), "base_line_ids": ["answer/ocr/0"]}
    variant = {"variant_id": "scale1", "scale": 1, "contrast": 1.0, "use_det": False, "use_cls": False,
               "use_rec": True, "transformed_pixels_sha256": hashlib.sha256(np.asarray(crop)[:, :, ::-1].copy().tobytes()).hexdigest(),
               "crop_to_original": [[1, 0, box[0]], [0, 1, box[1]], [0, 0, 1]], "raw_ocr_result": [["1.4", .95]],
               "elapsed_seconds": [.001], "ocr_lines": [replacement]}
    probe = {"probe_id": "fix-answer", "asset_id": "answer", "source_sha256": assets[1]["sha256"], "source_size": [700, 400],
             "crop_bbox": box, "crop_path": crop_path.name, "crop_sha256": file_digest(crop_path), "location": copy.deepcopy(location),
             "selected_variant_id": "scale1", "status": "SYNTHETIC_TEST_UNVERIFIED", "variants": [variant]}
    plan = {"plan_id": "synthetic-replacement", "asset_id": "answer", "source_sha256": assets[1]["sha256"],
            "action": "REPLACE_FOR_ASSEMBLY", "base_line_ids": ["answer/ocr/0"], "replacement_line_ids": [line_id],
            "selected_probe_ids": ["fix-answer"], "location": copy.deepcopy(location)}
    recovery = artifact("b-recovery-trial/0.1", "RecoveryEvidenceTrial", base,
                        {"base_evidence_ref": reference(base), "probes": [probe], "supersession_plan": [plan]}, [reference(base)],
                        {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST", "engine": "injected_test_backend",
                         "device": "SYNTHETIC_TEST", "dependencies": {}, "dependency_sha256": digest({}), "model_files": []})
    sr = artifact("b-source-review-trial/0.1", "SourceRecoveryReviewTrial", base,
                  {"base_evidence_ref": reference(base), "recovery_ref": reference(recovery), "reviewed_exclusions": [],
                   "reviewed_probe_selections": [], "formula_candidates": [], "triage": [], "remaining_source_groups": [],
                   "regression_additions": [], "recovered_answer_checks": []}, [reference(base), reference(recovery)],
                  {"module": "SYNTHETIC_TEST", "reference_quality": "SYNTHETIC_TEST"})
    review = {"schema_version": "b-review-trial/0.1", "artifact_id": "synthetic-review", "book_id": source["book_id"],
              "scope_id": source["scope_id"], "reference_quality": "SYNTHETIC_TEST", "answer_checks": [],
              "question_census": {"question": {"sha256": assets[0]["sha256"], "printed_numbers": ["1"]}}}
    current = copy.deepcopy(base)
    current.update(artifact_id="fresh-current-base", run_id="fresh-current-run", revision=2,
                   producer={"module": "SYNTHETIC_TEST_CURRENT", "execution_kind": "SYNTHETIC_TEST"})
    data = {"source": source, "context": context, "review": review, "base_evidence": base, "recovery": recovery,
            "source_review": sr, "current": current}
    for name, value in data.items(): write(root / (name+".json"), value)
    data["package"] = {"schema_version": "b-recovery-package-trial/0.1", "artifact_id": "synthetic-package", "book_id": source["book_id"],
                       "scope_id": source["scope_id"], "policy": POLICY, "documents": {}}
    refresh_package(root, data)
    return data


def refresh_package(root, data):
    """Explicit test editing utility; it never repairs a changed base payload."""
    root = Path(root)
    for name in ("base_evidence", "recovery", "source_review"):
        value = data[name]
        value["content_hash"] = digest(value["payload"])
        if name == "source_review":
            value["payload"]["recovery_ref"] = reference(data["recovery"])
            value["input_refs"] = [reference(data["base_evidence"]), reference(data["recovery"])]
            value["content_hash"] = digest(value["payload"])
        write(root / (name+".json"), value)
        text = (root / (name+".json")).read_text(encoding="utf-8")
        data["package"]["documents"][name] = {"path": name+".json", "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                              "artifact_ref": reference(value)}
    write(root / "package.json", data["package"])


class RecoveryStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = make_recovery_fixture(self.root)

    def recover(self, current=None):
        return recover_evidence(current or self.data["current"], self.root / "package.json", self.root / "source.json", self.data["context"])

    def test_new_identity_exact_payload_recovery_keeps_all_historical_envelopes(self):
        snapshot = copy.deepcopy(self.data)
        migrated = self.recover()
        migration = migrated["payload"]["recovery_migration"]
        self.assertTrue(migration["current_identity_differs"])
        self.assertEqual(migration["current_base_ref"], reference(self.data["current"]))
        self.assertEqual(migrated["run_id"], "fresh-current-run")
        legacy = derive_evidence(self.data["base_evidence"], self.data["recovery"], self.data["source_review"], artifact)
        self.assertEqual({k: v for k, v in migrated["payload"].items() if k != "recovery_migration"}, legacy["payload"])
        self.assertEqual(migrated["payload"]["base_evidence_archive"], self.data["base_evidence"])
        self.assertEqual(migrated["payload"]["recovery_evidence_archive"], self.data["recovery"])
        self.assertEqual(migration["original_source_review_archive"], self.data["source_review"])
        self.assertEqual(self.data, snapshot)

    def test_actual_replacement_is_active_but_old_raw_and_detail_survive_in_archive(self):
        migrated = self.recover()
        answer = migrated["payload"]["pages"][1]
        self.assertEqual([l["text"] for l in answer["ocr_lines"]], ["1.4"])
        self.assertEqual(answer["answer_detail_lines"], [])
        archived = migrated["payload"]["base_evidence_archive"]["payload"]["pages"][1]
        self.assertEqual(archived["ocr_lines"][0]["text"], "1.3")
        self.assertEqual(archived["answer_detail_lines"][0]["text"], "1.3")
        self.assertEqual(migrated["payload"]["recovery_evidence_archive"]["producer"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(migrated["producer"]["new_ocr_calls"], 0)

    def test_any_raw_detail_or_extra_payload_change_refuses_equivalence(self):
        for kind in ("raw", "detail", "metadata"):
            with self.subTest(kind=kind):
                current = copy.deepcopy(self.data["current"])
                if kind == "raw": current["payload"]["pages"][0]["ocr_lines"][0]["score"] = .91
                elif kind == "detail": current["payload"]["pages"][1]["answer_detail_lines"][0]["text"] = "changed"
                else: current["payload"]["extra"] = "not equivalent"
                current["content_hash"] = digest(current["payload"])
                with self.assertRaisesRegex(ValueError, "canonical base payload equivalence"): self.recover(current)

    def test_recovering_e3_twice_and_migrating_review_twice_are_refused(self):
        migrated = self.recover()
        with self.assertRaises(ValueError): self.recover(migrated)
        review = build_recovery_review(self.data["review"], migrated)
        self.assertEqual(review["payload"]["review"]["recovery_migration_ref"], reference(migrated))
        with self.assertRaises(ValueError): build_recovery_review(review["payload"]["review"], migrated)

    def test_crop_pixel_substitution_fails_even_after_rehashing_package_documents(self):
        path = self.root / "answer-crop.png"
        with Image.open(path) as source:
            size = source.size
        Image.new("RGB", size, "white").save(path)
        self.data["recovery"]["payload"]["probes"][0]["crop_sha256"] = file_digest(path)
        refresh_package(self.root, self.data)
        with self.assertRaisesRegex(ValueError, "original source pixels"): self.recover()

    def test_preprocessed_pixels_are_recomputed_from_the_actual_crop(self):
        self.data["recovery"]["payload"]["probes"][0]["variants"][0]["transformed_pixels_sha256"] = "0"*64
        refresh_package(self.root, self.data)
        with self.assertRaisesRegex(ValueError, "preprocessing pixels"): self.recover()

    def test_document_text_hash_normalizes_crlf_but_runtime_receipt_locks_bytes(self):
        path = self.root / "base_evidence.json"
        path.write_bytes(path.read_text(encoding="utf-8").encode("utf-8"))
        before = load_recovery_package(self.root / "package.json", self.root / "source.json", self.data["context"])["receipt"]
        path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
        after = load_recovery_package(self.root / "package.json", self.root / "source.json", self.data["context"])["receipt"]
        self.assertEqual(before["documents"]["base_evidence"]["text_sha256"], after["documents"]["base_evidence"]["text_sha256"])
        self.assertNotEqual(before["documents"]["base_evidence"]["file_sha256"], after["documents"]["base_evidence"]["file_sha256"])
        self.assertTrue(self.recover()["payload"]["recovery_migration"]["payloads_equal"])

    def test_normalized_package_and_reference_bound_time_give_stable_downstream_identities(self):
        files = [self.root / name for name in ("package.json", "base_evidence.json", "recovery.json", "source_review.json")]
        for path in files: path.write_bytes(path.read_text(encoding="utf-8").encode("utf-8"))
        before = self.recover()
        before_review = build_recovery_review(self.data["review"], before)
        before_graph = assemble(before)
        before_check = quality_check(before, before_graph, before_review["payload"]["review"])
        runtime_before = load_recovery_package(self.root / "package.json", self.root / "source.json", self.data["context"])["receipt"]
        for path in files: path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
        current = copy.deepcopy(self.data["current"])
        current["created_at"] = "2040-01-01T00:00:00Z"
        after = self.recover(current)
        after_review = build_recovery_review(self.data["review"], after)
        after_graph = assemble(after)
        after_check = quality_check(after, after_graph, after_review["payload"]["review"])
        runtime_after = load_recovery_package(self.root / "package.json", self.root / "source.json", self.data["context"])["receipt"]
        self.assertEqual(before, after)
        self.assertEqual(before_review, after_review)
        self.assertEqual(reference(before_graph), reference(after_graph))
        self.assertEqual(reference(before_check), reference(after_check))
        self.assertNotEqual(runtime_before["package"]["file_sha256"], runtime_after["package"]["file_sha256"])
        self.assertEqual(runtime_before["crops"], runtime_after["crops"])
        self.assertNotIn("created_at", after)
        self.assertNotIn("created_at", after_review)
        self.assertEqual(after["payload"]["base_evidence_archive"], self.data["base_evidence"])
        self.assertEqual(after["payload"]["recovery_evidence_archive"], self.data["recovery"])
        self.assertEqual(after["payload"]["recovery_migration"]["original_source_review_archive"], self.data["source_review"])

    def test_document_path_escape_unknown_policy_and_stale_refs_are_rejected(self):
        original = copy.deepcopy(self.data)
        for kind in ("escape", "policy", "ref"):
            with self.subTest(kind=kind):
                self.data = copy.deepcopy(original)
                if kind == "escape": self.data["package"]["documents"]["base_evidence"]["path"] = "../outside.json"
                elif kind == "policy": self.data["package"]["policy"] = "SAME_PAGE_SHA_IS_ENOUGH"
                else: self.data["package"]["documents"]["recovery"]["artifact_ref"]["artifact_id"] = "other"
                write(self.root / "package.json", self.data["package"])
                with self.assertRaises(ValueError): self.recover()


if __name__ == "__main__": unittest.main()
