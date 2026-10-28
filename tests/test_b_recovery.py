"""Recovery provenance, immutable assembly views, and injected input faults.

These tests replay recorded CPU hypotheses and small source crops. They never
run an OCR model, contact a website, or treat development formulas as gold truth.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0, str(ROOT / "src"))

from annotation.recognition.baseline import digest, file_digest, valid_bbox
from annotation.recognition.offline import artifact
from annotation.recognition.recovery import DEFAULT_PROBES, VARIANTS, _select
from annotation.recognition.recovery_apply import derive_evidence, reference


def read(name):
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


def minimal_review(base, recovery, **extra):
    payload = {"base_evidence_ref": reference(base), "recovery_ref": reference(recovery), "reviewed_exclusions": [],
               "reviewed_probe_selections": [], "formula_candidates": [], **extra}
    return artifact("b-source-review-trial/0.1", "SourceReviewTrial", base, payload,
                    [reference(base)], {"module": __name__, "reference_quality": "SYNTHETIC_TEST_ONLY"})


class RecoveryFixtureProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = read("ocr-evidence.json")
        cls.recovery = read("recovery-evidence.json")

    def test_exact_base_binding_and_original_counts(self):
        recovery, base = self.recovery, self.base
        self.assertEqual(recovery["schema_version"], "b-recovery-trial/0.1")
        self.assertEqual(recovery["content_hash"], digest(recovery["payload"]))
        self.assertEqual(recovery["payload"]["base_evidence_ref"], reference(base))
        self.assertEqual(recovery["payload"]["run_status"], "COMPLETE")
        self.assertTrue(recovery["payload"]["base_evidence_unchanged"])
        self.assertEqual(sum(len(p["ocr_lines"]) for p in base["payload"]["pages"]), 424)
        self.assertEqual(sum(len(p["answer_detail_lines"]) for p in base["payload"]["pages"]), 82)

    def test_all_crop_bytes_dimensions_and_source_hashes_are_bound(self):
        assets = {p["asset_id"]: p["source"] for p in self.base["payload"]["pages"]}
        probes = self.recovery["payload"]["probes"]
        self.assertEqual(len(probes), 27)
        for probe in probes:
            path = FIXTURE / probe["crop_path"]
            self.assertEqual(file_digest(path), probe["crop_sha256"])
            self.assertEqual(probe["source_sha256"], assets[probe["asset_id"]]["sha256"])
            self.assertEqual(probe["source_size"], [assets[probe["asset_id"]]["width"], assets[probe["asset_id"]]["height"]])
            x1,y1,x2,y2 = probe["crop_bbox"]
            with Image.open(path) as crop:
                self.assertEqual(crop.size, (x2-x1,y2-y1))

    def test_all_54_preprocessed_pixel_hashes_recompute_without_ocr(self):
        count = 0
        for probe in self.recovery["payload"]["probes"]:
            with Image.open(FIXTURE / probe["crop_path"]) as source:
                source = source.convert("RGB")
                for variant in probe["variants"]:
                    scale = variant["scale"]
                    pixels = source.resize((source.width*scale,source.height*scale),Image.Resampling.LANCZOS)
                    if variant["contrast"] != 1:
                        pixels = ImageEnhance.Contrast(pixels).enhance(variant["contrast"])
                    bgr = np.array(pixels)[:,:,::-1].copy()
                    self.assertEqual(hashlib.sha256(bgr.tobytes()).hexdigest(), variant["transformed_pixels_sha256"])
                    x,y = probe["crop_bbox"][:2]
                    self.assertEqual(variant["crop_to_original"], [[1/scale,0,x],[0,1/scale,y],[0,0,1]])
                    count += 1
        self.assertEqual(count, 54)

    def test_all_185_engine_hypotheses_keep_raw_text_score_and_geometry(self):
        ids = []
        for probe in self.recovery["payload"]["probes"]:
            for variant in probe["variants"]:
                raw = variant["raw_ocr_result"] or []
                self.assertEqual(len(raw),len(variant["ocr_lines"]))
                for item,line in zip(raw,variant["ocr_lines"]):
                    text,score = (item[1],item[2]) if variant["use_det"] else item[:2]
                    self.assertEqual(line["text"],text)
                    self.assertEqual(line["score"],score)
                    self.assertEqual(line["verification_status"],"UNVERIFIED")
                    self.assertTrue(valid_bbox(line["bbox"],*probe["source_size"]))
                    if variant["use_det"]:
                        x,y = probe["crop_bbox"][:2]
                        scale = variant["scale"]
                        expected = [[round(px/scale+x,4),round(py/scale+y,4)] for px,py in item[0]]
                        self.assertEqual(line["polygon"],expected)
                    else:
                        self.assertEqual(line["bbox"],probe["crop_bbox"])
                    ids.append(line["line_id"])
        self.assertEqual(len(ids),185)
        self.assertEqual(len(ids),len(set(ids)))

    def test_selection_policy_and_dependency_configuration_receipts_recompute(self):
        producer = self.recovery["producer"]
        self.assertEqual(producer["dependency_sha256"],digest(producer["dependencies"]))
        self.assertEqual(producer["configuration_sha256"],digest({"probes":DEFAULT_PROBES,"variants":VARIANTS}))
        self.assertEqual(len(producer["model_files"]),3)
        for model in producer["model_files"]:
            self.assertTrue(model["name"].endswith(".onnx"))
            self.assertRegex(model["sha256"],r"^[0-9a-f]{64}$")
        for probe in self.recovery["payload"]["probes"]:
            self.assertEqual(_select(probe),(probe["selected_variant_id"],probe["status"],probe["selection_rationale"]))

    def test_exact_five_plans_29_replacements_and_formula_limits(self):
        plans = self.recovery["payload"]["supersession_plan"]
        self.assertEqual(len(plans),5)
        self.assertEqual({p["plan_id"] for p in plans},{"unit2-q16","lesson2-row79","lesson2-q6-q7","unit2-q9-q10","topic1-training-q3-q4"})
        ids = [line for plan in plans for line in plan["replacement_line_ids"]]
        self.assertEqual(len(ids),29)
        self.assertEqual(len(ids),len(set(ids)))
        probes = {p["probe_id"]:p for p in self.recovery["payload"]["probes"]}
        self.assertEqual(probes["unit2-q16"]["status"],"ANCHOR_RECOVERED_FORMULAS_UNRESOLVED")
        self.assertIsNone(probes["lesson1-q16-formula-row1"]["selected_variant_id"])
        self.assertIsNone(probes["lesson2-variant"]["selected_variant_id"])
        for slot in self.recovery["payload"]["visual_transcription_slots"]:
            self.assertEqual(slot["method"],"MODEL_VISUAL_DEVELOPMENT_TRANSCRIPTION")
            self.assertIsNone(slot["text"])
            self.assertEqual(slot["status"],"NOT_POPULATED")


class RecoveryApplyFaultRegression(unittest.TestCase):
    def setUp(self):
        self.base = read("ocr-evidence.json")
        self.recovery = read("recovery-evidence.json")
        self.review = minimal_review(self.base,self.recovery)

    def derive(self):
        return derive_evidence(self.base,self.recovery,self.review,artifact)

    def bind_changed_recovery(self):
        """Rebind the test review so deeper faults cannot pass only via staleness."""
        rehash(self.recovery)
        self.review["payload"]["recovery_ref"] = reference(self.recovery)
        rehash(self.review)

    def first_selected_line(self):
        plan = self.recovery["payload"]["supersession_plan"][0]
        ref = plan["replacement_line_ids"][0]
        return next(line for probe in self.recovery["payload"]["probes"]
                    for variant in probe["variants"] for line in variant["ocr_lines"] if line["line_id"] == ref)

    def test_derivation_archives_base_without_mutating_any_input(self):
        before = copy.deepcopy((self.base,self.recovery,self.review))
        derived = self.derive()
        self.assertEqual((self.base,self.recovery,self.review),before)
        self.assertEqual(derived["schema_version"],"b-evidence-trial/0.3")
        self.assertEqual(derived["payload"]["base_evidence_archive"],self.base)
        self.assertEqual(sum(len(p["ocr_lines"]) for p in derived["payload"]["pages"]),439)
        self.assertEqual(len(derived["payload"]["recovery_application"]["replaced_base_line_ids"]),14)
        self.assertTrue(derived["payload"]["recovery_application"]["base_unchanged"])
        active = {l["line_id"]:l for p in derived["payload"]["pages"] for l in p["ocr_lines"]}
        for ref in derived["payload"]["recovery_application"]["replacement_line_ids"]:
            self.assertEqual(active[ref]["source_type"],"LOCAL_CPU_OCR_RECOVERY")
            self.assertFalse(active[ref]["independent_confirmation"])

    def test_stale_base_reference_and_changed_artifact_payload_rejected(self):
        for target in ("recovery","review"):
            with self.subTest(target=target):
                original = getattr(self,target)
                altered = copy.deepcopy(original)
                altered["payload"]["base_evidence_ref"]["revision"] += 1
                setattr(self,target,rehash(altered))
                with self.assertRaises(ValueError):self.derive()
                setattr(self,target,original)
        self.recovery["payload"]["run_status"] = "FORGED"
        with self.assertRaises(ValueError):self.derive()

    def test_foreign_book_or_scope_rejected(self):
        for key in ("book_id","scope_id"):
            original = self.recovery[key]
            self.recovery[key] = "foreign"
            with self.assertRaises(ValueError):self.derive()
            self.recovery[key] = original

    def test_probe_or_plan_source_hash_mismatch_rejected(self):
        for kind in ("probes","supersession_plan"):
            item = self.recovery["payload"][kind][0]
            original = item["source_sha256"]
            item["source_sha256"] = "0"*64
            self.bind_changed_recovery()
            with self.assertRaises(ValueError):self.derive()
            item["source_sha256"] = original
            self.bind_changed_recovery()

    def test_unknown_and_cross_asset_base_lines_rejected(self):
        plan = self.recovery["payload"]["supersession_plan"][0]
        old = plan["base_line_ids"][0]
        for ref in ("not-observed", "viewer-10/ocr/0"):
            plan["base_line_ids"][0] = ref
            self.bind_changed_recovery()
            with self.assertRaises(ValueError):self.derive()
        plan["base_line_ids"][0] = old

    def test_overlapping_plans_and_duplicate_old_ids_rejected(self):
        plan = self.recovery["payload"]["supersession_plan"][0]
        self.recovery["payload"]["supersession_plan"].append(copy.deepcopy(plan))
        self.bind_changed_recovery()
        with self.assertRaises(ValueError):self.derive()
        self.recovery["payload"]["supersession_plan"].pop()
        plan["base_line_ids"].append(plan["base_line_ids"][0])
        self.bind_changed_recovery()
        with self.assertRaises(ValueError):self.derive()

    def test_duplicate_unknown_and_unselected_replacements_rejected(self):
        plan = self.recovery["payload"]["supersession_plan"][0]
        original = list(plan["replacement_line_ids"])
        unselected = original[0].replace("/scale3/","/scale4-contrast/")
        for replacements in ([original[0],original[0]],["unknown-recovery-line"],[unselected]):
            plan["replacement_line_ids"] = replacements
            self.bind_changed_recovery()
            with self.assertRaises(ValueError):self.derive()
        plan["replacement_line_ids"] = original

    def test_duplicate_pool_ids_cross_asset_or_out_of_bounds_geometry_rejected(self):
        original = copy.deepcopy(self.recovery)
        line = self.first_selected_line()
        probe = self.recovery["payload"]["probes"][0]
        probe["variants"][0]["ocr_lines"].append(copy.deepcopy(line))
        self.bind_changed_recovery()
        with self.assertRaises(ValueError):self.derive()
        for key,value in (("asset_id","viewer-10"),("bbox",[-1,1,50,50])):
            self.recovery = copy.deepcopy(original)
            self.first_selected_line()[key] = value
            self.bind_changed_recovery()
            with self.assertRaises(ValueError):self.derive()

    def test_formula_reference_is_preserved_as_visual_candidate_not_cpu_ocr(self):
        candidate = {"candidate_id":"synthetic-formula-reference", "method":"MODEL_VISUAL_DEVELOPMENT_TRANSCRIPTION",
                     "text":"VISUAL-ONLY-TEST-CANDIDATE", "verification_status":"UNVERIFIED"}
        self.review = minimal_review(self.base,self.recovery,formula_candidates=[candidate])
        derived = self.derive()
        self.assertEqual(derived["payload"]["recovery_application"]["formula_candidates"],[candidate])
        self.assertNotIn(candidate["text"], [line["text"] for page in derived["payload"]["pages"] for line in page["ocr_lines"]])

    def test_reviewed_selection_requires_reason_source_and_correct_asset(self):
        probe = next(p for p in self.recovery["payload"]["probes"] if p["probe_id"] == "lesson2-variant")
        line = probe["variants"][0]["ocr_lines"][0]
        selection = {"line_id":line["line_id"], "source_sha256":probe["source_sha256"],
                     "reason":"SYNTHETIC_TEST: explicit review of recorded unresolved OCR hypothesis"}
        self.review = minimal_review(self.base,self.recovery,reviewed_probe_selections=[selection])
        derived = self.derive()
        added = next(l for p in derived["payload"]["pages"] for l in p["ocr_lines"] if l["line_id"] == line["line_id"])
        self.assertEqual(added["source_type"],"LOCAL_CPU_OCR_REVIEWED_SELECTION")
        self.assertFalse(added["independent_confirmation"])
        line["asset_id"] = "viewer-10"
        self.bind_changed_recovery()
        with self.assertRaises(ValueError):self.derive()

    def test_unknown_review_selection_or_changed_reviewed_source_rejected(self):
        for selection in ({"line_id":"unknown","source_sha256":"0"*64,"reason":"test"},
                          {"line_id":"recovery/lesson2-variant/scale3/0","source_sha256":"0"*64,"reason":"test"},
                          {"line_id":"recovery/lesson2-variant/scale3/0","source_sha256":self.recovery["payload"]["probes"][0]["source_sha256"],"reason":""}):
            self.review = minimal_review(self.base,self.recovery,reviewed_probe_selections=[selection])
            with self.assertRaises(ValueError):self.derive()

    def test_source_review_must_bind_exact_recovery_revision(self):
        self.review["payload"]["recovery_ref"]["revision"] += 1
        rehash(self.review)
        with self.assertRaises(ValueError):self.derive()

    def test_changed_derived_text_score_or_geometry_cannot_masquerade_as_cpu(self):
        original = copy.deepcopy(self.recovery)
        mutations = [("text","FORGED-CPU-TRANSCRIPTION"),("score",.12345),
                     ("bbox",[581,265,620,280])]
        for key,value in mutations:
            with self.subTest(field=key):
                self.recovery = copy.deepcopy(original)
                self.first_selected_line()[key] = value
                self.bind_changed_recovery()
                with self.assertRaises(ValueError):self.derive()

    def test_changed_transform_rejected_even_when_payload_and_review_rebound(self):
        self.recovery["payload"]["probes"][0]["variants"][0]["crop_to_original"][0][2] += 1
        self.bind_changed_recovery()
        with self.assertRaises(ValueError):self.derive()

    def test_unknown_plan_asset_and_cross_scope_replacement_rejected(self):
        plan = self.recovery["payload"]["supersession_plan"][0]
        old_asset = plan["asset_id"]
        plan["asset_id"] = "unknown-asset"
        self.bind_changed_recovery()
        with self.assertRaises(ValueError):self.derive()
        plan["asset_id"] = old_asset
        self.first_selected_line()["location"]["section_path"] = ["Foreign chapter"]
        self.bind_changed_recovery()
        with self.assertRaises(ValueError):self.derive()


if __name__ == "__main__":
    unittest.main()
