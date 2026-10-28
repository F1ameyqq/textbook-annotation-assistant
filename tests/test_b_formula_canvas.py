"""Preserved faint pixels, sizing traces and unselected old/new observations.

Recognizers in these tests are explicit tensor-only synthetic backends. No OCR
runtime, model inference, website or visual expected formula is consumed.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.formula_backend import plan_formula_units, reference
from annotation.recognition.formula_candidates import build_formula_candidates
from annotation.recognition.formula_canvas import (
    CONFIG, _full_pad, _minmax_size, plan_canvas_units, preprocess_canvas,
    collect_canvas_observations, build_canvas_candidates,
)


def read(name):
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def rehash(observation):
    observation["content_hash"] = digest(observation["payload"])
    observation["artifact_id"] = "formula-canvas-observations-" + digest([
        observation["input_refs"], observation["producer"], observation["payload"]])[:24]
    return observation


def test_recognizer(tensor):
    return r"\frac{a^{2}+1}{2}", .001


class FormulaCanvas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = read("formula-layout.json")
        cls.legacy = read("formula-observations.json")
        cls.crop = FIXTURE / "recovery-assets/unit2-q16.png"
        cls.image, cls.source, cls.units = plan_canvas_units(cls.layout, cls.crop)
        cls.observations = collect_canvas_observations(cls.layout, cls.crop, recognizer=test_recognizer)

    def build(self, observations=None):
        return build_canvas_candidates(self.layout, observations or self.observations, self.crop, self.legacy)

    def test_unchanged_full_fraction_plan_and_original_inputs(self):
        old_image, old_source, old_units = plan_formula_units(self.layout, self.crop)
        self.assertEqual(old_units, self.units)
        self.assertEqual(old_source, self.source)
        self.assertEqual(old_image.tobytes(), self.image.tobytes())
        self.assertEqual(len(self.units), 11)
        self.assertEqual(self.layout, read("formula-layout.json"))
        self.assertEqual(self.legacy, read("formula-observations.json"))
        self.assertEqual(file_digest(self.crop), self.layout["payload"]["crop_sha256"])

    def test_full_pad_keeps_faint_raised_edge_pixels_and_uniform_images(self):
        pixels = np.full((9, 41), 255, dtype=np.uint8)
        pixels[0, 0] = 220
        pixels[8, 40] = 190
        padded, receipt = _full_pad(Image.fromarray(pixels))
        self.assertEqual(padded.size, (64, 32))
        self.assertEqual(receipt["input_size"], [41, 9])
        self.assertFalse(receipt["threshold_crop"])
        # Both distant source edges stay at their original positions; a tight
        # threshold crop would move or discard the faint upper-left witness.
        self.assertLess(padded.getpixel((0, 0)), 255)
        self.assertEqual(padded.getpixel((40, 8)), 0)
        self.assertEqual(padded.getpixel((41, 8)), 255)
        white, _ = _full_pad(Image.new("L", (17, 3), 255))
        self.assertEqual(set(np.asarray(white).ravel()), {255})

    def test_minmax_resizes_whole_image_and_preserves_corner_positions(self):
        image = Image.new("RGB", (1344, 384), "white")
        image.putpixel((0, 0), (0, 0, 0))
        image.putpixel((1343, 383), (0, 0, 0))
        output, receipt = _minmax_size(image)
        self.assertEqual(output.size, (672, 192))
        self.assertEqual(receipt["downscaled_size"], [672, 192])
        self.assertLess(output.convert("L").getpixel((0, 0)), 255)
        self.assertLess(output.convert("L").getpixel((671, 191)), 255)

    def test_all_units_two_tensor_variants_and_explicit_synthetic_receipt(self):
        seen = []
        def recognize(tensor):
            self.assertEqual(tensor.dtype, np.dtype("float32"))
            self.assertEqual(tensor.shape[:2], (1, 1))
            self.assertTrue(tensor.flags.c_contiguous)
            self.assertTrue(np.isfinite(tensor).all())
            self.assertLessEqual(tensor.shape[-1], 672)
            self.assertLessEqual(tensor.shape[-2], 192)
            seen.append(hashlib.sha256(tensor.tobytes()).hexdigest())
            return test_recognizer(tensor)
        value = collect_canvas_observations(self.layout, self.crop, recognizer=recognize)
        self.assertEqual(len(seen), 22)
        self.assertEqual(value["producer"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertNotIn("model_files", value["producer"])
        self.assertNotIn("providers", value["producer"])
        self.assertFalse(value["payload"]["expected_text_consumed"])
        self.assertFalse(value["payload"]["graph_modified"])
        self.assertEqual(value["payload"]["decision"], "HOLD")
        for plan, unit in zip(self.units, value["payload"]["units"]):
            self.assertEqual({k: v for k, v in unit.items() if k != "variants"}, plan)
            self.assertEqual([v["variant_id"] for v in unit["variants"]], ["gray-native", "gray-scale3"])
            for variant in unit["variants"]:
                self.assertIsNone(variant["recognition_error"])
                self.assertEqual(variant["verification_status"], "UNVERIFIED")
                self.assertEqual(variant["preprocessing_trace"]["stop_reason"], "WIDTH_STABLE")

    def test_multistep_logits_replay_and_source_transform_roundtrip(self):
        calls = []
        def resizer(tensors):
            calls.append(tensors[0].shape)
            values = np.zeros((1, 21), dtype=np.float32)
            values[0, 0] = 2  # choose width32, then stabilize there
            return [values]
        unit = self.units[2]
        metadata, tensor = preprocess_canvas(self.image, unit, CONFIG["variants"][1], resizer=resizer)
        self.assertEqual(len(calls), 2)
        self.assertEqual(metadata["preprocessing_trace"]["stop_reason"], "WIDTH_STABLE")
        self.assertEqual(metadata["preprocessing_trace"]["steps"][0]["next_width"], 32)
        reproduced, replay_tensor = preprocess_canvas(self.image, unit, CONFIG["variants"][1],
            recorded_trace=metadata["preprocessing_trace"])
        self.assertEqual(metadata, reproduced)
        np.testing.assert_array_equal(tensor, replay_tensor)
        forward = np.array(metadata["source_to_canvas"])
        inverse = np.array(metadata["canvas_to_source"])
        for x, y in ((unit["source_bbox"][0], unit["source_bbox"][1]),
                     (unit["source_bbox"][2], unit["source_bbox"][3])):
            point = np.array([x, y, 1.0])
            np.testing.assert_allclose(inverse @ forward @ point, point, atol=1e-10)

    def test_resizer_nonconvergence_is_recorded_without_hiding_last_tensor(self):
        def resizer(tensors):
            width = tensors[0].shape[-1]
            target = 64 if width != 64 else 96
            values = np.zeros((1, 21), dtype=np.float32)
            values[0, target//32-1] = 1
            return [values]
        metadata, tensor = preprocess_canvas(self.image, self.units[2], CONFIG["variants"][0], resizer=resizer)
        trace = metadata["preprocessing_trace"]
        self.assertEqual(len(trace["steps"]), 10)
        self.assertEqual(trace["stop_reason"], "MAX_ITERATIONS")
        self.assertFalse(trace["steps"][-1]["terminated"])
        self.assertEqual(metadata["tensor_sha256"], hashlib.sha256(tensor.tobytes()).hexdigest())

    def test_resizer_exception_keeps_partial_source_and_tensor_receipt(self):
        def broken(tensors):
            raise RuntimeError("controlled resizer failure")
        metadata, tensor = preprocess_canvas(self.image, self.units[0], CONFIG["variants"][0], resizer=broken)
        trace = metadata["preprocessing_trace"]
        self.assertEqual(trace["stop_reason"], "RESIZER_FAILED")
        self.assertEqual(trace["steps"][0]["resizer_error"], dict(type="RuntimeError", status="RESIZER_FAILED"))
        self.assertIsNone(trace["steps"][0]["resizer_logits"])
        self.assertEqual(metadata["tensor_sha256"], hashlib.sha256(tensor.tobytes()).hexdigest())

    def test_recognition_errors_do_not_drop_units_or_make_fake_text(self):
        def broken(tensor):
            raise RuntimeError("controlled decoder failure")
        evidence = collect_canvas_observations(self.layout, self.crop, recognizer=broken)
        candidates = self.build(evidence)
        variants = [v for unit in evidence["payload"]["units"] for v in unit["variants"]]
        self.assertEqual(len(variants), 22)
        for v in variants:
            self.assertIsNone(v["raw_latex"])
            self.assertIsNone(v["engine_elapsed_seconds"])
            self.assertEqual(v["recognition_error"], dict(type="RuntimeError", status="RECOGNITION_FAILED"))
        self.assertTrue(all(not u["exact_ast_agreement"] for u in candidates["payload"]["units"]))

    def test_unknown_latex_is_retained_without_repair_or_selection(self):
        raw = r"\frac{a^{\dagger}+1}{4}"
        evidence = collect_canvas_observations(self.layout, self.crop, recognizer=lambda tensor: (raw, .001))
        candidates = self.build(evidence)
        for unit in candidates["payload"]["units"]:
            self.assertEqual(unit["selected_candidate_refs"], [])
            for variant in unit["variants"]:
                self.assertEqual(variant["raw_latex"], raw)
                self.assertFalse(variant["parse_result"]["supported"])
                self.assertIn(r"\dagger", variant["parse_result"]["unparsed_tail"])
                self.assertFalse(variant["complete"])

    def test_legacy_observation_and_all_candidates_survive_unchanged(self):
        original = copy.deepcopy(self.legacy)
        old = build_formula_candidates(self.layout, self.legacy, self.crop)
        current = self.build()
        p = current["payload"]
        self.assertEqual(p["legacy_observations_archive"], original)
        self.assertEqual(p["legacy_observation_ref"], reference(original))
        self.assertEqual(p["legacy_candidates_payload"], old["payload"])
        self.assertEqual(p["legacy_candidate_ref"], reference(old))
        self.assertEqual(sum(len(u["variants"]) for u in p["legacy_candidates_payload"]["units"]), 22)
        self.assertEqual(self.legacy, original)
        self.assertEqual(p["units"][0]["variants"][0]["legacy_agreement_candidate_refs"],
            [v["candidate_id"] for v in old["payload"]["units"][0]["variants"]])
        self.assertTrue(p["units"][0]["cross_path_exact_ast_agreement"])
        self.assertFalse(p["units"][1]["cross_path_exact_ast_agreement"])
        self.assertFalse(p["entire_answer_reconstructed"])
        self.assertTrue(all(u["selected_candidate_refs"] == [] for u in p["units"]))

    def test_tensor_and_trace_edits_fail_even_with_coordinated_artifact_rehash(self):
        for key in ("tensor_sha256", "source_to_canvas", "trace_pad"):
            evidence = copy.deepcopy(self.observations)
            v = evidence["payload"]["units"][0]["variants"][0]
            if key == "tensor_sha256":
                v[key] = "0"*64
            elif key == "source_to_canvas":
                v[key][0][2] += 1
            else:
                v["preprocessing_trace"]["steps"][0]["pad"]["threshold_crop"] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build(rehash(evidence))

    def test_missing_duplicate_or_foreign_units_are_rejected(self):
        for fault in ("missing", "duplicate", "foreign"):
            evidence = copy.deepcopy(self.observations)
            units = evidence["payload"]["units"]
            if fault == "missing": units.pop()
            elif fault == "duplicate": units[1] = copy.deepcopy(units[0])
            else: units[0]["source_bbox"][0] -= 1
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                self.build(rehash(evidence))

    def test_synthetic_observations_cannot_be_relabelled_as_cpu(self):
        evidence = copy.deepcopy(self.observations)
        evidence["producer"]["execution_kind"] = "CPU_RAPID_LATEX_OCR_PRESERVE_CANVAS"
        with self.assertRaises(ValueError):
            self.build(rehash(evidence))

    def test_source_crop_byte_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"crop.png"
            path.write_bytes(self.crop.read_bytes()+b" ")
            with self.assertRaises(ValueError):
                build_canvas_candidates(self.layout, self.observations, path, self.legacy)

    def test_random_state_is_restored_after_success_and_failure(self):
        state = np.random.get_state()
        expected = np.random.RandomState()
        expected.set_state(state)
        next_value = expected.random_sample()
        def random_recognizer(tensor):
            np.random.random_sample(9)
            return test_recognizer(tensor)
        collect_canvas_observations(self.layout, self.crop, recognizer=random_recognizer)
        self.assertEqual(np.random.random_sample(), next_value)
        np.random.set_state(state)

    def test_missing_explicit_model_directory_does_not_initialize_backend(self):
        with self.assertRaisesRegex(ValueError, "explicit local formula model directory"):
            collect_canvas_observations(self.layout, self.crop)

    def test_preprocessing_failure_before_receipt_cannot_reuse_prior_variant_metadata(self):
        with mock.patch("annotation.recognition.formula_canvas.preprocess_canvas",
                side_effect=RuntimeError("controlled pre-receipt setup error")):
            with self.assertRaisesRegex(ValueError, "before a complete receipt"):
                collect_canvas_observations(self.layout, self.crop, recognizer=test_recognizer)

    def test_unbounded_recorded_sizing_is_rejected_before_allocating_large_image(self):
        def excessive(tensors):
            logits = np.zeros((1, 1000), dtype=np.float32)
            logits[0, -1] = 1
            return [logits]
        with self.assertRaisesRegex(ValueError, "excessive intermediate image"):
            preprocess_canvas(self.image, self.units[2], CONFIG["variants"][0], resizer=excessive)


if __name__ == "__main__":
    unittest.main()
