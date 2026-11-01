"""Pixel accounting and layout boundaries, independent of transcription text."""
import copy
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from annotation.recognition.baseline import digest, file_digest
from annotation.recognition.region_runs import plan_region_runs


def reference(value):
    return {k: value[k] for k in ("artifact_id", "revision", "content_hash")}


def resign_layout(layout):
    layout["content_hash"] = digest(layout["payload"])
    layout["artifact_id"] = "math-layout-" + digest([layout["input_refs"], layout["producer"], layout["payload"]])[:24]
    return layout


def pixel_layout(directory, *, body_ink=True):
    """Two generated rows, faint/singleton/cross-slot/above-slot ink witnesses."""
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (80, 80), "white")
    draw = ImageDraw.Draw(image)
    fractions = []
    for i, y in enumerate((22, 57)):
        draw.rectangle((28, y - 10, 39, y - 3), fill="black")
        draw.rectangle((25, y, 44, y + 1), fill="black")
        draw.rectangle((32, y + 5, 36, y + 14), fill="black")
        fractions.append({"fraction_id": "synthetic-fraction-" + str(i),
            "bar_bbox": [125, 200 + y, 145, 202 + y], "threshold_votes": [180, 190, 200],
            "numerator": {"pixel_bbox": [128, 190 + y, 140, 198 + y], "ocr_refs": [], "raw_texts": [], "missing_ocr": True},
            "denominator": {"pixel_bbox": [132, 205 + y, 137, 215 + y], "ocr_refs": [], "raw_texts": [], "missing_ocr": True},
            "ambiguous_ocr_refs": [], "verification_status": "UNVERIFIED", "status": "LAYOUT_WITH_OCR_UNVERIFIED"})
    if body_ink:
        draw.rectangle((5, 21, 12, 29), fill="black")
        # The connected bar crosses the primary body/fraction ownership edge.
        draw.line((21, 23, 28, 23), fill="black", width=1)
        for point, shade in (((0, 0), 0), ((30, 1), 0), ((70, 3), 205), ((72, 4), 185), ((74, 4), 215)):
            image.putpixel(point, (shade, shade, shade))
    crop = root / "generated-region-crop.png"; image.save(crop)
    original = Image.new("RGB", (300, 400), "white"); original.paste(image, (100, 200))
    source_path = root / "generated-original.png"; original.save(source_path)
    payload = {"asset_id": "generated-source", "source_sha256": file_digest(source_path), "source_size": [300, 400],
        "crop_bbox": [100, 200, 180, 280], "crop_sha256": file_digest(crop), "probe_id": "generated-two-row-probe", "variant_id": "SYNTHETIC_TEST",
        "source_ocr": [{"line_id": "synthetic-size-only", "text": "Geometry-only OCR height", "bbox": [102, 217, 119, 229]}],
        "fraction_candidates": fractions, "reading_groups": [
            {"baseline_y": 223, "units": [{"kind": "body", "ocr_refs": ["synthetic-size-only"]},
                {"kind": "fraction", "fraction_id": fractions[0]["fraction_id"], "ocr_refs": []}]},
            {"baseline_y": 258, "units": [{"kind": "fraction", "fraction_id": fractions[1]["fraction_id"], "ocr_refs": []}]}],
        "token_coverage": [{"line_id": "synthetic-size-only", "status": "BODY"}], "issues": [],
        "decision": "HOLD", "layout_status": "UNVERIFIED", "transcription_verified": False,
        "formula_text_reconstructed": False, "visual_formula_references_consumed": False, "platform_actions": [], "limitations": []}
    layout = {"schema_version": "b-math-layout-trial/0.1", "kind": "MathLayoutTrial", "revision": 1,
        "book_id": "synthetic-pixel-book", "scope_id": "two-generated-rows", "payload": payload,
        "input_refs": [{"artifact_id": "synthetic-upstream", "revision": 1, "content_hash": "1" * 64},
                       {"asset_id": payload["asset_id"], "sha256": payload["source_sha256"]}, {"crop_sha256": payload["crop_sha256"]}],
        "producer": {"module": "SYNTHETIC_TEST", "execution_kind": "SYNTHETIC_TEST"}}
    return resign_layout(layout), crop


def components_from_pixels(crop, threshold, origin):
    """A small Python 8-neighbor flood fill; no planner/CC implementation reuse."""
    with Image.open(crop) as image:
        gray = image.convert("L"); width, height = gray.size; pixels = gray.load()
        remaining = {(x, y) for y in range(height) for x in range(width) if pixels[x, y] < threshold}
    found = []
    while remaining:
        first = min(remaining, key=lambda p: (p[1], p[0])); remaining.remove(first)
        queue = deque([first]); points = {first}
        while queue:
            x, y = queue.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    other = (x + dx, y + dy)
                    if other in remaining:
                        remaining.remove(other); points.add(other); queue.append(other)
        box = [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points) + 1, max(p[1] for p in points) + 1]
        original = [box[0] + origin[0], box[1] + origin[1], box[2] + origin[0], box[3] + origin[1]]
        found.append((original, points))
    return found


class RegionRunsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_layout = json.loads((FIXTURE / "formula-layout.json").read_text(encoding="utf-8"))
        cls.real_crop = FIXTURE / "recovery-assets/unit2-q16.png"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.layout, self.crop = pixel_layout(self.temp.name)

    def test_real_fixed_crop_has_three_rows_eleven_fractions_and_complete_crop_bands(self):
        before = copy.deepcopy(self.real_layout); p = plan_region_runs(self.real_layout, self.real_crop)["payload"]
        self.assertEqual(self.real_layout, before); self.assertEqual(p["layout_archive"], before)
        self.assertEqual(len(p["rows"]), 3); self.assertEqual(len(p["fraction_slots"]), 11)
        self.assertEqual([s["fraction_id"] for s in p["fraction_slots"]], [f["fraction_id"] for f in before["payload"]["fraction_candidates"]])
        for slot, fraction in zip(p["fraction_slots"], before["payload"]["fraction_candidates"]):
            boxes = [fraction["bar_bbox"], fraction["numerator"]["pixel_bbox"], fraction["denominator"]["pixel_bbox"]]
            self.assertEqual(slot["source_bbox"], [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)])
            self.assertEqual(slot["numerator_bbox"], fraction["numerator"]["pixel_bbox"])
            self.assertEqual(slot["denominator_bbox"], fraction["denominator"]["pixel_bbox"])
        rows = p["rows"]; bounds = p["source"]["crop_bbox"]
        self.assertEqual(rows[0]["source_bbox"][1], bounds[1]); self.assertEqual(rows[-1]["source_bbox"][3], bounds[3])
        self.assertTrue(all(a["source_bbox"][3] == b["source_bbox"][1] for a, b in zip(rows, rows[1:])))
        for row in rows:
            self.assertEqual([row["source_bbox"][0], row["source_bbox"][2]], [bounds[0], bounds[2]])
            fallback = row["full_row_fallback"]
            self.assertEqual(fallback["source_bbox"], row["source_bbox"]); self.assertEqual(fallback["recognition_bbox"], row["source_bbox"])
        self.assertFalse(p["complete"]); self.assertFalse(p["expected_text_consumed"]); self.assertFalse(p["graph_modified"])

    def test_all_threshold_components_including_singletons_match_independent_flood_fill(self):
        p = plan_region_runs(self.layout, self.crop)["payload"]
        self.assertEqual([v["threshold"] for v in p["components_by_threshold"]], [180, 190, 210, 220])
        for layer in p["components_by_threshold"]:
            expected = components_from_pixels(self.crop, layer["threshold"], [100, 200])
            witnesses = []
            for box, points in expected:
                bitmap = bytes(int((x, y) in points) for y in range(box[1] - 200, box[3] - 200) for x in range(box[0] - 100, box[2] - 100))
                witnesses.append((tuple(box), len(points), hashlib.sha256(bitmap).hexdigest()))
            self.assertEqual(sorted((tuple(c["bbox"]), c["pixel_count"], c["pixel_sha256"]) for c in layer["components"]), sorted(witnesses))
            self.assertEqual(layer["ink_pixels"], sum(len(points) for _, points in expected))
            self.assertTrue(any(c["bbox"] == [100, 200, 101, 201] and c["pixel_count"] == 1 for c in layer["components"]))
            self.assertTrue(all(len(c["pixel_sha256"]) == 64 for c in layer["components"]))
        coverage = p["coverage"]
        self.assertTrue(all(c["ink_pixels"] == c["component_pixels"] and c["pixel_accounting_closed"] for c in coverage))
        self.assertGreater(coverage[-1]["ink_pixels"], coverage[0]["ink_pixels"])

    def test_cross_slot_and_uncovered_ink_stay_residual_even_with_full_row_fallback(self):
        p = plan_region_runs(self.layout, self.crop)["payload"]
        self.assertEqual(len(p["rows"]), 2)
        for layer in p["components_by_threshold"]:
            crossed = [c for c in layer["components"] if len(c["memberships"]) > 1]
            self.assertTrue(crossed, "generated bar crosses the primary fraction/body edge")
            self.assertTrue(all(c["status"] == "RESIDUAL" for c in crossed))
            raised = next(c for c in layer["components"] if c["bbox"] == [130, 201, 131, 202])
            self.assertEqual(raised["pixel_count"], 1); self.assertEqual(raised["uncovered_pixels"], 1)
            self.assertEqual(raised["status"], "RESIDUAL")
            self.assertTrue(raised["risks"])
        self.assertTrue(p["risks"]); self.assertTrue(any(c["uncovered_pixels"] > 0 for c in p["coverage"]))
        self.assertTrue(all(r["blocks"] == ["AUTOMATIC_CONTENT_ACCEPTANCE"] for r in p["risks"]))
        self.assertEqual(p["decision"], "HOLD"); self.assertFalse(p["complete"])

    def test_body_halo_keeps_source_pixels_full_height_and_touching_component_context(self):
        p = plan_region_runs(self.layout, self.crop)["payload"]; rows = {r["row_id"]: r for r in p["rows"]}
        with Image.open(self.crop) as image:
            original = image.convert("RGB")
            for slot in p["body_slots"]:
                box, roi = slot["source_bbox"], slot["recognition_bbox"]
                self.assertEqual([roi[1], roi[3]], [rows[slot["row_id"]]["source_bbox"][1], rows[slot["row_id"]]["source_bbox"][3]])
                self.assertLessEqual(roi[0], box[0]); self.assertGreaterEqual(roi[2], box[2])
                crop = original.crop((roi[0] - 100, roi[1] - 200, roi[2] - 100, roi[3] - 200))
                self.assertEqual(slot["crop_size"], list(crop.size)); self.assertEqual(slot["crop_rgb_sha256"], hashlib.sha256(crop.tobytes()).hexdigest())
        left = next(s for s in p["body_slots"] if s["source_bbox"][0] == 100 and s["row_id"] == p["rows"][0]["row_id"])
        self.assertGreaterEqual(left["recognition_bbox"][2], 145, "halo closure must retain the complete touching bar, not trim at body edge")

    def test_empty_body_slots_are_preserved_and_planning_does_not_assume_real_scope_size(self):
        layout, crop = pixel_layout(Path(self.temp.name) / "no-body", body_ink=False)
        p = plan_region_runs(layout, crop)["payload"]
        self.assertEqual(len(p["rows"]), 2); self.assertEqual(len(p["fraction_slots"]), 2)
        self.assertEqual(len(p["body_slots"]), 4)
        self.assertTrue(any(not s["component_ids"] for s in p["body_slots"]))
        self.assertEqual(len({s["slot_id"] for s in p["body_slots"] + p["fraction_slots"]}), 6)

    def test_geometry_is_not_conditioned_on_ocr_words_or_an_expected_answer(self):
        changed = copy.deepcopy(self.layout)
        changed["payload"]["source_ocr"][0]["text"] = "Unrelated deliberately wrong synthetic text"
        resign_layout(changed)
        first = plan_region_runs(self.layout, self.crop)["payload"]; second = plan_region_runs(changed, self.crop)["payload"]
        self.assertEqual([r["source_bbox"] for r in first["rows"]], [r["source_bbox"] for r in second["rows"]])
        self.assertEqual([s["recognition_bbox"] for s in first["body_slots"]], [s["recognition_bbox"] for s in second["body_slots"]])
        self.assertEqual([(c["threshold"], c["ink_pixels"]) for c in first["coverage"]], [(c["threshold"], c["ink_pixels"]) for c in second["coverage"]])

    def test_source_bytes_dimensions_reference_and_approval_claims_cannot_be_substituted(self):
        for fault in ("crop-sha", "source-ref", "crop-size", "false-layout-approval"):
            changed = copy.deepcopy(self.layout)
            if fault == "crop-sha": changed["payload"]["crop_sha256"] = "0" * 64
            elif fault == "source-ref": changed["input_refs"][1]["sha256"] = "0" * 64
            elif fault == "crop-size": changed["payload"]["crop_bbox"][2] += 1
            else: changed["payload"]["transcription_verified"] = True
            resign_layout(changed)
            with self.subTest(fault=fault), self.assertRaises(ValueError): plan_region_runs(changed, self.crop)
        changed = Path(self.temp.name) / "corrupt.png"; changed.write_bytes(self.crop.read_bytes() + b"different")
        with self.assertRaises(ValueError): plan_region_runs(self.layout, changed)

    def test_repeat_is_deterministic_and_has_no_ocr_model_or_network_permission(self):
        snapshot = copy.deepcopy(self.layout)
        with patch.dict(sys.modules, {"rapidocr_onnxruntime": None, "rapid_latex_ocr": None, "onnxruntime": None}), \
             patch("socket.socket", side_effect=AssertionError("Pixel planning cannot use network")):
            first = plan_region_runs(self.layout, self.crop); second = plan_region_runs(self.layout, self.crop)
        self.assertEqual(first, second); self.assertEqual(self.layout, snapshot)
        self.assertNotIn("created_at", first); self.assertEqual(first["input_refs"], [reference(self.layout)])
        self.assertEqual(first["payload"]["platform_actions"], [])


if __name__ == "__main__":
    unittest.main()
