"""Real local continuation apply/rollback with immutable source evidence.

These tests use the retained source captures and actual frozen OCR. Structural
completion does not certify transcription, mathematical correctness, or business
acceptance. No website or OCR engine is invoked.
"""
from collections import Counter
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/"tests/fixtures/book46007447"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tools"))

from annotation.recognition.baseline import digest
from annotation.recognition.continuation_apply import apply_continuation,rollback_continuation,_graph_id
from annotation.recognition.offline import quality_check
from replay_structure_b import run


def ref(value):
    return {key:value[key] for key in ("artifact_id","revision","content_hash")}


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


class RealContinuationApply(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        results = run(FIXTURE)
        cls.evidence,cls.graph,cls.proof = (results[name] for name in
            ("evidence.json","question-graph-source-extension.json","continuation-proof.json"))
        cls.plan = results["continuation-check.json"]["payload"]["verified_plan"]
        cls.image_review = json.loads((FIXTURE/"image-region-review.json").read_text(encoding="utf-8"))
        cls.derived = apply_continuation(cls.evidence,cls.graph,cls.proof,image_review=cls.image_review,capture_root=FIXTURE)

    def answer(self,graph=None):
        graph = self.derived if graph is None else graph
        return next(a for a in graph["payload"]["answers"] if a["answer_id"] == self.plan["from_answer_id"])

    def test_real_apply_is_a_versioned_hold_with_structural_completion_only(self):
        derived,answer = self.derived,self.answer()
        self.assertEqual(derived["schema_version"],"b-graph-trial/0.4")
        self.assertEqual(derived["revision"],self.graph["revision"]+1)
        self.assertEqual(derived["supersedes"],ref(self.graph))
        self.assertEqual(derived["payload"]["decision"],"HOLD")
        self.assertFalse(derived["payload"]["business_acceptance"])
        self.assertEqual(derived["payload"]["platform_actions"],[])
        self.assertTrue(answer["structural_complete"])
        self.assertFalse(answer["complete"])
        self.assertFalse(answer["transcription_verified"])
        self.assertEqual(answer["assembly_status"],"BOUNDED")
        self.assertEqual(answer["boundary"]["text"],"回顾与思考（一） 勾股定理")
        self.assertEqual(set(answer["boundary"]["evidence_refs"]),{"resource-173/ocr/25","resource-173/ocr/26"})

    def test_all_questions_other_answers_and_original_eight_fragments_are_unchanged(self):
        self.assertEqual(self.derived["payload"]["questions"],self.graph["payload"]["questions"])
        before = {a["answer_id"]:a for a in self.graph["payload"]["answers"]}
        after = {a["answer_id"]:a for a in self.derived["payload"]["answers"]}
        self.assertEqual(set(before),set(after))
        answer_id = self.plan["from_answer_id"]
        for key in set(before)-{answer_id}:self.assertEqual(before[key],after[key])
        self.assertEqual(after[answer_id]["fragments"][:8],before[answer_id]["fragments"])
        self.assertEqual(len(after[answer_id]["fragments"]),33)
        self.assertEqual(after[answer_id]["bbox"],before[answer_id]["bbox"])
        self.assertEqual(after[answer_id]["bbox_scope"],before[answer_id]["bbox_scope"])
        self.assertEqual(after[answer_id]["assembly_flags"],before[answer_id]["assembly_flags"])
        self.assertEqual(after[answer_id]["coarse_detail_agreement"],before[answer_id]["coarse_detail_agreement"])

    def test_25_new_fragments_bind_full_original_ocr_without_rewriting_labels(self):
        source = {line["line_id"]:(page,line) for page in self.evidence["payload"]["pages"] for line in page["ocr_lines"]}
        added = self.answer()["fragments"][8:]
        self.assertEqual([f["parent_line_id"] for f in added],self.plan["target_line_ids"])
        self.assertEqual(len({f["fragment_id"] for f in self.answer()["fragments"]}),33)
        for fragment in added:
            page,line = source[fragment["parent_line_id"]]
            self.assertEqual(fragment["asset_id"],page["asset_id"])
            self.assertEqual(fragment["bbox"],line["bbox"])
            self.assertEqual(fragment["raw_text"],line["text"])
            self.assertEqual(fragment["text"],line["text"])
            self.assertEqual(fragment["text_span"],[0,len(line["text"])])
            self.assertEqual(fragment["source_sha256"],page["source"]["sha256"])
            self.assertEqual(fragment["evidence_refs"],[line["line_id"]])
        self.assertEqual(len(self.answer()["source_line_ids"]),33)
        self.assertEqual(len(self.answer()["evidence_refs"]),33)

    def test_15_typed_regions_render_ten_body_lines_and_five_original_pixel_images(self):
        answer = self.answer()
        render = answer["render_regions"]
        self.assertEqual(len(render),15)
        self.assertEqual(Counter(r["content_type"] for r in render),{"text":10,"image":5})
        self.assertEqual(answer["text"],"\n".join(r["text"] for r in render if r["content_type"] == "text"))
        self.assertEqual(len(answer["text"].splitlines()),10)
        diagnostic = self.plan["image_contained_ocr_refs"]
        expected_body = [f["text"] for f in self.answer(self.graph)["fragments"] if f["parent_line_id"] not in diagnostic]
        source = {l["line_id"]:l for p in self.evidence["payload"]["pages"] for l in p["ocr_lines"]}
        expected_body.extend(source[line_id]["text"] for line_id in self.plan["target_line_ids"] if line_id not in diagnostic)
        self.assertEqual(answer["text"],"\n".join(expected_body))
        self.assertEqual(sum(not item["render_as_separate_region"] for item in answer["fragment_representation"]),23)
        original_images = self.plan["source_image_regions"]+[r for r in self.plan["target_regions"] if r["content_type"] == "image"]
        images = {r["region_id"]:r for r in render if r["content_type"] == "image"}
        for original in original_images:
            projected = images[original["region_id"]]
            self.assertTrue(all(projected[key] == value for key,value in original.items()))
            self.assertTrue(projected["source_fragment_ids"])
            self.assertEqual(projected["image_ref"]["region_id"],original["region_id"])
            self.assertEqual(projected["image_ref"]["artifact_ref"],self.plan["image_region_artifact_ref"])
        self.assertEqual(answer["regions"],render)
        self.assertEqual(answer["regions_schema"],"b-render-region-trial/0.1")
        self.assertFalse(answer["regions_migration"]["legacy_consumers_supported"])

    def test_exactly_25_ledger_rows_change_and_both_boundary_rows_remain_excluded(self):
        before = self.graph["payload"]["answer_coverage"]
        after = self.derived["payload"]["answer_coverage"]
        self.assertEqual(len(after),202)
        self.assertEqual(Counter(row["status"] for row in after),{"CONSUMED":154,"EXCLUDED":29,"UNASSIGNED":19})
        targets = set(self.plan["target_line_ids"])
        by_parent = {f["parent_line_id"]:f for f in self.answer()["fragments"][8:]}
        changed = []
        for old,new in zip(before,after):
            if old["line_id"] not in targets:self.assertEqual(new,old)
            else:
                changed.append(old["line_id"])
                fragment = by_parent[old["line_id"]]
                self.assertEqual(old["status"],"UNASSIGNED")
                self.assertEqual(new["status"],"CONSUMED")
                self.assertEqual(new["answer_ids"],[self.answer()["answer_id"]])
                self.assertEqual(new["fragment_ids"],[fragment["fragment_id"]])
                self.assertEqual(new["allocations"],[{"answer_id":self.answer()["answer_id"],"fragment_id":fragment["fragment_id"],
                                 "evidence_refs":fragment["evidence_refs"],"text_span":fragment["text_span"]}])
        self.assertEqual(set(changed),targets)
        for line_id in ("resource-173/ocr/25","resource-173/ocr/26"):
            row = next(r for r in after if r["line_id"] == line_id)
            self.assertEqual(row["status"],"EXCLUDED")
            self.assertEqual(row["allocations"],[])

    def test_only_affected_boundary_issue_is_marked_resolved(self):
        affected = self.answer()["answer_id"]
        for old,new in zip(self.graph["payload"]["issues"],self.derived["payload"]["issues"]):
            if old.get("answer_id") == affected and old["code"] == "ANSWER_BOUNDARY_UNRESOLVED":
                self.assertEqual({key:new[key] for key in old},old)
                self.assertEqual(new["status"],"RESOLVED_STRUCTURAL_BOUNDARY")
            else:self.assertEqual(new,old)
        self.assertIn("ANSWER_SPATIAL_GAP_UNRESOLVED",self.answer()["active_assembly_flags"])
        self.assertNotIn("ANSWER_BOUNDARY_UNRESOLVED",self.answer()["active_assembly_flags"])
        self.assertEqual(self.answer()["structural_resolution"]["resolved_legacy_flags"],["ANSWER_BOUNDARY_UNRESOLVED"])

    def test_apply_mutates_no_input_and_created_at_does_not_change_identity(self):
        before = copy.deepcopy((self.evidence,self.graph,self.proof,self.image_review))
        derived = apply_continuation(self.evidence,self.graph,self.proof,image_review=self.image_review,capture_root=FIXTURE)
        self.assertEqual((self.evidence,self.graph,self.proof,self.image_review),before)
        self.assertEqual(derived["artifact_id"],self.derived["artifact_id"])
        self.assertEqual(derived["content_hash"],self.derived["content_hash"])
        changed_timestamp = copy.deepcopy(self.graph)
        changed_timestamp["created_at"] = "2000-01-01T00:00:00+00:00"
        other = apply_continuation(self.evidence,changed_timestamp,self.proof,image_review=self.image_review,capture_root=FIXTURE)
        self.assertEqual(other["artifact_id"],derived["artifact_id"])

    def test_rejected_proof_cannot_be_overridden_with_caller_acceptance_flags(self):
        proof = copy.deepcopy(self.proof)
        proof["payload"]["accepted"] = True
        proof["payload"]["force_apply"] = True
        proof["payload"]["image_regions"]["payload"]["regions"][0]["bbox"][0] += 1
        rehash(proof["payload"]["image_regions"])
        proof["input_refs"][-2] = ref(proof["payload"]["image_regions"])
        rehash(proof)
        with self.assertRaisesRegex(ValueError,"CONTINUATION_IMAGE_EVIDENCE_INVALID"):
            apply_continuation(self.evidence,self.graph,proof,image_review=self.image_review,capture_root=FIXTURE)

    def test_stale_proof_wrong_source_and_duplicate_apply_reject(self):
        stale = copy.deepcopy(self.graph)
        stale["revision"] += 1
        with self.assertRaisesRegex(ValueError,"CONTINUATION_STALE_PROOF"):
            apply_continuation(self.evidence,stale,self.proof,image_review=self.image_review,capture_root=FIXTURE)
        wrong = copy.deepcopy(self.evidence)
        wrong["payload"]["pages"][-1]["source"]["sha256"] = "0"*64
        rehash(wrong)
        with self.assertRaises(ValueError):
            apply_continuation(wrong,self.graph,self.proof,image_review=self.image_review,capture_root=FIXTURE)
        with self.assertRaises(ValueError):
            apply_continuation(self.evidence,self.derived,self.proof,image_review=self.image_review,capture_root=FIXTURE)

    def test_apply_rechecks_current_capture_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)/"fixture"
            shutil.copytree(FIXTURE,fixture)
            capture = fixture/self.image_review["payload"]["captures"][0]["path"]
            capture.write_bytes(capture.read_bytes()+b"changed-after-proof")
            with self.assertRaisesRegex(ValueError,"CONTINUATION_IMAGE_EVIDENCE_INVALID"):
                apply_continuation(self.evidence,self.graph,self.proof,image_review=self.image_review,capture_root=fixture)

    def test_old_quality_consumer_cannot_silently_accept_schema04(self):
        review = json.loads((FIXTURE/"review.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):quality_check(self.evidence,self.derived,review)

    def test_rollback_restores_exact_base_and_requires_independent_reference(self):
        original = copy.deepcopy(self.derived)
        saved_ref = copy.deepcopy(ref(self.derived))
        restored = rollback_continuation(self.evidence,self.derived,expected_graph_ref=saved_ref)
        self.assertEqual(restored,self.graph)
        self.assertIsNot(restored,self.graph)
        self.assertEqual(self.derived,original)
        with self.assertRaises(TypeError):rollback_continuation(self.evidence,self.derived)
        with self.assertRaises(ValueError):rollback_continuation(self.evidence,restored,expected_graph_ref=saved_ref)

    def test_rollback_refuses_payload_edits_even_when_caller_rehashes_guard_and_id(self):
        saved_ref = copy.deepcopy(ref(self.derived))
        for kind in ("answer","question","application"):
            with self.subTest(kind=kind):
                derived = copy.deepcopy(self.derived)
                if kind == "answer":self.answer(derived)["text"] += "\nLater local edit"
                elif kind == "question":derived["payload"]["questions"][0]["text"] += " Later local edit"
                else:derived["payload"]["continuation_application"]["note"] = "Later local edit"
                rehash(derived)
                derived["rollback_guard"]["expected_payload_hash"] = derived["content_hash"]
                derived["artifact_id"] = _graph_id(derived)
                with self.assertRaisesRegex(ValueError,"independently retained version"):
                    rollback_continuation(self.evidence,derived,expected_graph_ref=saved_ref)
                # Even an incorrectly supplied fresh reference does not turn a
                # later edited payload into the canonical applied projection.
                with self.assertRaises(ValueError):
                    rollback_continuation(self.evidence,derived,expected_graph_ref=ref(derived))

    def test_rollback_rejects_changed_evidence_and_stale_expected_version(self):
        wrong = copy.deepcopy(self.evidence)
        wrong["revision"] += 1
        with self.assertRaises(ValueError):rollback_continuation(wrong,self.derived,expected_graph_ref=ref(self.derived))
        stale = ref(self.derived)
        stale["revision"] += 1
        with self.assertRaises(ValueError):rollback_continuation(self.evidence,self.derived,expected_graph_ref=stale)


if __name__ == "__main__":unittest.main()
