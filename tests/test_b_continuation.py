"""Explicit cross-page proof tests; positive cases are synthetic, not book gold."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from annotation.recognition.baseline import digest
from annotation.recognition.answer_assembly import assemble_answers
from annotation.recognition.continuation import (
    build_adjacency_receipt, build_continuation_proof, validate_continuation)
from annotation.recognition.offline import assemble
from verify_continuation_b import load_continuation_fixture, prepare_continuation


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


def reference(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def graph_for(evidence):
    answers, issues, coverage = assemble_answers(evidence, lambda role, anchor: role + "-" + digest(anchor)[:24])
    return rehash({"schema_version": "b-graph-trial/0.2", "artifact_id": "synthetic-graph",
                   "revision": 1, "book_id": evidence["book_id"], "scope_id": evidence["scope_id"],
                   "run_id": evidence["run_id"], "input_refs": [reference(evidence)],
                   "payload": {"questions": [], "answers": answers, "issues": issues,
                               "answer_coverage": coverage, "platform_actions": []}})


def synthetic_pair():
    path = ["Synthetic chapter", "Synthetic lesson"]
    pages, contexts = [], {}
    for asset_id, index, column, rows in [
            ("synthetic-100", 100, 1, [("8.解：由已知条件可得", 1490), ("下一步求得x=", 1518)]),
            ("synthetic-101", 101, 0, [("13，因此继续验证条件。", 120), ("答：长13cm。", 140), ("9.D", 165)])]:
        source = {"asset_id": asset_id, "sha256": ("a" if index == 100 else "b") * 64,
                  "width": 1148, "height": 1621, "reading_order": index - 100,
                  "external_refs": {"resource_index": index, "viewer_page": index + 1}}
        x = 610 if column else 59
        lines = [{"line_id": asset_id + "/ocr/" + str(i), "text": text,
                  "bbox": [x, y, x + 450, y + 18], "score": .99,
                  "location": {"column": column, "window_index": 0, "section_path": path}}
                 for i, (text, y) in enumerate(rows)]
        pages.append({"asset_id": asset_id, "source": source, "page_role": "answer",
                      "layout": {"mode": "two_columns", "cut_x": 574},
                      "ocr_lines": lines, "answer_detail_lines": []})
        contexts[asset_id] = {"role": "answer", "windows": [
            {"column": column, "y_range": [120, 1540], "path": path}]}
    evidence = rehash({"schema_version": "b-evidence-trial/0.2", "artifact_id": "synthetic-evidence",
                       "revision": 1, "book_id": "synthetic-book", "scope_id": "synthetic-cross-page",
                       "run_id": "synthetic-run", "payload": {"pages": pages, "context": {"pages": contexts}}})
    return evidence, graph_for(evidence)


def proof_for(evidence, graph, **changes):
    answer = next(a for a in graph["payload"]["answers"] if a["printed_number"] == "8")
    args = {"from_answer_id": answer["answer_id"], "to_asset_id": "synthetic-101",
            "to_line_ids": ["synthetic-101/ocr/0", "synthetic-101/ocr/1"],
            "source_tail_line_id": "synthetic-100/ocr/1",
            "adjacency_receipt": build_adjacency_receipt(
                evidence, "synthetic-100", "synthetic-101",
                observation_refs=["synthetic-test-observation:" + digest("mapping100to101")],
                reference_quality="SYNTHETIC_TEST"),
            "review_basis": {"kind": "EXPLICIT_SOURCE_REVIEW", "reference_quality": "SYNTHETIC_TEST",
                             "source_tail_open": True, "target_prefix_unanchored": True,
                             "source_tail_line_id": "synthetic-100/ocr/1",
                             "reason": "Synthetic test: x= at page edge continues with 13 on next page."}}
    args.update(changes)
    return build_continuation_proof(evidence, graph, **args)


class SyntheticContinuationRegression(unittest.TestCase):
    def setUp(self):
        self.evidence, self.graph = synthetic_pair()

    def report(self, proof=None):
        return validate_continuation(self.evidence, self.graph,
                                     proof or proof_for(self.evidence, self.graph))["payload"]

    def codes(self, proof=None):
        report = self.report(proof)
        self.assertFalse(report["accepted"])
        self.assertIsNone(report["verified_plan"])
        return {i["code"] for i in report["issues"]}

    def rebuild(self):
        rehash(self.evidence)
        self.graph = graph_for(self.evidence)

    def test_synthetic_explicit_proof_produces_plan_without_mutation_or_acceptance_claim(self):
        proof = proof_for(self.evidence, self.graph)
        originals = copy.deepcopy((self.evidence, self.graph, proof))
        report = self.report(proof)
        self.assertTrue(report["accepted"], report["issues"])
        self.assertEqual(report["status"], "VALIDATED_PROPOSAL")
        self.assertEqual(report["decision"], "HOLD")
        self.assertEqual(report["reference_quality"], "SYNTHETIC_TEST")
        plan = report["verified_plan"]
        answer = next(a for a in self.graph["payload"]["answers"] if a["printed_number"] == "8")
        self.assertEqual(plan["source_fragment_ids_preserved"], [f["fragment_id"] for f in answer["fragments"]])
        self.assertEqual(plan["target_line_ids"], ["synthetic-101/ocr/0", "synthetic-101/ocr/1"])
        self.assertEqual(plan["next_boundary_ref"], "synthetic-101/ocr/2")
        self.assertEqual(len(plan["target_regions"]), 2)
        self.assertNotIn("bbox", plan)
        self.assertEqual(plan["verification_status"], "UNVERIFIED")
        self.assertFalse(plan["business_acceptance"])
        self.assertEqual(plan["platform_actions"], [])
        self.assertEqual((self.evidence, self.graph, proof), originals)

    def test_recovery_evidence_and_graph_versions_are_supported_explicitly(self):
        self.evidence["schema_version"] = "b-evidence-trial/0.3"
        self.graph["schema_version"] = "b-graph-trial/0.3"
        self.assertTrue(self.report()["accepted"])

    def test_reading_order_adjacent_but_observed_resource_gap_is_rejected(self):
        self.evidence["payload"]["pages"][1]["source"]["external_refs"]["resource_index"] = 103
        self.rebuild()
        self.assertIn("CONTINUATION_SOURCE_PAGE_GAP", self.codes())

    def test_missing_observed_resource_index_cannot_use_reading_order_as_substitute(self):
        del self.evidence["payload"]["pages"][1]["source"]["external_refs"]["resource_index"]
        self.rebuild()
        self.assertIn("CONTINUATION_RESOURCE_MAPPING_MISSING", self.codes())

    def test_wrong_asset_hash_in_proof_is_rejected_even_with_valid_payload_hash(self):
        proof = proof_for(self.evidence, self.graph)
        proof["payload"]["to_asset"]["sha256"] = "0" * 64
        rehash(proof)
        self.assertIn("CONTINUATION_ASSET_IDENTITY_MISMATCH", self.codes(proof))

    def test_source_descriptor_change_invalidates_existing_mapping_receipt(self):
        receipt = proof_for(self.evidence, self.graph)["payload"]["adjacency_receipt"]
        self.evidence["payload"]["pages"][1]["source"]["sha256"] = "c" * 64
        self.rebuild()
        proof = proof_for(self.evidence, self.graph, adjacency_receipt=receipt)
        self.assertIn("CONTINUATION_STALE_MAPPING_RECEIPT", self.codes(proof))

    def test_graph_revision_and_evidence_revision_invalidate_old_proof(self):
        proof = proof_for(self.evidence, self.graph)
        self.graph["revision"] += 1
        self.assertIn("CONTINUATION_STALE_PROOF", self.codes(proof))
        self.evidence["revision"] += 1
        self.assertIn("CONTINUATION_GRAPH_EVIDENCE_REVISION_MISMATCH", self.codes(proof))

    def test_cross_lesson_same_question_number_does_not_supply_continuity(self):
        other = ["Synthetic chapter", "Another lesson"]
        for line in self.evidence["payload"]["pages"][1]["ocr_lines"]:
            line["location"]["section_path"] = other
        self.evidence["payload"]["context"]["pages"]["synthetic-101"]["windows"][0]["path"] = other
        self.rebuild()
        self.assertIn("CONTINUATION_SECTION_CHANGED", self.codes())

    def test_new_repeated_primary_one_on_target_is_rejected(self):
        self.evidence["payload"]["pages"][1]["ocr_lines"][0]["text"] = "1.D"
        self.rebuild()
        self.assertIn("CONTINUATION_TARGET_HAS_PRIMARY_OR_HEADING", self.codes())

    def test_non_tail_source_anchor_cannot_extend_an_earlier_fragment(self):
        proof = proof_for(self.evidence, self.graph, source_tail_line_id="synthetic-100/ocr/0")
        self.assertIn("CONTINUATION_NON_TAIL_LINE", self.codes(proof))

    def test_already_closed_visible_tail_is_rejected(self):
        self.evidence["payload"]["pages"][0]["ocr_lines"][1]["text"] = "答：长13cm。"
        self.rebuild()
        self.assertIn("CONTINUATION_VISIBLE_TAIL_ALREADY_CLOSED", self.codes())

    def test_non_edge_source_and_non_top_target_are_rejected(self):
        page = self.evidence["payload"]["pages"][0]
        page["ocr_lines"][0]["bbox"][1::2] = [800, 818]
        page["ocr_lines"][1]["bbox"][1::2] = [830, 848]
        self.rebuild()
        self.assertIn("CONTINUATION_SOURCE_EDGE_NOT_PROVEN", self.codes())
        self.evidence, self.graph = synthetic_pair()
        for line in self.evidence["payload"]["pages"][1]["ocr_lines"]:
            line["bbox"][1] += 400
            line["bbox"][3] += 400
        self.rebuild()
        self.assertIn("CONTINUATION_TARGET_TOP_NOT_PROVEN", self.codes())

    def test_prefix_cannot_be_truncated_or_repeated(self):
        proof = proof_for(self.evidence, self.graph, to_line_ids=["synthetic-101/ocr/0"])
        self.assertIn("CONTINUATION_PREFIX_INCOMPLETE", self.codes(proof))
        proof = proof_for(self.evidence, self.graph, to_line_ids=["synthetic-101/ocr/0"] * 2)
        self.assertIn("CONTINUATION_TARGET_LINE_REUSED", self.codes(proof))

    def test_target_prefix_must_start_at_first_visible_body_line(self):
        proof = proof_for(self.evidence, self.graph, to_line_ids=["synthetic-101/ocr/1"])
        self.assertIn("CONTINUATION_TARGET_NOT_LEADING_PREFIX", self.codes(proof))

    def test_target_ownership_blocks_even_if_evidence_is_unanchored(self):
        row = next(r for r in self.graph["payload"]["answer_coverage"] if r["line_id"] == "synthetic-101/ocr/0")
        row.update(status="CONSUMED", answer_ids=["another-answer"])
        rehash(self.graph)
        self.assertIn("CONTINUATION_TARGET_ALREADY_OWNED_OR_UNACCOUNTED", self.codes())

    def test_plain_confirmed_flag_is_not_an_adjacency_receipt(self):
        receipt = proof_for(self.evidence, self.graph)["payload"]["adjacency_receipt"]
        receipt["payload"] = {"confirmed": True}
        rehash(receipt)
        proof = proof_for(self.evidence, self.graph, adjacency_receipt=receipt)
        self.assertIn("CONTINUATION_MAPPING_OBSERVATION_MISMATCH", self.codes(proof))

    def test_cross_book_answer_and_missing_explicit_review_are_rejected(self):
        answer = next(a for a in self.graph["payload"]["answers"] if a["printed_number"] == "8")
        answer["book_id"] = "another-book"
        rehash(self.graph)
        self.assertIn("CONTINUATION_ANSWER_SOURCE_MISMATCH", self.codes())
        self.evidence, self.graph = synthetic_pair()
        proof = proof_for(self.evidence, self.graph, review_basis={"confirmed": True})
        self.assertIn("CONTINUATION_EXPLICIT_REVIEW_MISSING", self.codes(proof))

    def test_tampered_source_fragment_is_not_preserved_as_valid_plan(self):
        answer = next(a for a in self.graph["payload"]["answers"] if a["printed_number"] == "8")
        answer["fragments"][0]["text"] = "invented formula"
        rehash(self.graph)
        self.assertIn("CONTINUATION_SOURCE_FRAGMENT_MISMATCH", self.codes())

    def test_missing_target_asset_reports_issue_without_key_error(self):
        receipt = build_adjacency_receipt(self.evidence, "synthetic-100", "not-collected",
                                         observation_refs=["synthetic:mapping"], reference_quality="SYNTHETIC_TEST")
        proof = proof_for(self.evidence, self.graph, to_asset_id="not-collected",
                          to_line_ids=["not-collected/ocr/0"], adjacency_receipt=receipt)
        self.assertIn("CONTINUATION_TARGET_ASSET_MISSING", self.codes(proof))

    def test_repeated_image_bytes_cannot_be_two_continuation_pages(self):
        self.evidence["payload"]["pages"][1]["source"]["sha256"] = "a" * 64
        self.rebuild()
        self.assertIn("CONTINUATION_DUPLICATE_SOURCE_IMAGE", self.codes())

    def test_invalid_artifact_and_malformed_snapshot_reject_without_plan(self):
        proof = proof_for(self.evidence, self.graph)
        proof["payload"]["source_tail_line_id"] = "unhashed-change"
        self.assertIn("CONTINUATION_PROOF_INVALID", self.codes(proof))
        proof = proof_for(self.evidence, self.graph)
        proof["payload"]["to_asset"] = None
        rehash(proof)
        self.assertIn("CONTINUATION_PROOF_SHAPE_INVALID", self.codes(proof))

    def test_review_and_reflection_heading_is_a_hard_boundary(self):
        self.evidence["payload"]["pages"][1]["ocr_lines"][2]["text"] = "回顾与思考（一） 勾股定理"
        self.rebuild()
        report = self.report()
        self.assertTrue(report["accepted"], report["issues"])
        self.assertEqual(report["verified_plan"]["next_boundary_ref"], "synthetic-101/ocr/2")
        proof = proof_for(self.evidence, self.graph,
                          to_line_ids=["synthetic-101/ocr/0", "synthetic-101/ocr/1", "synthetic-101/ocr/2"])
        self.assertIn("CONTINUATION_TARGET_HAS_PRIMARY_OR_HEADING", self.codes(proof))

    def test_large_figure_label_gap_is_not_silently_accepted_as_complete_prefix(self):
        page = self.evidence["payload"]["pages"][1]
        diagram_label = copy.deepcopy(page["ocr_lines"][1])
        diagram_label.update(line_id="synthetic-101/ocr/diagram", text="图5")
        diagram_label["bbox"] = [149, 350, 175, 368]
        page["ocr_lines"][2]["bbox"][1::2] = [442, 464]
        page["ocr_lines"][2]["text"] = "回顾与思考（一）"
        page["ocr_lines"].insert(2, diagram_label)
        self.rebuild()
        proof = proof_for(self.evidence, self.graph,
                          to_line_ids=["synthetic-101/ocr/0", "synthetic-101/ocr/1", "synthetic-101/ocr/diagram"])
        self.assertIn("CONTINUATION_PREFIX_SPATIAL_GAP", self.codes(proof))

    def test_figure_mentions_require_extent_evidence_even_with_contiguous_ocr_lines(self):
        self.evidence["payload"]["pages"][1]["ocr_lines"][0]["text"] = "如图5，继续计算长度。"
        self.rebuild()
        self.assertIn("CONTINUATION_FIGURE_EXTENT_UNVERIFIED", self.codes())

    def test_source_tail_must_belong_to_actual_fragments_not_only_declared_line_ledger(self):
        answer = next(a for a in self.graph["payload"]["answers"] if a["printed_number"] == "8")
        answer["fragments"] = [f for f in answer["fragments"]
                               if f.get("parent_line_id") != "synthetic-100/ocr/1"]
        rehash(self.graph)
        # A fresh proof must not make the graph's stale source_line_ids true.
        codes = self.codes()
        self.assertIn("CONTINUATION_SOURCE_LEDGER_MISMATCH", codes)
        self.assertIn("CONTINUATION_TAIL_NOT_OWNED", codes)

    def test_source_tail_cannot_be_owned_by_two_answers(self):
        answer = next(a for a in self.graph["payload"]["answers"] if a["printed_number"] == "8")
        other = copy.deepcopy(answer)
        other["answer_id"] = "another-answer-owning-tail"
        self.graph["payload"]["answers"].append(other)
        rehash(self.graph)
        self.assertIn("CONTINUATION_TAIL_OWNERSHIP_CONFLICT", self.codes())

    def test_located_lines_cannot_disagree_with_authoritative_semantic_windows(self):
        for field, value in [("path", ["Other chapter", "Other lesson"]),
                             ("column", 1), ("y_range", [500, 1540])]:
            with self.subTest(window_field=field):
                self.evidence, self.graph = synthetic_pair()
                window = self.evidence["payload"]["context"]["pages"]["synthetic-101"]["windows"][0]
                window[field] = value
                self.rebuild()
                self.assertIn("CONTINUATION_TARGET_WINDOW_INCONSISTENT", self.codes())
        self.evidence, self.graph = synthetic_pair()
        self.evidence["payload"]["context"]["pages"]["synthetic-100"]["windows"][0]["path"] = ["Other lesson"]
        self.rebuild()
        self.assertIn("CONTINUATION_SOURCE_WINDOW_INCONSISTENT", self.codes())


class ObservedBookContinuationNegatives(unittest.TestCase):
    """Real source mappings; deliberately invalid proposals, never real positives."""
    def setUp(self):
        self.evidence = json.loads((ROOT / "tests/fixtures/book46007447/ocr-evidence.json").read_text(encoding="utf-8"))
        self.graph = graph_for(self.evidence)
        self.pages = {p["asset_id"]: p for p in self.evidence["payload"]["pages"]}

    def invalid_metadata_proposal(self, from_id, to_id):
        # These question pages have no source answer. Add an explicitly
        # fabricated proposal identity only to exercise real mapping/scope gates.
        page = self.pages[from_id]
        scoped = sorted((line for line in page["ocr_lines"] if line.get("location")),
                        key=lambda line: (line["location"]["column"], line["bbox"][1], line["bbox"][0]))
        tail = scoped[-1]
        fake = {"answer_id": "invalid-test-proposal", "asset_id": from_id, "book_id": self.evidence["book_id"],
                "printed_number": "unknown", "section_path": tail["location"]["section_path"],
                "fragments": [], "source_line_ids": [tail["line_id"]], "assembly_status": "OPEN",
                "boundary": {"kind": "ANSWER_PAGE_EDGE"}}
        self.graph["payload"]["answers"].append(fake)
        rehash(self.graph)
        target_lines = [line for line in self.pages[to_id]["ocr_lines"] if line.get("location")]
        target = min(target_lines, key=lambda line: (line["location"]["column"], line["bbox"][1], line["bbox"][0]))
        receipt = build_adjacency_receipt(self.evidence, from_id, to_id,
                                         observation_refs=["committed-observed-source-descriptor:" + digest(page["source"])],
                                         reference_quality="MODEL_VISUAL_DEVELOPMENT_REVIEW")
        return build_continuation_proof(self.evidence, self.graph, from_answer_id=fake["answer_id"],
                    to_asset_id=to_id, to_line_ids=[target["line_id"]], source_tail_line_id=tail["line_id"],
                    adjacency_receipt=receipt, review_basis={"kind": "EXPLICIT_SOURCE_REVIEW",
                        "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW", "source_tail_open": True,
                        "target_prefix_unanchored": True, "source_tail_line_id": tail["line_id"],
                        "reason": "Negative test only; no claim that these pages contain a cross-page answer."})

    def test_observed_12_to_14_gap_is_rejected_despite_neighboring_manifest_order(self):
        proof = self.invalid_metadata_proposal("viewer-12", "viewer-14")
        report = validate_continuation(self.evidence, self.graph, proof)["payload"]
        self.assertFalse(report["accepted"])
        self.assertIn("CONTINUATION_SOURCE_PAGE_GAP", {i["code"] for i in report["issues"]})

    def test_observed_11_to_12_changes_lesson_and_cannot_continue_by_number(self):
        proof = self.invalid_metadata_proposal("viewer-11", "viewer-12")
        report = validate_continuation(self.evidence, self.graph, proof)["payload"]
        self.assertFalse(report["accepted"])
        self.assertIn("CONTINUATION_SECTION_CHANGED", {i["code"] for i in report["issues"]})

    def test_observed_173_has_no_collected_next_answer_page(self):
        answer = next(a for a in reversed(self.graph["payload"]["answers"])
                      if a["asset_id"] == "viewer-173" and a["assembly_status"] == "OPEN")
        tail = answer["source_line_ids"][-1]
        receipt = build_adjacency_receipt(self.evidence, "viewer-173", "viewer-174",
                                         observation_refs=["committed-five-assets-only"],
                                         reference_quality="MODEL_VISUAL_DEVELOPMENT_REVIEW")
        proof = build_continuation_proof(self.evidence, self.graph,
                    from_answer_id=answer["answer_id"], to_asset_id="viewer-174", to_line_ids=["viewer-174/unknown"],
                    source_tail_line_id=tail, adjacency_receipt=receipt,
                    review_basis={"kind": "EXPLICIT_SOURCE_REVIEW", "reference_quality": "MODEL_VISUAL_DEVELOPMENT_REVIEW",
                        "source_tail_open": True, "target_prefix_unanchored": True, "source_tail_line_id": tail,
                        "reason": "Next answer page is not collected; this proposal must be rejected."})
        report = validate_continuation(self.evidence, self.graph, proof)["payload"]
        self.assertFalse(report["accepted"])
        self.assertIn("CONTINUATION_TARGET_ASSET_MISSING", {i["code"] for i in report["issues"]})


class RealAdjacentResourceReplayRegression(unittest.TestCase):
    """Actual RapidOCR snapshot of the adjacent source crop, never a held-out score."""
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = ROOT / "tests/fixtures/book46007447"
        cls.fixture, cls.validation = load_continuation_fixture(cls.fixture_dir / "continuation-evidence.json")
        cls.evidence = json.loads((cls.fixture_dir / "ocr-evidence.json").read_text(encoding="utf-8"))
        cls.graph = assemble(cls.evidence)

    def test_real_snapshot_contains_all_prefix_atoms_diagram_labels_and_heading(self):
        data = self.fixture["payload"]
        self.assertEqual(data["source"]["sha256"], "8380f9a1872c830b1cf4fba12fa00e3b6d9c50ddaed357587de7333086e9cdbf")
        self.assertEqual(data["source"]["external_refs"]["resource_index"], 173)
        self.assertNotIn("viewer_page", data["source"]["external_refs"])
        self.assertEqual(data["source"]["external_refs"]["printed_page"], 26)
        self.assertEqual(len(data["ocr_lines"]), 27)
        body = [line for line in data["ocr_lines"] if line["location"]["window_index"] == 0]
        self.assertEqual(len(body), 25)
        self.assertEqual([line["text"] for line in body[-3:]], ["图6", "图7", "图5"])
        self.assertEqual([line["text"] for line in data["ocr_lines"][-2:]], ["勾股定理", "回顾与思考（一）"])
        self.assertEqual(len(data["producer"]["model_sha256"]), 3)
        self.assertEqual(data["crop"]["crop_to_original"], [[.5, 0, 75], [0, .5, 72], [0, 0, 1]])
        self.assertEqual(self.validation, "NOT_RECHECKED_CACHED_CROP_REPLAY")

    def test_real_six_asset_replay_preserves_entities_and_rejects_unproven_diagram_extents(self):
        originals = copy.deepcopy((self.evidence, self.graph, self.fixture))
        results = prepare_continuation(self.evidence, self.graph, self.fixture)
        evidence, graph = results["evidence"], results["graph"]
        self.assertEqual(len(evidence["payload"]["pages"]), 6)
        self.assertEqual(len(evidence["payload"]["pages"][-1]["ocr_lines"]), 27)
        self.assertEqual(graph["payload"]["questions"], self.graph["payload"]["questions"])
        self.assertEqual(graph["payload"]["answers"], self.graph["payload"]["answers"])
        self.assertEqual(graph["derivation_refs"][0], reference(self.graph))
        self.assertEqual(graph["input_refs"], [reference(evidence)])
        self.assertEqual(len(results["proof"]["payload"]["to_line_ids"]), 25)
        report = results["report"]["payload"]
        self.assertFalse(report["accepted"])
        self.assertEqual((report["status"], report["decision"]), ("REJECTED", "HOLD"))
        self.assertIn("CONTINUATION_FIGURE_EXTENT_UNVERIFIED", {i["code"] for i in report["issues"]})
        self.assertIsNone(report["verified_plan"])
        self.assertEqual((self.evidence, self.graph, self.fixture), originals)

    def fixture_copy(self, folder):
        destination = Path(folder)
        (destination / "continuation-assets").mkdir()
        shutil.copy2(self.fixture_dir / "continuation-assets/resource-173-prefix.png",
                     destination / "continuation-assets/resource-173-prefix.png")
        return destination / "continuation-evidence.json"

    def test_real_fixture_rejects_dropped_diagram_label_and_changed_transform(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.fixture_copy(folder)
            broken = copy.deepcopy(self.fixture)
            broken["payload"]["ocr_lines"] = [line for line in broken["payload"]["ocr_lines"] if line["text"] != "图7"]
            rehash(broken)
            path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "diagram labels missing"):
                load_continuation_fixture(path)
            broken = copy.deepcopy(self.fixture)
            broken["payload"]["ocr_lines"][0]["bbox"][0] += 1
            rehash(broken)
            path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "transform mismatch"):
                load_continuation_fixture(path)

    def test_real_fixture_requires_reviewed_previous_source_hash_and_cannot_append_twice(self):
        changed = copy.deepcopy(self.evidence)
        page = next(p for p in changed["payload"]["pages"] if p["asset_id"] == "viewer-173")
        page["source"]["sha256"] = "0" * 64
        rehash(changed)
        with self.assertRaisesRegex(ValueError, "base source asset identity"):
            prepare_continuation(changed, assemble(changed), self.fixture)
        results = prepare_continuation(self.evidence, self.graph, self.fixture)
        with self.assertRaisesRegex(ValueError, "already exists"):
            prepare_continuation(results["evidence"], results["graph"], self.fixture)


if __name__ == "__main__":
    unittest.main()
