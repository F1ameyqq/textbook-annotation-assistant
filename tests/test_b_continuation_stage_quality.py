"""Independent stage/extended quality faults using labelled synthetic pixels.

Production builders create candidates, never expected findings. Fixed source
line identities and fault outcomes below are independent of their graph output.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"),str(ROOT/"tools"),str(ROOT/"tests")]
from test_b_continuation_stage import make_continuation_fixture,refresh_package
from annotation.recognition.baseline import digest,file_digest
from annotation.recognition.continuation_stage import prepare_continuation_scope,build_continuation_stage_proof,apply_continuation_stage
from annotation.recognition.continuation_stage_quality import (inspect_continuation_package,audit_continuation_scope,
    audit_continuation_proof_stage,audit_continuation_apply_stage,audit_continued_quality,semantic_receipt)
from annotation.recognition.continued_quality import build_continued_quality


def rebind(value):
    """Coordinated hash/identity edit, so rejection must inspect contents."""
    value["content_hash"] = digest(value["payload"])
    body = {k:v for k,v in value.items()if k not in {"artifact_id","content_hash","created_at"}}
    value["artifact_id"] = value["kind"].lower()+"-"+digest(body)[:24]
    return value


class ContinuationStageIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data = make_continuation_fixture(self.temp.name)
        d = self.data
        self.args = (d["package_path"],d["source_path"],d["adjacent_source_path"])
        self.kwargs = dict(zip(("package_path","source_path","adjacent_source_path"),self.args))
        self.scope = prepare_continuation_scope(d["evidence"],d["graph"],*self.args)
        self.proof = build_continuation_stage_proof(self.scope,*self.args)
        self.applied = apply_continuation_stage(self.scope,self.proof,*self.args)

    def audit_scope(self,scope=None):
        return audit_continuation_scope(self.data["evidence"],self.data["graph"],scope or self.scope,*self.args)["payload"]

    def build(self):
        return build_continued_quality(self.scope,self.proof,self.applied,self.data["review"],**self.kwargs)

    def audit(self,value):
        return audit_continued_quality(self.scope,self.proof,self.applied,self.data["review"],value,**self.kwargs)["payload"]

    def test_all_current_stages_and_current_quality_are_traceable_but_hold(self):
        for check in (self.audit_scope(),audit_continuation_proof_stage(self.scope,self.proof,*self.args)["payload"],
                audit_continuation_apply_stage(self.scope,self.proof,self.applied,*self.args)["payload"]):
            self.assertTrue(check["accepted"],check["issues"])
            self.assertEqual(check["decision"],"HOLD")
        checked = self.build();self.assertTrue(self.audit(checked)["accepted"])
        payload = checked["payload"]
        self.assertEqual(payload["summary"]["source_assets"],2)
        self.assertEqual(payload["summary"]["continuation_target_lines"],3)
        self.assertEqual(payload["summary"]["answer_raw_lines"],6)
        self.assertEqual(payload["summary"]["answer_fragment_count"],5)
        self.assertEqual(payload["summary"]["unassigned_answer_lines"],0)
        codes = {i["code"]for i in payload["issues"]}
        self.assertTrue({"BUSINESS_REVIEW_REQUIRED","CONTINUATION_PARTIAL_ADJACENT_PAGE_OCR","CONTINUATION_TYPED_CONTENT_UNVERIFIED"} <= codes)
        self.assertNotIn("ANSWER_AGGREGATE_TEXT_MISMATCH",codes)
        self.assertFalse(payload["business_acceptance"])
        self.assertFalse(payload["transcription_verified"])
        self.assertEqual(payload["platform_actions"],[])

    def test_auditors_do_not_execute_the_stage_or_assembly_producers(self):
        checked = self.build()
        with patch("annotation.recognition.continuation_stage.prepare_continuation_scope",side_effect=AssertionError("producer rerun")), \
             patch("annotation.recognition.continuation_stage.build_continuation_stage_proof",side_effect=AssertionError("producer rerun")), \
             patch("annotation.recognition.continuation_stage.apply_continuation_stage",side_effect=AssertionError("producer rerun")), \
             patch("annotation.recognition.offline.assemble",side_effect=AssertionError("assembler rerun")), \
             patch("annotation.recognition.continued_quality.build_continued_quality",side_effect=AssertionError("check producer rerun")):
            self.assertTrue(self.audit(checked)["accepted"])

    def test_rehashed_scope_omitting_original_raw_or_new_heading_is_rejected(self):
        for page_index,line_index in ((0,0),(-1,-1)):
            with self.subTest(page=page_index):
                value = copy.deepcopy(self.scope)
                value["payload"]["evidence"]["payload"]["pages"][page_index]["ocr_lines"].pop(line_index)
                rebind(value["payload"]["evidence"]);rebind(value)
                self.assertFalse(self.audit_scope(value)["accepted"])

    def test_current_source_originals_are_required_even_with_valid_retained_captures(self):
        self.data["adjacent_source_path"].write_bytes(b"wrong full original")
        self.assertFalse(self.audit_scope()["accepted"])

    def test_coordinated_white_capture_hashes_cannot_replace_actual_source_pixels(self):
        d = self.data;descriptor = d["documents"]["image_review"]["payload"]["captures"][0]
        path = d["package_path"].parent/descriptor["path"]
        with Image.open(path)as image: white = Image.new("RGB",image.size,"white")
        white.save(path)
        descriptor["sha256"] = file_digest(path);descriptor["rgb_sha256"] = hashlib.sha256(white.tobytes()).hexdigest()
        d["package"]["captures"] = copy.deepcopy(d["documents"]["image_review"]["payload"]["captures"])
        refresh_package(d)
        result = self.audit_scope()
        self.assertFalse(result["accepted"])
        self.assertIn("original source pixels",str(result["issues"]))

    def test_old_open_tail_source_snapshot_is_not_rebased_to_edited_raw(self):
        value = copy.deepcopy(self.scope)
        value["payload"]["base_evidence_archive"]["payload"]["pages"][0]["ocr_lines"][0]["score"] = .11
        rebind(value["payload"]["base_evidence_archive"]);rebind(value)
        self.assertFalse(self.audit_scope(value)["accepted"])

    def test_rehashed_scope_false_whole_adjacent_page_ocr_claim_is_rejected(self):
        value = copy.deepcopy(self.scope);value["payload"]["source_scope"]["full_page_ocr_claimed"] = True;rebind(value)
        self.assertFalse(self.audit_scope(value)["accepted"])

    def test_current_proof_cannot_drop_a_diagnostic_line_after_rehash(self):
        value = copy.deepcopy(self.proof)
        proof = value["payload"]["proof"]
        proof["payload"]["to_line_ids"].remove("target-page/ocr/1")
        proof["content_hash"] = digest(proof["payload"]);rebind(value)
        self.assertFalse(audit_continuation_proof_stage(self.scope,value,*self.args)["payload"]["accepted"])

    def test_apply_metadata_false_rollback_and_false_human_are_rejected(self):
        for key in ("rollback_verification","business_acceptance"):
            with self.subTest(key=key):
                value = copy.deepcopy(self.applied)
                if key == "rollback_verification": value["payload"][key]["restored_complete_object_sha256"] = "0"*64
                else: value["payload"][key] = True
                rebind(value)
                self.assertFalse(audit_continuation_apply_stage(self.scope,self.proof,value,*self.args)["payload"]["accepted"])

    def test_missing_current_findings_cannot_be_hidden_by_updating_summary(self):
        value = self.build();value["payload"]["issues"] = []
        value["payload"]["summary"]["issues"] = 0;rebind(value)
        result = self.audit(value)
        self.assertFalse(result["accepted"])
        self.assertIn("CONTINUED_CURRENT_FINDINGS_MISMATCH",{i["code"]for i in result["issues"]})

    def test_review_expectations_are_frozen_source_not_mutable_graph_echo(self):
        value = self.build()
        case = value["payload"]["derived_review"]["multiline_checks"][-1]
        self.assertEqual(case["expected_source_line_ids"],["source-page/ocr/0","source-page/ocr/1","target-page/ocr/0","target-page/ocr/1","target-page/ocr/2"])
        case["expected_source_line_ids"].remove("target-page/ocr/1")
        value["payload"]["derived_review_ref"]["content_hash"] = digest(value["payload"]["derived_review"])
        rebind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_rule_dispositions_cannot_suppress_another_error_or_be_removed(self):
        for operation in ("remove","add"):
            with self.subTest(operation=operation):
                value = self.build()
                if operation == "remove": value["payload"]["rule_dispositions"] = []
                else: value["payload"]["rule_dispositions"].append({"finding":{"code":"BUSINESS_REVIEW_REQUIRED"},"status":"IGNORED"})
                rebind(value);self.assertFalse(self.audit(value)["accepted"])

    def test_false_human_or_complete_and_unknown_acceptance_fields_are_rejected(self):
        for key in ("transcription_verified","business_acceptance","complete","human_verified"):
            with self.subTest(key=key):
                value = self.build();value["payload"][key] = True;rebind(value)
                self.assertFalse(self.audit(value)["accepted"])

    def test_current_graph_reference_and_current_source_counts_are_required(self):
        for field in ("graph_ref","summary"):
            value = self.build()
            if field == "graph_ref": value["payload"][field] = self.scope["payload"]["graph"]["input_refs"][0]
            else: value["payload"][field]["answer_raw_lines"] = 2
            rebind(value);self.assertFalse(self.audit(value)["accepted"])

    def test_normalized_text_receipts_survive_lf_crlf_without_losing_binary_binding(self):
        paths = [self.data["package_path"],self.data["source_path"]]
        paths += [self.data["package_path"].parent/d["path"]for d in self.data["package"]["documents"].values()]
        for path in paths: path.write_bytes(path.read_text(encoding="utf8").encode())
        before = inspect_continuation_package(*self.args)
        for path in paths: path.write_bytes(path.read_text(encoding="utf8").replace("\n","\r\n").encode())
        after = inspect_continuation_package(*self.args)
        self.assertNotEqual(before["receipt"]["package"]["file_sha256"],after["receipt"]["package"]["file_sha256"])
        self.assertEqual(semantic_receipt(before["receipt"]),semantic_receipt(after["receipt"]))
        self.assertTrue(self.audit_scope()["accepted"])

    def test_development_content_difference_is_retained_without_ocr_correction(self):
        d = self.data;line = d["documents"]["continuation_fixture"]["payload"]["ocr_lines"][0]
        region = [8,8,92,24]
        with Image.open(d["adjacent_source_path"])as image: pixel_hash = hashlib.sha256(image.convert("RGB").crop(region).tobytes()).hexdigest()
        d["documents"]["content_review"]["payload"]["line_checks"] = [{"case_id":"synthetic-meaning-mismatch","asset_id":"target-page",
            "source_sha256":d["package"]["adjacent_source"]["sha256"],"line_id":line["line_id"],"raw_text":line["text"],
            "raw_text_sha256":hashlib.sha256(line["text"].encode()).hexdigest(),"line_bbox":line["bbox"],"review_region_bbox":region,
            "review_region_rgb_sha256":pixel_hash,"observed_text":"SYNTHETIC_TEST hypothetical source comparison",
            "differences":[{"kind":"SYNTHETIC_TEST","raw_fragment":line["text"][:1],"raw_text_span":[0,1],"observed_source_fragment":"other"}],
            "reference_quality":"MODEL_VISUAL_DEVELOPMENT_REVIEW","human_verified":False,"business_acceptance":False}]
        refresh_package(d)
        self.scope = prepare_continuation_scope(d["evidence"],d["graph"],*self.args)
        self.proof = build_continuation_stage_proof(self.scope,*self.args)
        self.applied = apply_continuation_stage(self.scope,self.proof,*self.args)
        value = self.build()
        disagreement = [i for i in value["payload"]["issues"]if i["code"] == "CONTINUATION_DEVELOPMENT_TRANSCRIPTION_DISAGREEMENT"]
        self.assertEqual(len(disagreement),1)
        self.assertEqual(disagreement[0]["evidence_refs"],["target-page/ocr/0"])
        self.assertFalse(disagreement[0]["detail"]["ocr_corrected"])
        self.assertNotIn("hypothetical",self.applied["payload"]["graph"]["payload"]["answers"][0]["text"])
        self.assertTrue(self.audit(value)["accepted"])
        value["payload"]["issues"].remove(disagreement[0]);value["payload"]["summary"]["issues"] -= 1;rebind(value)
        self.assertFalse(self.audit(value)["accepted"])

    def test_bad_inputs_reject_as_artifact_without_crashing(self):
        for value in ({}, {"payload":{}}):
            self.assertFalse(audit_continuation_scope(self.data["evidence"],self.data["graph"],value,*self.args)["payload"]["accepted"])
        scope = copy.deepcopy(self.scope)
        scope["payload"]["graph"]["payload"]["answers"] = []
        rebind(scope["payload"]["graph"]);rebind(scope)
        self.assertFalse(audit_continuation_proof_stage(scope,self.proof,*self.args)["payload"]["accepted"])


class RealContinuationDevelopmentReferences(unittest.TestCase):
    def test_five_source_bound_real_differences_keep_exact_raw_and_review_pixels(self):
        fixture = ROOT/"tests/fixtures/book46007447"
        # Preserve this exact historical development reference, including its
        # subsequently corrected radical mistake. The current package uses v2.
        content = json.loads((fixture/"continuation-content-review.json").read_text(encoding="utf8"))
        evidence = json.loads((fixture/"continuation-evidence.json").read_text(encoding="utf8"))
        cp = content["payload"];raw = {l["line_id"]:l for l in evidence["payload"]["ocr_lines"]}
        self.assertEqual([c["line_id"]for c in cp["line_checks"]],["resource-173/ocr/0","resource-173/ocr/4","resource-173/ocr/5","resource-173/ocr/6","resource-173/ocr/7"])
        self.assertEqual(sum(len(c["differences"])for c in cp["line_checks"]),6)
        self.assertEqual(cp["reference_quality"],"MODEL_VISUAL_DEVELOPMENT_REVIEW")
        self.assertFalse(cp["human_verified"])
        with Image.open(fixture/cp["capture"]["path"])as capture:
            for case in cp["line_checks"]:
                self.assertEqual(case["raw_text"],raw[case["line_id"]]["text"])
                self.assertEqual(case["raw_text_sha256"],hashlib.sha256(case["raw_text"].encode()).hexdigest())
                x,y,_,_ = cp["capture"]["source_bbox"];box = case["review_region_bbox"]
                pixels = capture.convert("RGB").crop([box[0]-x,box[1]-y,box[2]-x,box[3]-y])
                self.assertEqual(hashlib.sha256(pixels.tobytes()).hexdigest(),case["review_region_rgb_sha256"])
        # This is a frozen development discrepancy, never a replacement OCR row.
        self.assertIn("625=25",raw["resource-173/ocr/7"]["text"])
        self.assertIn("√625=25",cp["line_checks"][-1]["observed_text"])


if __name__ == "__main__": unittest.main()
