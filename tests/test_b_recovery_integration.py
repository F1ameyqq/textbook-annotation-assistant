"""Real recovery replay, source-bound regressions, and coordinated fault checks.

This development replay uses the committed review artifact and small source
crops. Candidate counts are not held-out accuracy or business acceptance.
"""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/book46007447"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tools"))

from annotation.recognition.baseline import digest
from annotation.recognition.offline import artifact, assemble, quality_check
from annotation.recognition.recovery_apply import derive_evidence, reference
from replay_recovery_b import replay


def read(name):
    return json.loads((FIXTURE/name).read_text(encoding="utf-8"))


def rehash(value):
    value["content_hash"] = digest(value["payload"])
    return value


class RealRecoveryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence,cls.review,cls.graph,cls.report = replay(FIXTURE)
        cls.source_review = read("source-recovery-review.json")
        cls.base = read("ocr-evidence.json")
        cls.recovery = read("recovery-evidence.json")
        cls.windows = cls.base["payload"]["context"]["pages"]["viewer-173"]["windows"]

    def answer(self,window,number):
        candidates = [a for a in self.graph["payload"]["answers"]
                      if a["section_path"] == self.windows[window]["path"] and a["printed_number"] == str(number)]
        self.assertEqual(len(candidates),1,(window,number))
        return candidates[0]

    def test_replay_counts_are_drafts_with_complete_original_archives(self):
        summary = self.report["payload"]["summary"]
        self.assertEqual((summary["questions"],summary["answers"],summary["unique_candidate_links"]),(34,66,34))
        self.assertEqual(self.report["payload"]["decision"],"HOLD")
        self.assertFalse(summary["ocr_transcription_verified"])
        self.assertEqual(self.evidence["payload"]["base_evidence_archive"],self.base)
        self.assertEqual(self.evidence["payload"]["recovery_evidence_archive"],self.recovery)
        self.assertEqual(self.graph["payload"]["platform_actions"],[])
        self.assertEqual(self.source_review["payload"]["platform_actions"],[])
        self.assertFalse(self.source_review["payload"]["business_acceptance"])

    def test_175_active_lines_and_38_original_dispositions_are_separate_ledgers(self):
        coverage = self.graph["payload"]["answer_coverage"]
        self.assertEqual(len(coverage),175)
        self.assertEqual(Counter(row["status"] for row in coverage),{"CONSUMED":129,"EXCLUDED":27,"UNASSIGNED":19})
        triage = self.source_review["payload"]["triage"]
        self.assertEqual(len(triage),38)
        self.assertEqual(Counter(row["disposition"] for row in triage),{
            "REPLACED_IN_ASSEMBLY_VIEW":13,"EXCLUDED_NON_CONTENT":6,"RETAINED_UNASSIGNED_SOURCE_REFERENCE":19})
        applied = self.evidence["payload"]["recovery_application"]
        self.assertEqual(len(applied["supersession_plan"]),5)
        self.assertEqual(len(applied["replaced_base_line_ids"]),14)
        self.assertEqual(len(applied["replacement_line_ids"]),30)
        # Raw105 was already assigned incorrectly, so it belongs to the 14
        # replaced originals but is not one of the original 38 unassigned rows.
        self.assertIn("viewer-173/ocr/105",applied["replaced_base_line_ids"])
        self.assertNotIn("viewer-173/ocr/105",{row["line_id"] for row in triage})

    def test_topic1_fraction_numerator_moves_from_q2_to_q4_without_text_repair(self):
        q2,q3,q4 = self.answer(6,2),self.answer(6,3),self.answer(6,4)
        self.assertNotIn("viewer-173/ocr/105",q2["source_line_ids"])
        self.assertEqual(q3["text"],"8")
        self.assertEqual(q4["source_line_ids"],["recovery/topic1-training-q4/scale3/0",
                         "recovery/topic1-training-q4-numerator/scale3/0",
                         "recovery/topic1-training-q4-denominator/scale3/0"])
        self.assertEqual([f["text"] for f in q4["fragments"]],["2或","25","8"])
        self.assertEqual(q4["text"],"2或\n25\n8")
        self.assertNotIn("25/8",q4["text"])
        self.assertFalse(q4["transcription_verified"])

    def test_unit2_q16_anchor_precedes_all_17_recovered_lines_and_not_q15(self):
        q15,q16 = self.answer(3,15),self.answer(3,16)
        expected = {"recovery/unit2-q16/scale3/"+str(n) for n in range(17)}
        self.assertEqual(q16["source_line_ids"][0],"recovery/unit2-q16/scale3/2")
        self.assertEqual(set(q16["source_line_ids"]),expected)
        self.assertFalse(expected.intersection(q15["source_line_ids"]))
        self.assertEqual(q15["source_line_ids"],["viewer-173/ocr/"+str(n) for n in [154,2,3,5,7,9]])
        self.assertFalse(q16["transcription_verified"])
        self.assertEqual(q16["assembly_status"],"OPEN")
        self.assertFalse(q16["complete"])
        self.assertIn("ANSWER_2D_READING_ORDER_UNRESOLVED",q16["assembly_flags"])
        self.assertIn("FORMULA_VISUAL_CANDIDATE_REQUIRES_REVIEW",{i["code"] for i in self.report["payload"]["issues"]})

    def test_recovered_primary_rows_keep_exact_source_values_and_own_scopes(self):
        for number,value in ((2,"D"),(3,"4"),(4,"100"),(6,"C"),(7,"D")):
            self.assertEqual(self.answer(1,number)["text"],value)
        self.assertEqual(self.answer(3,9)["text"],"D")
        self.assertEqual(self.answer(3,10)["text"],"25")
        self.assertEqual(self.answer(0,4)["text"],"13")
        self.assertEqual(self.answer(0,7)["text"],"0")  # old C/0 fault remains visible
        for answer in self.graph["payload"]["answers"]:
            self.assertFalse(answer["transcription_verified"])
            self.assertEqual(answer["verification_status"],"UNVERIFIED")

    def test_frozen_nine_multiline_cases_only_append_two_independent_refs(self):
        original = read("review.json")
        cases = {case["case_id"]:case for case in original["multiline_checks"]}
        migrated = {case["case_id"]:case for case in self.review["multiline_checks"]}
        self.assertEqual(len(cases),9)
        self.assertEqual(set(cases),set(migrated))
        additions = {row["case_id"]:row for row in self.source_review["payload"]["regression_additions"]}
        self.assertEqual(set(additions),{"46007447-window1-q1-multiline","46007447-window1-q8-multiline"})
        for case_id,old in cases.items():
            new = migrated[case_id]
            if case_id not in additions:
                self.assertEqual(new,old)
                continue
            extra = additions[case_id]
            self.assertEqual(new["expected_source_line_ids"],old["expected_source_line_ids"]+[extra["line_id"]])
            self.assertEqual(new["expected_source_spans"][:-1],old["expected_source_spans"])
            self.assertEqual(new["expected_source_spans"][-1],{key:extra[key] for key in
                             ("line_id","text_spans","source_text_sha256")})
            for old_gap,new_gap in zip(old.get("observed_source_gaps",[]),new.get("observed_source_gaps",[])):
                self.assertEqual({key:new_gap[key] for key in old_gap},old_gap)
        q1 = migrated["46007447-window1-q1-multiline"]
        self.assertEqual(q1["observed_source_gaps"][0]["recovery_status"],"PARTIALLY_RECOVERED_UNVERIFIED")
        self.assertIn("ANSWER_SOURCE_OCR_GAP",{i["code"] for i in self.report["payload"]["issues"]})

    def test_exact_19_math_originals_stay_unassigned_and_in_reference_namespaces(self):
        expected = {"viewer-173/ocr/"+str(n) for n in
                    [86,87,102,104,108,110,111,112,113,114,115,116,117,119,120,121,122,123,125]}
        ledger = self.graph["payload"]["answer_coverage"]
        self.assertEqual({row["line_id"] for row in ledger if row["status"] == "UNASSIGNED"},expected)
        review = self.source_review["payload"]
        self.assertEqual({ref for group in review["remaining_source_groups"] for ref in group["source_line_ids"]},expected)
        self.assertTrue(all(group["assignment_status"] == "UNASSIGNED" for group in review["remaining_source_groups"]))
        self.assertFalse(expected.intersection(row["line_id"] for row in review["reviewed_exclusions"]))
        self.assertFalse(expected.intersection(ref for answer in self.graph["payload"]["answers"] for ref in answer["source_line_ids"]))

    def test_five_visual_formula_candidates_are_references_and_never_ocr(self):
        candidates = self.source_review["payload"]["formula_candidates"]
        self.assertEqual(len(candidates),5)
        active = [line for page in self.evidence["payload"]["pages"] for line in page["ocr_lines"]]
        for candidate in candidates:
            self.assertEqual(candidate["method"],"MODEL_VISUAL_DEVELOPMENT_TRANSCRIPTION")
            self.assertEqual(candidate["verification_status"],"UNVERIFIED")
            self.assertTrue(all(candidate[key] is False for key in ("cpu_ocr","human_verified","applied_to_ocr","business_acceptance")))
            self.assertNotIn(candidate["latex"],[line["text"] for line in active])
            self.assertTrue(candidate["source_regions"])
        self.assertEqual(self.report["payload"]["summary"]["visual_formula_candidates"],5)
        self.assertFalse(self.report["payload"]["summary"]["formula_candidates_verified"])

    def test_downstream_formula_projections_cannot_claim_cpu_or_human_verification(self):
        for projection,field in (("recovery_application","cpu_ocr"),("source_review","human_verified")):
            with self.subTest(projection=projection,field=field):
                evidence = copy.deepcopy(self.evidence)
                evidence["payload"][projection]["formula_candidates"][0][field] = True
                rehash(evidence)
                graph = assemble(evidence)
                report = quality_check(evidence,graph,self.review)
                self.assertIn("RECOVERY_REVIEW_PROJECTION_MISMATCH",{i["code"] for i in report["payload"]["issues"]})
                self.assertEqual(report["payload"]["decision"],"HOLD")

    def test_coordinated_active_ocr_fragment_and_region_geometry_tamper_is_caught(self):
        evidence,graph = copy.deepcopy(self.evidence),copy.deepcopy(self.graph)
        line_id = "recovery/topic1-training-q4-numerator/scale3/0"
        line = next(l for p in evidence["payload"]["pages"] for l in p["ocr_lines"] if l["line_id"] == line_id)
        line["bbox"][0] += 1
        for answer in graph["payload"]["answers"]:
            for fragment in answer["fragments"]:
                if line_id in fragment["evidence_refs"]:
                    fragment["bbox"] = list(line["bbox"])
                    for region in answer["regions"]:
                        if region["fragment_id"] == fragment["fragment_id"]:
                            region["bbox"] = list(line["bbox"])
        # Rehash and rebind both artifacts: detection must compare independent
        # retained CPU receipts, rather than rely on a stale hash or graph box.
        rehash(evidence)
        graph["input_refs"] = [reference(evidence)]
        rehash(graph)
        report = quality_check(evidence,graph,self.review)
        self.assertIn("RECOVERY_CPU_LINE_CHANGED",{i["code"] for i in report["payload"]["issues"]})
        self.assertEqual(report["payload"]["decision"],"HOLD")

    def test_tampered_assembly_order_cannot_move_q4_numerator_into_q2(self):
        self.assertEqual(len(self.source_review["payload"]["recovered_answer_checks"]),10)
        healthy = {issue["code"] for issue in self.report["payload"]["issues"]}
        self.assertFalse({"RECOVERY_ANSWER_OWNERSHIP_MISMATCH","RECOVERY_ANSWER_ORDER_MISMATCH"}.intersection(healthy))
        evidence = copy.deepcopy(self.evidence)
        line_id = "recovery/topic1-training-q4-numerator/scale3/0"
        line = next(l for p in evidence["payload"]["pages"] for l in p["ocr_lines"] if l["line_id"] == line_id)
        line["assembly_order"] = [1040,663,1051]
        rehash(evidence)
        # Regenerate the graph from the tampered order, so graph, fragments and
        # ledger agree with one another. Independent source ownership still has
        # to catch the numerator being reassigned to the earlier worked answer.
        graph = assemble(evidence)
        wrong = next(a for a in graph["payload"]["answers"]
                     if a["section_path"] == self.windows[6]["path"] and a["printed_number"] == "2")
        self.assertIn(line_id,wrong["source_line_ids"])
        report = quality_check(evidence,graph,self.review)
        codes = {issue["code"] for issue in report["payload"]["issues"]}
        self.assertIn("RECOVERY_ANSWER_OWNERSHIP_MISMATCH",codes)
        self.assertIn("RECOVERY_ANSWER_ORDER_MISMATCH",codes)
        self.assertEqual(report["payload"]["decision"],"HOLD")

    def test_fake_exclusion_of_retained_math_row_is_caught(self):
        graph = copy.deepcopy(self.graph)
        row = next(row for row in graph["payload"]["answer_coverage"] if row["line_id"] == "viewer-173/ocr/112")
        row.update(status="EXCLUDED",reason="EXPLICIT_TIER_OR_REVIEWED_TITLE")
        rehash(graph)
        report = quality_check(self.evidence,graph,self.review)
        self.assertIn("RECOVERY_MATH_REFERENCE_LOST",{i["code"] for i in report["payload"]["issues"]})

    def test_decimal_answer_line97_cannot_be_declared_a_reviewed_title(self):
        review = copy.deepcopy(self.source_review)
        page = next(p for p in self.base["payload"]["pages"] if p["asset_id"] == "viewer-173")
        line = next(l for l in page["ocr_lines"] if l["line_id"] == "viewer-173/ocr/97")
        review["payload"]["reviewed_exclusions"].append({"line_id":line["line_id"],"kind":"title",
             "source_sha256":page["source"]["sha256"],"source_text_sha256":hashlib.sha256(line["text"].encode()).hexdigest()})
        rehash(review)
        with self.assertRaises(ValueError):derive_evidence(self.base,self.recovery,review,artifact)


