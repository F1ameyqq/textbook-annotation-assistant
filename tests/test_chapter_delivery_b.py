import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_chapter_delivery_b import check_delivery, input_contract, evidence_binding
from tools.report_source_coverage_b import DEFAULT_DESCRIPTOR, DEFAULT_EVALUATION


ROOT = Path(__file__).resolve().parents[1]


class ChapterDeliveryGateTests(unittest.TestCase):
    def _write_pair(self, directory: Path, manifest: dict, candidate: dict):
        if isinstance(candidate.get("checks"), dict):
            candidate["checks"].setdefault("binding", evidence_binding(manifest, candidate))
        manifest_path = directory / "manifest.json"
        candidate_path = directory / "candidate.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        return manifest_path, candidate_path

    def bound_pair(self):
        manifest = {"schema": "chapter-delivery-b/1", "book_id": "b", "chapter_id": "ch", "toc_entry_id": "toc", "complete": True,
            "pages": [{"page_id": "p", "asset_id": "x", "sha256": "a"*64, "role": "question", "complete_page": True},
                      {"page_id": "a", "asset_id": "y", "sha256": "b"*64, "role": "answer", "complete_page": True}],
            "questions": [{"question_id": "q", "page_ids": ["p"], "material_ids": []}],
            "answers": [{"answer_id": "ans", "question_id": "q", "page_ids": ["a"]}], "materials": []}
        candidate = {"schema": "chapter-candidate-b/1", "book_id": "b", "chapter_id": "ch",
            "source_pages": [{"page_id": r["page_id"], "asset_id": r["asset_id"], "sha256": r["sha256"], "observed_scope": "FULL_PAGE"} for r in manifest["pages"]],
            "questions": [dict(manifest["questions"][0], content_status="READY")],
            "answers": [dict(manifest["answers"][0], content_status="READY")], "materials": [],
            "checks": {"status": "PASS", "unresolved_count": 0},
            "human_review": {"status": "COMPLETE", "reviewer_ids": ["r"], "reviewed_question_ids": ["q"], "reviewed_answer_ids": ["ans"]}}
        candidate["checks"]["binding"] = evidence_binding(manifest, candidate)
        return manifest, candidate

    def test_unbound_or_stale_checks_cannot_pass(self):
        for change in ("missing", "manifest", "content", "unknown_ref"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                manifest, candidate = self.bound_pair()
                if change == "missing":
                    candidate["checks"]["binding"] = None
                elif change == "manifest":
                    manifest["toc_entry_id"] = "changed"
                elif change == "content":
                    candidate["questions"][0]["text"] = "changed text"
                else:
                    candidate["checks"]["stale_ref"] = {"revision": 1}
                result = check_delivery(*self._write_pair(Path(temp), manifest, candidate))
                self.assertNotEqual(result["machine_evidence_decision"], "PASS")
                self.assertTrue(any("checks:" in g for g in result["gaps"]))
                self.assertEqual(result["decision"], "HOLD")

    def test_page_roles_and_asset_aliases_cannot_pass_even_with_fresh_binding(self):
        for change in ("roles", "same_asset", "same_bytes", "missing_asset"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                manifest, candidate = self.bound_pair()
                if change == "roles":
                    manifest["pages"][0]["role"], manifest["pages"][1]["role"] = "answer", "question"
                elif change == "missing_asset":
                    del manifest["pages"][1]["asset_id"]
                else:
                    field = "asset_id" if change == "same_asset" else "sha256"
                    manifest["pages"][1][field] = manifest["pages"][0][field]
                    candidate["source_pages"][1][field] = manifest["pages"][0][field]
                candidate["checks"]["binding"] = evidence_binding(manifest, candidate)
                result = check_delivery(*self._write_pair(Path(temp), manifest, candidate))
                self.assertEqual(result["machine_evidence_decision"], "HOLD")

    def test_incomplete_or_empty_reviewer_claim_is_explicit_partial(self):
        for change in ("status", "reviewers", "absent"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                manifest, candidate = self.bound_pair()
                if change == "status":
                    candidate["human_review"]["status"] = "INCOMPLETE"
                elif change == "reviewers":
                    candidate["human_review"]["reviewer_ids"] = []
                else:
                    del candidate["human_review"]
                result = check_delivery(*self._write_pair(Path(temp), manifest, candidate))
                self.assertEqual(result["machine_evidence_decision"], "PARTIAL")
                self.assertTrue(any("human review claim:" in g for g in result["gaps"]))
                self.assertEqual(result["decision"], "HOLD")

    def test_contract_declares_denominator_identity_and_independent_review(self):
        contract = input_contract()
        self.assertIn("complete must be true", contract["manifest"]["denominator"])
        self.assertIn("machine_evidence_decision", contract["output"])
        self.assertIn("source_pages", contract["candidate"]["required"])

    def test_cli_can_show_contract_without_input_files(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_chapter_delivery_b.py"), "--contract"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("machine_evidence_decision", json.loads(result.stdout)["output"])

    def test_real_local_evidence_is_negative_and_stays_hold(self):
        descriptor = json.loads(DEFAULT_DESCRIPTOR.read_text(encoding="utf-8"))
        evaluation = json.loads(DEFAULT_EVALUATION.read_text(encoding="utf-8"))
        pages = [
            {"page_id": a["asset_id"], "role": "question", "asset_id": a["asset_id"], "sha256": a["sha256"], "complete_page": True}
            for a in descriptor["assets"]
        ]
        manifest = {
            "schema": "chapter-delivery-b/1", "book_id": descriptor["book_id"], "chapter_id": "UNKNOWN",
            "toc_entry_id": None, "complete": False, "pages": pages, "questions": [], "answers": [], "materials": [],
        }
        candidate = {
            "schema": "chapter-candidate-b/1", "book_id": evaluation["book_id"], "chapter_id": "UNKNOWN",
            "source_pages": [], "questions": [], "answers": [], "materials": [],
            "observed_local_candidate_counts": {"questions": 34, "answers": 66},
            "checks": {"status": "HOLD", "unresolved_count": 127},
            "human_review": {"status": "INCOMPLETE", "reviewer_ids": []},
        }
        with tempfile.TemporaryDirectory() as temp:
            manifest_path, candidate_path = self._write_pair(Path(temp), manifest, candidate)
            report = check_delivery(manifest_path, candidate_path)
        self.assertEqual(report["decision"], "HOLD")
        self.assertTrue(any("denominator" in gap for gap in report["gaps"]))
        self.assertTrue(any("toc_entry_id" in gap for gap in report["gaps"]))
        self.assertTrue(any("human review" in gap for gap in report["gaps"]))
        self.assertNotEqual(report["comparisons"]["questions"]["expected"], 34)

    def test_complete_machine_claim_never_becomes_g2_acceptance(self):
        manifest = {
            "schema": "chapter-delivery-b/1", "book_id": "book", "chapter_id": "chapter", "toc_entry_id": "toc-1", "complete": True,
            "pages": [{"page_id": "p1", "role": "question", "asset_id": "asset1", "sha256": "a" * 64, "complete_page": True},
                      {"page_id": "p2", "role": "answer", "asset_id": "asset2", "sha256": "b" * 64, "complete_page": True}],
            "questions": [{"question_id": "q1", "page_ids": ["p1"], "material_ids": []}],
            "answers": [{"answer_id": "ans1", "question_id": "q1", "page_ids": ["p2"]}], "materials": [],
        }
        candidate = {
            "schema": "chapter-candidate-b/1", "book_id": "book", "chapter_id": "chapter",
            "source_pages": [{"page_id": "p1", "asset_id": "asset1", "sha256": "a" * 64, "observed_scope": "FULL_PAGE"},
                             {"page_id": "p2", "asset_id": "asset2", "sha256": "b" * 64, "observed_scope": "FULL_PAGE"}],
            "questions": [{"question_id": "q1", "page_ids": ["p1"], "material_ids": [], "content_status": "READY"}],
            "answers": [{"answer_id": "ans1", "question_id": "q1", "page_ids": ["p2"], "content_status": "READY"}], "materials": [],
            "checks": {"status": "PASS", "unresolved_count": 0},
            "human_review": {"status": "COMPLETE", "reviewer_ids": ["r1", "r2"], "reviewed_question_ids": ["q1"], "reviewed_answer_ids": ["ans1"], "manifest_sha256": "self-reported"},
        }
        with tempfile.TemporaryDirectory() as temp:
            paths = self._write_pair(Path(temp), manifest, candidate)
            report = check_delivery(*paths)
        self.assertEqual(report["machine_evidence_decision"], "PASS")
        self.assertEqual(report["declared_human_review_claim"], "COMPLETE_CLAIMED")
        self.assertEqual(report["decision"], "HOLD")
        self.assertEqual(report["g2_acceptance"], "HOLD")
        candidate["answers"][0]["page_ids"] = ["p1"]
        with tempfile.TemporaryDirectory() as temp:
            paths = self._write_pair(Path(temp), manifest, candidate)
            wrong_answer_page = check_delivery(*paths)
        self.assertEqual(wrong_answer_page["comparisons"]["answers"]["conflicts"], ["ans1"])
        self.assertEqual(wrong_answer_page["machine_evidence_decision"], "PARTIAL")

    def test_malformed_json_and_duplicate_keys_return_hold_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "manifest.json"
            candidate = Path(temp) / "candidate.json"
            manifest.write_text('{"schema":', encoding="utf-8")
            candidate.write_text('{"schema":"chapter-candidate-b/1","schema":"chapter-candidate-b/1"}', encoding="utf-8")
            report = check_delivery(manifest, candidate)
        self.assertEqual(report["decision"], "HOLD")
        self.assertEqual(report["machine_evidence_decision"], "HOLD")
        self.assertTrue(any("malformed JSON" in gap for gap in report["gaps"]))

    def test_malformed_nested_rows_and_reference_types_return_hold_without_crashing(self):
        manifest = {
            "schema": "chapter-delivery-b/1", "book_id": "book", "chapter_id": "chapter", "toc_entry_id": "toc", "complete": True,
            "pages": [{"page_id": "p", "role": [], "asset_id": "asset", "sha256": "sha", "complete_page": True}],
            "questions": [{"question_id": "q", "page_ids": [["p"]], "material_ids": []}],
            "answers": [], "materials": [],
        }
        candidate = {
            "schema": "chapter-candidate-b/1", "book_id": "book", "chapter_id": "chapter",
            "source_pages": [{"page_id": "p", "asset_id": "asset", "sha256": "sha", "observed_scope": "FULL_PAGE"}],
            "questions": [{"question_id": "q", "page_ids": [["p"]], "material_ids": [], "content_status": "READY"}],
            "answers": [], "materials": [], "checks": {"status": [], "unresolved_count": False}, "human_review": [],
        }
        with tempfile.TemporaryDirectory() as temp:
            paths = self._write_pair(Path(temp), manifest, candidate)
            report = check_delivery(*paths)
        self.assertEqual(report["decision"], "HOLD")
        self.assertEqual(report["machine_evidence_decision"], "HOLD")
        self.assertTrue(any("array of non-empty strings" in gap for gap in report["gaps"]))
        self.assertTrue(any("unknown role" in gap for gap in report["gaps"]))
    def test_partial_inventory_cannot_pass_and_manual_review_absence_is_hold(self):
        manifest = {
            "schema": "chapter-delivery-b/1", "book_id": "book", "chapter_id": "chapter", "toc_entry_id": "toc-1", "complete": True,
            "pages": [{"page_id": "p1", "role": "question", "asset_id": "a1", "sha256": "abc", "complete_page": True}],
            "questions": [{"question_id": "q1", "page_ids": ["p1"], "material_ids": []}],
            "answers": [{"answer_id": "a1", "question_id": "q1"}], "materials": [],
        }
        candidate = {
            "schema": "chapter-candidate-b/1", "book_id": "book", "chapter_id": "chapter",
            "source_pages": [{"page_id": "p1", "asset_id": "a1", "sha256": "abc", "observed_scope": "FULL_PAGE"}],
            "questions": [], "answers": [], "materials": [], "checks": {"status": "PASS", "unresolved_count": 0},
            "human_review": {"status": "INCOMPLETE", "reviewer_ids": []},
        }
        with tempfile.TemporaryDirectory() as temp:
            paths = self._write_pair(Path(temp), manifest, candidate)
            report = check_delivery(*paths)
        self.assertEqual(report["decision"], "HOLD")
        self.assertEqual(report["comparisons"]["questions"]["missing"], ["q1"])
        self.assertEqual(report["comparisons"]["answers"]["missing"], ["a1"])

    def test_wrong_source_identity_is_reported(self):
        manifest = {
            "schema": "chapter-delivery-b/1", "book_id": "book", "chapter_id": "chapter", "toc_entry_id": "toc", "complete": True,
            "pages": [{"page_id": "p", "role": "question", "asset_id": "asset", "sha256": "a" * 64, "complete_page": True}],
            "questions": [], "answers": [], "materials": [],
        }
        candidate = {
            "schema": "chapter-candidate-b/1", "book_id": "book", "chapter_id": "chapter",
            "source_pages": [{"page_id": "p", "asset_id": "asset", "sha256": "b" * 64, "observed_scope": "FULL_PAGE"}],
            "questions": [], "answers": [], "materials": [], "checks": {"status": "PASS", "unresolved_count": 0},
            "human_review": {"status": "INCOMPLETE", "reviewer_ids": []},
        }
        with tempfile.TemporaryDirectory() as temp:
            paths = self._write_pair(Path(temp), manifest, candidate)
            report = check_delivery(*paths)
        self.assertEqual(report["decision"], "HOLD")
        self.assertEqual(report["comparisons"]["pages"]["conflicts"], ["p"])


if __name__ == "__main__":
    unittest.main()
