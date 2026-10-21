"""New same-stage controls only; no original reviewer or 20-test suite entry."""
import asyncio
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tests/a24_first_save_wire_r1"))
from test_r1 import authority_fixture  # fixed helper definition only, no test execution
from annotation.runtime.live_pilot import authority as auth, owner
from annotation.quality.live_pilot import PilotError
from annotation.runtime.storage.common import digest

def put(path,value):
    raw=json.dumps(value).encode();path.write_bytes(raw)
    return {"path":str(path),"bytes":len(raw),"sha256":auth.sha(raw)}

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="a24-new-gate-");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.scope={"body_admission":"FROZEN_QUALIFIED_ROUTE_CODEC"}
        self.request={"synthetic_only":True}
        self.profile={"mode":"SYNTHETIC","question_id":"synthetic-q","session":{"session_id":"synthetic-author"}}
        payload={"insert_after_order":22,"annotations_upsert":[{"rect_id":"r"+str(i)} for i in range(6)]}
        plan={"input_hash":digest(self.request),"baseline":{},"wire_profile_hash":digest(self.profile),"payload":payload}
        receipt={"code":0,"file_id":auth.BOOK,"platform_question_id":"new-q","question_order":23,"inserted":True,
            "rect_ids":[r["rect_id"] for r in payload["annotations_upsert"]],"response_hash":"1"*64,
            "payload_hash":digest(payload),"identity_source":"SERVER_RESPONSE","evidence_mode":"SYNTHETIC"}
        observed={"phase":"refresh","session_id":"synthetic-author","evidence_mode":"SYNTHETIC"}
        release={"released":True,"evidence_mode":"SYNTHETIC","session_id":"synthetic-author",
            "profile_hash":digest(self.profile),"plan_hash":digest(plan),"receipt_hash":digest(receipt),"last_observation_hash":digest(observed)}
        self.evidence={"question_id":"synthetic-q","result":{"state":"APPLIED_SYNTHETIC_WIRE","frames":"PASS","content":"VERIFIED"},
            "frozen_author_inputs":{"plan":plan,"baseline":{},"receipt":receipt,"author_observation":observed,"release":release}}
        self.raw_ref=put(self.root/"synthetic-held-proof.json",{"SYNTHETIC_ONLY":"no actual resource acquired"})
        self.cert={"schema":"A24OwnedRelease/v1","mode":"SYNTHETIC","issuer":auth.COORDINATOR,"status":"RELEASED",
            "subject_release_hash":digest(release),"author_result_hash":digest(self.evidence["result"]),
            "context_closed":True,"runtime_stopped":True,"held_identities_released":True,"jobs_closed":True,
            "launcher_released":True,"pending_tasks":0,"raw_evidence_refs":[self.raw_ref]}
        self.bind_cert()
    def bind_cert(self):
        ref=put(self.root/"certificate.json",self.cert)
        self.evidence["frozen_author_inputs"]["release"]["owner_release_evidence"]={"path":"certificate.json","sha256":ref["sha256"],"media_type":"application/json"}
    def gate(self):
        auth.validate_predecessor("INDEPENDENT_REOPEN",self.scope,self.request,self.profile,self.evidence,"SYNTHETIC",self.root)
    def test_qualified_hash_bound_synthetic_predecessor_admitted_without_resources(self):
        self.gate()
        cap,_=authority_fixture(self.root,self.request,self.profile,author_release=self.evidence)
        self.assertEqual(cap.check().role,"INDEPENDENT_REOPEN")
    def test_unbound_reopen_rejected_before_profile_and_native_constructor(self):
        with patch.object(owner,"WindowsBackend",side_effect=AssertionError("NO_RESOURCE")) as backend:
            with self.assertRaises(PilotError): authority_fixture(self.root,self.request,self.profile,unbound=True,author_release=self.evidence)
            backend.assert_not_called()
    def test_unknown_author_and_missing_receipt_rejected(self):
        for change in ("unknown","no_receipt","unreleased"):
            with self.subTest(change=change):
                evidence=copy.deepcopy(self.evidence)
                if change=="unknown":evidence["result"]["state"]="UNKNOWN"
                if change=="no_receipt":evidence["frozen_author_inputs"]["receipt"]=None
                if change=="unreleased":evidence["frozen_author_inputs"]["release"]["released"]=False
                with self.assertRaises(PilotError):auth.validate_predecessor("INDEPENDENT_REOPEN",self.scope,self.request,self.profile,evidence,"SYNTHETIC",self.root)
    def test_outer_certificate_requires_all_release_bits_and_integer_zero(self):
        for field in ("context_closed","runtime_stopped","held_identities_released","jobs_closed","launcher_released","pending_tasks"):
            with self.subTest(field=field):
                old=self.cert[field];self.cert[field]=False;self.bind_cert()
                with self.assertRaises(PilotError):self.gate()
                self.cert[field]=old
        self.bind_cert()
    def test_certificate_subject_and_raw_evidence_bytes_are_hash_bound(self):
        self.cert["subject_release_hash"]="0"*64;self.bind_cert()
        with self.assertRaises(PilotError):self.gate()
        self.cert["subject_release_hash"]=digest({k:v for k,v in self.evidence["frozen_author_inputs"]["release"].items() if k!="owner_release_evidence"})
        self.bind_cert();Path(self.raw_ref["path"]).write_bytes(b"changed")
        with self.assertRaises(PilotError):self.gate()
    def test_observation_receipt_plan_session_and_mode_chain_rejected_if_changed(self):
        for key in ("receipt","author_observation","plan"):
            with self.subTest(key=key):
                saved=copy.deepcopy(self.evidence["frozen_author_inputs"][key])
                self.evidence["frozen_author_inputs"][key]["changed"]=True
                with self.assertRaises(PilotError):self.gate()
                self.evidence["frozen_author_inputs"][key]=saved
        with self.assertRaises(PilotError):auth.validate_predecessor("INDEPENDENT_REOPEN",self.scope,self.request,self.profile,self.evidence,"OBSERVED",self.root)
    def test_direct_unbound_acquisition_is_author_only_before_io(self):
        with self.assertRaises(PilotError):asyncio.run(owner.acquire_current_schema(SimpleNamespace(role="INDEPENDENT_REOPEN"),None,None,None,{}))

class EntryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="a24-entry-wire-");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.cap,_=authority_fixture(self.root,{},None,unbound=True)
    def test_exact_navigation_timeout_step_and_close_failure_are_finite_without_retry(self):
        log=[]
        class Nav:
            def begin(self,phase):log.append("nav_begin");return 1
            def end(self,phase,since,error=None,response=None):log.append("nav_failed" if error else "nav_done")
        async def start():return runtime
        async def launch(*a,**k):return context
        async def install():log.append("install")
        async def online(value):log.append("online")
        async def goto(*a,**k):raise TimeoutError("PRIVATE_EXCEPTION_TEXT")
        async def context_close():log.append("close");raise OSError("PRIVATE_EXCEPTION_TEXT")
        async def runtime_stop():log.append("stop")
        async def settle(*a,**k):pass
        page=SimpleNamespace(url="about:blank",set_default_timeout=lambda *a:None,on=lambda *a:None,goto=goto)
        context=SimpleNamespace(pages=[page],on=lambda *a:None,set_offline=online,close=context_close)
        runtime=SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch),stop=runtime_stop)
        guard=SimpleNamespace(install=install,navigation=Nav(),auth=SimpleNamespace(arm_navigation=lambda *a:None),response=lambda *a:None,
            stopped=True,begin_shutdown=lambda:None,callbacks=set(),tasks=set(),failure=None)
        backend=object.__new__(owner.WindowsBackend)
        backend.authority=self.cap;backend.bootstrap_steps={};backend.runtime=backend.context=backend.guard=None
        backend.framework=SimpleNamespace(CurrentGuard=object,settle_callbacks=settle)
        module=SimpleNamespace(async_playwright=lambda:SimpleNamespace(start=start))
        with patch.dict(sys.modules,{"playwright":SimpleNamespace(),"playwright.async_api":module}),patch("annotation.delivery.live_pilot.usense.make_first_save_guard",return_value=guard):
            with self.assertRaises(TimeoutError):asyncio.run(backend.open(self.root,owner.base_binding(self.cap)))
        self.assertEqual(log,["install","online","nav_begin","nav_failed"])
        self.assertEqual(backend.bootstrap_steps["navigation"],"STARTED")
        released=asyncio.run(backend.close())
        self.assertFalse(released["released"]);self.assertFalse(released["context_closed"]);self.assertTrue(released["runtime_stopped"])
        self.assertEqual(released["errors"][0]["step"],"context_close")
        self.assertNotIn("PRIVATE_EXCEPTION_TEXT",json.dumps(released))
    def test_stderr_raw_is_saved_before_unsafe_output_rejection_and_handle_release(self):
        state={"exit":None,"handle":False,"job":False}
        class Handle:
            def __int__(self):return 1
            def Close(self):state["handle"]=True
        child=SimpleNamespace(_handle=Handle(),stdin=io.BytesIO(),stdout=io.BytesIO(),stderr=io.BytesIO())
        def communicate(**kwargs):state["exit"]=2;return b"{}",b"PRIVATE_STDERR_BYTES"
        child.communicate=communicate;child.poll=lambda:state["exit"]
        class API:
            def held_identity(self,handle):return {"pid":123,"created_filetime":456,"exit_observed":state["exit"] is not None,"exit_code":state["exit"]}
        class Job:
            def assign(self,child):pass
            def active(self):return 0
            def close(self):state["job"]=True
        framework=SimpleNamespace(load_native=lambda:(API,None),OwnedJob=Job)
        with patch.object(owner.subprocess,"Popen",return_value=child):result=owner.supervise(self.cap,framework,["SYNTHETIC"],"worker",b"",limit=10)
        self.assertTrue(result["released"]);self.assertFalse(result["stage_success"])
        self.assertEqual(Path(result["controlled_raw_output_refs"]["stderr"]["path"]).read_bytes(),b"PRIVATE_STDERR_BYTES")
        self.assertNotIn("PRIVATE_STDERR_BYTES",json.dumps(result))
