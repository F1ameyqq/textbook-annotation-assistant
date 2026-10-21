"""Inherited CurrentGuard classification/dispatch only; no real resources."""
import asyncio
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("a24_new_exclusion_framework",ROOT/"tools/a16_current_state_probe.py")
framework=importlib.util.module_from_spec(spec);sys.modules[spec.name]=framework;spec.loader.exec_module(framework)
from annotation.runtime.live_pilot import owner
from annotation.delivery.live_pilot.usense import make_first_save_guard
from annotation.source.usense.current_readonly.policy import excluded_static,EXCLUDED_STATIC,ReadPolicy
from annotation.source.usense.current_readonly.gate import Stop
from annotation.runtime.storage.common import digest

CDN="https://cdn.bootcdn.net/ajax/libs/synthetic-excluded/1.0/test.js"
SECRET="UNAPPROVED_PRIVATE_QUERY_BODY_SENTINEL"
class CDP:
    def __init__(self):self.commands=[]
    async def send(self,method,params):self.commands.append((method,params));return {}
class Route:
    def __init__(self,guard,url,kind="Script",method="GET"):
        self.request=SimpleNamespace(url=url,method=method,resource_type=kind.lower(),redirected_from=None,frame=guard.auth_frame)
        self.actions=[]
    async def abort(self,reason):self.actions.append("abort:"+reason)
    async def continue_(self):self.actions.append("continue")
    async def fulfill(self,**kwargs):raise AssertionError("EXCLUSION_MUST_NOT_FULFILL")
def make_guard():
    scope=json.loads((ROOT/"docs/evidence/A24/first-save-wire-r1/concrete-plan.json").read_bytes())["bootstrap"]
    authority=SimpleNamespace(check=lambda:None,raw_hash="SYNTHETIC_ONLY",plan={"bootstrap":scope})
    page=SimpleNamespace(main_frame=object())
    policy=owner.BootstrapPolicy(authority)
    binding={"schema":"A24FirstSaveGuardBinding/v1","activated":True,"lease_kind":"NEW_A24_FIRST_SAVE","request_hash":"1"*64,
        "profile_hash":"2"*64,"decision_ref":"SYNTHETIC_ONLY","independent_report_ref":"SYNTHETIC_ONLY","request_slots":[],"upload_objects":[]}
    guard=make_first_save_guard(owner.owner_guard_class(framework,authority),object(),page,policy,binding)
    guard.main_frame_id="synthetic-main";guard.session=CDP()
    return guard,policy
async def barriers(guard,url):
    route=Route(guard,url)
    await guard.route(route)
    await guard.paused({"requestId":"synthetic-fetch","networkId":"synthetic-network","frameId":"synthetic-main",
        "resourceType":"Script","request":{"url":url,"method":"GET"}})
    return route
