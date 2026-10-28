"""Original-byte and pixel binding for explicit spatial transcription drafts."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("prepare_region_sources_cli", ROOT / "tools/prepare_content_revision_b.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class RegionSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        image = Image.new("RGB", (30, 20), "white")
        image.putpixel((8, 7), (0, 20, 30))
        self.image = self.root / "original.png"
        image.save(self.image)
        sha = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.source = {"schema_version": "b-source-trial/0.1", "artifact_id": "source-test",
            "book_id": "test-book", "scope_id": "test-scope", "assets": [
                {"asset_id": "source-page", "path": "original.png", "sha256": sha,
                 "width": 30, "height": 20, "reading_order": 0}]}
        self.manifest = self.root / "source.json"
        self.save()
        self.evidence = {"book_id": "test-book", "payload": {"pages": [
            {"asset_id": "source-page", "source": {"sha256": sha, "width": 30, "height": 20}}]}}
        self.op = {"operation_id": "region-test", "kind": "REBUILD_TEXT_REGION", "source_region": {
            "asset_id": "source-page", "source_sha256": sha, "source_size": [30, 20], "bbox": [5, 4, 15, 12]}}

    def save(self):
        self.manifest.write_text(json.dumps(self.source), encoding="utf-8")

    def check(self):
        return cli._region_sources([self.op], self.evidence, [self.manifest])

    def test_actual_crop_receipt_has_original_pixel_bytes(self):
        receipts, watched = self.check()
        with Image.open(self.image) as image:
            expected = hashlib.sha256(image.convert("RGB").crop((5, 4, 15, 12)).tobytes()).hexdigest()
        self.assertEqual(receipts, [{"operation_id": "region-test", **self.op["source_region"],
                                    "source_crop_rgb_sha256": expected}])
        self.assertEqual(set(watched), {self.image.resolve(), self.manifest})

    def test_spatial_operation_requires_original_source_manifest(self):
        with self.assertRaisesRegex(ValueError, "requires --source"):
            cli._region_sources([self.op], self.evidence, None)

    def test_old_span_operations_need_no_extra_source(self):
        self.assertEqual(cli._region_sources([{"kind": "EDIT_TEXT"}], self.evidence, None), ([], {}))

    def test_corrupt_image_bytes_rejected(self):
        self.image.write_bytes(self.image.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.check()

    def test_manifest_dimensions_are_checked_from_image(self):
        self.source["assets"][0]["width"] = 31
        self.save()
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.check()

    def test_different_book_rejected(self):
        self.source["book_id"] = "another-book"
        self.save()
        with self.assertRaisesRegex(ValueError, "different book"):
            self.check()

    def test_duplicate_source_assets_rejected(self):
        with self.assertRaisesRegex(ValueError, "more than once"):
            cli._region_sources([self.op], self.evidence, [self.manifest, self.manifest])

    def test_current_evidence_sha_or_size_cannot_be_substituted(self):
        original = copy.deepcopy(self.evidence)
        for key, replacement in (("sha256", "0" * 64), ("width", 31)):
            with self.subTest(key=key):
                self.evidence = copy.deepcopy(original)
                self.evidence["payload"]["pages"][0]["source"][key] = replacement
                with self.assertRaisesRegex(ValueError, "SHA/dimensions"):
                    self.check()

    def test_outside_or_noninteger_pixel_crop_rejected(self):
        for bbox in ([5, 4, 31, 12], [5.0, 4, 15, 12], [True, 4, 15, 12], [5, 4, 5, 12]):
            with self.subTest(bbox=bbox):
                self.op["source_region"]["bbox"] = bbox
                with self.assertRaisesRegex(ValueError, "integer crop"):
                    self.check()

    def test_duplicate_manifest_json_key_rejected(self):
        text = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(text.replace('"book_id":', '"book_id": "ignored", "book_id":'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            self.check()


if __name__ == "__main__":
    unittest.main()
