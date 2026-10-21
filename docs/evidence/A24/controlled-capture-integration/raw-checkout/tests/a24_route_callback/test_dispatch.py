"""Actual installed Playwright dispatch with purely synthetic route/request."""
import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from playwright._impl._helper import RouteHandler
from playwright._impl._impl_to_api_mapping import ImplToApiMapping
from annotation.delivery.live_pilot.usense import make_first_save_guard
from annotation.runtime.live_pilot.owner import owner_guard_class
from annotation.quality.live_pilot import PilotError

ROOT=Path(__file__).resolve().parents[2]

class Route:
    def __init__(self,guard,url):
        self.request=SimpleNamespace(method="GET",url=url,resource_type="fetch",redirected_from=None,frame=guard.auth_frame)
        self.actions=[];self.guard=guard;self._did_throw=False
    def _start_handling(self):
        self.future=asyncio.get_running_loop().create_future();return self.future
    async def continue_(self):self.actions.append("continue");self.future.set_result(True)
    async def abort(self,reason):self.actions.append("abort:"+reason);self.future.set_result(True)

class Base:
    def __init__(self,context,page,policy):
        self.context,self.page,self.policy=context,page,policy
        self.auth_frame=page.main_frame;self.auth=SimpleNamespace(authenticated=True)
        self.stopped=False;self.sealed=False;self.shutdown_started=False;self.callbacks=set();self.seen=[];self.failures=[]
    def record_failure(self,error):self.failures.append(getattr(error,"code",type(error).__name__));self.stopped=True
    async def route(self,route):
        self.seen.append({"same_request":route.request is self.expected_request,"tracking":asyncio.current_task() in self.callbacks})
        if self.mode=="exception":raise PilotError("SYNTHETIC_CALLBACK_FAILURE")
        if self.mode=="deny":self.record_failure(PilotError("SYNTHETIC_UNLISTED"));await route.abort("blockedbyclient")
        else:await route.continue_()

class Policy:
    def decide(self,*args):return False,"SYNTHETIC_UNLISTED"

class DispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        evidence=json.loads((ROOT/"docs/evidence/A24/route-callback-minimum/library-provenance.json").read_bytes())
        for item in evidence["sources"]:
            raw=Path(item["path"]).read_bytes()
            assert len(raw)==item["bytes"] and hashlib.sha256(raw).hexdigest()==item["sha256"]
            assert Path(item["private_fixed_copy"]).read_bytes()==raw
    def guard(self,mode="success"):
        page=SimpleNamespace(main_frame=object())
        scope={"static_path_hashes":[],"passive_book_denial_events":4}
        authority=SimpleNamespace(check=lambda:None,raw_hash="SYNTHETIC_ONLY",plan={"bootstrap":scope})
        framework=SimpleNamespace(CurrentGuard=Base,resource_type=lambda value:value.title())
        now=datetime.now(timezone.utc)
        binding={"schema":"A24FirstSaveGuardBinding/v1","activated":True,"lease_kind":"NEW_A24_FIRST_SAVE",
            "decision_ref":"SYNTHETIC_ONLY","independent_report_ref":"SYNTHETIC_ONLY","request_hash":"1"*64,"profile_hash":"2"*64,
            "request_slots":[["baseline","GET","https://www.usense.com/synthetic-slot"]],"upload_objects":[],
            "starts_at":(now-timedelta(seconds=1)).isoformat(),"ends_at":(now+timedelta(seconds=100)).isoformat()}
        guard=make_first_save_guard(owner_guard_class(framework,authority),object(),page,Policy(),binding)
        guard.mode=mode
        return guard
    async def dispatch(self,guard,url="https://www.usense.com/synthetic-bootstrap"):
        route=Route(guard,url);guard.expected_request=route.request
        mapping=ImplToApiMapping()
        handler=RouteHandler(None,"**/*",mapping.wrap_handler(guard.route),False)
        try:return await handler.handle(route),route,handler
        finally:
            self.assertFalse(guard.callbacks)
            self.assertFalse(handler._active_invocations)
    def test_actual_library_mapping_and_route_dispatch_preserve_single_route_signature(self):
        guard=self.guard()
        self.assertEqual(list(inspect.signature(guard.route).parameters),["route"])
        self.assertEqual(guard.route.__name__,"route")
        handled,route,handler=asyncio.run(self.dispatch(guard))
        self.assertTrue(handled);self.assertEqual(route.actions,["continue"])
        self.assertEqual(guard.seen,[{"same_request":True,"tracking":True}]);self.assertEqual(guard.failures,[])
    def test_actual_library_exception_propagates_and_tracking_finally_settles(self):
        guard=self.guard("exception")
        with self.assertRaises(PilotError) as error:asyncio.run(self.dispatch(guard))
        self.assertEqual(error.exception.code,"SYNTHETIC_CALLBACK_FAILURE")
        self.assertTrue(guard.seen[0]["tracking"])
    def test_actual_library_unlisted_request_delegates_to_existing_deny(self):
        guard=self.guard("deny")
        handled,route,handler=asyncio.run(self.dispatch(guard))
        self.assertTrue(handled);self.assertEqual(route.actions,["abort:blockedbyclient"])
        self.assertTrue(guard.stopped);self.assertEqual(guard.failures,["SYNTHETIC_UNLISTED"])
    def test_actual_library_stopped_wire_request_rejects_without_base_or_continue(self):
        guard=self.guard();guard.arm_wire("baseline","GET","https://www.usense.com/synthetic-slot");guard.stopped=True
        handled,route,handler=asyncio.run(self.dispatch(guard,"https://www.usense.com/synthetic-slot"))
        self.assertTrue(handled);self.assertEqual(route.actions,["abort:blockedbyclient"])
        self.assertEqual(guard.seen,[]);self.assertIn("NATIVE_WIRE_REQUEST_REJECTED",guard.failures)
    def test_unknown_direct_extra_argument_is_rejected_and_never_silently_dropped(self):
        guard=self.guard();route=Route(guard,"https://www.usense.com/synthetic-bootstrap")
        with self.assertRaises(TypeError):asyncio.run(guard.route(route,object()))
        self.assertEqual(guard.seen,[]);self.assertFalse(guard.callbacks);self.assertEqual(route.actions,[])
