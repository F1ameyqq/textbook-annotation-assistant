from __future__ import annotations

import json
import hashlib
import copy
from pathlib import Path
import tempfile
import unittest

from tools.adapt_chapter_candidate_b import adapt


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/runs/46007447-region-automatic-v1/graph.json"
CHECK = ROOT / "data/runs/46007447-region-automatic-v1/check.json"


class ChapterCandidateAdapterTests(unittest.TestCase):
    def write_pair(self, folder: Path, graph: dict, check: dict | None = None):
        graph["content_hash"] = hashlib.sha256(json.dumps(graph["payload"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        graph_path = folder / "graph.json"
        check_path = folder / "check.json"
        if check is None:
            check = {"schema_version": "b-check-trial/0.7", "artifact_id": "check-1", "revision": 1,
                "book_id": graph["book_id"], "scope_id": graph["scope_id"],
                "payload": {"graph_ref": {k: graph[k] for k in ("artifact_id", "revision", "content_hash")},
                    "decision": "HOLD", "business_acceptance": False, "transcription_verified": False,
                    "issues": [{"code": "OPEN"}, {"code": "OPEN"}]}}
        check["content_hash"] = hashlib.sha256(json.dumps(check["payload"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        graph_path.write_text(json.dumps(graph), encoding="utf-8")
        check_path.write_text(json.dumps(check), encoding="utf-8")
        return graph_path, check_path

    def synthetic_graph(self):
        return {"schema_version": "b-graph-trial/0.7", "artifact_id": "graph-1", "revision": 2,
            "content_hash": "a" * 64, "book_id": "synthetic-book", "scope_id": "observed-sample",
            "payload": {"decision": "HOLD", "business_acceptance": False, "transcription_verified": False,
                "questions": [
                    {"question_id": "q-internal-1", "asset_id": "observed-asset-1", "candidate_answer_ids": ["a-internal-1"], "verification_status": "UNVERIFIED"},
                    {"question_id": "q-internal-2", "asset_id": "observed-asset-2", "candidate_answer_ids": ["a-internal-2"], "verification_status": "UNVERIFIED"}],
                "answers": [
                    {"answer_id": "a-internal-1", "asset_id": "answer-asset-observed", "verification_status": "UNVERIFIED"},
                    {"answer_id": "a-internal-2", "asset_id": "answer-asset-observed", "verification_status": "UNVERIFIED"},
                    {"answer_id": "a-unmatched", "asset_id": "unknown-answer-asset", "verification_status": "UNVERIFIED"}]}}

    def test_synthetic_pair_projects_only_open_candidates_and_unknown_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            graph = self.synthetic_graph()
            graph_path, check_path = self.write_pair(Path(temp), graph)
            candidate = adapt(graph_path, check_path)
        self.assertEqual(candidate["schema"], "chapter-candidate-b/1")
        self.assertEqual(candidate["book_id"], "synthetic-book")
        self.assertIsNone(candidate["chapter_id"])
        self.assertEqual(candidate["candidate_state"], "PARTIAL")
        self.assertEqual(candidate["coverage_status"]["chapter_denominator"], "UNKNOWN")
        self.assertEqual(candidate["source_pages"], [])
        self.assertEqual(len(candidate["questions"]), 2)
        self.assertEqual(len(candidate["answers"]), 3)
        self.assertEqual(candidate["checks"], {"status": "HOLD", "unresolved_count": 2})
        self.assertTrue(all(row["content_status"] == "OPEN" for row in candidate["questions"] + candidate["answers"]))
        self.assertTrue(all(row["page_ids"] == [] and row["source_page_status"] == "UNKNOWN" for row in candidate["answers"]))
        self.assertTrue(all(row["page_ids"] == [] and row["source_page_status"] == "UNKNOWN" for row in candidate["questions"]))
        self.assertEqual(candidate["coverage_status"]["material_inventory"], "UNKNOWN")
        self.assertEqual(candidate["human_review"]["status"], "INCOMPLETE")

    def test_check_must_bind_exact_graph_ref(self):
        with tempfile.TemporaryDirectory() as temp:
            graph = self.synthetic_graph()
            check = {"schema_version": "b-check-trial/0.7", "artifact_id": "check-1", "revision": 1,
                "book_id": graph["book_id"], "scope_id": graph["scope_id"],
                "payload": {"graph_ref": {k: graph[k] for k in ("artifact_id", "revision", "content_hash")},
                    "decision": "HOLD", "business_acceptance": False, "transcription_verified": False, "issues": []}}
            check["payload"]["graph_ref"]["content_hash"] = "0" * 64
            graph_path, check_path = self.write_pair(Path(temp), graph, check)
            with self.assertRaisesRegex(ValueError, "graph_ref"):
                adapt(graph_path, check_path)

    def test_geometry_version_stays_open_and_mixed_or_unknown_versions_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            graph = self.synthetic_graph()
            graph["schema_version"] = "b-graph-trial/0.8"
            paths = self.write_pair(Path(temp), graph)
            with self.assertRaisesRegex(ValueError, "schema"):
                adapt(*paths)
            check = json.loads(paths[1].read_text(encoding="utf-8"))
            check["schema_version"] = "b-check-trial/0.8"
            paths = self.write_pair(Path(temp), graph, check)
            candidate = adapt(*paths)
            self.assertEqual(candidate["candidate_state"], "PARTIAL")
            self.assertEqual(candidate["checks"]["status"], "HOLD")
            self.assertEqual(candidate["human_review"]["status"], "INCOMPLETE")
            self.assertEqual(candidate["source_basis"]["graph_schema"], "b-graph-trial/0.8")
            graph["schema_version"] = "b-graph-trial/0.9"
            paths = self.write_pair(Path(temp), graph, check)
            with self.assertRaisesRegex(ValueError, "unsupported graph schema"):
                adapt(*paths)

    def test_acceptance_or_verified_flags_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            graph_path = Path(temp) / "graph.json"
            check_path = Path(temp) / "check.json"
            graph = self.synthetic_graph()
            graph["payload"]["business_acceptance"] = True
            graph_path, check_path = self.write_pair(Path(temp), graph)
            with self.assertRaisesRegex(ValueError, "business_acceptance"):
                adapt(graph_path, check_path)

    def test_candidate_relationship_does_not_fill_answer_source_page(self):
        with tempfile.TemporaryDirectory() as temp:
            graph = self.synthetic_graph()
            graph_path, check_path = self.write_pair(Path(temp), graph)
            candidate = adapt(graph_path, check_path)
        linked = [row for row in candidate["answers"] if row["relationship_status"] == "CANDIDATE_OPEN"]
        unlinked = [row for row in candidate["answers"] if row["relationship_status"] == "UNKNOWN"]
        self.assertEqual(len(linked), 2)
        self.assertEqual(len(unlinked), 1)
        self.assertTrue(all(row["page_ids"] == [] for row in linked + unlinked))
        self.assertTrue(all(row["question_id"] is None for row in unlinked))

    def test_duplicate_dangling_and_malformed_links_are_rejected(self):
        for case in ("duplicate", "dangling", "string_links", "repeated_link", "empty_id"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                graph = self.synthetic_graph()
                if case == "duplicate":
                    graph["payload"]["answers"].append(copy.deepcopy(graph["payload"]["answers"][0]))
                elif case == "dangling":
                    graph["payload"]["questions"][0]["candidate_answer_ids"] = ["absent"]
                elif case == "string_links":
                    graph["payload"]["questions"][0]["candidate_answer_ids"] = "a-internal-1"
                elif case == "repeated_link":
                    graph["payload"]["questions"][0]["candidate_answer_ids"] *= 2
                else:
                    graph["payload"]["answers"][0]["answer_id"] = ""
                paths = self.write_pair(Path(temp), graph)
                with self.assertRaises(ValueError):
                    adapt(*paths)

    def test_changed_payload_without_new_hash_and_duplicate_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_pair(Path(temp), self.synthetic_graph())
            raw = json.loads(paths[0].read_text())
            raw["payload"]["answers"].pop()
            paths[0].write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "content_hash"):
                adapt(*paths)
            paths = self.write_pair(Path(temp), self.synthetic_graph())
            paths[0].write_text(paths[0].read_text().replace('{', '{"revision":1,', 1))
            with self.assertRaisesRegex(ValueError, "duplicate JSON"):
                adapt(*paths)

    @unittest.skipUnless(GRAPH.is_file() and CHECK.is_file(), "ignored local G07/Check07 objects are unavailable")
    def test_local_fixed_g07_check07_negative_case_when_run_objects_are_available(self):
        candidate = adapt(GRAPH, CHECK)
        self.assertEqual(candidate["book_id"], "46007447")
        self.assertIsNone(candidate["chapter_id"])
        self.assertEqual(candidate["candidate_state"], "PARTIAL")
        self.assertEqual(candidate["source_pages"], [])
        self.assertEqual((len(candidate["questions"]), len(candidate["answers"])), (34, 66))
        self.assertEqual(candidate["checks"], {"status": "HOLD", "unresolved_count": 127})
        self.assertEqual(sum(row["relationship_status"] == "CANDIDATE_OPEN" for row in candidate["answers"]), 34)
        self.assertEqual(sum(row["relationship_status"] == "UNKNOWN" for row in candidate["answers"]), 32)
        self.assertTrue(all(not row["page_ids"] for row in candidate["answers"]))


if __name__ == "__main__":
    unittest.main()
