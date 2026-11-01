"""Mathematical role evidence and omission-risk regressions, without new OCR.

Backend injections are explicitly synthetic.  The real-crop regression tests
pixel witnesses even when two synthetic OCR passes make the same omission; it
does not turn reviewed mathematical text into an OCR or accuracy expectation.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.math_reading import CONFIG, collect_math_roles, build_math_reading
from annotation.recognition.recovery_apply import reference
from replay_math_b import replay


def backend(bgr, **flags):
    if flags != {"use_det": False, "use_cls": False, "use_rec": True}:
        raise AssertionError("recognition-only flags required")
    if bgr.dtype != np.uint8 or not bgr.flags.c_contiguous or bgr.shape[2] != 3:
        raise AssertionError("BGR uint8 contiguous pixels required")
    return [["a+1", .999]], [.01]


def rehash(artifact):
    artifact["content_hash"] = digest(artifact["payload"])
    return artifact


def tiny_layout(directory):
    """Non-formula test geometry has no raised ink and a crop-edge numerator."""
    path = Path(directory) / "base.png"
    image = Image.new("RGB", (40, 32), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 6, 9], fill=(120, 0, 0))
    draw.rectangle([10, 0, 15, 9], fill="black")
    draw.rectangle([0, 13, 20, 14], fill="black")
    draw.rectangle([7, 17, 12, 26], fill="black")
    image.save(path)
    fraction = {"fraction_id": "test-fraction", "bar_bbox": [100, 213, 121, 215],
                "numerator": {"pixel_bbox": [100, 200, 116, 210], "ocr_refs": [], "raw_texts": []},
                "denominator": {"pixel_bbox": [107, 217, 113, 227], "ocr_refs": [], "raw_texts": []},
                "ambiguous_ocr_refs": []}
    payload = {"asset_id": "synthetic-source", "source_sha256": "1"*64, "source_size": [200, 400],
               "crop_bbox": [100, 200, 140, 232], "crop_sha256": file_digest(path),
               "fraction_candidates": [fraction], "source_ocr": [], "reading_groups": [], "issues": []}
    layout = {"schema_version": "b-math-layout-trial/0.1", "artifact_id": "synthetic-layout", "revision": 1,
              "book_id": "synthetic", "scope_id": "source-pixel-test", "content_hash": digest(payload), "payload": payload}
    return layout, path


class MathRoleEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout, _, cls.crop = replay(FIXTURE)
        cls.evidence = collect_math_roles(cls.layout, cls.crop, recognizer=backend)
        cls.reading = build_math_reading(cls.layout, cls.evidence, cls.crop)

    def test_all_22_roles_have_two_declared_raw_hypotheses_and_source_receipts(self):
        roles = self.evidence["payload"]["roles"]
        self.assertEqual(len(roles), 22)
        self.assertEqual(len({r["role_id"] for r in roles}), 22)
        self.assertEqual([(r["fraction_id"], r["role"]) for r in roles],
                         [(f["fraction_id"], role) for f in self.layout["payload"]["fraction_candidates"]
                          for role in ("numerator", "denominator")])
        for role in roles:
            self.assertEqual(role["verification_status"], "UNVERIFIED")
            self.assertEqual([v["variant_id"] for v in role["variants"]], [v["variant_id"] for v in CONFIG["variants"]])
            for variant in role["variants"]:
                self.assertEqual(variant["raw_ocr_result"], [["a+1", .999]])
                self.assertEqual(variant["engine_elapsed_seconds"], [.01])
                self.assertGreaterEqual(variant["wall_elapsed_seconds"], 0)
                self.assertIsNone(variant["recognition_error"])
                self.assertEqual(variant["candidates"][0]["text"], "a+1")
                self.assertEqual(variant["candidates"][0]["raw_result_index"], 0)
                self.assertEqual(len(variant["transformed_bgr_sha256"]), 64)
        self.assertEqual(self.evidence["payload"]["layout_ref"], reference(self.layout))

    def test_injected_recognizer_cannot_claim_real_cpu_or_model(self):
        backend.execution_kind = "CPU_RAPIDOCR"
        backend.model_files = [{"name": "pretend-real-model"}]
        evidence = collect_math_roles(self.layout, self.crop, recognizer=backend)
        producer = evidence["producer"]
        self.assertEqual(producer["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(producer["device"], "SYNTHETIC_TEST")
        self.assertEqual(producer["model_files"], [])
        self.assertEqual(producer["dependencies"], {})

    def test_every_existing_role_is_reread_and_original_tokens_remain(self):
        for original in self.layout["payload"]["fraction_candidates"]:
            result = next(f for f in self.reading["payload"]["fractions"] if f["fraction_id"] == original["fraction_id"])
            for role in ("numerator", "denominator"):
                self.assertEqual(result[role]["original_ocr_refs"], original[role]["ocr_refs"])
                self.assertEqual(result[role]["original_raw_texts"], original[role]["raw_texts"])
                self.assertEqual(len(result[role]["variants"]), 2)
                self.assertEqual(len(result[role]["candidate_refs"]), 2)
                self.assertEqual(result[role]["selected_candidate_refs"], [])
            self.assertEqual(result["ambiguous_ocr_refs"], original["ambiguous_ocr_refs"])

    def test_real_last_numerator_equal_omission_retains_faint_raised_pixel_risk(self):
        last = self.reading["payload"]["fractions"][-1]["numerator"]
        self.assertTrue(last["exact_two_pass_agreement"])
        self.assertEqual(last["consensus_text"], "a+1")
        risks = last["pixel_risks"]
        self.assertTrue(risks)
        # Source pixel location only, not an assertion of mathematical text.
        witness = next(r for r in risks if r["component_bbox"][0] <= 940 < r["component_bbox"][2])
        self.assertEqual(witness["code"], "SUPERSCRIPT_PIXEL_RISK")
        self.assertIn(210, witness["threshold_votes"])
        # Tight layout pixels start at y339. The OCR crop includes the faint
        # component's full top at y337, which must survive in a symbol slot.
        self.assertLessEqual(witness["component_bbox"][1], 337)
        self.assertGreaterEqual(witness["component_bbox"][3], 343)
        self.assertEqual(witness["status"], "UNRESOLVED")
        self.assertFalse(witness["transcription_verified"])
        self.assertTrue(last["raised_symbol_slots"])
        self.assertTrue(any(s["source_bbox"][1] <= 337 and s["source_bbox"][3] >= 343
                            for s in last["raised_symbol_slots"]))
        self.assertTrue(all(s["status"] == "NOT_ATTEMPTED" and s["candidate_refs"] == [] for s in last["raised_symbol_slots"]))
        self.assertFalse(last["complete"])

    def test_nested_reading_order_and_original_ocr_are_immutable(self):
        before = copy.deepcopy((self.layout, self.evidence))
        reading = build_math_reading(self.layout, self.evidence, self.crop)
        self.assertEqual((self.layout, self.evidence), before)
        self.assertEqual(reading["payload"]["reading_groups"], self.layout["payload"]["reading_groups"])
        self.assertEqual(reading["payload"]["source_ocr"], self.layout["payload"]["source_ocr"])
        row = reading["payload"]["reading_groups"][0]
        self.assertEqual([u.get("raw_text") for u in row["units"][:3]], ["16.解：（1）60", "61", "(2)"])
        self.assertEqual(row["units"][3]["kind"], "fraction")
        self.assertEqual(reading["artifact_id"], self.reading["artifact_id"])
        self.assertEqual(reading["content_hash"], self.reading["content_hash"])

    def test_no_consensus_or_confidence_is_upgraded_to_verification(self):
        for artifact in (self.evidence, self.reading):
            payload = artifact["payload"]
            self.assertEqual(payload["decision"], "HOLD")
            self.assertFalse(payload["complete"])
            self.assertFalse(payload["transcription_verified"])
            self.assertFalse(payload["formula_text_reconstructed"])
            self.assertFalse(payload["visual_formula_references_consumed"])
            self.assertEqual(payload["platform_actions"], [])
        self.assertFalse(self.reading["payload"]["graph_modified"])

    def test_wrong_crop_stale_layout_and_cross_source_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            wrong = Path(directory) / "wrong.png"
            Image.new("RGB", tuple(self.evidence["payload"]["source"]["base_crop_size"]), "white").save(wrong)
            with self.assertRaises(ValueError): collect_math_roles(self.layout, wrong, recognizer=backend)
        layout = copy.deepcopy(self.layout)
        layout["payload"]["source_sha256"] = "0"*64
        with self.assertRaises(ValueError): collect_math_roles(layout, self.crop, recognizer=backend)
        rehash(layout)
        with self.assertRaises(ValueError): build_math_reading(layout, self.evidence, self.crop)

    def test_missing_duplicate_or_reordered_role_cannot_be_read_as_full_coverage(self):
        for mutation in ("missing", "duplicate", "reordered"):
            with self.subTest(mutation=mutation):
                evidence = copy.deepcopy(self.evidence)
                roles = evidence["payload"]["roles"]
                if mutation == "missing": roles.pop()
                elif mutation == "duplicate": roles[-1] = copy.deepcopy(roles[0])
                else: roles.reverse()
                with self.assertRaises(ValueError): build_math_reading(self.layout, rehash(evidence), self.crop)

    def test_raw_candidate_source_coordinate_and_pixel_tampering_are_rejected(self):
        for mutation in ("candidate", "transform", "rgb", "bgr", "preprocess", "no_variant"):
            with self.subTest(mutation=mutation):
                evidence = copy.deepcopy(self.evidence)
                role = evidence["payload"]["roles"][0]
                variant = role["variants"][0]
                if mutation == "candidate": variant["candidates"][0]["text"] = "invented²"
                elif mutation == "transform": variant["transformed_to_source"][0][2] += 1
                elif mutation == "rgb": role["role_crop_rgb_sha256"] = "0"*64
                elif mutation == "bgr": variant["transformed_bgr_sha256"] = "0"*64
                elif mutation == "preprocess": variant["contrast"] = 7
                else: role["variants"].pop()
                with self.assertRaises(ValueError): build_math_reading(self.layout, rehash(evidence), self.crop)

    def test_failure_and_empty_raw_preserve_unresolved_roles_without_copying_other_text(self):
        with tempfile.TemporaryDirectory() as directory:
            layout, path = tiny_layout(directory)
            count = [0]
            def failing(bgr, **flags):
                count[0] += 1
                if count[0] % 2: raise RuntimeError("synthetic recognizer unavailable")
                return None, [.01]
            evidence = collect_math_roles(layout, path, recognizer=failing)
            reading = build_math_reading(layout, evidence, path)
            self.assertEqual(count[0], 4)
            for role in ("numerator", "denominator"):
                result = reading["payload"]["fractions"][0][role]
                self.assertIsNotNone(result["variants"][0]["recognition_error"])
                self.assertIsNone(result["variants"][1]["raw_ocr_result"])
                self.assertEqual(result["candidate_refs"], [])
                self.assertIsNone(result["consensus_text"])
                self.assertIn("MATH_ROLE_OCR_EMPTY_OR_FAILED", {r["code"] for r in result["recognition_risks"]})

    def test_unrecognized_symbols_and_disagreement_remain_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            layout, path = tiny_layout(directory)
            count = [0]
            def symbols(bgr, **flags):
                count[0] += 1
                return [["量" if count[0] % 2 else "?", .99]], [.01]
            evidence = collect_math_roles(layout, path, recognizer=symbols)
            reading = build_math_reading(layout, evidence, path)
            for role in ("numerator", "denominator"):
                result = reading["payload"]["fractions"][0][role]
                self.assertFalse(result["exact_two_pass_agreement"])
                codes = {r["code"] for r in result["recognition_risks"]}
                self.assertEqual(codes, {"MATH_ROLE_OCR_DISAGREEMENT", "MATH_UNSUPPORTED_SYMBOL_RISK"})
                self.assertFalse(result["complete"])

    def test_padding_is_exactly_two_clipped_to_base_and_plain_pixels_have_no_raised_risk(self):
        with tempfile.TemporaryDirectory() as directory:
            layout, path = tiny_layout(directory)
            evidence = collect_math_roles(layout, path, recognizer=backend)
            reading = build_math_reading(layout, evidence, path)
            numerator = evidence["payload"]["roles"][0]
            self.assertEqual(numerator["crop_bbox"], [100, 200, 118, 212])
            self.assertEqual(numerator["crop_local_bbox"], [0, 0, 18, 12])
            self.assertEqual(numerator["role_crop_size"], [18, 12])
            for role in ("numerator", "denominator"):
                self.assertEqual(reading["payload"]["fractions"][0][role]["pixel_risks"], [])

    def test_no_fraction_input_remains_empty_and_unverified(self):
        with tempfile.TemporaryDirectory() as directory:
            layout, path = tiny_layout(directory)
            layout["payload"]["fraction_candidates"] = []
            rehash(layout)
            def no_call(*args, **kwargs): raise AssertionError("no role to read")
            evidence = collect_math_roles(layout, path, recognizer=no_call)
            reading = build_math_reading(layout, evidence, path)
            self.assertEqual(evidence["payload"]["roles"], [])
            self.assertEqual(reading["payload"]["fractions"], [])
            self.assertEqual(reading["payload"]["decision"], "HOLD")

    def test_role_on_wrong_side_and_duplicate_fraction_are_rejected_before_ocr(self):
        for kind in ("side", "duplicate"):
            with self.subTest(kind=kind):
                layout = copy.deepcopy(self.layout)
                first = layout["payload"]["fraction_candidates"][0]
                if kind == "side": first["numerator"]["pixel_bbox"] = first["denominator"]["pixel_bbox"]
                else: layout["payload"]["fraction_candidates"].append(copy.deepcopy(first))
                with self.assertRaises(ValueError): collect_math_roles(rehash(layout), self.crop, recognizer=backend)

    def test_recorded_cpu_fixture_when_available_replays_without_loading_engine(self):
        path = FIXTURE / "math-role-evidence.json"
        if not path.exists(): self.skipTest("root has not yet saved the actual CPU role evidence")
        evidence = json.loads(path.read_text(encoding="utf-8"))
        reading = build_math_reading(self.layout, evidence, self.crop)
        self.assertEqual(evidence["producer"]["execution_kind"], "CPU_RAPIDOCR")
        self.assertTrue(evidence["producer"]["model_files"])
        self.assertTrue(evidence["producer"]["dependencies"])
        self.assertEqual(len(evidence["payload"]["roles"]), 22)
        self.assertEqual(sum(len(r["variants"]) for r in evidence["payload"]["roles"]), 44)
        self.assertEqual(reading["payload"]["decision"], "HOLD")
        self.assertFalse(reading["payload"]["formula_text_reconstructed"])


if __name__ == "__main__": unittest.main()
