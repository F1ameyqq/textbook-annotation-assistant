"""Independent pipeline faults with explicit synthetic OCR and real local files.

New objects/journal/report references are coordinated in the stronger faults;
rejection must not rely only on a stale content hash. No model/network is used.
"""
from contextlib import closing
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image,ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from annotation.recognition.baseline import digest,file_digest
from annotation.recognition.pipeline import run_pipeline
from annotation.recognition.pipeline_quality import audit_pipeline,_recognizer_current


def ref(value):
    return {k:value[k]for k in ("artifact_id","revision","content_hash")}


def synthetic_inputs(directory):
    root = Path(directory)
    assets = []
    for aid,order in (("question-page",0),("answer-page",1)):
        image = Image.new("RGB",(200,120),"white")
        draw = ImageDraw.Draw(image)
        draw.rectangle([10,10,80,20],fill="black")
        draw.rectangle([10,45,80,55],fill="black")
        image.save(root/(aid+".png"))
        assets.append({"asset_id":aid,"path":aid+".png","sha256":file_digest(root/(aid+".png")),
                       "width":200,"height":120,"reading_order":order})
    source = {"schema_version":"b-source-trial/0.1","artifact_id":"synthetic-source",
              "book_id":"synthetic-book","scope_id":"synthetic-two-page-scope","assets":assets}
    path = ["Synthetic section"]
    windows = [{"column":0,"y_range":[0,120],"path":path},{"column":1,"y_range":[0,120],"path":path}]
    context = {"schema_version":"b-context-trial/0.1","artifact_id":"synthetic-context",
               "book_id":source["book_id"],"scope_id":source["scope_id"],"pages":{a["asset_id"]:{
                   "sha256":a["sha256"],"role":"question"if a["reading_order"] == 0 else"answer",
                   "windows":copy.deepcopy(windows)}for a in assets}}
    pages = []
    for asset in assets:
        aid = asset["asset_id"]
        texts = ["1.求x的值。","2.求y的值。"]if aid == "question-page"else["1.13","2.24"]
        lines = [{"line_id":aid+"/ocr/"+str(i),"text":text,"bbox":[10,10+i*35,80,20+i*35],"score":.99,
                  "asset_id":aid,"location":{"column":0,"window_index":0,"section_path":path[:]}}for i,text in enumerate(texts)]
        pages.append({"asset_id":aid,"source":copy.deepcopy(asset),"page_role":context["pages"][aid]["role"],
                      "layout":{"mode":"two_columns","cut_x":100,"verified":False},"ocr_lines":lines,
                      "answer_detail_lines":[],"unscoped_line_ids":[]})
    payload = {"pages":pages,"quality_decision":"NOT_EVALUATED","context":copy.deepcopy(context),
               "history_annotations_consumed":False,"limitations":["SYNTHETIC_TEST observations"]}
    evidence = {"schema_version":"b-evidence-trial/0.2","kind":"EvidenceBundleTrial","artifact_id":"synthetic-evidence",
                "revision":1,"run_id":"synthetic-observation-run","book_id":source["book_id"],"scope_id":source["scope_id"],
                "input_refs":[{"artifact_id":"synthetic-baseline","revision":1,"content_hash":"0"*64},
                    {"artifact_id":context["artifact_id"],"content_hash":digest(context)}],
                "producer":{"module":"SYNTHETIC_TEST","version":"test-only"},"payload":payload,"content_hash":digest(payload)}
    review = {"schema_version":"b-review-trial/0.1","artifact_id":"synthetic-review","book_id":source["book_id"],
              "scope_id":source["scope_id"],"reference_quality":"SYNTHETIC_TEST","question_census":{
                  "question-page":{"sha256":assets[0]["sha256"],"printed_numbers":["1","2"]}},"answer_checks":[]}
    paths = []
    for name,value in (("source",source),("context",context),("review",review),("evidence",evidence)):
        target = root/(name+".json")
        target.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
        paths.append(target)
    return paths


