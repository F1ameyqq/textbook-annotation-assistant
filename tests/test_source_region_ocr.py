"""Synthetic source-page binding tests; no native business data or models."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from annotation.recognition.usense_capture import file_ref, read_json
from annotation.recognition.source_region_ocr import validate_sources, region_image, collect, check_inventory


def put(path, value):
    Path(path).write_text(json.dumps(value), encoding="utf-8")


class RegionSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root/"source.png"
        Image.new("RGB", (100, 80), "gray").save(self.image)
        self.native = self.root/"native.json"
        put(self.native, {"code": 0, "data": {"file_id": "synthetic-book", "pages": [
            {"image": "memory://source-1.png", "page_index": 1, "blocks": []}]}})
        self.inventory = self.root/"inventory.json"
        put(self.inventory, {"book_id": "synthetic-book", "pages": [{"viewer_page": 2,
            "source_image_index": 1, "image_url": "memory://source-1.png",
            "native_response_sha256": file_ref(self.native)["sha256"]}]})
        self.download = self.root/"download.json"
        put(self.download, {"book_id": "synthetic-book", "pages": [{"viewer_page": 2,
            "source_url": "memory://source-1.png", "sha256": file_ref(self.image)["sha256"],
            "bytes": self.image.stat().st_size, "width": 100, "height": 80,
            "metadata_sha256": file_ref(self.native)["sha256"]}]})
        self.source = {"viewer_page": 2, "image": file_ref(self.image), "dimensions": [100, 80],
            "native_metadata": file_ref(self.native), "page_inventory": file_ref(self.inventory),
            "download_manifest": file_ref(self.download), "allowed_roles": ["question", "diagram"]}
        self.region = {"region_id": "synthetic.q1", "viewer_page": 2, "role": "question",
            "bbox": [10, 10, 70, 60], "ocr": False}
        self.spec = {"schema": "SourceRegionOCRSpec/v1", "book_id": "synthetic-book",
                     "sources": [self.source], "regions": [self.region]}
        self.spec_path = self.root/"spec.json"

    def refresh(self, key, path):
        self.source[key] = file_ref(path)

    def run_collect(self):
        put(self.spec_path, self.spec)
        return collect(self.spec_path, self.root/"out")

    def test_current_source_download_and_native_page_match(self):
        sources = validate_sources(self.spec)
        _, box, image = region_image(self.region, sources)
        self.assertEqual(box, [10, 10, 70, 60])
        self.assertEqual(image.size, (60, 50))

    def test_wrong_native_page_rejected_even_with_resigned_native_reference(self):
        native = read_json(self.native)
        native["data"]["pages"][0]["page_index"] = 2
        put(self.native, native)
        self.refresh("native_metadata", self.native)
        inventory = read_json(self.inventory)
        inventory["pages"][0]["native_response_sha256"] = file_ref(self.native)["sha256"]
        put(self.inventory, inventory)
        self.refresh("page_inventory", self.inventory)
        with self.assertRaisesRegex(ValueError, "Wrong native page"):
            validate_sources(self.spec)

    def test_different_book_native_is_rejected(self):
        native = read_json(self.native)
        native["data"]["file_id"] = "other-book"
        put(self.native, native)
        self.refresh("native_metadata", self.native)
        inventory = read_json(self.inventory)
        inventory["pages"][0]["native_response_sha256"] = file_ref(self.native)["sha256"]
        put(self.inventory, inventory)
        self.refresh("page_inventory", self.inventory)
        with self.assertRaisesRegex(ValueError, "another book"):
            validate_sources(self.spec)

    def test_metadata_hash_must_match_inventory(self):
        inventory = read_json(self.inventory)
        inventory["pages"][0]["native_response_sha256"] = "a"*64
        put(self.inventory, inventory)
        self.refresh("page_inventory", self.inventory)
        with self.assertRaisesRegex(ValueError, "inventory disagree"):
            validate_sources(self.spec)

    def test_native_false_code_is_not_success(self):
        native = read_json(self.native)
        native["code"] = False
        put(self.native, native)
        self.refresh("native_metadata", self.native)
        inventory = read_json(self.inventory)
        inventory["pages"][0]["native_response_sha256"] = file_ref(self.native)["sha256"]
        put(self.inventory, inventory)
        self.refresh("page_inventory", self.inventory)
        with self.assertRaisesRegex(ValueError, "unsuccessful"):
            validate_sources(self.spec)

    def test_wrong_downloaded_image_bytes_rejected(self):
        Image.new("RGB", (100, 80), "white").save(self.image)
        self.refresh("image", self.image)
        with self.assertRaisesRegex(ValueError, "Wrong image bytes"):
            validate_sources(self.spec)

    def test_wrong_download_url_rejected(self):
        download = read_json(self.download)
        download["pages"][0]["source_url"] = "memory://other-page.png"
        put(self.download, download)
        self.refresh("download_manifest", self.download)
        with self.assertRaisesRegex(ValueError, "Downloaded image URL"):
            validate_sources(self.spec)

    def test_old_url_key_download_manifest_supported(self):
        download = read_json(self.download)
        row = download["pages"][0]
        row["url"] = row.pop("source_url")
        row.pop("metadata_sha256")
        put(self.download, download)
        self.refresh("download_manifest", self.download)
        self.assertEqual(len(validate_sources(self.spec)), 1)

    def test_source_dimensions_rejected(self):
        self.source["dimensions"] = [101, 80]
        with self.assertRaisesRegex(ValueError, "dimensions"):
            validate_sources(self.spec)

    def test_wrong_role_page_rejected_for_answer(self):
        self.region["role"] = "answer"
        with self.assertRaisesRegex(ValueError, "forbidden"):
            region_image(self.region, validate_sources(self.spec))

    def test_outside_page_rejected(self):
        self.region["bbox"] = [10, 10, 101, 50]
        with self.assertRaisesRegex(ValueError, "outside page"):
            region_image(self.region, validate_sources(self.spec))

    def test_nonfinite_and_boolean_coordinates_rejected(self):
        for first in (True, float("inf"), float("nan")):
            self.region["bbox"][0] = first
            with self.assertRaisesRegex(ValueError, "Finite"):
                region_image(self.region, validate_sources(self.spec))

    def test_fractional_bbox_preserves_floor_ceil_extent(self):
        self.region["bbox"] = [10.7, 10.1, 70.2, 60.9]
        _, box, image = region_image(self.region, validate_sources(self.spec))
        self.assertEqual(box, [10, 10, 71, 61])
        self.assertEqual(image.size, (61, 51))

    def test_duplicate_page_or_region_rejected(self):
        self.spec["sources"].append(deepcopy(self.source))
        with self.assertRaisesRegex(ValueError, "duplicate viewer"):
            validate_sources(self.spec)

    def test_crop_only_collection_and_fresh_check_are_model_free(self):
        run = self.run_collect()
        self.assertEqual(run["inference_calls"], 0)
        self.assertNotIn("backend", run)
        result = check_inventory(self.root/"out/run.json")
        self.assertEqual(result["regions"], 1)
        self.assertFalse(result["write_allowed"])
        self.assertIsNone(result["human_confirmation"])

    def test_duplicate_regions_leave_failed_run(self):
        self.spec["regions"].append(deepcopy(self.region))
        with self.assertRaisesRegex(ValueError, "Duplicate source-region"):
            self.run_collect()
        self.assertEqual(read_json(self.root/"out/run.json")["status"], "FAILED")

    def test_changed_crop_rejected_after_coordinated_reference_updates(self):
        run = self.run_collect()
        path = Path(run["regions"][0]["observation"]["path"])
        observation = read_json(path)
        crop = Path(observation["crop"]["path"])
        Image.new("RGB", (60, 50), "white").save(crop)
        observation["crop"] = file_ref(crop)
        put(path, observation)
        run["regions"][0]["observation"] = file_ref(path)
        put(self.root/"out/run.json", run)
        with self.assertRaisesRegex(ValueError, "pixels changed"):
            check_inventory(self.root/"out/run.json")

    def test_observation_cannot_be_elevated(self):
        run = self.run_collect()
        path = Path(run["regions"][0]["observation"]["path"])
        observation = read_json(path)
        observation["write_allowed"] = True
        put(path, observation)
        run["regions"][0]["observation"] = file_ref(path)
        put(self.root/"out/run.json", run)
        with self.assertRaisesRegex(ValueError, "elevated"):
            check_inventory(self.root/"out/run.json")

    def test_inference_count_is_not_fabricated(self):
        run = self.run_collect()
        run["inference_calls"] = 1
        put(self.root/"out/run.json", run)
        with self.assertRaisesRegex(ValueError, "Inference count"):
            check_inventory(self.root/"out/run.json")

    def test_mocked_cpu_raw_variants_retained(self):
        self.region["ocr"] = True
        engine = lambda *args, **kwargs: ([["synthetic raw", 0.4]], [0.01])
        with patch("annotation.recognition.inline_ocr._cpu_backend", return_value=(engine, {"synthetic": True})), \
                patch("annotation.recognition.source_region_ocr.row_boxes", return_value=([[0, 0, 50, 20]], 127.0)):
            run = self.run_collect()
        self.assertEqual(run["inference_calls"], 2)
        observation = read_json(run["regions"][0]["observation"]["path"])
        self.assertEqual([v["scale"] for v in observation["variants"]], [3, 4])
        self.assertEqual(observation["variants"][0]["rows"][0]["raw_result"], [["synthetic raw", 0.4]])
        self.assertEqual(check_inventory(self.root/"out/run.json")["inference_calls"], 2)

    def test_cli_check_from_other_working_directory(self):
        self.run_collect()
        tool = Path(__file__).resolve().parents[1]/"tools/run_source_region_ocr.py"
        result = subprocess.run([sys.executable, str(tool), "check", "--run", str(self.root/"out/run.json")],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["write_allowed"])


if __name__ == "__main__":
    unittest.main()
