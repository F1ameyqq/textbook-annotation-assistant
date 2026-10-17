from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

from tools.prepare_chapter_scope_b import prepare

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ChapterScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scope_path = self.root / "scope.json"
        self.out = self.root
        self.assets = []
        for index, page in enumerate(("p1", "p2")):
            path = self.root / f"{page}.png"
            Image.new("RGB", (12 + index, 18), "white").save(path)
            self.assets.append({"asset_id": f"a{index+1}", "page_id": page, "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "width": 12 + index, "height": 18})
        self.scope = {"schema_version": "b-chapter-scope-input/0.1", "book_id": "book1",
            "scope_id": "chapter-one", "chapter_id": "ch1", "inventory_frozen": True,
            "pages": [{"page_id": "p1", "page_order": 0, "required_asset_ids": ["a1"]},
                {"page_id": "p2", "page_order": 1, "required_asset_ids": ["a2"]}],
            "assets": self.assets}
        self.write()

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.scope_path.write_text(json.dumps(self.scope), encoding="utf-8")

    def test_reconciled_frozen_inventory_emits_ordered_pipeline_source_but_keeps_acceptance_hold(self):
        report = prepare(self.scope_path, self.out)
        self.assertEqual(report["scope_state"], "DECLARED_COMPLETE_SOURCE_INVENTORY")
        self.assertEqual(report["decision"], "HOLD")
        self.assertFalse(report["independent_denominator_verified"])
        source = json.loads((self.out / "source-descriptor.json").read_text(encoding="utf-8"))
        self.assertEqual([a["asset_id"] for a in source["assets"]], ["a1", "a2"])
        self.assertEqual([a["reading_order"] for a in source["assets"]], [0, 1])
        self.assertEqual(source["assets"][1]["external_refs"]["chapter_page_id"], "p2")
        from annotation.recognition.baseline import load_source
        loaded, image_inputs = load_source(self.out / "source-descriptor.json")
        self.assertEqual(loaded["schema_version"], "b-source-trial/0.1")
        self.assertEqual([asset["asset_id"] for asset, _ in image_inputs], ["a1", "a2"])

    def test_same_path_or_copied_bytes_cannot_count_as_two_assets(self):
        for copied in (False, True):
            with self.subTest(copied=copied):
                self.assets[1].update(sha256=self.assets[0]["sha256"], width=12, height=18)
                if copied:
                    (self.root / "copy.png").write_bytes((self.root / "p1.png").read_bytes())
                    self.assets[1]["path"] = "copy.png"
                else:
                    self.assets[1]["path"] = "p1.png"
                self.write()
                report = prepare(self.scope_path, self.out)
                self.assertEqual(report["scope_state"], "PARTIAL")
                self.assertIn("ALIASED_SOURCE_ASSET", {g["code"] for g in report["gaps"]})

    def test_missing_page_asset_keeps_partial_and_reports_missing_identity(self):
        self.scope["assets"].pop()
        self.write()
        report = prepare(self.scope_path, self.out)
        self.assertEqual(report["scope_state"], "PARTIAL")
        self.assertIn("MISSING_ASSET", {gap["code"] for gap in report["gaps"]})
        self.assertEqual(report["expected_page_count"], 2)
        self.assertEqual(report["received_asset_count"], 1)

    def test_duplicate_asset_and_page_identity_conflicts_are_reported(self):
        self.scope["assets"].append(dict(self.assets[0]))
        self.scope["assets"][1]["page_id"] = "p1"
        self.write()
        report = prepare(self.scope_path, self.out)
        codes = {gap["code"] for gap in report["gaps"]}
        self.assertIn("DUPLICATE_ASSET_ID", codes)
        self.assertIn("ASSET_PAGE_IDENTITY_CONFLICT", codes)
        self.assertEqual(report["scope_state"], "PARTIAL")

    def test_duplicate_expected_page_and_asset_references_do_not_close_scope(self):
        self.scope["pages"].append(dict(self.scope["pages"][0]))
        self.scope["pages"][1]["required_asset_ids"] = ["a1", "a1"]
        self.write()
        report = prepare(self.scope_path, self.out)
        codes = {gap["code"] for gap in report["gaps"]}
        self.assertIn("DUPLICATE_PAGE_ID", codes)
        self.assertIn("DUPLICATE_REQUIRED_ASSET", codes)
        self.assertEqual(report["decision"], "HOLD")

    def test_hash_mismatch_is_detected_against_file_bytes(self):
        self.scope["assets"][0]["sha256"] = "0" * 64
        self.write()
        report = prepare(self.scope_path, self.out)
        self.assertIn("ASSET_SHA256_MISMATCH", {gap["code"] for gap in report["gaps"]})
        self.assertEqual(report["scope_state"], "PARTIAL")

    def test_unfrozen_inventory_never_claims_complete_scope(self):
        self.scope["inventory_frozen"] = False
        self.write()
        report = prepare(self.scope_path, self.out)
        self.assertEqual(report["scope_state"], "PARTIAL")
        self.assertFalse(report["inventory_frozen_claim"])
        self.assertIn("INVENTORY_NOT_FROZEN", {gap["code"] for gap in report["gaps"]})

    def test_malformed_page_order_and_asset_page_identity_return_partial(self):
        self.scope["pages"][0]["page_order"] = "first"
        self.scope["assets"][0]["page_id"] = ["p1"]
        self.write()
        report = prepare(self.scope_path, self.out)
        self.assertEqual(report["scope_state"], "PARTIAL")
        self.assertEqual(report["decision"], "HOLD")
        self.assertTrue({"INVALID_PAGE_ORDER", "UNEXPECTED_PAGE_IDENTITY"}.issubset(
            {gap["code"] for gap in report["gaps"]}))

    def test_missing_asset_path_returns_gap_instead_of_crashing(self):
        self.scope["assets"][0]["path"] = None
        self.write()
        report = prepare(self.scope_path, self.out)
        self.assertEqual(report["scope_state"], "PARTIAL")
        self.assertIn("ASSET_PATH_MISSING", {gap["code"] for gap in report["gaps"]})


if __name__ == "__main__":
    unittest.main()
