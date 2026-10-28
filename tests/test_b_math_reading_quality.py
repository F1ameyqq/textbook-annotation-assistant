"""Independent quality faults over labelled synthetic OCR and fixed pixels.

The backend is deliberately an invented test backend, never a CPU receipt or
formula gold. Actual cached CPU observations are tested separately when present.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.math_reading import collect_math_roles, build_math_reading
from annotation.recognition.math_reading_quality import audit_math_reading, raised_ink_observations


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


def ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def synthetic_layout(directory, *, raised=True, equal_noise=False):
    """Known test rectangles, including a visibly elevated, detached ink group.

    Numerator coordinates imitate the geometry of the 40x14 real counterexample
    without calling these blocks a recognized mathematical expression.
    """
    path = Path(directory)/"synthetic-math.png"
    image = Image.new("RGB", (60, 50), "white")
    draw = ImageDraw.Draw(image)
    # Tight numerator: local [5,2,45,16], body baseline=14.
    draw.rectangle([7,7,13,13], fill="black")
    draw.rectangle([23,3,34,13], fill="black")
    draw.rectangle([39,4,42,13], fill="black")
    if raised:
        draw.rectangle([16,2,18,7], fill="black")
    if equal_noise:
        draw.line([16,2,18,2], fill="black")
        draw.line([16,4,18,4], fill="black")
    draw.rectangle([4,20,45,21], fill="black")
    draw.rectangle([20,29,29,40], fill="black")
    image.save(path)
    fraction = {"fraction_id": "synthetic-fraction-1", "bar_bbox": [104,220,146,222],
                "numerator": {"pixel_bbox": [105,202,145,216], "ocr_refs": ["synthetic/old/0"],
                              "raw_texts": ["old candidate"], "missing_ocr": False},
                "denominator": {"pixel_bbox": [120,229,130,241], "ocr_refs": [],
                                "raw_texts": [], "missing_ocr": True},
                "ambiguous_ocr_refs": [], "status": "LAYOUT_TRANSCRIPTION_PARTIAL", "verification_status": "UNVERIFIED"}
    payload = {"asset_id": "synthetic-source", "source_sha256": "1"*64, "source_size": [1000,1000],
               "crop_bbox": [100,200,160,250], "crop_sha256": file_digest(path),
               "fraction_candidates": [fraction], "reading_groups": [{"row_id": "test-row", "baseline_y": 221,
                   "units": [{"kind": "fraction", "fraction_id": fraction["fraction_id"], "x": 104,
                              "ocr_refs": ["synthetic/old/0"]}], "status": "LAYOUT_CANDIDATE_UNVERIFIED"}],
               "source_ocr": [{"line_id": "synthetic/old/0", "text": "old candidate", "bbox": [105,202,145,216]}],
               "issues": [{"code": "MATH_ROLE_MISSING_OCR", "role": "denominator"}],
               "decision": "HOLD", "transcription_verified": False, "formula_text_reconstructed": False,
               "visual_formula_references_consumed": False, "platform_actions": []}
    layout = {"schema_version": "b-math-layout-trial/0.1", "kind": "MathLayoutTrial",
              "artifact_id": "synthetic-layout", "revision": 1, "run_id": "synthetic-run",
              "book_id": "synthetic-book", "scope_id": "synthetic-scope", "payload": payload}
    return rehash(layout), path


def make_observations(layout, path, outputs=None):
    outputs = outputs if outputs is not None else ["a+1", "a+1", "2", "2"]
    position = iter(outputs)

    def labelled_synthetic_backend(pixels, **flags):
        text = next(position)
        if isinstance(text, Exception):
            raise text
        return ([] if text is None else [[text, .95]]), [0.001]

    evidence = collect_math_roles(layout, path, recognizer=labelled_synthetic_backend)
    reading = build_math_reading(layout, evidence, path)
    return evidence, reading


class IndependentMathReadingQuality(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.layout, self.path = synthetic_layout(self.directory.name)
        self.evidence, self.reading = make_observations(self.layout, self.path)

    def audit(self, evidence=None, reading=None, layout=None):
        return audit_math_reading(layout or self.layout, evidence or self.evidence,
                                  reading or self.reading, self.path)["payload"]

    def assertCode(self, code, *, evidence=None, reading=None, layout=None):
        result = self.audit(evidence, reading, layout)
        self.assertFalse(result["accepted"], result)
        self.assertIn(code, {i["code"] for i in result["issues"]}, result)
        self.assertEqual(result["decision"], "HOLD")

    def with_evidence_fault(self):
        return copy.deepcopy(self.evidence), copy.deepcopy(self.reading)

    def bind_modified_evidence(self, evidence, reading):
        rehash(evidence)
        reading["payload"]["role_evidence_ref"] = ref(evidence)
        reading["input_refs"][1] = ref(evidence)
        return rehash(reading)

    def test_traceable_synthetic_agreement_retains_unresolved_pixels_and_hold(self):
        result = self.audit()
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["summary"]["role_count"], 2)
        self.assertEqual(result["summary"]["two_pass_agreement_count"], 2)
        self.assertGreater(result["summary"]["raised_ink_risk_count"], 0)
        role = self.reading["payload"]["fractions"][0]["numerator"]
        self.assertEqual(role["consensus_text"], "a+1")
        self.assertTrue(role["pixel_risks"])
        self.assertFalse(result["transcription_verified"])
        self.assertFalse(result["business_acceptance"])
        self.assertEqual(result["platform_actions"], [])
        self.assertEqual(self.evidence["producer"]["execution_kind"], "SYNTHETIC_TEST")

    def test_quality_does_not_import_or_run_the_reading_producer(self):
        before = copy.deepcopy((self.layout, self.evidence, self.reading))
        with mock.patch("annotation.recognition.math_reading.collect_math_roles", side_effect=AssertionError("producer ran")), \
             mock.patch("annotation.recognition.math_reading.build_math_reading", side_effect=AssertionError("producer ran")):
            self.assertTrue(self.audit()["accepted"])
        self.assertEqual(before, (self.layout, self.evidence, self.reading))
        module = sys.modules["annotation.recognition.math_reading_quality"]
        self.assertNotIn("from .math_reading import", Path(module.__file__).read_text(encoding="utf-8"))

    def test_missing_or_duplicated_role_is_not_inferred_from_other_role(self):
        for operation in ("missing", "duplicate"):
            with self.subTest(operation=operation):
                evidence, reading = self.with_evidence_fault()
                if operation == "missing": evidence["payload"]["roles"].pop()
                else: evidence["payload"]["roles"].append(copy.deepcopy(evidence["payload"]["roles"][0]))
                self.bind_modified_evidence(evidence, reading)
                self.assertCode("MATH_READING_ROLE_COVERAGE_MISMATCH", evidence=evidence, reading=reading)

    def test_role_order_and_numerator_denominator_projection_are_bound(self):
        reading = copy.deepcopy(self.reading)
        fraction = reading["payload"]["fractions"][0]
        fraction["numerator"], fraction["denominator"] = fraction["denominator"], fraction["numerator"]
        self.assertCode("MATH_READING_ROLE_PROJECTION_MISMATCH", reading=rehash(reading))

    def test_missing_second_preprocessing_is_not_two_independent_reads(self):
        evidence, reading = self.with_evidence_fault()
        evidence["payload"]["roles"][0]["variants"].pop()
        reading["payload"]["fractions"][0]["numerator"]["variants"].pop()
        self.bind_modified_evidence(evidence, reading)
        self.assertCode("MATH_READING_VARIANT_COVERAGE_MISMATCH", evidence=evidence, reading=reading)

    def test_coordinated_candidate_change_cannot_override_retained_raw(self):
        evidence, reading = self.with_evidence_fault()
        evidence["payload"]["roles"][0]["variants"][0]["candidates"][0]["text"] = "a²+1"
        reading["payload"]["fractions"][0]["numerator"]["variants"] = copy.deepcopy(evidence["payload"]["roles"][0]["variants"])
        self.bind_modified_evidence(evidence, reading)
        self.assertCode("MATH_READING_RAW_TRANSCRIPTION_MISMATCH", evidence=evidence, reading=reading)

    def test_omitted_raw_alternative_is_not_silently_selected(self):
        evidence, reading = self.with_evidence_fault()
        evidence["payload"]["roles"][0]["variants"][0]["candidates"] = []
        reading["payload"]["fractions"][0]["numerator"]["variants"] = copy.deepcopy(evidence["payload"]["roles"][0]["variants"])
        self.bind_modified_evidence(evidence, reading)
        self.assertCode("MATH_READING_RAW_CANDIDATE_COVERAGE_MISMATCH", evidence=evidence, reading=reading)

    def test_coordinated_wrong_transform_and_pixel_digest_are_recomputed(self):
        for key, value in (("transformed_to_source", [[1/6,0,0],[0,1/6,0],[0,0,1]]),
                           ("transformed_bgr_sha256", "0"*64)):
            with self.subTest(key=key):
                evidence, reading = self.with_evidence_fault()
                evidence["payload"]["roles"][0]["variants"][0][key] = value
                reading["payload"]["fractions"][0]["numerator"]["variants"] = copy.deepcopy(evidence["payload"]["roles"][0]["variants"])
                self.bind_modified_evidence(evidence, reading)
                self.assertCode("MATH_READING_TRANSFORM_MISMATCH", evidence=evidence, reading=reading)

    def test_role_crop_must_include_the_bound_source_pixels(self):
        evidence, reading = self.with_evidence_fault()
        evidence["payload"]["roles"][0]["crop_bbox"][0] += 1
        reading["payload"]["fractions"][0]["numerator"]["crop_bbox"][0] += 1
        self.bind_modified_evidence(evidence, reading)
        self.assertCode("MATH_READING_ROLE_PIXELS_MISMATCH", evidence=evidence, reading=reading)

    def test_two_pass_agreement_cannot_delete_actual_raised_ink_risk(self):
        reading = copy.deepcopy(self.reading)
        numerator = reading["payload"]["fractions"][0]["numerator"]
        numerator["pixel_risks"], numerator["raised_symbol_slots"] = [], []
        reading["payload"]["issues"] = []  # Coordinated ledger deletion too.
        self.assertCode("MATH_READING_RAISED_INK_RISK_DROPPED", reading=rehash(reading))

    def test_risk_slot_cannot_invent_a_recognized_character(self):
        reading = copy.deepcopy(self.reading)
        reading["payload"]["fractions"][0]["numerator"]["raised_symbol_slots"][0]["text"] = "2"
        self.assertCode("MATH_READING_RAISED_SLOT_MISMATCH", reading=rehash(reading))

    def test_two_equal_strings_do_not_authorize_completeness_or_selection(self):
        for field, value in (("complete", True), ("transcription_verified", True), ("selected_candidate_refs", ["invented"])):
            with self.subTest(field=field):
                reading = copy.deepcopy(self.reading)
                reading["payload"]["fractions"][0]["numerator"][field] = value
                self.assertCode("MATH_READING_FALSE_VERIFICATION", reading=rehash(reading))

    def test_changed_source_crop_bytes_and_stale_revisions_reject(self):
        reading = copy.deepcopy(self.reading)
        reading["payload"]["layout_ref"]["revision"] = 99
        self.assertCode("MATH_READING_STALE_REFERENCE", reading=rehash(reading))
        Image.new("RGB", (60,50), "white").save(self.path)
        self.assertCode("MATH_READING_SOURCE_PIXELS_MISMATCH")

    def test_reading_order_and_original_ambiguities_cannot_disappear(self):
        reading = copy.deepcopy(self.reading)
        reading["payload"]["reading_groups"][0]["units"] = []
        self.assertCode("MATH_READING_LAYOUT_ORDER_CHANGED", reading=rehash(reading))
        reading = copy.deepcopy(self.reading)
        reading["payload"]["source_layout_issues"] = []
        self.assertCode("MATH_READING_LAYOUT_ISSUES_CHANGED", reading=rehash(reading))

    def test_backend_failures_and_empty_readings_remain_explicit_hold(self):
        for first in (None, RuntimeError("labelled synthetic failure")):
            with self.subTest(first=str(first)):
                evidence, reading = make_observations(self.layout, self.path, [first, "a+1", "2", "2"])
                result = self.audit(evidence, reading)
                self.assertTrue(result["accepted"], result)
                role = reading["payload"]["fractions"][0]["numerator"]
                self.assertFalse(role["exact_two_pass_agreement"])
                self.assertEqual(role["recognition_risks"][0]["code"], "MATH_ROLE_OCR_EMPTY_OR_FAILED")
                role["recognition_risks"] = []
                self.assertCode("MATH_READING_RECOGNITION_RISK_DROPPED", evidence=evidence, reading=rehash(reading))

    def test_disagreement_and_unsupported_characters_are_not_silently_resolved(self):
        evidence, reading = make_observations(self.layout, self.path, ["a+1", "α+1", "2", "2"])
        result = self.audit(evidence, reading)
        self.assertTrue(result["accepted"], result)
        role = reading["payload"]["fractions"][0]["numerator"]
        self.assertIsNone(role["consensus_text"])
        self.assertEqual({r["code"] for r in role["recognition_risks"]},
                         {"MATH_ROLE_OCR_DISAGREEMENT", "MATH_UNSUPPORTED_SYMBOL_RISK"})

    def test_plain_body_height_and_one_pixel_equal_noise_do_not_prove_superscript(self):
        for equal_noise in (False, True):
            with self.subTest(equal_noise=equal_noise):
                layout, path = synthetic_layout(self.directory.name, raised=False, equal_noise=equal_noise)
                evidence, reading = make_observations(layout, path)
                result = self.audit(evidence, reading, layout)
                self.assertTrue(result["accepted"], result)
                self.assertEqual(result["summary"]["raised_ink_risk_count"], 0)
                self.assertFalse(result["transcription_verified"])

    def test_synthetic_backend_cannot_be_relabelled_human_or_cpu_without_receipts(self):
        evidence, reading = self.with_evidence_fault()
        evidence["producer"]["execution_kind"] = "CPU_RAPIDOCR"
        reading["producer"]["execution_kind"] = "CPU_RAPIDOCR"
        self.assertCode("MATH_READING_BACKEND_RECEIPT_INVALID", evidence=evidence, reading=reading)
        reading = copy.deepcopy(self.reading)
        reading["payload"]["human_reviewed"] = True
        self.assertCode("MATH_READING_FALSE_VERIFICATION", reading=rehash(reading))

    def test_unknown_nested_final_formula_claim_cannot_bypass_false_verification_guards(self):
        reading = copy.deepcopy(self.reading)
        reading["payload"]["fractions"][0]["verified_formula"] = "(a²+1)/2"
        self.assertCode("MATH_READING_UNKNOWN_FIELD", reading=rehash(reading))


class RealCachedMathReadingQuality(unittest.TestCase):
    """Frozen real CPU observations; expected omissions are never input gold."""
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT/"tools"))
        from replay_math_b import replay
        fixture = ROOT/"tests/fixtures/book46007447"
        cls.layout, _, cls.path = replay(fixture)
        cls.evidence = json.loads((fixture/"math-role-evidence.json").read_text(encoding="utf-8"))
        cls.reading = build_math_reading(cls.layout, cls.evidence, cls.path)

    def test_real_22_roles_44_cached_passes_are_traceable_not_verified(self):
        checked = audit_math_reading(self.layout, self.evidence, self.reading, self.path)["payload"]
        self.assertTrue(checked["accepted"], checked)
        self.assertEqual(checked["summary"]["fraction_count"], 11)
        self.assertEqual(checked["summary"]["role_count"], 22)
        self.assertEqual(sum(len(role["variants"]) for role in self.evidence["payload"]["roles"]), 44)
        self.assertEqual(checked["summary"]["missing_reading_count"], 0)
        self.assertEqual(checked["summary"]["two_pass_agreement_count"], 19)
        self.assertEqual(self.evidence["producer"]["execution_kind"], "CPU_RAPIDOCR")
        self.assertEqual(checked["decision"], "HOLD")
        self.assertFalse(checked["transcription_verified"])
        self.assertFalse(checked["business_acceptance"])

    def test_actual_last_numerator_agrees_a_plus_one_but_source_raised_ink_remains(self):
        numerator = self.reading["payload"]["fractions"][-1]["numerator"]
        self.assertEqual(numerator["pixel_bbox"], [930,339,966,349])
        self.assertEqual([v["raw_ocr_result"][0][0] for v in numerator["variants"]], ["a+1", "a+1"])
        self.assertTrue(numerator["exact_two_pass_agreement"])
        checked = audit_math_reading(self.layout, self.evidence, self.reading, self.path)["payload"]
        local = [risk for risk in checked["pixel_risks"] if risk["role_id"] == numerator["role_id"]]
        self.assertEqual(len(local), 1)
        self.assertEqual(local[0]["component_bbox"], [939,337,942,343])
        self.assertEqual(local[0]["threshold"], 210)
        self.assertEqual(local[0]["status"], "UNRESOLVED")
        self.assertFalse(numerator["complete"])
        # The original 40x14 padded crop is retained; quality inspects unscaled
        # source ink rather than inferring a missing character from its text.
        self.assertEqual(numerator["role_crop_size"], [40,14])

    def test_coordinated_real_risk_slot_and_issue_deletion_is_rejected_after_rehash(self):
        reading = copy.deepcopy(self.reading)
        numerator = reading["payload"]["fractions"][-1]["numerator"]
        rid = numerator["role_id"]
        numerator["pixel_risks"], numerator["raised_symbol_slots"] = [], []
        reading["payload"]["issues"] = [i for i in reading["payload"]["issues"]
                                         if i.get("role_id") != rid or i.get("code") != "SUPERSCRIPT_PIXEL_RISK"]
        checked = audit_math_reading(self.layout, self.evidence, rehash(reading), self.path)["payload"]
        self.assertFalse(checked["accepted"])
        self.assertIn("MATH_READING_RAISED_INK_RISK_DROPPED", {i["code"] for i in checked["issues"]})
        self.assertEqual(numerator["consensus_text"], "a+1")
        self.assertEqual(self.evidence["payload"]["roles"][-2]["variants"][0]["raw_ocr_result"][0][0], "a+1")

    def test_clipped_high_component_cannot_become_a_future_half_character_slot(self):
        reading = copy.deepcopy(self.reading)
        numerator = reading["payload"]["fractions"][-1]["numerator"]
        risk = numerator["pixel_risks"][0]
        risk["component_bbox"][1] = 339  # Drops the actual top two source rows.
        origin = self.layout["payload"]["crop_bbox"][:2]
        with Image.open(self.path) as image:
            local = [risk["component_bbox"][i]-origin[i % 2] for i in range(4)]
            tile = image.convert("RGB").crop(local)
            risk["component_pixel_sha256"] = hashlib.sha256(np.asarray(tile).tobytes()).hexdigest()
        slot = numerator["raised_symbol_slots"][0]
        slot.update(source_bbox=copy.deepcopy(risk["component_bbox"]), source_pixel_sha256=risk["component_pixel_sha256"],
                    slot_id="math-raised-symbol-"+digest([numerator["role_id"],risk["component_bbox"],risk["component_pixel_sha256"]])[:24])
        # Keep all duplicated ledgers coherent: the source pixel independently
        # proves that this risk still omits part of the raised component.
        for item in reading["payload"]["issues"]:
            if item.get("role_id") == numerator["role_id"] and item.get("code") == "SUPERSCRIPT_PIXEL_RISK":
                item.update(copy.deepcopy(risk))
        checked = audit_math_reading(self.layout,self.evidence,rehash(reading),self.path)["payload"]
        self.assertFalse(checked["accepted"])
        self.assertIn("MATH_READING_RAISED_INK_RISK_DROPPED", {i["code"] for i in checked["issues"]})


if __name__ == "__main__":
    unittest.main()