class IntegrationTests(unittest.TestCase):
    def test_exact_preexisting_exclusion_aborted_nonfatal_by_both_inherited_barriers(self):
        guard,policy=make_guard()
        self.assertTrue(excluded_static("GET",CDN,"Script"))
        self.assertEqual(policy.decide("GET",CDN,"Script"),ReadPolicy().decide("GET",CDN,"Script"))
        route=asyncio.run(barriers(guard,CDN))
        self.assertEqual(route.actions,["abort:blockedbyclient"])
        self.assertEqual(guard.session.commands[0][0],"Fetch.failRequest")
        self.assertEqual(guard.excluded_static_events,2);self.assertEqual(guard.excluded_static_denials_completed,2)
        self.assertFalse(guard.stopped);self.assertIsNone(guard.failure);self.assertFalse(guard.callbacks)
        self.assertTrue(all(event["decision"]=="BLOCK" and event["category"]==EXCLUDED_STATIC for event in guard.events))
    def test_unknown_protected_redirect_method_document_and_host_variants_are_fatal(self):
        variants=[("GET","https://unapproved.invalid/static.js","Script",False),
            ("GET","https://cdn.bootcdn.net/api/test.js","Script",False),
            ("GET","https://cdn.bootcdn.net/login.js","Script",False),
            ("GET",CDN,"Script",True),("POST",CDN,"Script",False),("GET",CDN,"Document",False),
            ("GET","http://cdn.bootcdn.net/test.js","Script",False),
            ("GET","https://cdn.bootcdn.net.evil.invalid/test.js","Script",False)]
        for method,url,kind,redirected in variants:
            with self.subTest(url=url,kind=kind,method=method):
                guard,policy=make_guard()
                allowed,category,nonfatal=guard.classify(method,url,kind,redirected,True)
                self.assertFalse(allowed);self.assertFalse(nonfatal);self.assertNotEqual(category,EXCLUDED_STATIC)
    def test_shared16_budget_counts_both_layers_and_seventeenth_is_fatal(self):
        guard,policy=make_guard()
        async def run():
            for _ in range(8):await barriers(guard,CDN)
            self.assertEqual(guard.excluded_static_events,16);self.assertFalse(guard.stopped)
            route=Route(guard,CDN);await guard.route(route);return route
        route=asyncio.run(run())
        self.assertEqual(route.actions,["abort:blockedbyclient"])
        self.assertEqual(guard.excluded_static_events,17);self.assertTrue(guard.stopped)
        self.assertIn("EXCLUDED_STATIC_EVENT_LIMIT",guard.failure["codes"])
    def test_existing_safe_audit_projection_retains_no_raw_query_or_body(self):
        guard,policy=make_guard();asyncio.run(barriers(guard,CDN+"?token="+SECRET))
        guard.audit("GET","https://unknown.invalid/private/"+SECRET+"?username="+SECRET+"&token="+SECRET,
                    "Script","ORIGIN_BLOCKED",False,"FETCH_REQUEST_STAGE")
        guard.record_failure(Stop("ORIGIN_BLOCKED"))
        guard.events[-1]["body"]={"token":SECRET};guard.events[-1]["raw_url"]="https://unknown.invalid/"+SECRET
        result=owner.guard_evidence(guard)
        self.assertEqual(result["status"],"PROJECTED");self.assertTrue(result["complete"])
        self.assertEqual(result["first_failure"]["codes"],["ORIGIN_BLOCKED"])
        self.assertNotIn(SECRET,json.dumps(result));self.assertIn("username",json.dumps(result))
        self.assertEqual(result["exclusions"]["combined_guard_events"],2)
    def test_earliest_block_and_failure_event_are_retained_after_head_limit(self):
        guard,policy=make_guard()
        for _ in range(160):guard.audit("GET",owner.TARGET,"Document","NAVIGATION",True,"FETCH_REQUEST_STAGE")
        guard.audit("GET",CDN,"Script",EXCLUDED_STATIC,False,"FETCH_REQUEST_STAGE")
        guard.audit("GET","https://unknown.invalid/x","Script","ORIGIN_BLOCKED",False,"FETCH_REQUEST_STAGE")
        guard.record_failure(Stop("ORIGIN_BLOCKED"))
        for _ in range(20):guard.audit("GET",owner.TARGET,"Document","STOPPED",False,"FETCH_REQUEST_STAGE")
        result=owner.guard_evidence(guard)
        self.assertEqual(result["status"],"PROJECTED");self.assertTrue(result["truncated"]);self.assertFalse(result["complete"])
        self.assertEqual(result["total_events"],182);self.assertEqual(result["retained_events"],130)
        self.assertEqual(result["earliest_block_index"],160);self.assertEqual(result["first_failure_category_event_index"],161)
        self.assertIn(160,[event["index"] for event in result["events"]]);self.assertIn(161,[event["index"] for event in result["events"]])
    def test_projection_error_is_explicit_and_never_complete_empty_success(self):
        guard,policy=make_guard();guard.events.append({"method":"GET","decision":"BLOCK","path_template":"/private/"+SECRET})
        result=owner.guard_evidence(guard)
        self.assertEqual(result["status"],"PROJECTION_ERROR");self.assertFalse(result["complete"])
        self.assertNotIn("events",result);self.assertNotIn(SECRET,json.dumps(result))
        self.assertEqual(owner.guard_evidence(None)["status"],"NOT_CREATED")
    def test_worker_success_failure_and_cleanup_error_save_both_existing_event_snapshots(self):
        sys.path.insert(0,str(ROOT/"tests/a24_first_save_wire_r1"))
        from test_r1 import authority_fixture  # immutable helper definitions, no suite
        for behavior in ("success","failed_open","failed_cleanup"):
            with self.subTest(behavior=behavior),tempfile.TemporaryDirectory(prefix="a24-exclusion-evidence-") as directory:
                root=Path(directory);cap,_=authority_fixture(root,{},None,unbound=True)
                guard,policy=make_guard()
                class Backend:
                    def __init__(self):self.guard=guard
                    def profile(self):return root
                    def occupancy(self,*args):pass
                    async def open(self,*args):
                        guard.audit("GET",owner.TARGET,"Document","NAVIGATION",True,"FETCH_REQUEST_STAGE")
                        if behavior=="failed_open":
                            guard.audit("GET","https://unknown.invalid/x","Script","ORIGIN_BLOCKED",False,"FETCH_REQUEST_STAGE")
                            guard.record_failure(Stop("ORIGIN_BLOCKED"));raise Stop("ORIGIN_BLOCKED")
                        return None,None,guard
                    async def close(self):
                        guard.audit("GET",owner.TARGET,"Document","STOPPED",False,"FETCH_REQUEST_STAGE")
                        guard.begin_shutdown();guard.sealed=True
                        if behavior=="failed_cleanup":raise ValueError(SECRET)
                        return {"released":True}
                backend=Backend()
                # No synthetic source acquisition here: only the changed finalizer is under test.
                async def unavailable(*args):return {"status":"CURRENT_SCHEMA_UNBOUND","reads":[],"successors":"NOT_RUN"}
                from unittest.mock import patch
                with patch.object(owner,"acquire_current_schema",side_effect=unavailable):
                    result=asyncio.run(owner.run_owned_worker(cap,backend))
                self.assertEqual(result["guard_evidence_before_release"]["status"],"PROJECTED")
                self.assertEqual(result["guard_evidence_after_release"]["status"],"PROJECTED")
                self.assertFalse(result["guard_evidence_before_release"]["settlement"]["sealed"])
                self.assertTrue(result["guard_evidence_after_release"]["settlement"]["sealed"])
                if behavior=="failed_open":
                    self.assertEqual(result["guard_evidence_before_release"]["first_failure"],result["guard_evidence_after_release"]["first_failure"])
                    self.assertEqual(result["guard_evidence_after_release"]["first_failure"]["codes"],["ORIGIN_BLOCKED"])
                if behavior=="failed_cleanup":self.assertEqual(result["status"],"OWNER_RELEASE_UNPROVEN")
                self.assertNotIn(SECRET,json.dumps(result));self.assertTrue((cap.output/"worker-result.json").exists())