class RecoveryReplayInterface(unittest.TestCase):
    def test_replay_needs_no_cpu_ocr_runtime(self):
        original_import = __import__
        def no_ocr_import(name,*args,**kwargs):
            if name.split(".",1)[0] in {"rapidocr_onnxruntime","onnxruntime"}:
                raise AssertionError("replay attempted to load an OCR runtime")
            return original_import(name,*args,**kwargs)
        with mock.patch("builtins.__import__",side_effect=no_ocr_import):
            evidence,review,graph,report = replay(FIXTURE)
        self.assertEqual(report["payload"]["summary"]["unique_candidate_links"],34)

    def test_replay_rejects_changed_crop_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)/"fixture"
            shutil.copytree(FIXTURE,fixture)
            target = fixture/"recovery-assets/unit2-q16.png"
            target.write_bytes(target.read_bytes()+b"injected-change")
            with self.assertRaisesRegex(ValueError,"crop hash mismatch"):
                replay(fixture)

    def test_cli_writes_four_bound_artifacts_and_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)/"replay"
            command = [sys.executable,str(ROOT/"tools/replay_recovery_b.py"),"--fixture",str(FIXTURE),"--out",str(out)]
            first = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",check=False)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(json.loads(first.stdout)["unique_candidate_links"],34)
            names = {"evidence.json","recovery-review.json","question-graph.json","check-report.json"}
            self.assertEqual({p.name for p in out.iterdir()},names)
            before = {name:(out/name).read_bytes() for name in names}
            second = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",check=False)
            self.assertNotEqual(second.returncode,0)
            self.assertIn("new directory",second.stderr)
            self.assertEqual(before,{name:(out/name).read_bytes() for name in names})


if __name__ == "__main__":
    unittest.main()
