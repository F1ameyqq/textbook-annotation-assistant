"""Version-bound draft text stages over generated pixels and synthetic observations."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tests")]
from annotation.recognition import pipeline
from annotation.recognition.baseline import digest
from annotation.recognition.pipeline_quality import audit_pipeline
from test_b_inline_stage import make_inline_fixture,write


def stage_result(workdir,entry):
    return json.loads((Path(workdir)/entry["output"]["path"]).read_text(encoding="utf-8"))["payload"]["result"]


def run_fixture(data,workdir,**options):
    kwargs=dict(evidence_path=data["evidence_path"],inline_path=data["package_path"],inline_source_path=data["original"])
    if data.get("continuation_path"):
        kwargs.update(continuation_path=data["continuation_path"],adjacent_source_path=data["adjacent_source_path"])
    kwargs.update(options)
    return pipeline.run_pipeline(data["source_path"],data["context_path"],data["review_path"],workdir,**kwargs)


def make_pipeline_revision_fixture(directory,*,continuation=False):
    """The plan is created from actual current pipeline outputs, never fake CPU."""
    from annotation.recognition.content_revision import make_revision_plan
    root=Path(directory);data=make_inline_fixture(root,continuation=continuation);workdir=root/"pipeline"
    report=run_fixture(data,workdir)
    if report["payload"]["pipeline_state"]!="READY":raise AssertionError(report["payload"]["stages"])
    rows={s["stage_id"]:s for s in report["payload"]["stages"]}
    e=stage_result(workdir,rows["inline_prepare"])["payload"]["base_evidence_archive"]
    g=stage_result(workdir,rows["inline_apply"])["payload"]["graph"]
    check=stage_result(workdir,rows["inline_quality"])
    answer=next(a for a in g["payload"]["answers"] if any("继续"in f["text"] for f in a["fragments"]))
    fragment=next(f for f in answer["fragments"] if "继续"in f["text"])
    lo=fragment["text"].index("继续")
    target=dict(answer_id=answer["answer_id"],fragment_id=fragment["fragment_id"],role=fragment["role"],
        fragment_span=[lo,lo+2],expected_text="继续")
    operation=dict(operation_id="synthetic-edit",kind="EDIT_TEXT",target=target,replacement="1:3",format="plain",reason="SYNTHETIC_TEST draft correction")
    author=dict(kind="SYNTHETIC_TEST",id="pipeline-test",note="Generated source; no human verification")
    plan=make_revision_plan(e,g,check,[operation],author)
    path=root/"content-plan.json";write(path,plan)
    return {**data,"workdir":workdir,"current_evidence":e,"current_graph":g,"current_check":check,"operation":operation,
        "author":author,"plan":plan,"plan_path":path,"base_report":report,"answer_id":answer["answer_id"]}


def resign_plan(plan):
    plan["content_hash"]=digest(plan["payload"])
    body={k:v for k,v in plan.items()if k not in {"artifact_id","content_hash"}}
    plan["artifact_id"]="content-revision-plan-"+digest(body)[:24]
    return plan


class PipelineContentRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.d=make_pipeline_revision_fixture(self.root);self.work=self.d["workdir"]

    def run_pipeline(self,**kwargs):return run_fixture(self.d,self.work,content_revision_path=self.d["plan_path"],**kwargs)
    def rows(self,report):return {s["stage_id"]:s for s in report["payload"]["stages"]}
    def result(self,row):return stage_result(self.work,row)
    def audit(self,report):
        kwargs=dict(evidence_path=self.d["evidence_path"],inline_path=self.d["package_path"],inline_source_path=self.d["original"],content_revision_path=self.d["plan_path"])
        if self.d.get("continuation_path"):kwargs.update(continuation_path=self.d["continuation_path"],adjacent_source_path=self.d["adjacent_source_path"])
        return audit_pipeline(self.d["source_path"],self.d["context_path"],self.d["review_path"],report,self.work,**kwargs)
    def accepted(self,report):
        checked=self.audit(report)
        self.assertTrue(checked["payload"]["accepted"],checked["payload"]["issues"])
        self.assertEqual(report["payload"]["decision"],"HOLD");self.assertFalse(report["payload"]["business_acceptance"])
        return checked

    def test_current_materialization_and_current_check_then_warm_cache_preserve_raw_archives(self):
        originals={p:p.read_bytes()for p in self.root.rglob("*")if p.is_file()and not p.is_relative_to(self.work)}
        report=self.run_pipeline();self.assertEqual(report["payload"]["pipeline_state"],"READY",report["payload"]["stages"])
        rows=self.rows(report);self.assertEqual(list(rows)[-2:],["content_apply","content_quality"])
        self.assertTrue(all(rows[n]["cached"]for n in list(rows)[:-2]))
        graph=self.result(rows["content_apply"])["payload"]["graph"];check=self.result(rows["content_quality"])
        self.assertEqual(graph["schema_version"],"b-graph-trial/0.6");self.assertEqual(check["schema_version"],"b-check-trial/0.6")
        old=next(a for a in self.d["current_graph"]["payload"]["answers"]if a["answer_id"]==self.d["answer_id"])
        new=next(a for a in graph["payload"]["answers"]if a["answer_id"]==self.d["answer_id"])
        self.assertEqual(new["text"],old["text"].replace("继续","1:3",1))
        self.assertEqual(new["fragments"],old["fragments"])
        self.assertEqual(graph["payload"]["answer_coverage"],self.d["current_graph"]["payload"]["answer_coverage"])
        self.assertEqual(graph["payload"]["inline_content"],self.d["current_graph"]["payload"]["inline_content"])
        self.assertEqual(graph["payload"]["content_revision"]["base_graph_archive"],self.d["current_graph"])
        self.assertEqual(report["payload"]["final_outputs"],dict(evidence_ref=pipeline._ref(self.d["current_evidence"]),graph_ref=pipeline._ref(graph),quality_ref=pipeline._ref(check)))
        self.assertIn(pipeline._ref(graph),check["input_refs"])
        self.accepted(report)
        warm=self.run_pipeline();self.accepted(warm)
        self.assertTrue(all(row["cached"]for row in warm["payload"]["stages"]))
        self.assertEqual(warm["payload"]["final_outputs"],report["payload"]["final_outputs"])
        for path,raw in originals.items():self.assertEqual(path.read_bytes(),raw,str(path))

    def test_stop_after_apply_then_resume_never_publishes_stale_g05_as_final(self):
        first=self.run_pipeline(stop_after="content_apply");rows=self.rows(first)
        self.assertEqual(first["payload"]["pipeline_state"],"PARTIAL")
        self.assertEqual(rows["content_apply"]["state"],"DONE");self.assertEqual(rows["content_quality"]["reason"],"STOP_AFTER")
        self.assertIsNone(first["payload"]["final_outputs"]);self.accepted(first)
        resumed=self.run_pipeline(stop_after="content_quality");self.accepted(resumed)
        self.assertTrue(self.rows(resumed)["content_apply"]["cached"])
        self.assertFalse(self.rows(resumed)["content_quality"]["cached"])
        self.assertEqual(resumed["payload"]["pipeline_state"],"READY")

    def test_plan_only_change_repeats_two_stages_and_preserves_full_plan_lineage(self):
        from annotation.recognition.content_revision import make_revision_plan
        first=self.run_pipeline();self.accepted(first)
        operations=copy.deepcopy(self.d["plan"]["payload"]["operations"]);operations[0]["replacement"]="explicit longer draft\nsecond line"
        revised=make_revision_plan(self.d["current_evidence"],self.d["current_graph"],self.d["current_check"],operations,self.d["author"],previous_plan=self.d["plan"])
        write(self.d["plan_path"],revised)
        second=self.run_pipeline();self.accepted(second);rows=self.rows(second)
        self.assertEqual([r["cached"]for r in rows.values()],[True]*6+[False]*2)
        self.assertEqual(self.result(rows["content_apply"])["payload"]["graph"]["payload"]["content_revision"]["plan_archive"],revised)
        self.assertEqual(revised["payload"]["previous_plan_archive"],self.d["plan"])

    def test_review_only_makes_old_plan_stale_until_explicit_new_plan_revision(self):
        from annotation.recognition.content_revision import make_revision_plan
        first=self.run_pipeline();self.accepted(first)
        review=json.loads(self.d["review_path"].read_text(encoding="utf-8"));review["synthetic_note"]="review changed, not transcription"
        write(self.d["review_path"],review)
        failed=self.run_pipeline();rows=self.rows(failed)
        self.assertEqual(failed["payload"]["pipeline_state"],"FAILED");self.assertIsNone(failed["payload"]["final_outputs"])
        self.assertEqual(rows["content_apply"]["state"],"FAILED");self.assertEqual(rows["content_quality"]["state"],"WAITING")
        self.assertTrue(all(rows[n]["cached"]for n in ("evidence","assemble","inline_prepare","inline_apply")))
        self.assertFalse(rows["quality"]["cached"]);self.assertFalse(rows["inline_quality"]["cached"])
        self.accepted(failed)
        current_check=self.result(rows["inline_quality"])
        revised=make_revision_plan(self.d["current_evidence"],self.d["current_graph"],current_check,
            self.d["plan"]["payload"]["operations"],self.d["author"],previous_plan=self.d["plan"])
        write(self.d["plan_path"],revised)
        resumed=self.run_pipeline();self.accepted(resumed)
        self.assertEqual(resumed["payload"]["pipeline_state"],"READY")

    def test_each_current_ref_is_strict_after_coordinated_plan_self_hashes(self):
        for field in ("evidence_ref","graph_ref","base_check_ref"):
            plan=copy.deepcopy(self.d["plan"]);plan["payload"][field]["artifact_id"]="foreign-"+field
            write(self.d["plan_path"],resign_plan(plan))
            with self.subTest(field=field):
                report=self.run_pipeline();self.accepted(report)
                self.assertEqual(self.rows(report)["content_apply"]["state"],"FAILED")
                self.assertIsNone(report["payload"]["final_outputs"])

    def test_malformed_or_missing_ref_plan_still_has_terminal_failed_stage_and_raw_receipt(self):
        for raw in (b'{"broken":',b'{}',b'null',b'{"kind":"a","kind":"b"}',
                    b'{"artifact_id":{},"revision":true,"content_hash":[]}',b'['*1600+b'null'+b']'*1600):
            self.d["plan_path"].write_bytes(raw)
            with self.subTest(raw=raw):
                report=self.run_pipeline();self.accepted(report);rows=self.rows(report)
                self.assertTrue(all(rows[n]["cached"]for n in list(rows)[:-2]))
                self.assertEqual(rows["content_apply"]["state"],"FAILED")
                self.assertEqual(rows["content_quality"]["state"],"WAITING")
                self.assertIsNone(report["payload"]["input_receipts"]["content_revision"]["reference"])
                self.assertIsNone(report["payload"]["final_outputs"])

    def test_partial_inline_retains_content_stage_scope_without_attempting_plan(self):
        self.d=make_inline_fixture(self.root/"partial",max_items=1)|{"plan_path":self.d["plan_path"]}
        report=self.run_pipeline();self.accepted(report);rows=self.rows(report)
        self.assertEqual(report["payload"]["pipeline_state"],"PARTIAL")
        self.assertEqual(rows["inline_prepare"]["state"],"PARTIAL")
        self.assertEqual([rows[n]["state"]for n in ("content_apply","content_quality")],["WAITING","WAITING"])
        self.assertIsNone(report["payload"]["final_outputs"])

    def test_inflight_plan_edit_fails_run_even_if_only_whitespace_and_old_plan_ref_is_unchanged(self):
        publish=pipeline.batch._put_object;changed=[]
        def edit(work,value):
            descriptor=publish(work,value)
            if value.get("kind")=="PipelineStageTrial"and value["payload"]["stage_id"]=="content_apply"and not changed:
                self.d["plan_path"].write_bytes(self.d["plan_path"].read_bytes()+b" ");changed.append(True)
            return descriptor
        with patch.object(pipeline.batch,"_put_object",new=edit):report=self.run_pipeline()
        self.assertEqual(changed,[True]);self.assertEqual(report["payload"]["pipeline_state"],"FAILED")
        self.assertEqual(report["payload"]["run_error"]["code"],"INPUT_CHANGED_DURING_RUN")
        self.assertIsNone(report["payload"]["final_outputs"]);self.assertFalse(self.audit(report)["payload"]["accepted"])
        resumed=self.run_pipeline();self.accepted(resumed)
        self.assertEqual([r["cached"]for r in resumed["payload"]["stages"]],[True]*6+[False]*2)

    def test_corrupt_apply_wrapper_preserves_bad_bytes_then_rebuilds_only_current_two_stages(self):
        first=self.run_pipeline();self.accepted(first)
        path=self.work/self.rows(first)["content_apply"]["output"]["path"]
        corrupted=path.read_bytes()+b"corrupt";path.write_bytes(corrupted)
        self.assertFalse(self.audit(first)["payload"]["accepted"])
        second=self.run_pipeline();self.accepted(second)
        self.assertEqual([r["cached"]for r in second["payload"]["stages"]],[True]*6+[False]*2)
        self.assertEqual(path.read_bytes(),corrupted)

    def test_version_change_of_new_qa_dependency_invalidates_only_new_stages(self):
        self.accepted(self.run_pipeline())
        real=pipeline.code_digest
        def changed(path):
            actual=real(path)
            return digest(["SYNTHETIC_TEST version only",actual])if Path(path).name=="content_revision_quality.py"else actual
        with patch.object(pipeline,"code_digest",side_effect=changed):report=self.run_pipeline()
        self.assertEqual(report["payload"]["pipeline_state"],"READY",report["payload"]["stages"])
        self.assertEqual([r["cached"]for r in report["payload"]["stages"]],[True]*6+[False]*2)
        # Independent consumer rejects simulated metadata against actual source;
        # this is cache invalidation evidence, not a producer version promotion.
        self.assertFalse(self.audit(report)["payload"]["accepted"])

    def test_forged_materialized_text_is_independently_rejected_before_success_or_cache(self):
        from annotation.recognition import content_revision
        actual=content_revision.apply_content_revision
        def forged(*args, **kwargs):
            result=actual(*args, **kwargs);graph=result["payload"]["graph"]
            graph["payload"]["answers"][0]["text"]+="not in plan"
            for value,prefix in ((graph,"content-graph"),(result,"content-revision-application")):
                value["content_hash"]=digest(value["payload"])
                value["artifact_id"]=prefix+"-"+digest({k:v for k,v in value.items()if k not in {"artifact_id","content_hash"}})[:24]
            return result
        with patch.object(content_revision,"apply_content_revision",new=forged):report=self.run_pipeline()
        rows=self.rows(report)
        self.assertEqual(rows["content_apply"]["state"],"FAILED")
        self.assertIn("independent content stage audit rejected",rows["content_apply"]["last_error"])
        self.assertIsNone(rows["content_apply"]["output"]);self.assertIsNone(report["payload"]["final_outputs"])
        with closing(sqlite3.connect(self.work/"pipeline.sqlite3"))as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM stage_cache WHERE stage_id='content_apply'").fetchone()[0],0)

    def test_final_output_cannot_point_back_to_unedited_g05(self):
        report=self.run_pipeline();self.accepted(report)
        report["payload"]["final_outputs"]["graph_ref"]=pipeline._ref(self.d["current_graph"])
        report["content_hash"]=digest(report["payload"])
        checked=self.audit(report)
        self.assertFalse(checked["payload"]["accepted"])
        self.assertTrue(any(i["code"]=="PIPELINE_CONTENT_REVISION_FINAL_OUTPUTS_MISMATCH"for i in checked["payload"]["issues"]))

    def test_original_source_changed_during_content_stage_is_terminal_and_not_final(self):
        publish=pipeline.batch._put_object;changed=[];source=self.d["original"];original=source.read_bytes()
        def edit_source(work,value):
            descriptor=publish(work,value)
            if value.get("kind")=="PipelineStageTrial"and value["payload"]["stage_id"]=="content_apply"and not changed:
                source.write_bytes(original+b"source changed");changed.append(True)
            return descriptor
        with patch.object(pipeline.batch,"_put_object",new=edit_source):report=self.run_pipeline()
        self.assertEqual(changed,[True]);self.assertEqual(report["payload"]["pipeline_state"],"FAILED")
        self.assertIsNone(report["payload"]["final_outputs"])
        self.assertEqual(report["payload"]["run_error"]["code"],"INPUT_CHANGED_DURING_RUN")
        self.assertFalse(self.audit(report)["payload"]["accepted"])
        self.assertEqual(source.read_bytes(),original+b"source changed")

    def test_real_process_exit_after_apply_publish_retries_without_consuming_orphan(self):
        before={p:p.read_bytes()for p in (self.work/"objects").glob("*.json")}
        script=r'''
import os,sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'src'),str(Path.cwd()/'tests')]
from annotation.recognition import pipeline
root=Path(sys.argv[1]);put=pipeline.batch._put_object
def abrupt(work,value):
 descriptor=put(work,value)
 if value.get('kind')=='PipelineStageTrial'and value['payload']['stage_id']=='content_apply':os._exit(73)
 return descriptor
pipeline.batch._put_object=abrupt
pipeline.run_pipeline(root/'source.json',root/'context.json',root/'review.json',root/'pipeline',
 evidence_path=root/'inline-evidence.json',inline_path=root/'inline-package.json',inline_source_path=root/'source-page.png',
 content_revision_path=root/'content-plan.json')
'''
        completed=subprocess.run([sys.executable,"-c",script,str(self.root)],cwd=ROOT,capture_output=True,text=True,timeout=45)
        self.assertEqual(completed.returncode,73,completed.stdout+completed.stderr)
        orphans=[]
        for path in (self.work/"objects").glob("*.json"):
            if path not in before:
                value=json.loads(path.read_text(encoding="utf-8"))
                if value.get("kind")=="PipelineStageTrial"and value["payload"]["stage_id"]=="content_apply":orphans.append((path,path.read_bytes(),value))
        self.assertEqual(len(orphans),1)
        recovered=self.run_pipeline();self.accepted(recovered)
        self.assertEqual([r["cached"]for r in recovered["payload"]["stages"]],[True]*6+[False]*2)
        with closing(sqlite3.connect(self.work/"pipeline.sqlite3"))as db:
            state,output=db.execute("SELECT state,output_json FROM stage_attempts WHERE attempt_id=?",(orphans[0][2]["payload"]["attempt_id"],)).fetchone()
            self.assertEqual(state,"INTERRUPTED");self.assertIsNone(output)
        self.assertEqual(orphans[0][0].read_bytes(),orphans[0][1])
        self.assertNotEqual(self.rows(recovered)["content_apply"]["output"]["path"],orphans[0][0].relative_to(self.work).as_posix())

    def test_continued_current_evidence_and_check_stay_bound_across_fresh_workdirs(self):
        self.d=make_pipeline_revision_fixture(self.root/"combined",continuation=True);self.work=self.d["workdir"]
        first=self.run_pipeline();self.accepted(first);rows=self.rows(first)
        self.assertEqual(len(rows),12)
        app=self.result(rows["content_apply"]);check=self.result(rows["content_quality"])
        self.assertEqual(app["payload"]["evidence_ref"],pipeline._ref(self.d["current_evidence"]))
        self.assertEqual(app["payload"]["base_graph_ref"],pipeline._ref(self.d["current_graph"]))
        self.assertEqual(app["payload"]["base_check_ref"],pipeline._ref(self.d["current_check"]))
        self.assertEqual(check["payload"]["review_basis"]["selection"],"CHECK04_ARCHIVED_DERIVED_REVIEW")
        graph=app["payload"]["graph"]
        self.assertEqual(graph["payload"]["answers"][0]["render_regions"][1:],
            self.d["current_graph"]["payload"]["answers"][0]["render_regions"][1:])
        self.work=self.root/"fresh-combined"
        second=self.run_pipeline();self.accepted(second)
        self.assertEqual(first["payload"]["final_outputs"],second["payload"]["final_outputs"])

    def test_scalar_and_explicit_explanation_are_materialized_and_current_rules_rechecked(self):
        from content_revision_fixture import make_content_fixture,edit_target
        from annotation.recognition.content_revision import make_revision_plan
        self.d=make_content_fixture(self.root/"rich");self.work=self.root/"rich-pipeline"
        base=run_fixture(self.d,self.work);rows=self.rows(base)
        e=self.result(rows["inline_prepare"])["payload"]["base_evidence_archive"]
        g=self.result(rows["inline_apply"])["payload"]["graph"];c=self.result(rows["inline_quality"])
        scalar=next(a for a in g["payload"]["answers"]if a["printed_number"]=="4")
        answer=next(a for a in g["payload"]["answers"]if a["printed_number"]=="9")
        scalar_fragment=next(f for f in scalar["fragments"]if f["role"]=="answer"and "0"in f["text"])
        lo=scalar_fragment["text"].index("0")
        operations=[dict(operation_id="scalar-draft",kind="EDIT_TEXT",target=edit_target(g,answer_id=scalar["answer_id"],
            fragment_id=scalar_fragment["fragment_id"],span=[lo,lo+1]),replacement="13",format="plain",reason="Explicit synthetic scalar draft"),
            dict(operation_id="analysis-draft",kind="EDIT_TEXT",target=edit_target(g,answer_id=answer["answer_id"],role="explanation"),
            replacement="synthetic analysis line one\nline two",format="plain",reason="Existing explicit analysis only")]
        plan=make_revision_plan(e,g,c,operations,self.d["author"]if "author"in self.d else dict(kind="SYNTHETIC_TEST",id="rich-pipeline",note="No verification"))
        self.d["plan_path"]=self.root/"rich-plan.json";write(self.d["plan_path"],plan)
        report=self.run_pipeline();self.accepted(report);rows=self.rows(report)
        derived=self.result(rows["content_apply"])["payload"]["graph"];checked=self.result(rows["content_quality"])
        newscalar=next(a for a in derived["payload"]["answers"]if a["answer_id"]==scalar["answer_id"])
        newanswer=next(a for a in derived["payload"]["answers"]if a["answer_id"]==answer["answer_id"])
        self.assertEqual(newscalar["text"],"13")
        self.assertEqual(newanswer["text"],answer["text"])
        self.assertIn("synthetic analysis line one\nline two",newanswer["explanation_text"])
        self.assertEqual(newanswer["fragments"],answer["fragments"])
        self.assertTrue(any(i["code"]=="ANSWER_VALUE_MISMATCH"for i in c["payload"]["issues"]))
        self.assertFalse(any(i["code"]=="ANSWER_VALUE_MISMATCH"for i in checked["payload"]["fresh_question_findings"]))
        self.assertTrue(any(d["prior_issue"]["code"]=="ANSWER_VALUE_MISMATCH"and d["status"]=="FRESH_QUESTION_RULES_RECHECKED"for d in checked["payload"]["rule_dispositions"]))
        self.assertEqual(checked["payload"]["base_check_archive"],c)

    def test_current_pipeline_audit_never_calls_revision_producer_or_plan_builder_as_gold(self):
        from annotation.recognition import content_revision
        report=self.run_pipeline();self.accepted(report)
        def forbidden(*args,**kwargs):raise AssertionError("independent audit called new producer")
        with patch.object(content_revision,"apply_content_revision",new=forbidden), \
             patch.object(content_revision,"build_content_quality",new=forbidden), \
             patch.object(content_revision,"make_revision_plan",new=forbidden), \
             patch.object(content_revision,"validate_revision_plan",new=forbidden):
            self.accepted(report)


if __name__=="__main__":unittest.main()
