"""Local integrity gates for source coverage; no platform or OCR calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("coverage_inventory", Path(__file__).resolve().parents[1] / "tools/book_coverage_inventory.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CoverageIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "synthetic.jpg"
        self.image.write_bytes(b"synthetic-local-source-bytes-not-a-real-book")
        self.raw = self.root / "native.json"
        self.url = "https://synthetic.invalid/upload_images/synthetic/synthetic_page_0.jpg"
        self.raw.write_text(json.dumps({"code": 0, "data": {"file_id": "synthetic", "pages": [{"image": self.url, "page_index": 0}]}}), encoding="utf-8")
        self.pages = {"book_id": "synthetic", "source_total_pages": 1, "pages": [{"viewer_page": 1, "source_image_index": 0,
                      "image_url": self.url, "native_response": str(self.raw), "native_response_sha256": m.sha(self.raw), "pre_annotation_blocks": 0}]}
        self.dirs = {"directories": [{"id": "old", "path": ["Chapter", "Old lesson"], "subdirectories": 0, "direct_questions": 1},
                                      {"id": "new", "path": ["Chapter", "New lesson"], "subdirectories": 0, "direct_questions": 0}],
                     "questions": [{"id": "node", "native_order": "18", "parent_id": "old"}]}
        self.images = {"book_id": "synthetic", "pages": [{"viewer_page": 1, "source_image_index": 0, "source_url": self.url,
                       "status": "IMAGE_VERIFIED", "path": str(self.image), "sha256": m.sha(self.image), "bytes": self.image.stat().st_size}]}
        self.review = {"book_id": "synthetic", "directories": []}

    def build(self):
        return m.build_ledger(book_id="synthetic", page_inventory=self.pages, directory_inventory=self.dirs,
                              image_manifest=self.images, mappings=self.review)

    def mapped(self, complete=False):
        value = {"directory_id": "new", "question_pages": [1], "answer_pages": [],
                 "source_evidence": [{"viewer_page": 1, "source_sha256": m.sha(self.image)}],
                 "complete_enumeration": complete, "recognized_items": [{"item_key": "local-1", "kind": "QUESTION",
                    "viewer_page": 1, "source_sha256": m.sha(self.image), "evidence_kind": "MODEL_SOURCE_INSPECTION"}]}
        self.review["directories"] = [value]
        return value

    def test_zero_preannotation_and_native_empty_do_not_become_zero_questions(self):
        result = self.build()
        self.assertEqual(result["summary"]["pre_annotation_blocks"], 0)
        self.assertEqual(result["summary"]["native_question_nodes"], 1)
        self.assertIsNone(result["summary"]["whole_book_question_count"])
        self.assertTrue(all(d["question_count"] is None for d in result["directories"]))

    def test_partial_recognition_keeps_denominator_null(self):
        self.mapped()
        row = self.build()["directories"][1]
        self.assertIsNone(row["question_count"])
        self.assertEqual(row["mapping"]["recognized_items_observed"], 1)

    def test_complete_enumeration_counts_questions_and_examples_separately(self):
        value = self.mapped(True)
        value["recognized_items"].append({**value["recognized_items"][0], "item_key": "example", "kind": "WORKED_EXAMPLE"})
        row = self.build()["directories"][1]
        self.assertEqual(row["question_count"], 1)
        self.assertEqual(row["mapping"]["worked_example_count"], 1)
        self.assertIsNone(row["mapping"]["human_confirmation"])

    def test_existing_native_sequence_is_preserved_during_proposed_relocation(self):
        value = self.mapped(True)
        value["native_bindings"] = [{"node_id": "node", "native_order": 18, "current_directory_id": "old", "item_key": "local-1"}]
        binding = self.build()["directories"][1]["mapping"]["native_bindings"][0]
        self.assertTrue(binding["migration_needed"])
        self.assertEqual(binding["item_key"], "local-1")
        self.assertEqual(self.dirs["questions"][0]["parent_id"], "old")

    def test_relabeling_native_sequence_without_raw_binding_is_rejected(self):
        value = self.mapped(True)
        value["native_bindings"] = [{"node_id": "node", "native_order": 1, "current_directory_id": "old", "item_key": "local-1"}]
        with self.assertRaisesRegex(ValueError, "NATIVE_ORDER_MISMATCH"):
            self.build()

    def test_wrong_book_native_response_rejected_even_after_rehash(self):
        native = json.loads(self.raw.read_text()); native["data"]["file_id"] = "other"
        self.raw.write_text(json.dumps(native))
        self.pages["pages"][0]["native_response_sha256"] = m.sha(self.raw)
        with self.assertRaisesRegex(ValueError, "NATIVE_BOOK_MISMATCH"):
            self.build()

    def test_changed_image_bytes_rejected(self):
        self.image.write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "IMAGE_BYTES_CHANGED"):
            self.build()

    def test_wrong_page_review_hash_rejected(self):
        self.mapped()["source_evidence"][0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "REVIEW_SOURCE_MISMATCH"):
            self.build()

    def test_empty_complete_enumeration_rejected(self):
        self.mapped(True)["recognized_items"] = []
        with self.assertRaisesRegex(ValueError, "COMPLETE_ENUMERATION_NEEDS_ITEMS"):
            self.build()

    def test_missing_page_metadata_rejected(self):
        self.pages["source_total_pages"] = 2
        with self.assertRaisesRegex(ValueError, "PAGE_SCOPE_INCOMPLETE"):
            self.build()

    def test_native_wrong_image_index_rejected(self):
        self.pages["pages"][0]["source_image_index"] = 1
        with self.assertRaisesRegex(ValueError, "NATIVE_PAGE_BINDING_MISMATCH"):
            self.build()

    def test_source_from_other_book_is_rejected_after_coordinated_metadata_change(self):
        wrong_url = self.url.replace("/synthetic/synthetic_page", "/other/other_page")
        native = json.loads(self.raw.read_text()); native["data"]["pages"][0]["image"] = wrong_url
        self.raw.write_text(json.dumps(native)); self.pages["pages"][0].update(image_url=wrong_url, native_response_sha256=m.sha(self.raw))
        with self.assertRaisesRegex(ValueError, "SOURCE_BOOK_OR_INDEX_MISMATCH"):
            self.build()

    def test_unbound_paper_scope_retains_null_directory_and_count(self):
        self.review["unbound_scopes"] = [{"scope_id": "extra-paper", "directory_id": None, "question_count": None,
            "question_pages": [1], "answer_pages": [],
            "source_evidence": [{"viewer_page": 1, "source_sha256": m.sha(self.image)}]}]
        result = self.build()
        self.assertEqual(result["summary"]["unbound_source_scopes"], 1)
        self.assertIsNone(result["unbound_scopes"][0]["question_count"])
        self.review["unbound_scopes"][0]["question_count"] = 25
        with self.assertRaisesRegex(ValueError, "UNBOUND_SCOPE_MUST_NOT_FABRICATE_DIRECTORY_OR_COUNT"):
            self.build()

    def test_evidence_row_from_another_page_rejected_after_rehash(self):
        value = self.mapped()
        ocr = self.root / "ocr.json"
        ocr.write_text(json.dumps({"book_id": "synthetic", "viewer_page": 2, "source_sha256": m.sha(self.image), "rows": []}))
        value["source_evidence"][0].update(ocr_path=str(ocr), ocr_sha256=m.sha(ocr))
        with self.assertRaisesRegex(ValueError, "OCR_SOURCE_MISMATCH"):
            self.build()


if __name__ == "__main__":
    unittest.main()
