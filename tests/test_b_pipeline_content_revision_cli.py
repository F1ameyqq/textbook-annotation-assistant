"""Explicit content-plan CLI, cached-only replay and terminal audit receipts."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tools"),str(ROOT/"tests")]
from run_pipeline_b import execute,main


class ContentRevisionCLIArguments(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def args(self,*flags):return ["--source",str(self.root/"S"),"--context",str(self.root/"C"),"--review",str(self.root/"R"),
        "--workdir",str(self.root/"work"),"--evidence",str(self.root/"E"),*flags]
    def inline(self):return ["--inline",str(self.root/"inline.json"),"--inline-source",str(self.root/"source.png")]
    def bad(self,args):
        with patch("run_pipeline_b.execute")as runner,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit)as error:main(args)
            self.assertEqual(error.exception.code,2);runner.assert_not_called()
        self.assertFalse((self.root/"work").exists())

    def test_plan_and_both_stops_require_explicit_inline_inputs_and_plan(self):
        self.bad(self.args("--content-revision",str(self.root/"plan.json")))
        for stage in ("content_apply","content_quality"):
            with self.subTest(stage=stage):
                self.bad(self.args(*self.inline(),"--stop-after",stage))
                self.bad(self.args("--content-revision",str(self.root/"plan.json"),"--stop-after",stage))

    def test_plan_paths_reject_urls_unc_and_cached_ocr_flags_before_execution(self):
        for value in ("https://example.invalid/plan","//server/share/plan","\\\\server\\share\\plan"):
            self.bad(self.args(*self.inline(),"--content-revision",value))
        for flags in (("--ocr",),("--max-items","1"),("--stop-after","refine")):
            self.bad(self.args(*self.inline(),"--content-revision","plan.json",*flags))

    def test_new_stops_parse_and_forward_plan_without_enabling_ocr(self):
        for stage in ("content_apply","content_quality"):
            with patch("run_pipeline_b.execute",return_value={"exit_code":0})as runner,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(self.args(*self.inline(),"--content-revision",str(self.root/"plan.json"),"--stop-after",stage)),0)
                self.assertEqual(runner.call_args.kwargs["content_revision_path"],self.root/"plan.json")
                self.assertEqual(runner.call_args.kwargs["stop_after"],stage)
                self.assertFalse(runner.call_args.kwargs["use_ocr"])

    def test_core_and_independent_auditor_both_receive_plan_and_failed_status_cannot_pass(self):
        for state,accepted,code in (("READY",True,0),("PARTIAL",True,0),("FAILED",True,1),("READY",False,1)):
            calls=[]
            report=dict(artifact_id="synthetic-interface-report",revision=1,content_hash="1"*64,run_id="synthetic-"+state+str(accepted),
                payload=dict(pipeline_state=state,mode="CACHED_INPUT",counts={},decision="HOLD",business_acceptance=False,transcription_verified=False,platform_actions=[]))
            check=dict(schema_version="b-pipeline-check-trial/0.1",artifact_id="synthetic-interface-check",revision=1,content_hash="2"*64,
                payload=dict(accepted=accepted,issues=[],decision="HOLD",business_acceptance=False,transcription_verified=False,platform_actions=[]))
            def runner(*args,**kwargs):calls.append(kwargs);return report
            def auditor(*args,**kwargs):calls.append(kwargs);return check
            result=execute(self.root/"S",self.root/"C",self.root/"R",self.root/"work",inline_path=self.root/"inline.json",
                inline_source_path=self.root/"source.png",content_revision_path=str(self.root/"plan.json"),runner=runner,auditor=auditor)
            self.assertEqual(len(calls),2)
            self.assertTrue(all(k["content_revision_path"]==self.root/"plan.json"for k in calls))
            self.assertEqual(result["exit_code"],code);self.assertTrue(result["audit_performed"])
            self.assertTrue((self.root/"work"/result["check"]["path"]).is_file())


class ContentRevisionCLIIntegration(unittest.TestCase):
    def setUp(self):
        from test_b_pipeline_content_revision import make_pipeline_revision_fixture
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.d=make_pipeline_revision_fixture(self.root);self.work=self.d["workdir"]

    def args(self,*flags,plan=True,cached=True):
        d=self.d;result=["--source",str(d["source_path"]),"--context",str(d["context_path"]),"--review",str(d["review_path"]),
            "--workdir",str(self.work),"--inline",str(d["package_path"]),"--inline-source",str(d["original"])]
        if cached:result += ["--evidence",str(d["evidence_path"])]
        if plan:result += ["--content-revision",str(d["plan_path"])]
        return [*result,*flags]
    def cli(self,*flags,expected=0,script=None,**kwargs):
        prefix=[sys.executable,"-c",script]if script else[sys.executable]
        completed=subprocess.run([*prefix,str(ROOT/"tools/run_pipeline_b.py"),*self.args(*flags,**kwargs)],cwd=ROOT,
            capture_output=True,text=True,encoding="utf-8",timeout=45)
        self.assertEqual(completed.returncode,expected,completed.stdout+completed.stderr)
        value=json.loads(completed.stdout)
        self.assertEqual(value["schema_version"],"b-pipeline-cli-result-trial/0.1")
        self.assertEqual(value["decision"],"HOLD");self.assertFalse(value["business_acceptance"]);self.assertFalse(value["transcription_verified"])
        if value.get("audit_performed"):self.assertTrue((self.work/value["check"]["path"]).exists())
        return value
    def report(self,value):
        for path in (self.work/"objects").glob("*.json"):
            try:report=json.loads(path.read_text(encoding="utf-8"))
            except ValueError:continue
            if all(report.get(k)==v for k,v in value["report_ref"].items()):return report
        self.fail("missing immutable pipeline report")
    def rows(self,value):return {s["stage_id"]:s for s in self.report(value)["payload"]["stages"]}
    def raw(self,row):return json.loads((self.work/row["output"]["path"]).read_text(encoding="utf-8"))["payload"]["result"]

    def test_stops_resume_and_warm_return_actual_g06_check06_with_immutable_audit_receipts(self):
        first=self.cli("--stop-after","content_apply");rows=self.rows(first)
        self.assertEqual(first["pipeline_state"],"PARTIAL");self.assertTrue(first["integrity_accepted"])
        self.assertEqual(rows["content_quality"]["state"],"WAITING");self.assertIsNone(self.report(first)["payload"]["final_outputs"])
        first_check=self.work/first["check"]["path"];first_bytes=first_check.read_bytes()
        second=self.cli("--stop-after","content_quality");rows=self.rows(second)
        self.assertEqual(second["pipeline_state"],"READY");self.assertTrue(second["integrity_accepted"])
        self.assertTrue(rows["content_apply"]["cached"])
        graph=self.raw(rows["content_apply"])["payload"]["graph"];check=self.raw(rows["content_quality"])
        self.assertEqual(graph["schema_version"],"b-graph-trial/0.6");self.assertEqual(check["schema_version"],"b-check-trial/0.6")
        self.assertEqual(self.report(second)["payload"]["final_outputs"]["graph_ref"]["content_hash"],graph["content_hash"])
        self.assertFalse(check["payload"]["complete"]);self.assertEqual(check["payload"]["new_model_calls"],0)
        warm=self.cli();self.assertTrue(all(s["cached"]for s in self.rows(warm).values()))
        self.assertEqual(first_check.read_bytes(),first_bytes)

    def test_malformed_plan_and_review_stale_plan_have_explicit_failed_exit_and_receipt(self):
        original=self.d["plan_path"].read_bytes();self.d["plan_path"].write_bytes(b'{"broken":')
        failed=self.cli(expected=1);self.assertEqual(failed["pipeline_state"],"FAILED");self.assertTrue(failed["audit_performed"])
        self.assertEqual(self.rows(failed)["content_apply"]["state"],"FAILED")
        self.assertIsNone(self.report(failed)["payload"]["final_outputs"])
        self.d["plan_path"].write_bytes(original)
        review=json.loads(self.d["review_path"].read_text(encoding="utf-8"));review["cli_synthetic_note"]="new check requires explicit rebase"
        self.d["review_path"].write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding="utf-8")
        stale=self.cli(expected=1);self.assertTrue(stale["audit_performed"])
        self.assertEqual(self.rows(stale)["content_apply"]["state"],"FAILED")
        self.assertEqual(self.rows(stale)["content_quality"]["state"],"WAITING")

    def test_without_plan_original_chain_is_retained_and_live_geometry_cannot_reach_content(self):
        old=self.cli(plan=False);self.assertNotIn("content_apply",self.rows(old))
        self.work=self.root/"live"
        live=self.cli(cached=False);rows=self.rows(live)
        self.assertEqual(live["pipeline_state"],"PARTIAL");self.assertEqual(rows["refine"]["reason"],"OCR_REQUIRED")
        self.assertEqual(rows["content_apply"]["state"],"WAITING");self.assertEqual(rows["content_quality"]["state"],"WAITING")
        self.assertIsNone(self.report(live)["payload"]["final_outputs"])

    def test_cached_fresh_process_forbids_models_and_network_and_preserves_original_journal_bytes(self):
        old={p:p.read_bytes()for p in self.d["journal_dir"].rglob("*")if p.is_file()}
        script=r'''
import importlib.abc,runpy,socket,sys
class NoRuntime(importlib.abc.MetaPathFinder):
 def find_spec(self,name,path=None,target=None):
  if name.split('.')[0]in{'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}:
   raise AssertionError('forbidden runtime '+name)
sys.meta_path.insert(0,NoRuntime())
class LocalSocket(socket.socket):
 def connect(self,*a,**k):raise AssertionError('network forbidden')
 def connect_ex(self,*a,**k):raise AssertionError('network forbidden')
socket.socket=LocalSocket
socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(tool,run_name='__main__')
'''
        result=self.cli(script=script);self.assertEqual(result["pipeline_state"],"READY");self.assertTrue(result["integrity_accepted"])
        for path,raw in old.items():self.assertEqual(path.read_bytes(),raw,str(path))


if __name__=="__main__":unittest.main()
