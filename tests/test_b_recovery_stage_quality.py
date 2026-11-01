"""Independent recovery migration faults; generated pixels are SYNTHETIC_TEST.

Expected raw source membership is fixed by the package, never made by an
assembler. Coordinated payload hashes/identities are recomputed in fault tests.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import sqlite3
import shutil
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"),str(ROOT/"tests")]
import test_b_pipeline_cli as common
from test_b_pipeline_recovery_cli import make_package
from annotation.recognition.baseline import code_digest,digest,file_digest
from annotation.recognition.recovery_stage import recover_evidence,build_recovery_review
from annotation.recognition.recovery_stage_quality import audit_recovery_stage,audit_recovery_review
from annotation.recognition.offline import assemble,quality_check
from annotation.recognition.pipeline import run_pipeline
from annotation.recognition.pipeline_quality import audit_pipeline


def ref(value):
    return {key:value[key]for key in ("artifact_id","revision","content_hash")}


def sign(value,source):
    """Rehash a fault consistently, retaining the unchanged producer receipt."""
    value["content_hash"] = digest(value["payload"])
    identity_source = {"book_id":source["book_id"],"scope_id":source["scope_id"],"identity_ref":ref(source)}
    if source.get("run_id"): identity_source["run_id"] = source["run_id"]
    identity = digest({"schema":value["schema_version"],"source":identity_source,"payload":value["payload"],
        "inputs":value["input_refs"],"producer":value["producer"]})
    value["artifact_id"] = value["kind"].lower()+"-"+identity[:24]
    return value


class RecoveryStageQuality(unittest.TestCase):
    write = common.PipelineCLI.write

    def setUp(self):
        common.PipelineCLI.setUp(self)
        answer = self.evidence["payload"]["pages"][1]
        parent = answer["ocr_lines"][0]
        answer["answer_detail_lines"].append(dict(line_id=parent["line_id"]+"/detail/0",
            parent_line_id=parent["line_id"],text=parent["text"],score=.99,bbox=parent["bbox"][:],
            location=copy.deepcopy(parent["location"]),crop_to_original=[[1,0,0],[0,1,0],[0,0,1]]))
        self.evidence["content_hash"] = digest(self.evidence["payload"])
        self.write(self.evidence_path,self.evidence)
        self.package_path,self.package = make_package(self.root,self.source,self.evidence)
        self.current = copy.deepcopy(self.evidence)
        self.current["artifact_id"] = "a-new-live-evidence-identity-with-identical-payload"
        self.current["run_id"] = "new-live-run"
        self.derived = recover_evidence(self.current,self.package_path,self.source_path,self.context)
        self.review_artifact = build_recovery_review(self.review,self.derived)

    def stage(self,derived=None,current=None):
        return audit_recovery_stage(self.source_path,self.package_path,current or self.current,derived or self.derived)

    def codes(self,check):
        return {i["code"]for i in check["payload"]["issues"]}

    def rejected(self,check,code):
        self.assertFalse(check["payload"]["accepted"],check)
        self.assertIn(code,self.codes(check))
        self.assertEqual(check["payload"]["decision"],"HOLD")
        self.assertFalse(check["payload"]["business_acceptance"])

    def document(self,name):
        return json.loads((self.package_path.parent/self.package["documents"][name]["path"]).read_text(encoding="utf-8"))

    def rewrite_document(self,name,value):
        path = self.package_path.parent/self.package["documents"][name]["path"]
        self.write(path,value)
        self.package["documents"][name].update(text_sha256=hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest(),artifact_ref=ref(value))
        self.write(self.package_path,self.package)

    def test_identical_whole_payload_new_identity_retains_historical_receipts(self):
        frozen = {p:p.read_bytes()for p in self.package_path.parent.iterdir()}
        checked = self.stage()
        self.assertTrue(checked["payload"]["accepted"],checked)
        p = self.derived["payload"]
        self.assertEqual(p["base_evidence_archive"],self.evidence)
        self.assertEqual(p["recovery_evidence_archive"],self.document("recovery"))
        self.assertTrue(p["recovery_migration"]["current_identity_differs"])
        self.assertEqual(p["recovery_migration"]["new_ocr_calls"],0)
        self.assertEqual(checked["payload"]["summary"]["raw_hypothesis_count"],1)
        self.assertEqual(checked["payload"]["summary"]["replaced_raw_count"],1)
        self.assertEqual(p["pages"][1]["answer_detail_lines"],[])
        for path,data in frozen.items(): self.assertEqual(path.read_bytes(),data)

    def test_same_base_reference_changed_generation_time_keeps_derived_chain_stable(self):
        later = copy.deepcopy(self.current)
        later["created_at"] = "2030-12-31T23:59:59.999999+00:00"
        d = recover_evidence(later,self.package_path,self.source_path,self.context)
        self.assertEqual(ref(later),ref(self.current))
        self.assertEqual(ref(d),ref(self.derived))
        self.assertNotIn("created_at",d)
        self.assertEqual(d["payload"]["base_evidence_archive"],self.evidence)
        rr = build_recovery_review(self.review,d)
        self.assertEqual(ref(rr),ref(self.review_artifact))
        graph1,graph2 = assemble(self.derived),assemble(d)
        self.assertEqual(ref(graph1),ref(graph2))
        check1 = quality_check(self.derived,graph1,self.review_artifact["payload"]["review"])
        check2 = quality_check(d,graph2,rr["payload"]["review"])
        self.assertEqual(ref(check1),ref(check2))
        self.assertTrue(self.stage(d,later)["payload"]["accepted"])

    def test_same_identity_base_is_also_valid(self):
        d = recover_evidence(self.evidence,self.package_path,self.source_path,self.context)
        self.assertTrue(self.stage(d,self.evidence)["payload"]["accepted"])
        self.assertFalse(d["payload"]["recovery_migration"]["current_identity_differs"])

    def test_same_page_sha_changed_raw_text_score_detail_or_location_rejected(self):
        for field in ("text","score","detail","location"):
            with self.subTest(field=field):
                b,d = copy.deepcopy(self.current),copy.deepcopy(self.derived)
                page = b["payload"]["pages"][1]
                if field == "detail": page["answer_detail_lines"][0]["score"] = .1
                elif field == "location": page["ocr_lines"][0]["location"]["section_path"] = ["Other section"]
                else: page["ocr_lines"][0][field] = "same image but changed OCR"if field == "text"else .1
                b["content_hash"] = digest(b["payload"])
                d["input_refs"][0] = ref(b)
                d["payload"]["recovery_migration"].update(current_base_ref=ref(b),current_payload_sha256=digest(b["payload"]))
                sign(d,b)
                self.rejected(self.stage(d,b),"RECOVERY_BASE_PAYLOAD_NOT_IDENTICAL")

    def test_recovered_base_cannot_be_recovered_again(self):
        self.rejected(self.stage(current=self.derived),"RECOVERY_CURRENT_BASE_VERSION_INVALID")

    def test_old_recovery_receipt_cannot_be_rebased_to_new_id(self):
        d = copy.deepcopy(self.derived)
        archive = d["payload"]["recovery_evidence_archive"]
        archive["payload"]["base_evidence_ref"] = ref(self.current)
        archive["input_refs"][0] = ref(self.current)
        archive["content_hash"] = digest(archive["payload"])
        d["payload"]["recovery_ref"] = ref(archive)
        sign(d,self.current)
        self.rejected(self.stage(d),"RECOVERY_ORIGINAL_ARCHIVE_OR_REFERENCE_CHANGED")

    def test_drop_original_raw_or_math_source_is_not_silent(self):
        d = copy.deepcopy(self.derived)
        d["payload"]["pages"][0]["ocr_lines"] = []
        sign(d,self.current)
        self.rejected(self.stage(d),"RECOVERY_ACTIVE_RAW_PROJECTION_MISMATCH")

    def test_coordinated_recovered_text_and_order_edits_rejected(self):
        for field,value in (("text","1.解：2+2=5"),("assembly_order",[0,0,0]),("independent_confirmation",True)):
            with self.subTest(field=field):
                d = copy.deepcopy(self.derived)
                d["payload"]["pages"][1]["ocr_lines"][0][field] = value
                sign(d,self.current)
                self.rejected(self.stage(d),"RECOVERY_ACTIVE_RAW_PROJECTION_MISMATCH")

    def test_replaced_details_cannot_return_as_duplicate_sources(self):
        d = copy.deepcopy(self.derived)
        d["payload"]["pages"][1]["answer_detail_lines"] = copy.deepcopy(self.evidence["payload"]["pages"][1]["answer_detail_lines"])
        sign(d,self.current)
        self.rejected(self.stage(d),"RECOVERY_ACTIVE_DETAIL_PROJECTION_MISMATCH")

    def test_replacement_ledger_cannot_drop_a_selected_line(self):
        d = copy.deepcopy(self.derived)
        d["payload"]["recovery_application"]["replacement_line_ids"] = []
        sign(d,self.current)
        self.rejected(self.stage(d),"RECOVERY_APPLICATION_LEDGER_MISMATCH")

    def test_alternative_raw_variant_retained_even_if_not_selected(self):
        recovery = self.document("recovery")
        variant = copy.deepcopy(recovery["payload"]["probes"][0]["variants"][0])
        variant["variant_id"] = "alternative"
        variant["raw_ocr_result"][0][0] = "1.解：2+2=9"
        variant["ocr_lines"][0].update(line_id="recovery/synthetic-answer/alternative/0",text="1.解：2+2=9")
        recovery["payload"]["probes"][0]["variants"].append(variant)
        recovery["content_hash"] = digest(recovery["payload"])
        self.rewrite_document("recovery",recovery)
        sr = self.document("source_review")
        sr["payload"]["recovery_ref"] = ref(recovery);sr["input_refs"][1] = ref(recovery)
        sr["content_hash"] = digest(sr["payload"])
        self.rewrite_document("source_review",sr)
        d = recover_evidence(self.current,self.package_path,self.source_path,self.context)
        self.assertTrue(self.stage(d)["payload"]["accepted"])
        self.assertEqual(self.stage(d)["payload"]["summary"]["raw_hypothesis_count"],2)
        d["payload"]["recovery_evidence_archive"]["payload"]["probes"][0]["variants"].pop()
        sign(d,self.current)
        self.rejected(self.stage(d),"RECOVERY_ORIGINAL_ARCHIVE_OR_REFERENCE_CHANGED")

    def test_output_fake_human_or_new_cpu_receipt_rejected(self):
        d = copy.deepcopy(self.derived)
        d["producer"] = {"module":"human","execution_kind":"HUMAN_REVIEWED","new_ocr_calls":100}
        sign(d,self.current)
        self.rejected(self.stage(d),"RECOVERY_OUTPUT_PRODUCER_OR_IDENTITY_MISMATCH")

    def test_synthetic_receipt_cannot_be_silently_relabelled_cpu(self):
        recovery = self.document("recovery")
        recovery["producer"] = {"module":"annotation.recognition.recovery","engine":"rapidocr_onnxruntime",
            "device":"CPU","dependencies":{"synthetic":"invented"},"dependency_sha256":digest({"synthetic":"invented"}),
            "model_files":[{"name":"pretend.onnx","sha256":"1"*64}]}
        self.rewrite_document("recovery",recovery)
        self.rejected(self.stage(),"RECOVERY_BACKEND_PROVENANCE_INVALID")

    def test_arbitrary_output_identity_is_rejected_without_payload_change(self):
        d = copy.deepcopy(self.derived);d["artifact_id"] = "forged-derived-identity"
        self.rejected(self.stage(d),"RECOVERY_OUTPUT_PRODUCER_OR_IDENTITY_MISMATCH")

    def test_white_crop_with_coordinated_file_and_manifest_hash_rejected(self):
        recovery = self.document("recovery")
        probe = recovery["payload"]["probes"][0]
        path = self.package_path.parent/probe["crop_path"]
        Image.new("RGB",(270,20),"white").save(path)
        probe["crop_sha256"] = file_digest(path)
        recovery["content_hash"] = digest(recovery["payload"])
        self.rewrite_document("recovery",recovery)
        self.rejected(self.stage(),"RECOVERY_CROP_SOURCE_PIXELS_MISMATCH")

    def test_wrong_source_side_with_same_dimensions_rejected(self):
        recovery = self.document("recovery")
        recovery["payload"]["probes"][0]["crop_bbox"] = [390,210,660,230]
        recovery["content_hash"] = digest(recovery["payload"])
        self.rewrite_document("recovery",recovery)
        self.rejected(self.stage(),"RECOVERY_CROP_SOURCE_PIXELS_MISMATCH")

    def test_unhashed_or_escaping_package_paths_rejected(self):
        for descriptor in ({"path":"../synthetic-evidence.json"}, {"text_sha256":None}):
            with self.subTest(descriptor=descriptor):
                package = copy.deepcopy(self.package)
                package["documents"]["base_evidence"].update(descriptor)
                self.write(self.package_path,package)
                checked = self.stage()
                self.assertFalse(checked["payload"]["accepted"])
        self.write(self.package_path,self.package)

    def test_crlf_normalized_text_hash_is_valid_but_byte_receipt_changes(self):
        path = self.package_path.parent/self.package["documents"]["base_evidence"]["path"]
        text = path.read_text(encoding="utf-8")
        path.write_bytes(text.encode("utf-8")if b"\r\n"in path.read_bytes()else text.replace("\n","\r\n").encode("utf-8"))
        self.assertEqual(hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest(),self.package["documents"]["base_evidence"]["text_sha256"])
        d = recover_evidence(self.current,self.package_path,self.source_path,self.context)
        self.assertTrue(self.stage(d)["payload"]["accepted"])
        self.assertEqual(ref(d),ref(self.derived))
        rr = build_recovery_review(self.review,d)
        self.assertEqual(ref(rr),ref(self.review_artifact))
        self.assertTrue(self.stage()["payload"]["accepted"])

    def test_review_migration_retains_fields_and_holds(self):
        checked = audit_recovery_review(self.review,self.derived,self.review_artifact)
        self.assertTrue(checked["payload"]["accepted"],checked)
        self.assertEqual(checked["payload"]["decision"],"HOLD")
        self.assertEqual(self.review_artifact["payload"]["review"]["answer_checks"],self.review["answer_checks"])

    def test_review_human_producer_or_arbitrary_id_rejected(self):
        for key,value in (("producer",{"module":"HUMAN_GOLD"}),("artifact_id","fake-review-id")):
            with self.subTest(key=key):
                rr = copy.deepcopy(self.review_artifact);rr[key] = value
                if key == "producer": sign(rr,self.derived)
                self.rejected(audit_recovery_review(self.review,self.derived,rr),"RECOVERY_OUTPUT_PRODUCER_OR_IDENTITY_MISMATCH")

    def test_review_census_cannot_be_changed_during_migration(self):
        rr = copy.deepcopy(self.review_artifact)
        rr["payload"]["review"]["question_census"] = {}
        sign(rr,self.derived)
        self.rejected(audit_recovery_review(self.review,self.derived,rr),"RECOVERY_REVIEW_ORIGINAL_FIELDS_CHANGED")

    def test_remaining_math_source_group_not_retired_or_removed(self):
        review = copy.deepcopy(self.review)
        review["unresolved_source_groups"] = [{"group_id":"remaining-math","source_line_ids":["source-not-replaced"]}]
        rr = build_recovery_review(review,self.derived)
        self.assertTrue(audit_recovery_review(review,self.derived,rr)["payload"]["accepted"])
        rr["payload"]["review"]["unresolved_source_groups"] = []
        rr["payload"]["review"]["retired_unresolved_source_groups"] = copy.deepcopy(review["unresolved_source_groups"])
        sign(rr,self.derived)
        self.rejected(audit_recovery_review(review,self.derived,rr),"RECOVERY_REVIEW_UNRESOLVED_SOURCE_LOST")

    def test_review_already_migrated_rejected(self):
        migrated = copy.deepcopy(self.review)
        migrated["recovery_migration_ref"] = ref(self.derived)
        self.rejected(audit_recovery_review(migrated,self.derived,self.review_artifact),"RECOVERY_REVIEW_ALREADY_MIGRATED")

    def test_pipeline_full_then_review_only_reuses_recovery_and_graph(self):
        self.write(self.evidence_path,self.current)
        args = (self.source_path,self.context_path,self.review_path,self.workdir)
        kw = dict(evidence_path=self.evidence_path,recovery_path=self.package_path)
        first = run_pipeline(*args,**kw)
        checked = audit_pipeline(self.source_path,self.context_path,self.review_path,first,self.workdir,**kw)
        self.assertTrue(checked["payload"]["accepted"],checked)
        self.review["provenance"] += "; updated review only"
        self.write(self.review_path,self.review)
        second = run_pipeline(*args,**kw)
        bystage = {s["stage_id"]:s for s in second["payload"]["stages"]}
        self.assertEqual([s for s,v in bystage.items()if v["cached"]],["evidence","recover","assemble"])
        self.assertFalse(bystage["recovery_review"]["cached"])
        self.assertFalse(bystage["quality"]["cached"])
        checked = audit_pipeline(self.source_path,self.context_path,self.review_path,second,self.workdir,**kw)
        self.assertTrue(checked["payload"]["accepted"],checked)

    def test_model_visual_formula_never_promoted_to_cpu_or_human(self):
        sr = self.document("source_review")
        sr["payload"]["formula_candidates"] = [{"candidate_id":"synthetic-model-visual-formula",
            "method":"MODEL_VISUAL_DEVELOPMENT_TRANSCRIPTION","verification_status":"UNVERIFIED",
            "cpu_ocr":False,"human_verified":False,"applied_to_ocr":False,"business_acceptance":False}]
        sr["content_hash"] = digest(sr["payload"])
        self.rewrite_document("source_review",sr)
        d = recover_evidence(self.current,self.package_path,self.source_path,self.context)
        self.assertTrue(self.stage(d)["payload"]["accepted"])
        sr["payload"]["formula_candidates"][0]["cpu_ocr"] = True
        sr["content_hash"] = digest(sr["payload"])
        self.rewrite_document("source_review",sr)
        d = recover_evidence(self.current,self.package_path,self.source_path,self.context)
        self.rejected(self.stage(d),"RECOVERY_VISUAL_FORMULA_PROVENANCE_ESCALATED")

    def test_retained_source_review_math_group_cannot_be_omitted(self):
        sr = self.document("source_review")
        sr["payload"]["remaining_source_groups"] = [{"group_id":"synthetic-unassigned-math",
            "source_line_ids":[self.evidence["payload"]["pages"][0]["ocr_lines"][0]["line_id"]],
            "reason":"Ambiguous generated mathematics; not a completed transcription"}]
        sr["content_hash"] = digest(sr["payload"])
        self.rewrite_document("source_review",sr)
        d = recover_evidence(self.current,self.package_path,self.source_path,self.context)
        self.assertTrue(self.stage(d)["payload"]["accepted"])
        self.assertEqual(self.stage(d)["payload"]["summary"]["retained_source_group_count"],1)
        d["payload"]["source_review"]["remaining_source_groups"] = []
        d["payload"]["recovery_source_review"]["remaining_source_groups"] = []
        sign(d,self.current)
        self.rejected(self.stage(d),"RECOVERY_ORIGINAL_ARCHIVE_OR_REFERENCE_CHANGED")

    def test_regression_addition_is_exact_source_span_and_never_verified(self):
        sr = self.document("source_review")
        lid = "recovery/synthetic-answer/scale1/0"
        text = "1.解：2+2=4"
        addition = {"case_id":"q1-synthetic-regression","line_id":lid,"text_spans":[[0,len(text)]],
            "source_text_sha256":hashlib.sha256(text.encode()).hexdigest()}
        sr["payload"]["regression_additions"] = [addition]
        sr["content_hash"] = digest(sr["payload"])
        self.rewrite_document("source_review",sr)
        d = recover_evidence(self.current,self.package_path,self.source_path,self.context)
        review = copy.deepcopy(self.review)
        review["multiline_checks"] = [{"case_id":addition["case_id"],"expected_source_line_ids":[],
            "expected_source_spans":[],"observed_source_gaps":[{"reason":"synthetic missing role"}]}]
        rr = build_recovery_review(review,d)
        self.assertTrue(audit_recovery_review(review,d,rr)["payload"]["accepted"])
        actual = rr["payload"]["review"]["multiline_checks"][0]
        self.assertEqual(actual["expected_source_line_ids"],[lid])
        self.assertEqual(actual["observed_source_gaps"][0]["recovery_status"],"PARTIALLY_RECOVERED_UNVERIFIED")
        actual["expected_source_spans"][0]["text_spans"] = [[0,1]]
        sign(rr,d)
        self.rejected(audit_recovery_review(review,d,rr),"RECOVERY_REVIEW_REGRESSION_SOURCE_MISMATCH")

    def republish_stage_and_journal(self,report,stage_id,change):
        """Coordinate immutable object, SQL/event and terminal report references."""
        def put(value):
            value["content_hash"] = digest(value["payload"])
            if value["kind"] == "PipelineStageTrial": value["artifact_id"] = "pipeline-stage-"+digest(value["payload"])[:24]
            data = json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
            sha = hashlib.sha256(data).hexdigest()
            path = "objects/"+sha+".json"
            (self.workdir/path).write_bytes(data)
            return {"path":path,"sha256":sha,"artifact_ref":ref(value)}
        entry = next(s for s in report["payload"]["stages"]if s["stage_id"] == stage_id)
        wrapper = json.loads((self.workdir/entry["output"]["path"]).read_text(encoding="utf-8"))
        change(wrapper["payload"]["result"])
        output = put(wrapper)
        result_ref = ref(wrapper["payload"]["result"])
        entry.update(output=output,result_ref=result_ref)
        with sqlite3.connect(self.workdir/"pipeline.sqlite3")as db:
            db.execute("UPDATE stage_attempts SET output_json=?,result_ref_json=? WHERE attempt_id=?",
                (json.dumps(output),json.dumps(result_ref),entry["origin_attempt_id"]))
            db.execute("UPDATE stage_cache SET output_json=?,result_ref_json=? WHERE expected_key=?",
                (json.dumps(output),json.dumps(result_ref),entry["expected_key"]))
            for event_id,text in db.execute("SELECT event_id,details_json FROM stage_events WHERE attempt_id=?",(entry["origin_attempt_id"],)).fetchall():
                detail = json.loads(text)
                if "output"in detail: detail["output"] = output
                if "result_ref"in detail: detail["result_ref"] = result_ref
                db.execute("UPDATE stage_events SET details_json=? WHERE event_id=?",(json.dumps(detail),event_id))
            report["content_hash"] = digest(report["payload"])
            report["artifact_id"] = "pipeline-report-"+digest([report["payload"]["source_ref"],report["producer"],report["payload"]])[:24]
            report_descriptor = put(report)
            row = db.execute("SELECT event_id,details_json FROM stage_events WHERE run_id=? AND event_type='RUN_FINISHED'",(report["run_id"],)).fetchone()
            detail = json.loads(row[1]);detail.update(report_ref=ref(report),report_artifact=report_descriptor)
            db.execute("UPDATE stage_events SET details_json=? WHERE event_id=?",(json.dumps(detail),row[0]))

    def test_pipeline_coordinated_recovery_object_sql_report_fault_rejected_semantically(self):
        self.write(self.evidence_path,self.current)
        kw = dict(evidence_path=self.evidence_path,recovery_path=self.package_path)
        report = run_pipeline(self.source_path,self.context_path,self.review_path,self.workdir,stop_after="recover",**kw)
        def fault(result):
            result["payload"]["pages"][1]["ocr_lines"][0]["text"] = "1.解：2+2=5"
            sign(result,self.current)
        self.republish_stage_and_journal(report,"recover",fault)
        check = audit_pipeline(self.source_path,self.context_path,self.review_path,report,self.workdir,**kw)
        self.rejected(check,"PIPELINE_RECOVERY_MIGRATION_REJECTED")
        self.assertNotIn("PIPELINE_STAGE_WRAPPER_MISMATCH",self.codes(check))
        self.assertNotIn("PIPELINE_REPORT_RECEIPT_MISMATCH",self.codes(check))
        issue = next(i for i in check["payload"]["issues"]if i["code"] == "PIPELINE_RECOVERY_MIGRATION_REJECTED")
        self.assertIn("RECOVERY_ACTIVE_RAW_PROJECTION_MISMATCH",{i["code"]for i in issue["detail"]})

    def test_pipeline_coordinated_review_object_sql_report_fault_rejected_semantically(self):
        self.write(self.evidence_path,self.current)
        kw = dict(evidence_path=self.evidence_path,recovery_path=self.package_path)
        report = run_pipeline(self.source_path,self.context_path,self.review_path,self.workdir,stop_after="recovery_review",**kw)
        recovered_entry = next(s for s in report["payload"]["stages"]if s["stage_id"] == "recover")
        recovered = json.loads((self.workdir/recovered_entry["output"]["path"]).read_text(encoding="utf-8"))["payload"]["result"]
        def fault(result):
            result["payload"]["review"]["question_census"] = {}
            sign(result,recovered)
        self.republish_stage_and_journal(report,"recovery_review",fault)
        check = audit_pipeline(self.source_path,self.context_path,self.review_path,report,self.workdir,**kw)
        self.rejected(check,"PIPELINE_RECOVERY_REVIEW_REJECTED")
        self.assertNotIn("PIPELINE_STAGE_WRAPPER_MISMATCH",self.codes(check))
        self.assertNotIn("PIPELINE_REPORT_RECEIPT_MISMATCH",self.codes(check))

    @unittest.skipUnless((ROOT.parent/"usense-readonly/source.json").is_file(),"Original real-book source JPGs are external; no downloading or OCR in tests")
    def test_real_package_crlf_lf_preserves_migration_and_review_identity(self):
        fixture = ROOT/"tests/fixtures/book46007447"
        target = self.root/"real-recovery-package"
        target.mkdir()
        names = ("recovery-package.json","ocr-evidence.json","recovery-evidence.json","source-recovery-review.json")
        for name in names:
            (target/name).write_bytes((fixture/name).read_text(encoding="utf-8").encode("utf-8"))
        shutil.copytree(fixture/"recovery-assets",target/"recovery-assets")
        source_path = ROOT.parent/"usense-readonly/source.json"
        context = json.loads((fixture/"context.json").read_text(encoding="utf-8"))
        base = json.loads((fixture/"ocr-evidence.json").read_text(encoding="utf-8"))
        base["artifact_id"] = "real-cpu-new-envelope-identical-full-payload"
        review = json.loads((fixture/"review.json").read_text(encoding="utf-8"))
        package = target/"recovery-package.json"
        lf = recover_evidence(base,package,source_path,context)
        lf_review = build_recovery_review(review,lf)
        checked = audit_recovery_stage(source_path,package,base,lf)
        self.assertTrue(checked["payload"]["accepted"],checked)
        self.assertEqual(checked["payload"]["summary"]["probe_count"],27)
        self.assertEqual(checked["payload"]["summary"]["source_asset_count"],5)
        for name in names:
            text = (target/name).read_text(encoding="utf-8")
            (target/name).write_bytes(text.replace("\n","\r\n").encode("utf-8"))
        crlf = recover_evidence(base,package,source_path,context)
        crlf_review = build_recovery_review(review,crlf)
        self.assertEqual(lf["payload"],crlf["payload"])
        self.assertEqual(ref(lf),ref(crlf))
        self.assertEqual(ref(lf_review),ref(crlf_review))
        graph1,graph2 = assemble(lf),assemble(crlf)
        self.assertEqual(ref(graph1),ref(graph2))
        self.assertEqual(ref(quality_check(lf,graph1,lf_review["payload"]["review"])),
            ref(quality_check(crlf,graph2,crlf_review["payload"]["review"])))
        self.assertTrue(audit_recovery_stage(source_path,package,base,crlf)["payload"]["accepted"])
        self.assertTrue(audit_recovery_review(review,crlf,crlf_review)["payload"]["accepted"])

    def test_independent_audit_has_no_producer_import_or_call(self):
        import ast
        path = ROOT/"src/annotation/recognition/recovery_stage_quality.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = {"derive_evidence","derive_review","recover_evidence","build_recovery_review"}
        self.assertFalse([n for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)and n.module in {"recovery_apply","recovery_stage"}])
        self.assertFalse([n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in forbidden])


if __name__ == "__main__": unittest.main()
