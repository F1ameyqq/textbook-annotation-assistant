"""Real source-structure integration and fresh, coherently rebound fault cases.

Pixel/heading acceptance remains a development structural proposal. These tests
neither merge a graph nor imply mathematical, human, or platform acceptance.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]

from annotation.recognition.baseline import digest
from annotation.recognition.continuation import build_continuation_proof, validate_continuation
from annotation.recognition.image_regions import build_image_regions
from replay_structure_b import run


def rehash(artifact):
    artifact["content_hash"] = digest(artifact["payload"])
    return artifact


_DEFAULT = object()


class RealStructureIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = run(FIXTURE)
        cls.original_review = json.loads((FIXTURE / "image-region-review.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.results = copy.deepcopy(self.original)
        self.evidence = self.results["evidence.json"]
        self.graph = self.results["question-graph-source-extension.json"]
        self.images = self.results["image-regions.json"]
        self.boundary = self.results["boundary-candidate.json"]
        self.review = copy.deepcopy(self.original_review)

    def source_answer(self):
        aid = self.results["continuation-proof.json"]["payload"]["from_answer_id"]
        return next(a for a in self.graph["payload"]["answers"] if a["answer_id"] == aid)

    def proof(self, *, images=_DEFAULT, boundary=_DEFAULT, **changes):
        original = self.results["continuation-proof.json"]["payload"]
        arguments = {"from_answer_id": original["from_answer_id"],
                     "to_asset_id": original["to_asset"]["asset_id"],
                     "to_line_ids": original["to_line_ids"],
                     "source_tail_line_id": original["source_tail_line_id"],
                     "adjacency_receipt": original["adjacency_receipt"],
                     "review_basis": original["review_basis"],
                     "image_regions": self.images if images is _DEFAULT else images,
                     "boundary_candidate": self.boundary if boundary is _DEFAULT else boundary}
        arguments.update(changes)
        return build_continuation_proof(self.evidence, self.graph, **arguments)

    def report(self, proof=None, *, image_review=_DEFAULT, capture_root=_DEFAULT):
        return validate_continuation(self.evidence, self.graph, proof or self.proof(),
            image_review=self.review if image_review is _DEFAULT else image_review,
            capture_root=FIXTURE if capture_root is _DEFAULT else capture_root)["payload"]

    def codes(self, proof=None, **changes):
        report = self.report(proof, **changes)
        self.assertFalse(report["accepted"], "Consumer accepted a freshly rebound injected fault")
        self.assertEqual(report["decision"], "HOLD")
        self.assertIsNone(report["verified_plan"])
        codes = {issue["code"] for issue in report["issues"]}
        self.assertNotIn("CONTINUATION_STALE_PROOF", codes,
                         "Fault tests must exercise consumer checks, not only an old artifact hash")
        return codes

    def test_real_five_images_and_two_heading_components_are_source_validated(self):
        summary = self.results["summary.json"]
        self.assertTrue(summary["image_region_check_accepted"])
        self.assertTrue(summary["boundary_check_accepted"])
        image_check = self.results["image-check.json"]["payload"]
        self.assertEqual(image_check["structural_status"], "PIXEL_REGION_VALIDATED")
        regions = image_check["validated_regions"]
        self.assertEqual({r["figure_number"] for r in regions}, set("34567"))
        self.assertEqual({r["figure_number"] for r in regions if r["asset_id"] == "viewer-173"}, {"3", "4"})
        self.assertEqual({r["figure_number"] for r in regions if r["asset_id"] == "resource-173"}, {"5", "6", "7"})
        self.assertTrue(all(len(r["crop_rgb_sha256"]) == 64 for r in regions))
        boundary = self.results["boundary-check.json"]["payload"]["boundary"]
        self.assertEqual(boundary["text"], "回顾与思考（一） 勾股定理")
        self.assertEqual(set(boundary["line_ids"]), {"resource-173/ocr/25", "resource-173/ocr/26"})
        self.assertEqual(len(boundary["members"]), 2)
        plan = self.report()["verified_plan"]
        self.assertEqual(set(plan["next_boundary_binding"]["line_ids"]), set(boundary["line_ids"]))

    def test_all_25_prefix_lines_survive_but_render_as_nine_text_and_three_image_regions(self):
        report = self.report()
        self.assertTrue(report["accepted"], report["issues"])
        plan = report["verified_plan"]
        expected = ["resource-173/ocr/" + str(i) for i in range(25)]
        self.assertEqual(plan["target_line_ids"], expected)
        text = [region for region in plan["target_regions"] if region["content_type"] == "text"]
        images = [region for region in plan["target_regions"] if region["content_type"] == "image"]
        self.assertEqual([region["line_id"] for region in text], expected[:9])
        self.assertEqual({region["figure_number"] for region in images}, {"5", "6", "7"})
        self.assertEqual(len(plan["target_regions"]), 12)
        represented = [ref for region in images for ref in region["diagnostic_ocr_refs"]]
        self.assertCountEqual(represented, expected[9:])
        self.assertEqual(len(represented), len(set(represented)))

    def test_source_seven_diagnostic_fragments_are_images_and_stem_141_is_never_hidden(self):
        plan = self.report()["verified_plan"]
        source = self.source_answer()
        by_id = {f["fragment_id"]: f for f in source["fragments"]}
        projections = plan["source_fragment_representation"]
        expected_refs = {"viewer-173/ocr/" + str(n) for n in (143,145,148,150,153,155,156)}
        self.assertEqual(len(projections), 7)
        self.assertEqual({by_id[item["fragment_id"]]["parent_line_id"] for item in projections}, expected_refs)
        self.assertTrue(all(item["render_as_separate_region"] is False for item in projections))
        stem = next(f for f in source["fragments"] if f["evidence_refs"] == ["viewer-173/ocr/141"])
        self.assertNotIn(stem["fragment_id"], {item["fragment_id"] for item in projections})
        self.assertEqual(plan["source_fragment_ids_preserved"], [f["fragment_id"] for f in source["fragments"]])
        self.assertEqual({region["figure_number"] for region in plan["source_image_regions"]}, {"3", "4"})

    def test_structural_acceptance_has_no_graph_merge_business_acceptance_or_actions(self):
        before = copy.deepcopy((self.evidence, self.graph))
        report = self.report()
        plan, summary = report["verified_plan"], self.results["summary.json"]
        self.assertTrue(report["accepted"])
        self.assertEqual((report["status"], report["decision"]), ("VALIDATED_PROPOSAL", "HOLD"))
        self.assertEqual(plan["verification_status"], "UNVERIFIED")
        self.assertFalse(report["business_acceptance"])
        self.assertFalse(plan["business_acceptance"])
        self.assertFalse(plan["image_semantics_verified"])
        self.assertEqual(plan["platform_actions"], [])
        self.assertFalse(summary["graph_merge_performed"])
        self.assertEqual(summary["platform_actions"], 0)
        self.assertFalse(summary["ocr_rerun"])
        self.assertEqual((self.evidence, self.graph), before)
        target = {"resource-173/ocr/" + str(i) for i in range(25)}
        self.assertFalse(any(target.intersection(f["evidence_refs"])
                             for answer in self.graph["payload"]["answers"] for f in answer["fragments"]))

    def test_no_supplements_preserves_old_rejected_behavior(self):
        proof = self.proof(images=None, boundary=None)
        self.assertEqual(proof["schema_version"], "b-continuation-proof-trial/0.1")
        codes = self.codes(proof)
        self.assertIn("CONTINUATION_FIGURE_EXTENT_UNVERIFIED", codes)
        self.assertIn("CONTINUATION_PREFIX_INCOMPLETE", codes)

    def test_capture_root_and_image_review_are_both_required_at_consumer(self):
        for changes in ({"capture_root": None}, {"image_review": None},
                        {"capture_root": None, "image_review": None}):
            with self.subTest(changes=changes):
                self.assertIn("CONTINUATION_IMAGE_PIXELS_NOT_RECHECKED", self.codes(**changes))

    def test_missing_image_is_rejected_after_image_and_proof_hashes_are_rebuilt(self):
        self.images["payload"]["regions"] = [region for region in self.images["payload"]["regions"]
                                            if region["figure_number"] != "7"]
        rehash(self.images)
        self.assertIn("CONTINUATION_IMAGE_EVIDENCE_INVALID", self.codes(self.proof()))

    def test_changed_caption_is_rejected_with_coherently_rebuilt_review_image_and_proof(self):
        regions = self.review["payload"]["regions"]
        fig5 = next(region for region in regions if region["figure_number"] == "5")
        fig6 = next(region for region in regions if region["figure_number"] == "6")
        fig5["caption_ref"] = fig6["caption_ref"]
        rehash(self.review)
        self.images = build_image_regions(self.evidence, self.review, FIXTURE)
        report = self.report(self.proof())
        self.assertFalse(report["accepted"])
        wrapped = next(issue for issue in report["issues"] if issue["code"] == "CONTINUATION_IMAGE_EVIDENCE_INVALID")
        self.assertIn("IMAGE_REGION_CAPTION_MISMATCH", {issue["code"] for issue in wrapped["detail"]})
        self.assertNotIn("CONTINUATION_STALE_PROOF", {issue["code"] for issue in report["issues"]})

    def test_stale_boundary_binding_is_rejected_with_a_new_outer_proof(self):
        self.boundary["input_refs"][0]["revision"] -= 1
        self.assertIn("CONTINUATION_BOUNDARY_EVIDENCE_INVALID", self.codes(self.proof()))

    def test_wrong_prefix_is_rejected_with_fresh_line_snapshots(self):
        ids = self.results["continuation-proof.json"]["payload"]["to_line_ids"]
        self.assertIn("CONTINUATION_TARGET_NOT_LEADING_PREFIX", self.codes(self.proof(to_line_ids=ids[1:])))

    def test_forged_parent_cannot_hide_real_stem_141_as_figure_caption_155(self):
        source = self.source_answer()
        stem = next(f for f in source["fragments"] if f["evidence_refs"] == ["viewer-173/ocr/141"])
        stem["parent_line_id"] = "viewer-173/ocr/155"
        rehash(self.graph)
        self.assertIn("CONTINUATION_SOURCE_PARENT_MISMATCH", self.codes(self.proof()))

    def test_actual_caption_transfer_to_same_scope_q8_cannot_leave_image_owned_by_q9(self):
        source = self.source_answer()
        destination = next(a for a in self.graph["payload"]["answers"]
                           if a["printed_number"] == "8" and a["section_path"] == source["section_path"])
        caption = next(f for f in source["fragments"] if f["evidence_refs"] == ["viewer-173/ocr/155"])
        region = next(r for r in source["regions"] if r["fragment_id"] == caption["fragment_id"])
        source["fragments"].remove(caption)
        source["regions"].remove(region)
        source["source_line_ids"].remove("viewer-173/ocr/155")
        source["evidence_refs"].remove("viewer-173/ocr/155")
        destination["fragments"].append(caption)
        destination["regions"].append(region)
        destination["source_line_ids"].append("viewer-173/ocr/155")
        destination["evidence_refs"].append("viewer-173/ocr/155")
        for answer in (source, destination):
            answer["text"] = "\n".join(f["text"] for f in answer["fragments"]
                                      if f["role"] == "answer" and not f.get("structural_marker"))
        row = next(r for r in self.graph["payload"]["answer_coverage"] if r["line_id"] == "viewer-173/ocr/155")
        row["answer_ids"] = [destination["answer_id"]]
        for allocation in row["allocations"]:
            if allocation["fragment_id"] == caption["fragment_id"]:
                allocation["answer_id"] = destination["answer_id"]
        self.assertEqual(source["source_line_ids"][-1], "viewer-173/ocr/156")
        rehash(self.graph)
        self.assertIn("CONTINUATION_SOURCE_IMAGE_OWNERSHIP_CONFLICT", self.codes(self.proof()))

    def test_fresh_human_label_cannot_promote_model_source_review(self):
        basis = copy.deepcopy(self.results["continuation-proof.json"]["payload"]["review_basis"])
        basis["reference_quality"] = "HUMAN_REVIEWED"
        self.assertIn("CONTINUATION_HUMAN_REVIEW_RECEIPT_MISSING", self.codes(self.proof(review_basis=basis)))

    def test_proof_and_receipt_scope_must_match_current_evidence(self):
        proof = self.proof()
        proof["scope_id"] = "another-scope"
        self.assertIn("CONTINUATION_SCOPE_MISMATCH", self.codes(proof))
        receipt = copy.deepcopy(self.results["continuation-proof.json"]["payload"]["adjacency_receipt"])
        receipt["scope_id"] = "another-scope"
        self.assertIn("CONTINUATION_SCOPE_MISMATCH", self.codes(self.proof(adjacency_receipt=receipt)))

    def test_cli_replays_without_ocr_or_network_and_refuses_existing_output(self):
        # A clean interpreter blocks OCR-runtime imports and Python network
        # connection attempts. Replay must rely solely on committed snapshots.
        code = """
