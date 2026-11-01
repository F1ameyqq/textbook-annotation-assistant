"""Explicit saved-inline pipeline attachment; all generated observations synthetic."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"tools"), str(ROOT/"tests")]
from run_pipeline_b import execute, main, PipelineCLIError

STAGES = ("inline_prepare", "inline_apply", "inline_quality")


class InlineCLIArguments(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def args(self, *flags):
        return ["--source", str(self.root/"source.json"), "--context", str(self.root/"context.json"),
            "--review", str(self.root/"review.json"), "--workdir", str(self.root/"work"),
            "--evidence", str(self.root/"E.json"), *flags]

    def pair(self): return ["--inline", str(self.root/"inline.json"), "--inline-source", str(self.root/"original.png")]

    def bad(self, flags):
        with patch("run_pipeline_b.execute") as runner, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised: main(flags)
            self.assertEqual(raised.exception.code, 2)
            runner.assert_not_called()
        self.assertFalse((self.root/"work").exists())

    def test_new_paths_are_paired_and_all_three_stops_require_explicit_inline_package(self):
        self.bad(self.args("--inline", "package.json"))
        self.bad(self.args("--inline-source", "original.png"))
        for stage in STAGES:
            with self.subTest(stage=stage): self.bad(self.args("--stop-after", stage))

    def test_each_stop_forwards_pair_and_preserves_zero_ocr_default(self):
        for stage in STAGES:
            with self.subTest(stage=stage), patch("run_pipeline_b.execute", return_value={"exit_code":0}) as runner, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(self.args(*self.pair(), "--stop-after", stage)), 0)
                kwargs = runner.call_args.kwargs
                self.assertEqual(kwargs["inline_path"], self.root/"inline.json")
                self.assertEqual(kwargs["inline_source_path"], self.root/"original.png")
                self.assertEqual(kwargs["stop_after"], stage)
                self.assertFalse(kwargs["use_ocr"])
                self.assertIsNone(kwargs["continuation_path"])

    def test_urls_unc_and_cached_ocr_budget_flags_fail_before_execution(self):
        for flag in ("--inline", "--inline-source"):
            for value in ("https://example.invalid/file", "//server/share/file", "\\\\server\\share\\file"):
                args = self.args(*self.pair()); args[args.index(flag)+1] = value
                with self.subTest(flag=flag, value=value): self.bad(args)
        for flags in (("--ocr",), ("--max-items","1"), ("--stop-after","refine"), ("--stop-after","recover")):
            with self.subTest(flags=flags): self.bad(self.args(*self.pair(), *flags))

    def test_inline_paths_are_forwarded_to_runner_and_independent_auditor_for_all_execution_states(self):
        for state, accepted, code in (("READY",True,0), ("PARTIAL",True,0), ("FAILED",True,1), ("READY",False,1)):
            calls = []
            report = dict(artifact_id="synthetic-cli-interface-report", revision=1, content_hash="1"*64,
                run_id="synthetic-interface-"+state+str(accepted), payload=dict(pipeline_state=state, mode="CACHED_INPUT", counts={},
                decision="HOLD",business_acceptance=False,transcription_verified=False,platform_actions=[]))
            check = dict(schema_version="b-pipeline-check-trial/0.1",artifact_id="synthetic-cli-interface-check",revision=1,content_hash="2"*64,
                payload=dict(accepted=accepted,issues=[],decision="HOLD",business_acceptance=False,transcription_verified=False,platform_actions=[]))
            def runner(*args, **kwargs): calls.append(("producer",kwargs)); return report
            def auditor(*args, **kwargs): calls.append(("consumer",kwargs)); return check
            result = execute(self.root/"source.json",self.root/"context.json",self.root/"review.json",self.root/"work",
                inline_path=str(self.root/"inline.json"),inline_source_path=str(self.root/"original.png"),runner=runner,auditor=auditor)
            self.assertEqual([c[0] for c in calls],["producer","consumer"])
            for _, kwargs in calls:
                self.assertEqual(kwargs["inline_path"],self.root/"inline.json")
                self.assertEqual(kwargs["inline_source_path"],self.root/"original.png")
            self.assertEqual(result["exit_code"],code)
            self.assertEqual(result["schema_version"],"b-pipeline-cli-result-trial/0.1")
            self.assertTrue(result["audit_performed"])
            self.assertTrue((self.root/"work"/result["check"]["path"]).is_file())
            self.assertEqual(result["decision"],"HOLD")
            self.assertFalse(result["business_acceptance"])

    def test_audit_acceptance_cannot_hide_promoted_business_or_transcription_flags(self):
        report = dict(artifact_id="synthetic-interface",revision=1,content_hash="1"*64,
            payload=dict(pipeline_state="READY",mode="CACHED_INPUT",counts={},decision="HOLD",business_acceptance=False,transcription_verified=False,platform_actions=[]))
        for field, value in (("decision","APPROVED"),("business_acceptance",True),("transcription_verified",True),("platform_actions",["SAVE"])):
            check = dict(schema_version="b-pipeline-check-trial/0.1",artifact_id="synthetic-audit",revision=1,content_hash="2"*64,
                payload=dict(accepted=True,issues=[],decision="HOLD",business_acceptance=False,transcription_verified=False,platform_actions=[]))
            check["payload"][field] = value
            with self.subTest(field=field), self.assertRaises(PipelineCLIError) as raised:
                execute(self.root/"S",self.root/"C",self.root/"R",self.root/"work",inline_path=self.root/"P",inline_source_path=self.root/"I",
                    runner=lambda *a,**k: report,auditor=lambda *a,**k:check)
            self.assertEqual(raised.exception.stage,"AUDIT_FAILED")


class InlineCLIIntegration(unittest.TestCase):
    def setUp(self):
        from test_b_inline_stage import make_inline_fixture
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.d = make_inline_fixture(self.root)
        self.workdir = self.root/"pipeline"

    def args(self, *flags, cached=True, inline=True, continuation=False):
        d = self.d
        values = ["--source",str(d["source_path"]),"--context",str(d["context_path"]),"--review",str(d["review_path"]),"--workdir",str(self.workdir)]
        if cached: values += ["--evidence",str(d["evidence_path"])]
        if inline: values += ["--inline",str(d["package_path"]),"--inline-source",str(d["original"])]
        if continuation: values += ["--continuation",str(d["continuation_path"]),"--adjacent-source",str(d["adjacent_source_path"])]
        return [*values,*flags]

    def cli(self,*flags,expected=0,script=None,**kwargs):
        prefix = [sys.executable,"-c",script] if script else [sys.executable]
        completed = subprocess.run([*prefix,str(ROOT/"tools/run_pipeline_b.py"),*self.args(*flags,**kwargs)],
            cwd=ROOT,capture_output=True,text=True,encoding="utf-8",timeout=45)
        self.assertEqual(completed.returncode,expected,completed.stdout+completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["decision"],"HOLD")
        self.assertFalse(result["business_acceptance"])
        self.assertFalse(result["transcription_verified"])
        return result

    def report(self,result):
        for path in (self.workdir/"objects").glob("*.json"):
            try: value = json.loads(path.read_text(encoding="utf-8"))
            except ValueError: continue
            if all(value.get(k)==v for k,v in result["report_ref"].items()): return value
        self.fail("report ref is not backed by an immutable report object")

    def stages(self,result): return {row["stage_id"]:row for row in self.report(result)["payload"]["stages"]}
    def raw(self,row): return json.loads((self.workdir/row["output"]["path"]).read_text(encoding="utf-8"))["payload"]["result"]
    @staticmethod
    def ref(value): return {k:value[k] for k in ("artifact_id","revision","content_hash")}

    def test_three_stops_resume_to_current_g5_check5_without_changing_old_core_or_receipts(self):
        old = {p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        receipts = {}
        for index,stage in enumerate(STAGES):
            result = self.cli("--stop-after",stage)
            rows = self.stages(result)
            self.assertEqual(list(rows),["evidence","assemble","quality",*STAGES])
            self.assertEqual(rows[stage]["state"],"DONE")
            self.assertTrue(all(rows[name]["cached"] for name in STAGES[:index]))
            self.assertTrue(all(rows[name]["state"]=="WAITING" for name in STAGES[index+1:]))
            self.assertEqual(result["pipeline_state"],"READY" if index==2 else "PARTIAL")
            self.assertTrue(result["integrity_accepted"],result["issues"])
            if index<2: self.assertIsNone(self.report(result)["payload"]["final_outputs"])
            receipt = self.workdir/result["check"]["path"]; receipts[receipt]=receipt.read_bytes()
        warm = self.cli(); rows=self.stages(warm)
        self.assertTrue(all(row["cached"] for row in rows.values()))
        prepared = self.raw(rows["inline_prepare"])
        graph = self.raw(rows["inline_apply"])["payload"]["graph"]
        checked = self.raw(rows["inline_quality"])
        base = self.raw(rows["assemble"])
        self.assertEqual(graph["schema_version"],"b-graph-trial/0.5")
        self.assertEqual(checked["schema_version"],"b-check-trial/0.5")
        self.assertEqual({k:v for k,v in graph["payload"].items() if k!="inline_content"},base["payload"])
        self.assertEqual(graph["payload"]["inline_content"]["selected_candidate_refs"],[])
        self.assertEqual(graph["payload"]["inline_content"]["selected_unit_ids"],[])
        self.assertEqual(self.report(warm)["payload"]["final_outputs"],dict(evidence_ref=prepared["payload"]["base_evidence_ref"],
            graph_ref=self.ref(graph),quality_ref=self.ref(checked)))
        self.assertIn(self.ref(graph),checked["input_refs"])
        self.assertEqual(checked["payload"]["issues"][:-1],self.raw(rows["quality"])["payload"]["issues"])
        self.assertEqual(prepared["payload"]["formula_observations_archive"]["producer"]["execution_kind"],"SYNTHETIC_TEST")
        for path,content in {**old,**receipts}.items(): self.assertEqual(path.read_bytes(),content,str(path))

    def test_without_inline_old_chain_and_live_geometry_have_no_implicit_model_attachment(self):
        result = self.cli(inline=False)
        self.assertEqual(list(self.stages(result)),["evidence","assemble","quality"])
        self.workdir = self.root/"live"
        live = self.cli(cached=False)
        rows=self.stages(live)
        self.assertEqual(live["pipeline_state"],"PARTIAL")
        self.assertEqual(rows["refine"]["reason"],"OCR_REQUIRED")
        self.assertTrue(all(rows[name]["state"]=="WAITING" for name in STAGES))

    def test_review_only_rechecks_base_and_latest_quality_while_saved_observations_stay_cached(self):
        first = self.cli(); before=self.stages(first)
        review=json.loads(self.d["review_path"].read_text(encoding="utf-8"));review["synthetic_note"]="development review only"
        self.d["review_path"].write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding="utf-8")
        second=self.cli(); after=self.stages(second)
        for name in ("evidence","assemble","inline_prepare","inline_apply"):
            self.assertTrue(after[name]["cached"],name)
            self.assertEqual(after[name]["result_ref"],before[name]["result_ref"])
        for name in ("quality","inline_quality"): self.assertFalse(after[name]["cached"],name)

    def test_partial_saved_scope_has_no_application_and_can_resume_with_exact_new_saved_result(self):
        from test_b_inline_stage import make_inline_fixture,refresh_inline_package
        from test_b_inline_formula import FormulaWorker
        from annotation.recognition.inline_formula import collect_inline_formula
        self.d=make_inline_fixture(self.root/"partial",max_items=1)
        first=self.cli(); rows=self.stages(first)
        self.assertEqual(first["pipeline_state"],"PARTIAL")
        self.assertEqual(rows["inline_prepare"]["state"],"PARTIAL")
        self.assertTrue(all(rows[name]["state"]=="WAITING" for name in ("inline_apply","inline_quality")))
        prepared=self.raw(rows["inline_prepare"])
        self.assertEqual(prepared["payload"]["counts"]["rows"],len(self.d["line_ids"]))
        self.assertIsNone(self.report(first)["payload"]["final_outputs"])
        worker=FormulaWorker(outputs=("1+2=1",))
        observations,report=collect_inline_formula(self.d["evidence"],self.d["layout"],self.d["original"],self.d["journal_dir"],
            line_ids=self.d["line_ids"],recognizer=worker)
        self.d["documents"]["formula_observations"]=observations;self.d["documents"]["formula_report"]=report
        refresh_inline_package(self.d)
        resumed=self.cli();after=self.stages(resumed)
        self.assertEqual(resumed["pipeline_state"],"READY")
        self.assertTrue(all(after[n]["cached"] for n in ("evidence","assemble","quality")))
        self.assertFalse(after["inline_prepare"]["cached"])

    def test_failed_saved_execution_has_terminal_receipt_exit_one_and_no_false_application(self):
        from test_b_inline_stage import make_inline_fixture
        self.d=make_inline_fixture(self.root/"failed",fail=True)
        failed=self.cli(expected=1); rows=self.stages(failed)
        self.assertEqual(failed["pipeline_state"],"FAILED")
        self.assertTrue(failed["audit_performed"])
        self.assertEqual(rows["inline_prepare"]["state"],"FAILED")
        self.assertIsNone(rows["inline_apply"]["output"])
        self.assertIsNone(self.report(failed)["payload"]["final_outputs"])
        self.assertTrue((self.workdir/failed["check"]["path"]).is_file())

    def test_selected_source_raw_field_change_cannot_rebind_old_cached_formula_observations(self):
        from annotation.recognition.baseline import digest
        value=copy.deepcopy(self.d["evidence"])
        value["payload"]["pages"][0]["ocr_lines"][0]["score"] += .01
        value["content_hash"]=digest(value["payload"])
        # The current input is separate from the immutable old evidence in the
        # package, so this reaches exact selected-page comparison after loading.
        self.d["evidence_path"]=self.root/"current-changed-evidence.json"
        self.d["evidence_path"].write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
        result=self.cli(expected=1)
        self.assertEqual(result["pipeline_state"],"FAILED")
        self.assertEqual(self.stages(result)["inline_prepare"]["state"],"FAILED")
        self.assertIsNone(self.report(result)["payload"]["final_outputs"])

    def test_corrupt_journal_or_original_source_is_explicitly_rejected_before_stage_execution(self):
        for path in (self.d["journal_dir"]/"inline-formula.sqlite3",self.d["original"]):
            original=path.read_bytes()
            path.write_bytes(original+b"changed")
            result=self.cli(expected=1)
            self.assertEqual(result["pipeline_state"],"FAILED")
            self.assertFalse(result["integrity_accepted"])
            self.assertEqual(result["error"]["stage"],"RUN_FAILED")
            path.write_bytes(original)

    def test_inflight_package_edit_retains_failed_run_and_requires_new_stage_receipts(self):
        from annotation.recognition import pipeline
        publish=pipeline.batch._put_object;changed=[]
        def edit_after_publish(workdir,value):
            result=publish(workdir,value)
            if value.get("kind")=="PipelineStageTrial" and value["payload"]["stage_id"]=="inline_apply" and not changed:
                self.d["package_path"].write_bytes(self.d["package_path"].read_bytes()+b" ");changed.append(True)
            return result
        with patch("annotation.recognition.pipeline.batch._put_object",new=edit_after_publish):
            result=execute(self.d["source_path"],self.d["context_path"],self.d["review_path"],self.workdir,
                evidence_path=self.d["evidence_path"],inline_path=self.d["package_path"],inline_source_path=self.d["original"])
        self.assertEqual(changed,[True])
        self.assertEqual(result["exit_code"],1)
        self.assertFalse(result["integrity_accepted"])
        self.assertTrue(result["audit_performed"])
        self.assertTrue(self.report(result)["payload"]["run_error"])
        self.assertTrue((self.workdir/result["check"]["path"]).exists())
        resumed=self.cli();rows=self.stages(resumed)
        self.assertTrue(rows["evidence"]["cached"])
        self.assertFalse(rows["inline_prepare"]["cached"])

    def test_fresh_process_runs_cached_chain_with_network_and_model_imports_blocked(self):
        script=r'''
import importlib.abc,runpy,socket,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}:
   raise AssertionError('forbidden model/network import: '+fullname)
sys.meta_path.insert(0,NoModels())
class OfflineSocket(socket.socket):
 def connect(self,*a,**k):raise AssertionError('network forbidden')
 def connect_ex(self,*a,**k):raise AssertionError('network forbidden')
socket.socket=OfflineSocket
socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(tool,run_name='__main__')
'''
        result=self.cli(script=script)
        self.assertEqual(result["pipeline_state"],"READY")
        self.assertTrue(result["integrity_accepted"],result["issues"])
        for name in STAGES:
            self.assertEqual(self.raw(self.stages(result)[name])["payload"]["new_model_calls"],0)

    def test_continuation_then_inline_uses_current_e6_g4_and_promotes_only_unselected_attachment(self):
        from test_b_inline_stage import make_inline_fixture
        self.d=make_inline_fixture(self.root/"combined",continuation=True)
        first=self.cli(continuation=True);rows=self.stages(first)
        self.assertEqual(list(rows),["evidence","assemble","quality","continuation_prepare","continuation_proof",
            "continuation_apply","continuation_quality",*STAGES])
        prepared=self.raw(rows["inline_prepare"])
        old_e=self.raw(rows["continuation_prepare"])["payload"]["evidence"]
        old_g=self.raw(rows["continuation_apply"])["payload"]["graph"]
        old_check=self.raw(rows["continuation_quality"])
        self.assertEqual(prepared["payload"]["base_evidence_ref"],self.ref(old_e))
        self.assertEqual(prepared["payload"]["base_graph_ref"],self.ref(old_g))
        graph=self.raw(rows["inline_apply"])["payload"]["graph"]
        latest=self.raw(rows["inline_quality"])
        self.assertEqual(latest["payload"]["base_check_archive"],old_check)
        self.assertEqual({k:v for k,v in graph["payload"].items() if k!="inline_content"},old_g["payload"])
        self.assertEqual(self.report(first)["payload"]["final_outputs"],dict(evidence_ref=self.ref(old_e),graph_ref=self.ref(graph),quality_ref=self.ref(latest)))
        self.assertEqual(graph["payload"]["inline_content"]["selected_candidate_refs"],[])
        self.assertTrue(all(row["cached"] for row in self.stages(self.cli(continuation=True)).values()))

    def test_new_workdir_keeps_latest_refs_stable_without_rewriting_saved_execution_archives(self):
        old={p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        first=self.cli();refs=self.report(first)["payload"]["final_outputs"]
        self.workdir=self.root/"second-pipeline"
        second=self.cli()
        self.assertEqual(self.report(second)["payload"]["final_outputs"],refs)
        self.assertTrue(second["integrity_accepted"])
        for path,raw in old.items():self.assertEqual(path.read_bytes(),raw,str(path))


if __name__=="__main__": unittest.main()