def synthetic_baseline_worker(source_path,*,use_ocr=False):
    """Labelled test baseline, with no model invocation."""
    source = json.loads(Path(source_path).read_text(encoding="utf-8"))
    asset = source["assets"][0]
    aid = asset["asset_id"]
    crop_id = aid+"/synthetic-crop"
    texts = ["1.求x的值。","2.求y的值。"]if aid == "question-page"else["1.13","2.24"]
    payload = {"quality_decision":"NOT_EVALUATED","pages":[{"asset_id":aid,"source":asset,
        "regions":[],"crop_transforms":[{"crop_id":crop_id,"asset_id":aid,"original_bbox":[0,0,200,120],
            "crop_to_original":[[1,0,0],[0,1,0],[0,0,1]]}],"ocr_lines":[{"text":text,"score":.99,
            "bbox":[10,10+i*35,80,20+i*35],"crop_id":crop_id}for i,text in enumerate(texts)],"issues":[]}]}
    return {"schema_version":"b-evidence-trial/0.1","kind":"EvidenceBundleTrial","artifact_id":"test-baseline-"+digest(source)[:24],
        "revision":1,"book_id":source["book_id"],"scope_id":source["scope_id"],
        "input_refs":[{"artifact_id":source["artifact_id"],"content_hash":digest(source)}],
        "producer":{"module":"SYNTHETIC_TEST","ocr_enabled":use_ocr},"payload":payload,"content_hash":digest(payload)}


def synthetic_refiner(source_path,baseline,context):
    value = json.loads((Path(source_path).parent/"evidence.json").read_text(encoding="utf-8"))
    value["payload"]["context"] = context
    value["input_refs"] = [ref(baseline),{"artifact_id":context["artifact_id"],"content_hash":digest(context)}]
    value["content_hash"] = digest(value["payload"])
    value["artifact_id"] = "synthetic-refined-"+digest(value["input_refs"])[:24]
    return value


class PipelineQualityRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source,self.context,self.review,self.evidence = synthetic_inputs(self.root)
        self.work = self.root/"work"

    def pipeline(self,**kwargs):
        return run_pipeline(self.source,self.context,self.review,self.work,evidence_path=self.evidence,**kwargs)

    def check(self,report,*,live=False):
        return audit_pipeline(self.source,self.context,self.review,report,self.work,
                              evidence_path=None if live else self.evidence)["payload"]

    def assertCode(self,report,code,*,live=False):
        checked = self.check(report,live=live)
        self.assertFalse(checked["accepted"],checked)
        self.assertIn(code,{i["code"]for i in checked["issues"]},checked)
        self.assertEqual(checked["decision"],"HOLD")

    def read_object(self,descriptor):
        return json.loads((self.work/descriptor["path"]).read_text(encoding="utf-8"))

    def put_object(self,value):
        value["content_hash"] = digest(value["payload"])
        if value["kind"] == "PipelineStageTrial": value["artifact_id"] = "pipeline-stage-"+digest(value["payload"])[:24]
        data = json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()
        path = "objects/"+sha+".json"
        (self.work/path).write_bytes(data)
        return {"path":path,"sha256":sha,"artifact_ref":ref(value)}

    def sql(self,statement,values=()):
        with closing(sqlite3.connect(self.work/"pipeline.sqlite3"))as db:
            with db: db.execute(statement,values)

    def publish_report(self,report):
        report["content_hash"] = digest(report["payload"])
        report["artifact_id"] = "pipeline-report-"+digest([report["payload"]["source_ref"],report["producer"],report["payload"]])[:24]
        descriptor = self.put_object(report)
        with closing(sqlite3.connect(self.work/"pipeline.sqlite3"))as db:
            with db:
                for event_id,text in db.execute("SELECT event_id,details_json FROM stage_events WHERE run_id=? AND event_type='RUN_FINISHED'",(report["run_id"],)):
                    detail = json.loads(text)
                    detail.update(report_ref=ref(report),report_artifact=descriptor)
                    db.execute("UPDATE stage_events SET details_json=? WHERE event_id=?",(json.dumps(detail),event_id))

    def republish(self,report,stage_id,mutate,*,change_implementation=None,repair_downstream=True):
        """Coordinate actual objects, SQL cache/origin/events and current report."""
        found = False
        previous = {}
        for entry in report["payload"]["stages"]:
            name = entry["stage_id"]
            if name == stage_id: found = True
            if not found or not entry.get("output"):
                if entry.get("output"): previous[name] = entry
                if name == "refine"and entry.get("output"): previous["evidence"] = entry
                continue
            if name != stage_id and not repair_downstream: break
            old_key = entry["expected_key"]
            wrapper = self.read_object(entry["output"])
            result = wrapper["payload"]["result"]
            before_result = copy.deepcopy(result)
            if name == stage_id:
                mutate(result)
                if change_implementation: change_implementation(entry["implementation"])
            if name == "assemble":
                result["input_refs"] = [previous["evidence"]["result_ref"]]
                entry["dependencies"]["evidence"] = {"output":previous["evidence"]["output"],"result_ref":previous["evidence"]["result_ref"]}
            if name == "quality":
                result["input_refs"][:2] = [previous["evidence"]["result_ref"],previous["assemble"]["result_ref"]]
                for dependency,key in (("evidence","evidence"),("graph","assemble")):
                    entry["dependencies"][dependency] = {"output":previous[key]["output"],"result_ref":previous[key]["result_ref"]}
            if result != before_result:
                result["content_hash"] = digest(result["payload"])
                result["artifact_id"] = "test-republished-"+digest([name,result["payload"],result["input_refs"]])[:24]
            key = digest({"mode":report["payload"]["mode"],"stage_id":name,"dependencies":entry["dependencies"],"implementation":entry["implementation"]})
            wrapper["payload"].update(expected_key=key,dependencies=copy.deepcopy(entry["dependencies"]),
                                      implementation=copy.deepcopy(entry["implementation"]),result=result)
            descriptor = self.put_object(wrapper)
            entry.update(expected_key=key,output=descriptor,result_ref=ref(result))
            attempt_id = entry["origin_attempt_id"]
            with closing(sqlite3.connect(self.work/"pipeline.sqlite3"))as db:
                with db:
                    db.execute("UPDATE stage_attempts SET expected_key=?,dependencies_json=?,implementation_json=?,output_json=?,result_ref_json=? WHERE attempt_id=?",
                               (key,json.dumps(entry["dependencies"]),json.dumps(entry["implementation"]),json.dumps(descriptor),json.dumps(ref(result)),attempt_id))
                    db.execute("UPDATE stage_cache SET expected_key=?,output_json=?,result_ref_json=? WHERE expected_key=?",
                               (key,json.dumps(descriptor),json.dumps(ref(result)),old_key))
                    for eid,text in db.execute("SELECT event_id,details_json FROM stage_events WHERE attempt_id=?",(attempt_id,)).fetchall():
                        detail = json.loads(text)
                        if "expected_key"in detail: detail["expected_key"] = key
                        if "output"in detail: detail["output"] = descriptor
                        if "result_ref"in detail: detail["result_ref"] = ref(result)
                        db.execute("UPDATE stage_events SET details_json=? WHERE event_id=?",(json.dumps(detail),eid))
            previous[name] = entry
            if name == "refine": previous["evidence"] = entry
        self.publish_report(report)

    def test_cached_three_stages_preserve_scope_and_hold_despite_business_review(self):
        report = self.pipeline()
        checked = self.check(report)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(checked["summary"]["declared_asset_count"],2)
        self.assertEqual(checked["summary"]["completed_stage_count"],3)
        self.assertEqual(report["payload"]["pipeline_state"],"READY")
        self.assertEqual(checked["decision"],"HOLD")
        self.assertFalse(checked["business_acceptance"])
        self.assertEqual(checked["platform_actions"],[])

    def test_cache_hits_retain_actual_origin_and_current_run_receipts(self):
        original = self.pipeline()
        resumed = self.pipeline()
        self.assertTrue(self.check(resumed)["accepted"],self.check(resumed))
        self.assertEqual(resumed["payload"]["counts"]["cache_hits"],3)
        self.assertNotEqual(original["run_id"],resumed["run_id"])
        for old,new in zip(original["payload"]["stages"],resumed["payload"]["stages"]):
            self.assertEqual(old["origin_attempt_id"],new["origin_attempt_id"])
            self.assertEqual(new["current_run_receipt"]["event_type"],"CACHE_HIT")
            self.assertEqual(new["current_run_receipt"]["run_id"],resumed["run_id"])

    def test_default_live_geometry_waits_for_ocr_and_never_claims_full_ready(self):
        report = run_pipeline(self.source,self.context,self.review,self.work)
        checked = self.check(report,live=True)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual(report["payload"]["pipeline_state"],"PARTIAL")
        self.assertEqual(report["payload"]["stages"][1]["reason"],"OCR_REQUIRED")
        self.assertEqual(checked["summary"]["completed_stage_count"],1)

    def test_partial_batch_budget_keeps_all_assets_declared_then_resumes(self):
        partial = run_pipeline(self.source,self.context,self.review,self.work,max_items=1)
        self.assertTrue(self.check(partial,live=True)["accepted"],self.check(partial,live=True))
        self.assertEqual(len(partial["payload"]["source_assets"]),2)
        resumed = run_pipeline(self.source,self.context,self.review,self.work)
        self.assertTrue(self.check(resumed,live=True)["accepted"],self.check(resumed,live=True))
        self.assertEqual(resumed["payload"]["stages"][0]["state"],"DONE")
        self.assertEqual(resumed["payload"]["stages"][1]["reason"],"OCR_REQUIRED")

    def test_review_only_change_reuses_evidence_graph_but_not_quality(self):
        original = self.pipeline()
        review = json.loads(self.review.read_text(encoding="utf-8"))
        review["provenance"] = "New explicit synthetic development review revision"
        self.review.write_text(json.dumps(review),encoding="utf-8")
        changed = self.pipeline()
        checked = self.check(changed)
        self.assertTrue(checked["accepted"],checked)
        self.assertEqual([s["cached"]for s in changed["payload"]["stages"]],[True,True,False])
        self.assertEqual(original["payload"]["stages"][1]["output"],changed["payload"]["stages"][1]["output"])
        self.assertNotEqual(original["payload"]["stages"][2]["expected_key"],changed["payload"]["stages"][2]["expected_key"])

    def test_consumer_does_not_rerun_any_stage_producer(self):
        report = self.pipeline()
        with mock.patch("annotation.recognition.pipeline.run_pipeline",side_effect=AssertionError("runner ran")), \
             mock.patch("annotation.recognition.offline.assemble",side_effect=AssertionError("assembler ran")), \
             mock.patch("annotation.recognition.offline.refine",side_effect=AssertionError("refiner ran")), \
             mock.patch("annotation.recognition.offline.quality_check",side_effect=AssertionError("checker ran")):
            self.assertTrue(self.check(report)["accepted"])

    def test_new_context_cannot_be_attached_to_old_cached_evidence(self):
        report = self.pipeline()
        context = json.loads(self.context.read_text(encoding="utf-8"))
        context["pages"]["question-page"]["windows"][0]["path"] = ["Changed synthetic section"]
        self.context.write_text(json.dumps(context),encoding="utf-8")
        self.assertCode(report,"PIPELINE_EVIDENCE_CONTEXT_MISMATCH")

    def test_bad_source_bytes_are_rejected_without_trusting_ready_sql(self):
        report = self.pipeline()
        (self.root/"answer-page.png").write_bytes(b"changed source")
        self.assertCode(report,"PIPELINE_PERSISTED_DATA_INVALID")

    def test_missing_stage_cannot_be_hidden_by_adjusted_ready_counts(self):
        report = self.pipeline()
        report["payload"]["stages"].pop()
        report["payload"]["counts"].update(declared_stages=2,done=2)
        self.publish_report(report)
        self.assertCode(report,"PIPELINE_STAGE_SCOPE_MISMATCH")

    def test_unknown_line_rejects_coordinated_new_objects_sql_and_downstream_check(self):
        report = self.pipeline()
        self.republish(report,"assemble",lambda graph:graph["payload"]["questions"][0]["fragments"][0].update(evidence_refs=["unobserved-line"]))
        self.assertCode(report,"PIPELINE_GRAPH_FRAGMENT_SOURCE_MISMATCH")

    def test_cross_page_fragment_cannot_use_another_assets_pixels(self):
        report = self.pipeline()
        self.republish(report,"assemble",lambda graph:graph["payload"]["questions"][0]["fragments"][0].update(asset_id="answer-page"))
        self.assertCode(report,"PIPELINE_GRAPH_FRAGMENT_SOURCE_MISMATCH")

    def test_duplicate_entity_id_rejects_even_when_summary_counts_are_preserved(self):
        report = self.pipeline()
        def mutate(graph): graph["payload"]["questions"][1]["question_id"] = graph["payload"]["questions"][0]["question_id"]
        self.republish(report,"assemble",mutate)
        self.assertCode(report,"PIPELINE_GRAPH_ENTITY_ID_REUSED")

    def test_aggregate_text_cannot_diverge_from_unchanged_source_fragments(self):
        report = self.pipeline()
        self.republish(report,"assemble",lambda graph:graph["payload"]["answers"][0].update(text="invented answer"))
        self.assertCode(report,"PIPELINE_GRAPH_TEXT_PROJECTION_MISMATCH")

    def test_omitted_source_ledger_row_cannot_shrink_answer_scope(self):
        report = self.pipeline()
        self.republish(report,"assemble",lambda graph:graph["payload"]["answer_coverage"].pop())
        self.assertCode(report,"PIPELINE_GRAPH_LEDGER_SCOPE_MISMATCH")

    def test_graph_source_range_cannot_shrink_with_coordinated_report_and_attempts(self):
        report = self.pipeline()
        self.republish(report,"evidence",lambda evidence:evidence["payload"]["pages"].pop())
        self.assertCode(report,"PIPELINE_EVIDENCE_SOURCE_SCOPE_MISMATCH")

    def test_upstream_only_hash_change_does_not_make_old_downstream_dependencies_current(self):
        report = self.pipeline()
        self.republish(report,"evidence",lambda evidence:evidence["payload"]["limitations"].append("changed"),repair_downstream=False)
        self.assertCode(report,"PIPELINE_STAGE_DEPENDENCY_MISMATCH")

    def test_quality_summary_is_compared_to_actual_graph(self):
        report = self.pipeline()
        self.republish(report,"quality",lambda check:check["payload"]["summary"].update(questions=0))
        self.assertCode(report,"PIPELINE_QUALITY_SUMMARY_MISMATCH")

    def test_business_review_required_cannot_be_cleared_by_coordinated_counts(self):
        report = self.pipeline()
        def mutate(check):
            p = check["payload"]
            p["issues"] = [i for i in p["issues"]if i["code"] != "BUSINESS_REVIEW_REQUIRED"]
            p["summary"]["issues"] = len(p["issues"])
        self.republish(report,"quality",mutate)
        self.assertCode(report,"PIPELINE_QUALITY_BUSINESS_REVIEW_MISSING")

    def test_regex_and_schema_global_receipts_must_match_current_source(self):
        for stage,name in (("assemble","QSTART"),("evidence","EVIDENCE_SCHEMA")):
            with self.subTest(stage=stage,name=name):
                # Separate workdirs keep each coordinated fault independent.
                self.work = self.root/("work-"+stage)
                report = self.pipeline()
                def alter(implementation):
                    implementation["configuration"]["offline_globals"][name] = {"pattern":"changed","flags":32}if name == "QSTART"else"b-evidence-trial/99"
                self.republish(report,stage,lambda result:None,change_implementation=alter)
                self.assertCode(report,"PIPELINE_IMPLEMENTATION_VERSION_MISMATCH")

    def test_missing_success_event_and_forged_current_cache_receipt_reject(self):
        report = self.pipeline()
        self.sql("DELETE FROM stage_events WHERE stage_id='assemble' AND event_type='STAGE_SUCCEEDED'")
        self.assertCode(report,"PIPELINE_ATTEMPT_EVENT_MISMATCH")
        self.work = self.root/"second-work"
        self.pipeline()
        report = self.pipeline()
        report["payload"]["stages"][1]["current_run_receipt"]["event_id"] = -1
        self.publish_report(report)
        self.assertCode(report,"PIPELINE_CURRENT_RUN_RECEIPT_MISMATCH")

    def test_interrupted_assembly_is_terminalized_then_safely_resumed(self):
        from annotation.recognition import pipeline
        original = pipeline._wrapper
        pending = [True]
        def interrupt(source,mode,stage,*args):
            if stage == "assemble"and pending:
                pending.pop()
                raise KeyboardInterrupt("synthetic interruption before publication")
            return original(source,mode,stage,*args)
        with mock.patch.object(pipeline,"_wrapper",side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt): self.pipeline()
        recovered = self.pipeline()
        self.assertTrue(self.check(recovered)["accepted"],self.check(recovered))
        self.assertEqual(recovered["payload"]["stages"][0]["cached"],True)

    def test_explicit_synthetic_refinement_keeps_cpu_and_test_provenance_distinct(self):
        with mock.patch("annotation.recognition.pipeline.refine",synthetic_refiner):
            report = run_pipeline(self.source,self.context,self.review,self.work,use_ocr=True,worker=synthetic_baseline_worker)
        checked = self.check(report,live=True)
        self.assertTrue(checked["accepted"],checked)
        refinement = report["payload"]["stages"][1]["implementation"]
        self.assertEqual(refinement["configuration"]["refinement_mode"],"SYNTHETIC_TEST_OVERRIDE")
        self.assertEqual(refinement["recognizer"]["execution_kind"],"SYNTHETIC_TEST")
        self.assertEqual(refinement["recognizer"]["model_files"],[])

    def test_refinement_cannot_drop_its_recognizer_receipt_after_coordinated_rehash(self):
        with mock.patch("annotation.recognition.pipeline.refine",synthetic_refiner):
            report = run_pipeline(self.source,self.context,self.review,self.work,use_ocr=True,worker=synthetic_baseline_worker)
        self.republish(report,"refine",lambda result:None,
                       change_implementation=lambda implementation:implementation.update(recognizer=None))
        self.assertCode(report,"PIPELINE_RECOGNIZER_VERSION_MISMATCH",live=True)

    def test_stage_setup_failure_has_a_terminal_report_without_a_fabricated_attempt(self):
        from annotation.recognition import pipeline
        original = pipeline._implementation
        def unavailable(stage,*args):
            if stage == "assemble": raise RuntimeError("synthetic unavailable dependency receipt")
            return original(stage,*args)
        with mock.patch.object(pipeline,"_implementation",side_effect=unavailable): report = self.pipeline()
        checked = self.check(report)
        self.assertTrue(checked["accepted"],checked)
        failed = report["payload"]["stages"][1]
        self.assertEqual(failed["reason"],"STAGE_SETUP_FAILED")
        self.assertIsNone(failed["expected_key"])
        self.assertIsNone(failed["implementation"])
        self.assertIsNone(failed["origin_attempt_id"])
        self.assertEqual(report["payload"]["pipeline_state"],"FAILED")

    def test_actual_cpu_model_receipt_cannot_rehash_a_stale_weight_into_current_version(self):
        if importlib.util.find_spec("rapidocr_onnxruntime")is None:
            self.skipTest("optional CPU OCR model receipt is not installed")
        from annotation.recognition import pipeline
        # This reads package/model metadata; it never instantiates a model.
        receipt = pipeline._implementation("refine","LIVE_BATCH","LIVE_CPU_OCR",True,None)["recognizer"]
        self.assertTrue(_recognizer_current(receipt,use_ocr=True,synthetic=False))
        changed = copy.deepcopy(receipt)
        changed["model_files"][0]["sha256"] = "0"*64
        changed["fingerprint"] = digest({k:v for k,v in changed.items()if k != "fingerprint"})
        self.assertFalse(_recognizer_current(changed,use_ocr=True,synthetic=False))


if __name__ == "__main__": unittest.main()
