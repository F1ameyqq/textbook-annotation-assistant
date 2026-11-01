"""Raw ordinary-OCR observations, not expected answers or content acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from annotation.recognition.baseline import digest
from annotation.recognition.region_runs import plan_region_runs
from annotation.recognition.region_ocr import collect_region_observations, validate_region_observations
from test_region_runs import pixel_layout, reference, resign_layout


class RawWorker:
    """The locked recognition-only API returns [rec_elapsed], not a scalar."""
    execution_kind = "CPU_RAPIDOCR"
    device = "CPU"
    model_files = [{"name": "fake-real-model", "sha256": "0" * 64}]

    def __init__(self, text=" 邻近分式∵𝛼²\\unknown{a} <script> "):
        self.calls = []; self.text = text

    def __call__(self, bgr, **flags):
        if flags != {"use_det": False, "use_cls": False, "use_rec": True}:
            raise AssertionError("Only the declared recognition-only flags may be used")
        if bgr.dtype != np.uint8 or bgr.ndim != 3 or bgr.shape[2] != 3 or not bgr.flags.c_contiguous:
            raise AssertionError("Actual contiguous BGR uint8 crop pixels are required")
        self.calls.append((bgr.copy(), copy.deepcopy(flags)))
        return [[self.text, .875]], [.0125]


def resign_observations(value):
    value["content_hash"] = digest(value["payload"])
    body = {k: v for k, v in value.items() if k not in {"artifact_id", "content_hash"}}
    value["artifact_id"] = "region-ocr-observation-" + digest(body)[:24]
    return value


def resign_plan(value):
    value["content_hash"] = digest(value["payload"])
    value["artifact_id"] = "region-runs-" + digest([value["input_refs"], value["producer"], value["payload"]])[:24]
    return value


class RegionOCRTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.layout, self.crop = pixel_layout(self.temp.name)
        self.plan = plan_region_runs(self.layout, self.crop)

    def collect(self, worker=None):
        return collect_region_observations(self.plan, self.crop, recognizer=worker if worker is not None else RawWorker())

    def check(self, observed, *, plan=None, crop=None):
        return validate_region_observations(plan if plan is not None else self.plan, observed, crop if crop is not None else self.crop)["payload"]

    def assert_hold(self, payload):
        self.assertEqual(payload["decision"], "HOLD")
        for key in ("complete", "transcription_verified", "business_acceptance", "expected_text_consumed", "graph_modified"):
            self.assertIs(payload[key], False)
        self.assertEqual(payload["verification_status"], "UNVERIFIED")
        self.assertEqual(payload["selected_candidate_refs"], []); self.assertEqual(payload["platform_actions"], [])

    def test_every_body_and_full_row_fallback_has_two_source_bound_actual_pixel_calls(self):
        worker = RawWorker(); before = copy.deepcopy(self.plan); observed = self.collect(worker)
        p = observed["payload"]; slots = self.plan["payload"]["body_slots"] + [r["full_row_fallback"] for r in self.plan["payload"]["rows"]]
        self.assertEqual(len(worker.calls), len(slots) * 2); self.assertEqual(len(p["units"]), len(slots))
        self.assertEqual([u["slot_id"] for u in p["units"]], [s["slot_id"] for s in slots])
        with Image.open(self.crop) as image: source = image.convert("RGB")
        origin = self.plan["payload"]["source"]["crop_bbox"][:2]
        for unit_index, (unit, slot) in enumerate(zip(p["units"], slots)):
            for key, value in slot.items(): self.assertEqual(unit[key], value)
            self.assertEqual([v["variant_id"] for v in unit["variants"]], ["CORE_GAP_SCALE6", "CONTEXT_SCALE8_CONTRAST15"])
            for variant_index, (variant, scale, contrast) in enumerate(zip(unit["variants"], (6, 8), (1.0, 1.5))):
                actual_box = slot["source_bbox"] if variant_index == 0 else slot["recognition_bbox"]
                tile = source.crop([actual_box[i] - origin[i % 2] for i in range(4)])
                transformed = tile.resize((tile.width * scale, tile.height * scale), Image.Resampling.LANCZOS)
                transformed = ImageEnhance.Contrast(transformed).enhance(contrast)
                expected_bgr = np.ascontiguousarray(np.asarray(transformed, dtype=np.uint8)[:, :, ::-1])
                self.assertTrue(np.array_equal(worker.calls[unit_index * 2 + variant_index][0], expected_bgr), "actual OCR input must use this variant's exact crop, not merely relabel metadata")
                self.assertEqual(variant["source_bbox"], actual_box)
                self.assertEqual(variant["crop_size"], list(tile.size)); self.assertEqual(variant["crop_rgb_sha256"], hashlib.sha256(tile.tobytes()).hexdigest())
                self.assertEqual(variant["transformed_bgr_sha256"], hashlib.sha256(expected_bgr.tobytes()).hexdigest())
                self.assertEqual(variant["raw_call_result"], [[[worker.text, .875]], [.0125]])
                self.assertEqual(variant["raw_backend_elapsed_seconds"], [.0125]); self.assertEqual(variant["engine_elapsed_seconds"], .0125)
                self.assertIsNone(variant["recognition_error"])
                self.assertEqual(variant["candidates"][0]["text"], worker.text)
                self.assertTrue(variant["candidates"][0]["usable"])
                self.assertEqual(variant["transformed_to_source"], [[1 / scale, 0, actual_box[0]], [0, 1 / scale, actual_box[1]], [0, 0, 1]])
        self.assertEqual(self.plan, before); self.assertEqual(p["plan_archive"], before)
        self.assertEqual(p["plan_ref"], reference(before)); self.assertEqual(p["source"], before["payload"]["source"])
        self.assert_hold(p); self.assertTrue(self.check(observed)["accepted"])
        self.assertFalse(p["precise_glyph_localization"]); self.assertFalse(p["spatial_role_verified"])

    def test_injected_backend_attributes_never_become_cpu_or_human_receipts(self):
        worker = RawWorker(); worker.human_verified = True
        observed = self.collect(worker); producer = observed["producer"]
        self.assertEqual(producer["execution_kind"], "SYNTHETIC_TEST"); self.assertEqual(producer["device"], "SYNTHETIC_TEST")
        self.assertEqual(producer["dependencies"], {}); self.assertEqual(producer["model_files"], []); self.assertEqual(producer["session_providers"], {})
        self.assertNotIn("human_verified", producer); self.assert_hold(observed["payload"])
        for mutate in (lambda o:o["producer"].update(execution_kind="HUMAN_REVIEWED"),
                       lambda o:o["producer"].update(execution_kind="CPU_RAPIDOCR", device="CPU")):
            changed = copy.deepcopy(observed); mutate(changed); resign_observations(changed)
            self.assertFalse(self.check(changed)["accepted"])

    def test_unknown_characters_neighbor_context_and_malformed_raw_rows_are_never_trimmed(self):
        rows = [["  ∵𝑥²\\unknown{a}是邻接字  ", .6], [42, .9], None, [], ["", .4], ["extra", .8, "field"], ["bad-score", 1.5]]
        def worker(bgr, **flags): return copy.deepcopy(rows), [.01]
        observed = self.collect(worker)
        for unit in observed["payload"]["units"]:
            for variant in unit["variants"]:
                self.assertEqual(variant["raw_ocr_result"], rows)
                self.assertEqual([c["raw_observation"] for c in variant["candidates"]], rows)
                self.assertEqual([c["raw_result_index"] for c in variant["candidates"]], list(range(len(rows))))
                self.assertEqual(variant["candidates"][0]["text"], rows[0][0]); self.assertTrue(variant["candidates"][0]["usable"])
                self.assertTrue(all(not c["usable"] for c in variant["candidates"][1:])); self.assertTrue(variant["issues"])
        self.assertTrue(self.check(observed)["accepted"]); self.assert_hold(observed["payload"])

    def test_backend_failure_invalid_elapsed_and_empty_return_preserve_complete_declared_scope(self):
        calls = 0
        def worker(bgr, **flags):
            nonlocal calls
            calls += 1
            if calls == 1: raise RuntimeError("SYNTHETIC_TEST explicit failure")
            if calls == 2: return [["仍保留原文", .8]], [-.01]
            if calls == 3: return None, None
            if calls == 4: return [[["wrong-pair-length", .8]]]
            if calls == 5: return [], [.01]
            return [["later-unit", .8]], [.01]
        observed = self.collect(worker); variants = [v for u in observed["payload"]["units"] for v in u["variants"]]
        self.assertEqual(calls, 2 * (len(self.plan["payload"]["body_slots"]) + len(self.plan["payload"]["rows"])))
        self.assertIsNone(variants[0]["raw_call_result"]); self.assertEqual(variants[0]["recognition_error"]["status"], "BACKEND_FAILED")
        self.assertEqual(variants[1]["raw_call_result"], [[["仍保留原文", .8]], [-.01]])
        self.assertIsNone(variants[1]["engine_elapsed_seconds"]); self.assertEqual(variants[1]["candidates"][0]["text"], "仍保留原文")
        self.assertFalse(variants[1]["candidates"][0]["usable"])
        self.assertEqual(variants[2]["raw_call_result"], [None, None]); self.assertEqual(variants[3]["raw_call_result"], [[["wrong-pair-length", .8]]])
        self.assertIsNone(variants[4]["recognition_error"]); self.assertEqual(variants[4]["candidates"], [])
        self.assertTrue(self.check(observed)["accepted"]); self.assert_hold(observed["payload"])

    def test_nonfinite_return_values_have_lossless_json_tags_and_never_usable_confidence(self):
        def worker(bgr, **flags): return [["nan-score", np.float32(float("nan"))], ["inf-score", float("inf")]], [float("nan")]
        observed = self.collect(worker)
        json.dumps(observed, ensure_ascii=False, allow_nan=False)
        for unit in observed["payload"]["units"]:
            for variant in unit["variants"]:
                self.assertEqual(variant["raw_ocr_result"][0][1], {"__nonfinite_float__": "nan"})
                self.assertEqual(variant["raw_ocr_result"][1][1], {"__nonfinite_float__": "inf"})
                self.assertEqual(variant["raw_backend_elapsed_seconds"], [{"__nonfinite_float__": "nan"}])
                self.assertTrue(all(not c["usable"] and c["score"] is None for c in variant["candidates"]))
                self.assertIsNotNone(variant["recognition_error"])
        self.assertTrue(self.check(observed)["accepted"])

    def test_cached_validation_rejects_changed_candidate_even_after_all_self_hashes_are_recomputed(self):
        observed = self.collect()
        for fault in ("candidate-text", "raw-pair", "drop-row", "transform", "variant-box", "variant-crop-hash", "unit-role", "scope", "risk", "false-precise", "false-human"):
            changed = copy.deepcopy(observed); p = changed["payload"]; v = p["units"][0]["variants"][0]
            if fault == "candidate-text": v["candidates"][0]["text"] = "invented missing superscript"
            elif fault == "raw-pair": v["raw_ocr_result"][0][0] = "does not match original returned pair"
            elif fault == "drop-row": p["units"].pop()
            elif fault == "transform": v["transformed_to_source"][0][2] += 1
            elif fault == "variant-box": v["source_bbox"] = copy.deepcopy(p["units"][0]["recognition_bbox"])
            elif fault == "variant-crop-hash": v["crop_rgb_sha256"] = "0" * 64
            elif fault == "unit-role": p["units"][0]["kind"] = "FRACTION"
            elif fault == "scope": changed["scope_id"] = "another-book-scope"
            elif fault == "risk": v["issues"].append({"code": "made-up-risk"})
            elif fault == "false-precise": p["precise_glyph_localization"] = True
            else: p["transcription_verified"] = True
            resign_observations(changed)
            with self.subTest(fault=fault): self.assertFalse(self.check(changed)["accepted"])

    def test_malformed_or_foreign_external_plan_and_crop_are_rejected_before_recognizer(self):
        observed = self.collect(); calls = []
        def never(bgr, **flags): calls.append(True); raise AssertionError("source rejection must precede OCR")
        for fault in ("false-approved", "body-as-fraction", "missing-fallback", "source-hash"):
            plan = copy.deepcopy(self.plan)
            if fault == "false-approved": plan["payload"]["business_acceptance"] = True
            elif fault == "body-as-fraction": plan["payload"]["body_slots"][0]["kind"] = "FRACTION"
            elif fault == "missing-fallback": plan["payload"]["rows"][0]["full_row_fallback"]["source_bbox"][2] -= 1
            else: plan["payload"]["source"]["source_sha256"] = "0" * 64
            resign_plan(plan)
            with self.subTest(fault=fault):
                with self.assertRaises(ValueError): collect_region_observations(plan, self.crop, recognizer=never)
                self.assertFalse(self.check(observed, plan=plan)["accepted"])
        bad = Path(self.temp.name) / "changed-crop.png"; bad.write_bytes(self.crop.read_bytes() + b"changed")
        with self.assertRaises(ValueError): collect_region_observations(self.plan, bad, recognizer=never)
        self.assertFalse(self.check(observed, crop=bad)["accepted"]); self.assertEqual(calls, [])

    def test_source_change_during_collection_retains_every_call_but_cannot_pass_cached_validation(self):
        calls = 0; before = self.crop.read_bytes()
        def worker(bgr, **flags):
            nonlocal calls
            calls += 1
            if calls == 1: self.crop.write_bytes(before + b"changed-during-collection")
            return [["unverified retained observation", .8]], [.01]
        observed = self.collect(worker); p = observed["payload"]
        self.assertEqual(calls, p["counts"]["variants"]); self.assertEqual(p["counts"]["units"], 6)
        self.assertIs(p["source_unchanged"], False); self.assertIsNotNone(p["source_revalidation_error"])
        self.assertTrue(any(i["code"] == "SOURCE_CHANGED_DURING_COLLECTION" for i in p["issues"]))
        self.crop.write_bytes(before)
        self.assertFalse(self.check(observed)["accepted"], "restoring bytes cannot erase the recorded failed revalidation")
        self.assert_hold(p)

    def test_changed_layout_version_invalidates_old_observations_without_new_ocr(self):
        observed = self.collect(); changed = copy.deepcopy(self.layout)
        changed["payload"]["source_ocr"][0]["text"] = "New synthetic source observation version"
        resign_layout(changed); newer = plan_region_runs(changed, self.crop)
        self.assertNotEqual(reference(newer), reference(self.plan))
        self.assertFalse(self.check(observed, plan=newer)["accepted"])

    def test_injected_collection_and_cache_validation_do_not_import_models_or_use_network(self):
        worker = RawWorker()
        with patch.dict(sys.modules, {"rapidocr_onnxruntime": None, "rapid_latex_ocr": None, "onnxruntime": None}), \
             patch("annotation.recognition.region_ocr._actual_backend", side_effect=AssertionError("No implicit backend")), \
             patch("socket.socket", side_effect=AssertionError("No network in offline observations")):
            observed = self.collect(worker); count = len(worker.calls); checked = self.check(observed)
        self.assertTrue(checked["accepted"]); self.assertEqual(len(worker.calls), count); self.assert_hold(checked)

    def test_fixed_Q16_observation_scope_keeps_all_body_and_row_alternatives_without_expected_text(self):
        layout = json.loads((FIXTURE / "formula-layout.json").read_text(encoding="utf-8")); crop = FIXTURE / "recovery-assets/unit2-q16.png"
        plan = plan_region_runs(layout, crop); worker = RawWorker("SYNTHETIC observation, no reference transcription")
        observed = collect_region_observations(plan, crop, recognizer=worker)
        slots = plan["payload"]["body_slots"] + [r["full_row_fallback"] for r in plan["payload"]["rows"]]
        self.assertEqual(len(slots), 17); self.assertEqual(len(worker.calls), 34)
        self.assertEqual([u["slot_id"] for u in observed["payload"]["units"]], [s["slot_id"] for s in slots])
        self.assertTrue(validate_region_observations(plan, observed, crop)["payload"]["accepted"])
        self.assert_hold(observed["payload"])


if __name__ == "__main__":
    unittest.main()
