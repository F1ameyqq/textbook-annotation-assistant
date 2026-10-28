"""Early source gates cannot be replaced by a later snapshot or cache archive."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests"), str(ROOT / "tools")]
from annotation.recognition.baseline import file_digest
from annotation.recognition.region_runs import plan_region_runs
from test_region_runs import pixel_layout, resign_layout

spec = importlib.util.spec_from_file_location("independent_prepare_region_draft", ROOT / "tools/prepare_region_draft_b.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class PrepareRegionDraftSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.layout, self.crop = pixel_layout(self.root)
        self.plan = plan_region_runs(self.layout, self.crop)
        source = self.layout["payload"]
        self.original = self.root / "generated-original.png"
        self.manifest = {"schema_version": "b-source-trial/0.1", "artifact_id": "source-gate-generated",
            "book_id": self.layout["book_id"], "scope_id": "actual-generated-original",
            "assets": [{"asset_id": source["asset_id"], "path": self.original.name, "sha256": source["source_sha256"],
                        "width": source["source_size"][0], "height": source["source_size"][1], "reading_order": 0}]}
        self.paths = {}
        for name in ("layout", "legacy", "canvas", "roles", "evidence", "graph", "base-check", "review", "previous", "observations", "runs", "source"):
            value = self.layout if name == "layout" else self.plan if name == "runs" else self.manifest if name == "source" else {"not_consumed_before_source_gate": name}
            self.paths[name] = self.write(name, value)

    def write(self, name, value):
        path = self.root / (name + ".json")
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def args(self):
        args = []
        for name in ("layout", "legacy", "canvas", "roles", "evidence", "graph", "base-check", "review", "previous", "observations", "runs", "source"):
            args += ["--" + name, str(self.paths[name])]
        return args + ["--crop", str(self.crop), "--answer-id", "not-consumed-before-source-gate", "--out", str(self.root / "fresh-output")]

    def guards(self):
        return (patch("annotation.recognition.region_ocr.collect_region_observations", side_effect=AssertionError("No OCR may precede source rejection")),
                patch("annotation.recognition.region_ocr.validate_region_observations", side_effect=AssertionError("Source gate must precede observation validation")),
                patch("annotation.recognition.region_draft.build_region_draft", side_effect=AssertionError("No assembly may precede source rejection")))

    def test_explicit_layout_cannot_validate_one_asset_while_cache_consumes_another_with_identical_crop(self):
        foreign = copy.deepcopy(self.layout)
        foreign["payload"]["asset_id"] = "other-original-asset"
        foreign["input_refs"][1]["asset_id"] = "other-original-asset"
        resign_layout(foreign)
        foreign_plan = plan_region_runs(foreign, self.crop)
        self.assertNotEqual(foreign_plan["payload"]["layout_ref"], self.plan["payload"]["layout_ref"])
        self.assertEqual(foreign_plan["payload"]["source"]["crop_sha256"], self.plan["payload"]["source"]["crop_sha256"])
        self.assertEqual(foreign_plan["payload"]["source"]["crop_rgb_sha256"], self.plan["payload"]["source"]["crop_rgb_sha256"])
        self.write("runs", foreign_plan)
        collector_guard, observation_guard, assembly_guard = self.guards()
        with collector_guard as collect, observation_guard as validate, assembly_guard as assemble, \
             patch.dict(sys.modules, {"rapidocr_onnxruntime": None, "rapid_latex_ocr": None, "onnxruntime": None}):
            with self.assertRaisesRegex(ValueError, r"explicit.*layout.*(?:differ|match)|plan.*layout.*(?:differ|match)|layout.*(?:differ|match).*plan"):
                cli.main(self.args())
            collect.assert_not_called(); validate.assert_not_called(); assemble.assert_not_called()

    def test_original_tail_change_after_load_source_is_not_accepted_as_a_late_initial_hash(self):
        original_bytes = self.original.read_bytes(); original_sha = file_digest(self.original)
        real_loader = cli.load_source
        loads = []
        def changed_after_validation(path):
            result = real_loader(path)
            loads.append(str(path))
            self.original.write_bytes(original_bytes + b"changed-only-after-source-validation")
            return result
        collector_guard, observation_guard, assembly_guard = self.guards()
        with patch.object(cli, "load_source", side_effect=changed_after_validation), \
             collector_guard as collect, observation_guard as validate, assembly_guard as assemble, \
             patch.dict(sys.modules, {"rapidocr_onnxruntime": None, "rapid_latex_ocr": None, "onnxruntime": None}):
            with self.assertRaisesRegex(ValueError, r"source.*(?:changed|mismatch)|original.*(?:changed|mismatch)|input.*changed"):
                cli.main(self.args())
            collect.assert_not_called(); validate.assert_not_called(); assemble.assert_not_called()
        self.assertEqual(len(loads), 1); self.assertNotEqual(file_digest(self.original), original_sha)
        with Image.open(self.original) as original, Image.open(self.crop) as crop:
            tile = original.convert("RGB").crop(self.layout["payload"]["crop_bbox"])
            self.assertEqual(tile.tobytes(), crop.convert("RGB").tobytes(), "the rejection must concern original bytes even though source crop pixels still match")


if __name__ == "__main__":
    unittest.main()
