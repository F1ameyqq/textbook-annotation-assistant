import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from annotation.recognition.baseline import load_source, recognize, valid_bbox, write_result, legacy_backend
from page_mapping import image_name, is_coord_space_usable
from verify_data import check_records


class RecognitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        image = Image.new("RGB", (900, 400), "white")
        draw = ImageDraw.Draw(image)
        # Two separated panels to exercise crop -> original x offsets.
        for left in (30, 500):
            for y in (30, 60, 90, 160, 190):
                draw.rectangle((left, y, left + 330, y + 9), fill="black")
        image.save(self.root / "page.png")
        self.source = {"schema_version": "b-source-trial/0.1", "artifact_id": "source-fixture",
                       "book_id": "fixture-book", "scope_id": "fixture-scope", "assets": [
                           {"asset_id": "page", "path": "page.png", "width": 900, "height": 400,
                            "sha256": hashlib.sha256((self.root / "page.png").read_bytes()).hexdigest(),
                            "reading_order": 0}]}
        self.path = self.root / "source.json"
        self.save(self.source)

    def save(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")

    def test_hash_and_dimensions_reject_changed_source(self):
        for field, bad in (("sha256", "0" * 64), ("width", 901)):
            source = copy.deepcopy(self.source)
            source["assets"][0][field] = bad
            self.save(source)
            with self.assertRaises(ValueError):
                load_source(self.path)

    def test_portability_and_traversal(self):
        for bad in ("../page.png", "C:/private/page.png", "/private/page.png", "..\\page.png"):
            source = copy.deepcopy(self.source)
            source["assets"][0]["path"] = bad
            self.save(source)
            with self.assertRaises(ValueError):
                load_source(self.path)

    def test_duplicates_and_unknown_contract_rejected(self):
        source = copy.deepcopy(self.source)
        source["assets"].append(source["assets"][0])
        self.save(source)
        with self.assertRaises(ValueError):
            load_source(self.path)
        source = copy.deepcopy(self.source)
        source["schema_version"] = "SourceBundle-v1"
        self.save(source)
        with self.assertRaises(ValueError):
            load_source(self.path)

    def test_crop_offsets_candidates_and_reproducibility(self):
        first, previews = recognize(self.path)
        second, _ = recognize(self.path)
        self.assertEqual(first["content_hash"], second["content_hash"])
        self.assertEqual(first["artifact_id"], second["artifact_id"])
        page = first["payload"]["pages"][0]
        self.assertGreater(len(page["regions"]), 0)
        transforms = {t["crop_id"]: t for t in page["crop_transforms"]}
        self.assertTrue(any(t["crop_to_original"][0][2] > 0 for t in transforms.values()))
        for region in page["regions"]:
            self.assertTrue(valid_bbox(region["bbox"], 900, 400))
            crop = transforms[region["crop_id"]]
            offset = crop["crop_to_original"][0][2]
            self.assertGreaterEqual(region["bbox"][0], offset)
            local_x = region["bbox"][0] - offset
            self.assertEqual(local_x + offset, region["bbox"][0])
            self.assertIsNone(region["role_candidate"])
            self.assertEqual(region["verification_status"], "UNVERIFIED")
        self.assertEqual(first["payload"]["quality_decision"], "NOT_EVALUATED")
        self.assertFalse(page["coverage_evidence"]["independent_of_recognizer"])
        self.assertEqual(previews["page"].size, (900, 400))
        output = self.root / "run"
        write_result(first, previews, output)
        with self.assertRaises(FileExistsError):
            write_result(second, previews, output)

    def test_blank_page_does_not_report_quality_pass(self):
        Image.new("RGB", (900, 400), "white").save(self.root / "page.png")
        self.source["assets"][0]["sha256"] = hashlib.sha256((self.root / "page.png").read_bytes()).hexdigest()
        self.save(self.source)
        result, _ = recognize(self.path)
        page = result["payload"]["pages"][0]
        self.assertEqual(page["regions"], [])
        self.assertIn({"code": "NO_CANDIDATES"}, page["issues"])
        self.assertEqual(result["payload"]["quality_decision"], "NOT_EVALUATED")

    def test_changed_source_changes_identity(self):
        old, _ = recognize(self.path)
        self.source["scope_id"] = "another-scope"
        self.save(self.source)
        new, _ = recognize(self.path)
        self.assertNotEqual(old["artifact_id"], new["artifact_id"])
        self.assertNotEqual(old["payload"]["pages"][0]["regions"][0]["region_id"],
                            new["payload"]["pages"][0]["regions"][0]["region_id"])

    def test_invalid_geometry(self):
        for box in ([0, 0, 901, 20], [20, 20, 10, 30], [0, 0, float("nan"), 20]):
            self.assertFalse(valid_bbox(box, 900, 400))


class MappingRegression(unittest.TestCase):
    def test_known_sample_and_new_book(self):
        self.assertEqual(image_name("46006966", 234), "46006966_page_233.jpg")
        self.assertTrue(is_coord_space_usable(234))
        self.assertFalse(is_coord_space_usable(234, "46007447"))
        for book, page in (("46007447", 234), ("46006966", 1), ("46006966", 0)):
            with self.assertRaises(ValueError):
                image_name(book, page)

    def test_partial_width_not_wrong_coordinate_space(self):
        records = [{"page_index": 234, "rect_bbox": "2,254,594,1164"}]
        report = check_records(records, ROOT / "data/raw/images")
        self.assertEqual(report["pages"][0]["asset_path"], "46006966_page_233.jpg")
        self.assertEqual(report["pages"][0]["verdict"], "IN_BOUNDS")
        self.assertFalse(report["pages"][0]["business_ground_truth"])
        legacy = legacy_backend().unusable_report(
            [{"page_index": 234, "bbox": [2, 254, 594, 1164]}], {233: (3467, 1615)})
        self.assertEqual(legacy["pages"]["234"]["verdict"], "OK")

    def test_real_sample_mapping_and_invalid_boxes_retained(self):
        records = json.loads((ROOT / "data/raw/annotations/annotations_unified_snapshot.json").read_text(encoding="utf-8"))
        report = check_records(records, ROOT / "data/raw/images")
        self.assertEqual({p["page_index"] for p in report["pages"]}, {8, 9, 10, 234})
        self.assertEqual(sum(len(p["boxes"]) for p in report["pages"]), 36)
        self.assertTrue(any(not box["within_image"] for p in report["pages"] for box in p["boxes"]))


if __name__ == "__main__":
    unittest.main()
