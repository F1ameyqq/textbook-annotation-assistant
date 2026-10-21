"""Inherited response/capture + actual WindowsBackend configuration, fake I/O."""
import asyncio
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tests/a24_first_save_wire_r1"))
from test_r1 import authority_fixture  # helper definitions only, no old tests
from annotation.runtime.live_pilot import owner,authority as auth
from annotation.delivery.live_pilot.usense import make_first_save_guard,CurrentPageIO
from annotation.runtime.storage.common import digest
from annotation.quality.live_pilot import PilotError

SCRIPT="https://www.usense.com/qieti/assets/synthetic-owner.js"
RAW=b"SYNTHETIC_SCRIPT_BYTES_NOT_EXECUTED"
def put(path,value):
    raw=json.dumps(value).encode();path.write_bytes(raw)
    return {"path":str(path),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
def capability(root):
    cap,data=authority_fixture(root,{},None,unbound=True)
    plan=copy.deepcopy(cap.plan);plan["bootstrap"]["static_path_hashes"][0]["path_sha256"]=auth.sha(b"/qieti/assets/synthetic-owner.js")
    data["refs"]["plan"]=put(root/"plan-current.json",plan);data["scope_sha256"]=digest(plan)
    candidate=copy.deepcopy(cap.candidate);candidate["scope_sha256"]=digest(plan)
    data["refs"]["candidate"]=put(root/"candidate-current.json",candidate)
    for key in ("decision","independent_report"):
        doc=json.loads(Path(data["refs"][key]["path"]).read_bytes())
        doc.update(scope_sha256=digest(plan),plan_sha256=data["refs"]["plan"]["sha256"],candidate_sha256=data["refs"]["candidate"]["sha256"])
        data["refs"][key]=put(root/(key+"-current.json"),doc)
    reference=put(root/"authority-current.json",data)
    cap=auth.verify_authority(reference["path"],reference["sha256"],ROOT,synthetic_root=root)
    cap.output.mkdir();return cap
def framework(root):
    spec=importlib.util.spec_from_file_location("a24_current_capture_"+root.name.replace("-","_"),ROOT/"tools/a16_current_state_probe.py")
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    old=root/"old-spent-output";old.mkdir();(old/"claimed.json").write_bytes(b"SYNTHETIC_OLD_CLAIM_UNCHANGED")
    module.LIVE_OUT=old  # synthetic old namespace only; never inspect a real spent output
    return module,old
class Events:
    def __init__(self):self.handlers={}
    def on(self,name,handler):self.handlers.setdefault(name,[]).append(handler)
    def emit(self,name,value=None):
        for handler in self.handlers.get(name,[]):handler(value) if value is not None else handler()
class CDP(Events):
    async def send(self,method,params=None):
        if method=="Page.getFrameTree":return {"frameTree":{"frame":{"id":"synthetic-main"}}}
        return {}
class Route:
    def __init__(self,request):self.request=request;self.actions=[]
    async def continue_(self):self.actions.append("continue")
    async def abort(self,reason):self.actions.append("abort")
class Response:
    def __init__(self,request,raw):self.request=request;self.url=request.url;self.status=200;self.raw=raw;self.reads=0;self.headers={"content-type":"application/javascript"}
    async def body(self):self.reads+=1;return self.raw
class Context(Events):
    def __init__(self):super().__init__();self.pages=[];self.session=CDP();self.closed=False
    async def route_web_socket(self,*args):pass
    async def route(self,*args):self.route_handler=args[1]
    async def new_cdp_session(self,page):return self.session
    async def set_offline(self,value):
        if not value:
            assert self.page.guard.owner_capture_binding and self.page.guard.output.exists()
    async def close(self):self.closed=True
class Page(Events):
    def __init__(self,context):
        super().__init__();self.url="about:blank";self.main_frame=object();self.context=context;context.page=self;context.pages=[self];self.serial=0
    def set_default_timeout(self,value):pass
    @property
    def guard(self):return self.context.route_handler.__self__
    def locator(self,selector):
        async def visible():return "pdf-zones-container" in selector
        async def count():return 0
        return SimpleNamespace(is_visible=visible,count=count)
    async def exchange(self,url,kind,raw=None):
        self.serial+=1;nid="synthetic-"+str(self.serial)
        request=SimpleNamespace(method="GET",url=url,resource_type=kind.lower(),redirected_from=None,frame=self.main_frame)
        event={"requestId":"fetch-"+nid,"networkId":nid,"frameId":"synthetic-main","resourceType":kind,"request":{"method":"GET","url":url}}
        await self.guard.paused(event);route=Route(request);await self.guard.route(route)
        assert route.actions==["continue"] and not self.guard.stopped
        self.context.session.emit("Network.responseReceived",{"requestId":nid,"frameId":"synthetic-main","type":kind,"response":{"status":200}})
        if raw is not None:
            response=Response(request,raw);self.emit("response",response)
        else:response=None
        return response
    async def goto(self,url,**kwargs):
        self.url=url;await self.exchange(url,"Document")
        self.script_response=await self.exchange(SCRIPT,"Script",RAW)
        await self.exchange("https://www.usense.com/qieti/api/user_login/config/permissions","XHR",b'{"code":0,"data":[]}')
        self.emit("domcontentloaded")
        return SimpleNamespace(status=200)
def guard_for(cap,fw):
    context=Context();page=Page(context)
    guard=make_first_save_guard(owner.owner_guard_class(fw,cap),context,page,owner.BootstrapPolicy(cap),owner.base_binding(cap))
    guard.main_frame_id="synthetic-main";guard.session=context.session
    return guard,context,page

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="a24-owned-capture-");self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cap=capability(self.root);self.fw,self.old=framework(self.root)
    def test_actual_owner_bootstrap_inherited_script_and_session_capture_reaches_four_read_boundary(self):
        context=Context();page=Page(context);runtime=SimpleNamespace(stopped=False)
        async def launch(*args,**kwargs):self.assertTrue(kwargs["offline"]);return context
        async def start():return runtime
        async def stop():runtime.stopped=True
        runtime.chromium=SimpleNamespace(launch_persistent_context=launch);runtime.stop=stop
        backend=object.__new__(owner.WindowsBackend);backend.authority=self.cap;backend.framework=self.fw
        backend.runtime=backend.context=backend.guard=None;backend.bootstrap_steps={}
        backend.profile=lambda:self.root;backend.occupancy=lambda *args:None
        reads=[]
        async def fake_fetch(io,method,path,**kwargs):
            self.assertTrue(io.guard.auth.authenticated);self.assertEqual(io.guard.output,self.cap.output/"private/source-capture")
            reads.append((method,path));return {"http_status":200,"body":"SYNTHETIC_UNBOUND_SNAPSHOT"}
        module=SimpleNamespace(async_playwright=lambda:SimpleNamespace(start=start))
        with patch.dict(sys.modules,{"playwright.async_api":module}),patch.object(CurrentPageIO,"fetch_async",new=fake_fetch):
            result=asyncio.run(owner.run_owned_worker(self.cap,backend))
        self.assertEqual(result["status"],"PREWRITE_BLOCKED_NO_EFFECT",result)
        self.assertEqual(len(reads),4);self.assertTrue(all(method=="GET" for method,path in reads))
        self.assertTrue(context.closed and runtime.stopped);self.assertFalse(backend.guard.tasks);self.assertFalse(backend.guard.callbacks)
        self.assertEqual(page.script_response.reads,1)
        capture=result["private_capture_evidence"];self.assertEqual(capture["status"],"BOUND_PRIVATE_CAPTURE")
        self.assertEqual(len(capture["assets"]),1);asset=capture["assets"][0]
        self.assertEqual(Path(asset["private_raw_ref"]["path"]).read_bytes(),RAW)
        provenance=json.loads(Path(asset["private_provenance_ref"]["path"]).read_bytes())
        self.assertEqual(provenance["source_url"],SCRIPT);self.assertFalse(provenance["executed_by_collector"])
        self.assertNotIn(SCRIPT,json.dumps(capture));self.assertEqual((self.old/"claimed.json").read_bytes(),b"SYNTHETIC_OLD_CLAIM_UNCHANGED")
        self.assertEqual([p.name for p in self.old.iterdir()],["claimed.json"])
    def response(self,guard):
        return Response(SimpleNamespace(url=SCRIPT,method="GET",resource_type="script",frame=guard.auth_frame),RAW)
    def test_unbound_owner_rejects_before_consuming_script_or_writing(self):
        guard,context,page=guard_for(self.cap,self.fw);response=self.response(guard)
        with self.assertRaises(PilotError):asyncio.run(guard.capture(response))
        self.assertEqual(response.reads,0);self.assertFalse((self.cap.output/"private/source-capture").exists())
    def test_wrong_and_lexically_aliased_capture_paths_reject_before_body(self):
        guard,context,page=guard_for(self.cap,self.fw);owner.bind_capture_owner(self.cap,self.fw,guard)
        proper=guard.output
        for wrong in (self.old,proper/".."/"source-capture"):
            with self.subTest(path=str(wrong)):
                guard.output=wrong;self.fw.LIVE_OUT=wrong;response=self.response(guard)
                with self.assertRaises(PilotError):asyncio.run(guard.capture(response))
                self.assertEqual(response.reads,0)
        self.assertEqual((self.old/"claimed.json").read_bytes(),b"SYNTHETIC_OLD_CLAIM_UNCHANGED")
    def test_reparse_capture_root_rejects_before_directory_or_marker_creation(self):
        guard,context,page=guard_for(self.cap,self.fw);private=self.cap.output/"private";private.mkdir()
        original=Path.lstat
        def lstat(path):
            info=original(path)
            if path==private:return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=getattr(info,"st_file_attributes",0)|0x400)
            return info
        with patch.object(Path,"lstat",new=lstat):
            with self.assertRaises(Exception):owner.bind_capture_owner(self.cap,self.fw,guard)
        self.assertFalse((private/"source-capture").exists());self.assertEqual(self.fw.LIVE_OUT,self.old)
    def test_capture_owner_marker_scope_tamper_rejects_before_response_read(self):
        guard,context,page=guard_for(self.cap,self.fw);owner.bind_capture_owner(self.cap,self.fw,guard)
        marker=guard.output/"capture-owner.json";data=json.loads(marker.read_bytes());data["scope_sha256"]="0"*64;marker.write_bytes(json.dumps(data).encode())
        response=self.response(guard)
        with self.assertRaises(PilotError):asyncio.run(guard.capture(response))
        self.assertEqual(response.reads,0)
    def test_existing_inherited_exclusive_script_file_and_response_task_failure_settle(self):
        guard,context,page=guard_for(self.cap,self.fw);owner.bind_capture_owner(self.cap,self.fw,guard)
        response=self.response(guard)
        async def run():
            guard.response(response);await self.fw.settle_callbacks(guard,seconds=1)
            path=guard.output/guard.scripts[0]["ref"];before=path.read_bytes()
            guard.scripts=[]  # synthetic duplicate callback must hit the inherited xb guard
            guard.response(self.response(guard));await self.fw.settle_callbacks(guard,seconds=1)
            self.assertEqual(path.read_bytes(),before)
        asyncio.run(run());self.assertTrue(guard.stopped);self.assertFalse(guard.callbacks);self.assertFalse(guard.tasks)
    def test_unknown_decision_is_explicit_projection_error_without_replaying_old_control(self):
        guard,context,page=guard_for(self.cap,self.fw)
        guard.audit("GET",owner.TARGET,"Document","NAVIGATION",True,"FETCH_REQUEST_STAGE")
        guard.events[0]["decision"]="UNRECOGNIZED_DECISION"
        result=owner.guard_evidence(guard)
        self.assertEqual(result["status"],"PROJECTION_ERROR");self.assertFalse(result["complete"])
