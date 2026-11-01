"""Independent small row/crop expectations; all engine calls are synthetic."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition import inline_ocr


def tiny_evidence(directory):
    path = Path(directory) / "original.png"
    pixels = np.zeros((20, 30, 3), dtype=np.uint8)
    pixels[:, :, 0] = np.arange(30, dtype=np.uint8)[None, :]
    pixels[:, :, 1] = np.arange(20, dtype=np.uint8)[:, None]*5
    pixels[:, :, 2] = 180
    Image.fromarray(pixels).save(path)
    asset = {"asset_id": "test-page", "path": "original.png", "width": 30, "height": 20,
             "sha256": file_digest(path), "reading_order": 0, "side": "answer"}
    lines = [{"line_id": "test-page/ocr/0", "text": "SOURCE WORDS MUST NOT REACH ENGINE",
              "bbox": [3.2, 4.8, 17.1, 11.2], "score": .7,
              "location": {"column": 0, "window_index": 0, "section_path": ["synthetic"]}},
             {"line_id": "test-page/ocr/1", "text": "edge", "bbox": [.1, .2, 29.9, 19.9], "score": .5}]
    payload = {"pages": [{"asset_id": "test-page", "source": asset, "ocr_lines": lines,
                          "answer_detail_lines": []}], "context": {"book_id": "test"}}
    evidence = {"schema_version": "b-evidence-trial/0.3", "kind": "EvidenceBundleTrial",
                "artifact_id": "synthetic-evidence", "revision": 1, "book_id": "test", "scope_id": "two-row",
                "payload": payload, "content_hash": digest(payload)}
    return evidence, path


def backend(bgr, **flags):
    if flags != {"use_det": True, "use_cls": False, "use_rec": True, "return_word_box": True, "text_score": 0}:
        raise AssertionError("wrong explicit engine flags")
    if bgr.dtype != np.uint8 or not bgr.flags.c_contiguous or bgr.ndim != 3:
        raise AssertionError("contiguous BGR uint8 required")
    polygon = [[0, 0], [12, 0], [12, 9], [0, 9]]
    boxes = [[[0, 0], [6, 0], [6, 9], [0, 9]], [[6, 0], [12, 0], [12, 9], [6, 9]]]
    return [[polygon, "错十", .0, boxes, ["错", "十"], [.02, .99]]], [.01, 0., .02]


class InlineOCRTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.evidence, self.path = tiny_evidence(self.tmp.name)
        self.line_ids = ["test-page/ocr/0"]

    def collect(self, recognizer=backend, evidence=None, line_ids=None):
        return inline_ocr.collect_inline_observations(evidence or self.evidence, self.path, asset_id="test-page",
            line_ids=self.line_ids if line_ids is None else line_ids, recognizer=recognizer)

    def plan(self, evidence=None, **kwargs):
        return inline_ocr.plan_inline_rows(evidence or self.evidence, self.path,
            asset_id=kwargs.pop("asset_id", "test-page"), line_ids=kwargs.pop("line_ids", self.line_ids), **kwargs)

    def test_floor_ceil_padding_clamp_and_exact_original_pixels(self):
        image, source, plans = self.plan(line_ids=["test-page/ocr/1", "test-page/ocr/0"])
        self.assertEqual(image.mode, "RGB")
        self.assertEqual([p["crop_bbox"] for p in plans], [[0, 0, 30, 20], [1, 2, 20, 14]])
        self.assertEqual(plans[1]["crop_size"], [19, 12])
        self.assertEqual(plans[1]["crop_rgb_sha256"], hashlib.sha256(image.crop([1, 2, 20, 14]).tobytes()).hexdigest())
        self.assertEqual(source["original_sha256"], file_digest(self.path))
        self.assertEqual(source["asset"], self.evidence["payload"]["pages"][0]["source"])
        self.assertNotIn(str(self.path), json.dumps(source))

    def test_engine_receives_only_lanczos_pixels_and_exact_flags(self):
        calls = []
        def observe(bgr, **flags):
            calls.append((bgr.copy(), flags))
            return backend(bgr, **flags)
        result = self.collect(observe)
        with Image.open(self.path) as opened:
            crop = opened.convert("RGB").crop([1, 2, 20, 14])
        for call, scale, variant in zip(calls, (3, 4), result["payload"]["rows"][0]["variants"]):
            expected_rgb = crop.resize((19*scale, 12*scale), Image.Resampling.LANCZOS)
            expected = np.ascontiguousarray(np.asarray(expected_rgb)[:, :, ::-1])
            np.testing.assert_array_equal(call[0], expected)
            self.assertEqual(variant["bgr_sha256"], hashlib.sha256(expected.tobytes()).hexdigest())
            self.assertEqual(variant["rgb_sha256"], hashlib.sha256(expected_rgb.tobytes()).hexdigest())
            self.assertEqual(variant["variant_to_original"], [[1/scale, 0, 1], [0, 1/scale, 2], [0, 0, 1]])
        self.assertEqual(len(calls), 2)

    def test_raw_arrays_zero_score_and_sequence_are_preserved(self):
        result = self.collect()
        for variant in result["payload"]["rows"][0]["variants"]:
            raw = variant["raw_ocr_result"]
            self.assertEqual(variant["raw_call_result"], [raw, [.01, 0., .02]])
            candidate = variant["candidates"][0]
            self.assertEqual(candidate["raw_observation"], raw[0])
            self.assertEqual(candidate["text"], "错十")
            self.assertEqual(candidate["score"], 0.)
            self.assertEqual([w["text"] for w in candidate["word_estimates"]], ["错", "十"])
            self.assertEqual(candidate["word_alignment_status"], "ALIGNED")
            self.assertIsNone(variant["recognition_error"])
            self.assertEqual(candidate["source_polygon"][2], [1+12/variant["scale"], 2+9/variant["scale"]])

    def test_multiple_detector_results_keep_their_raw_order_not_x_order(self):
        def reversed_order(bgr, **flags):
            raw, elapsed = backend(bgr, **flags)
            second = copy.deepcopy(raw[0]); second[1] = "AB"; second[4] = ["A", "B"]
            second[0] = [[20, 0], [30, 0], [30, 9], [20, 9]]
            return [second, raw[0]], elapsed
        candidates = self.collect(reversed_order)["payload"]["rows"][0]["variants"][0]["candidates"]
        self.assertEqual([c["raw_result_index"] for c in candidates], [0, 1])
        self.assertEqual([c["text"] for c in candidates], ["AB", "错十"])
        self.assertEqual(len({c["candidate_id"] for c in candidates}), 2)

    def test_mismatched_word_arrays_do_not_zip_away_extra_tokens(self):
        def mismatched(bgr, **flags):
            raw, elapsed = backend(bgr, **flags)
            raw[0][3] = raw[0][3][:1]
            raw[0][4] = ["A", "B", "C"]
            return raw, elapsed
        variant = self.collect(mismatched)["payload"]["rows"][0]["variants"][0]
        candidate = variant["candidates"][0]
        self.assertEqual(len(candidate["word_estimates"]), 3)
        self.assertEqual(candidate["word_estimates"][2]["text"], "C")
        self.assertIsNone(candidate["word_estimates"][2]["polygon"])
        self.assertEqual(candidate["word_alignment_status"], "LENGTH_MISMATCH")
        self.assertIn("WORD_ARRAY_LENGTH_MISMATCH", [i["code"] for i in variant["issues"]])
        self.assertIn("WORD_SEQUENCE_MISMATCH", [i["code"] for i in variant["issues"]])

    def test_degenerate_and_outside_polygons_remain_raw_and_projected(self):
        def bad_boxes(bgr, **flags):
            raw, elapsed = backend(bgr, **flags)
            raw[0][0] = [[0, 0]]*4
            raw[0][3][0] = [[-2, 0], [6, 0], [6, 9], [-2, 9]]
            return raw, elapsed
        candidate = self.collect(bad_boxes)["payload"]["rows"][0]["variants"][0]["candidates"][0]
        self.assertEqual(candidate["polygon_status"], "DEGENERATE")
        self.assertEqual(candidate["source_polygon"], [[1., 2.]]*4)
        self.assertEqual(candidate["word_estimates"][0]["polygon_status"], "OUTSIDE_INPUT")
        self.assertEqual(candidate["word_estimates"][0]["source_polygon"][0], [1-2/3, 2.])

    def test_malformed_rows_and_numpy_raw_result_are_retained(self):
        def malformed(bgr, **flags):
            raw, elapsed = backend(bgr, **flags)
            raw[0][0] = np.array(raw[0][0], dtype=np.float32)
            raw[0][2] = np.float32(.125)
            return [raw[0], ["incomplete"], None], np.array(elapsed)
        variant = self.collect(malformed)["payload"]["rows"][0]["variants"][0]
        self.assertEqual(len(variant["candidates"]), 3)
        self.assertEqual(variant["candidates"][1]["raw_observation"], ["incomplete"])
        self.assertEqual(variant["candidates"][2]["raw_observation"], None)
        self.assertEqual(variant["candidates"][0]["score"], .125)
        self.assertEqual([i["code"] for i in variant["issues"]], ["RAW_ROW_INVALID", "RAW_ROW_INVALID"])

    def test_empty_and_engine_failure_remain_independent_two_variants(self):
        calls = []
        def fail_once(bgr, **flags):
            calls.append(bgr.shape)
            if len(calls) == 1:
                raise RuntimeError("synthetic failure, not OCR")
            return None, None
        variants = self.collect(fail_once)["payload"]["rows"][0]["variants"]
        self.assertEqual(variants[0]["recognition_error"], {"type": "RuntimeError", "message": "synthetic failure, not OCR"})
        self.assertEqual(variants[1]["raw_call_result"], [None, None])
        self.assertEqual(variants[1]["issues"], [{"code": "OCR_EMPTY"}])
        self.assertEqual(len(calls), 2)

    def test_malformed_call_keeps_full_serializable_raw_return(self):
        result = self.collect(lambda bgr, **flags: {"unexpected": ["raw", 1]})
        for variant in result["payload"]["rows"][0]["variants"]:
            self.assertEqual(variant["raw_call_result"], {"unexpected": ["raw", 1]})
            self.assertEqual(variant["recognition_error"]["type"], "ValueError")
            self.assertEqual(variant["candidates"], [])

    def test_input_objects_are_not_mutated_and_no_text_is_selected(self):
        original = copy.deepcopy(self.evidence)
        result = self.collect()
        self.assertEqual(self.evidence, original)
        result["payload"]["rows"][0]["source_line"]["text"] = "altered output copy"
        self.assertEqual(self.evidence, original)
        self.assertNotIn("created_at", result)
        self.assertFalse(result["payload"]["complete"])
        self.assertFalse(result["payload"]["transcription_verified"])
        self.assertFalse(result["payload"]["business_acceptance"])
        self.assertFalse(result["payload"]["graph_modified"])
        self.assertEqual(result["payload"]["decision"], "HOLD")
        self.assertEqual(result["payload"]["platform_actions"], [])

    def test_injected_backend_cannot_upgrade_itself_to_cpu_or_touch_optional_dependencies(self):
        backend.execution_kind = "CPU_RAPIDOCR_INLINE"
        with patch.object(inline_ocr.importlib.metadata, "distribution", side_effect=AssertionError("optional metadata forbidden")), \
             patch.object(inline_ocr.importlib.util, "find_spec", side_effect=AssertionError("optional imports forbidden")), \
             patch.object(inline_ocr, "_cpu_backend", side_effect=AssertionError("no CPU setup")):
            result = self.collect()
        self.assertEqual(result["producer"]["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(result["producer"]["model_files"], [])
        self.assertEqual(result["producer"]["session_providers"], {})

    def test_hash_schema_kind_revision_and_identity_rejected_before_backend(self):
        changes = [("content_hash", "0"*64), ("schema_version", "b-evidence-trial/0.1"),
                   ("kind", "QuestionGraphTrial"), ("revision", True), ("book_id", "")]
        for key, value in changes:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.evidence); changed[key] = value
                with self.assertRaises(ValueError):
                    self.plan(changed)

    def test_source_file_sha_and_dimensions_cannot_be_laundered(self):
        self.path.write_bytes(self.path.read_bytes()+b"different trailing bytes")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.plan()
        changed = copy.deepcopy(self.evidence)
        changed["payload"]["pages"][0]["source"]["sha256"] = file_digest(self.path)
        changed["payload"]["pages"][0]["source"]["width"] = 31
        changed["content_hash"] = digest(changed["payload"])
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.plan(changed)

    def test_duplicate_assets_raw_ids_and_cross_page_ids_rejected(self):
        for kind in ("page", "line", "line_asset"):
            changed = copy.deepcopy(self.evidence)
            page = changed["payload"]["pages"][0]
            if kind == "page":
                changed["payload"]["pages"].append(copy.deepcopy(page))
            elif kind == "line":
                page["ocr_lines"].append(copy.deepcopy(page["ocr_lines"][0]))
            else:
                page["ocr_lines"][0]["asset_id"] = "foreign"
            changed["content_hash"] = digest(changed["payload"])
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.plan(changed)

    def test_selection_requires_exact_nonempty_unique_raw_ids(self):
        for selection in ([], "test-page/ocr/0", ["test-page/ocr/0"]*2, ["missing"], [None]):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                self.plan(line_ids=selection)
        with self.assertRaises(ValueError):
            self.plan(asset_id="another")

    def test_invalid_source_bbox_cannot_be_clamped_into_usable_crop(self):
        for box in ([-1, 0, 4, 5], [1, 2, 1, 4], [0, True, 4, 5], [0, 0, 31, 4]):
            changed = copy.deepcopy(self.evidence)
            changed["payload"]["pages"][0]["ocr_lines"][0]["bbox"] = box
            changed["content_hash"] = digest(changed["payload"])
            with self.subTest(box=box), self.assertRaises(ValueError):
                self.plan(changed)

    def test_cpu_provider_verification_checks_all_three_actual_sessions(self):
        def session(providers, *, recognition=False):
            ort = SimpleNamespace(session=SimpleNamespace(get_providers=lambda: providers))
            return SimpleNamespace(**{"session" if recognition else "infer": ort})
        cpu = SimpleNamespace(text_det=session(["CPUExecutionProvider"]), text_cls=session(["CPUExecutionProvider"]),
                              text_rec=session(["CPUExecutionProvider"], recognition=True))
        self.assertEqual(inline_ocr._cpu_sessions(cpu), {k: ["CPUExecutionProvider"] for k in ("Det", "Cls", "Rec")})
        for attr in ("text_det", "text_cls", "text_rec"):
            bad = copy.copy(cpu)
            setattr(bad, attr, session(["CUDAExecutionProvider", "CPUExecutionProvider"], recognition=attr == "text_rec"))
            with self.subTest(attr=attr), self.assertRaises(ValueError):
                inline_ocr._cpu_sessions(bad)

    def test_fresh_import_does_not_import_or_instantiate_ocr_or_network(self):
        script = """
import sys
class Forbidden:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'rapidocr_onnxruntime','onnxruntime','requests','urllib3'}:
            raise RuntimeError('implicit optional/network import: '+fullname)
sys.meta_path.insert(0, Forbidden())
from annotation.recognition.inline_ocr import plan_inline_rows, collect_inline_observations
print('lazy-import-ok')
"""
        completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True,
                                   env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")})
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("lazy-import-ok", completed.stdout)


if __name__ == "__main__":
    unittest.main()