import importlib.abc, pathlib, runpy, socket, sys
class RejectOCR(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'rapidocr_onnxruntime','onnxruntime'}:
            raise AssertionError('OCR runtime imported during offline replay: '+fullname)
def reject_network(*args, **kwargs):
    raise AssertionError('Network attempted during offline replay')
sys.meta_path.insert(0, RejectOCR())
socket.create_connection=reject_network
socket.socket.connect=reject_network
socket.socket.connect_ex=reject_network
out, script=sys.argv[1:]
sys.path.insert(0,str(pathlib.Path(script).resolve().parent))
sys.argv=[script,'--out',out]
runpy.run_path(script,run_name='__main__')
"""
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "structure-replay"
            command = [sys.executable, "-c", code, str(output), str(ROOT / "tools/replay_structure_b.py")]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            summary = json.loads(first.stdout)
            self.assertEqual(summary["continuation_status"], "VALIDATED_PROPOSAL")
            self.assertFalse(summary["ocr_rerun"])
            self.assertEqual(summary["platform_actions"], 0)
            self.assertFalse(summary["graph_merge_performed"])
            original = (output / "summary.json").read_bytes()
            (output / "sentinel.txt").write_text("preserve existing output", encoding="utf-8")
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("--out must be a new directory", second.stderr)
            self.assertEqual((output / "summary.json").read_bytes(), original)
            self.assertEqual((output / "sentinel.txt").read_text(encoding="utf-8"), "preserve existing output")


if __name__ == "__main__":
    unittest.main()
