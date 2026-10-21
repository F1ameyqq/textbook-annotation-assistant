"""R1 delta controls, exclusively synthetic. Every attempt is recorded by run.py."""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qsl

from annotation.delivery.live_pilot import wire
from annotation.delivery.live_pilot.usense import UsenseTransport, CurrentPageIO, make_first_save_guard
from annotation.quality.live_pilot import PilotError, check_preservation
from annotation.runtime.live_pilot import authority as auth, owner
from annotation.runtime.live_pilot.journal import Journal
from annotation.runtime.live_pilot.private_payload import ControlledVault, resolve_intent
from annotation.runtime.live_pilot.runner import apply, apply_current_context
from annotation.runtime.storage.common import digest
from fixture import fixture, bind_profile, FakeIO
from browser_helpers import Page, Context, BaseGuard, Policy

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = "R1_PRIVATE_SESSION_QUERY_SENTINEL_7429"
REQUIRED = ["tools/a24_first_save_launcher.py", "src/annotation/runtime/live_pilot/owner.py",
    "src/annotation/runtime/live_pilot/authority.py", "src/annotation/runtime/live_pilot/runner.py",
    "src/annotation/runtime/live_pilot/private_payload.py", "src/annotation/delivery/live_pilot/usense.py",
    "src/annotation/delivery/live_pilot/wire.py", "src/annotation/delivery/live_pilot/plan.py",
    "src/annotation/quality/live_pilot.py", "src/annotation/runtime/live_pilot/journal.py",
    "tools/a16_current_state_probe.py", "docs/evidence/A16/current-readonly/dependencies/a15_native_reference.py",
    "docs/evidence/A15/certificate-exception/reviewed-native/native_windows.py",
    "docs/evidence/A15/certificate-exception/reviewed-native/process_check.py"]


def put(path, value):
    raw = json.dumps(value, ensure_ascii=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": str(path), "bytes": len(raw), "sha256": auth.sha(raw)}


def authority_fixture(root, request, profile, *, unbound=False, author_release=None):
    plan = json.loads((ROOT/"docs/evidence/A24/first-save-wire-r1/concrete-plan.json").read_bytes())
    plan["body_admission"] = "CURRENT_SCHEMA_UNBOUND" if unbound else "FROZEN_QUALIFIED_ROUTE_CODEC"
    crops = {"schema": "A24R1ExactCropBindings/v1", "regions": []}
    for index, role in enumerate(("Q", "W", "W", "W", "W", "A")):
        path = root/"crop"/str(index)
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"SYNTHETIC_CROP")
        crops["regions"].append({"role": role, "private_path": str(path), "jpeg_bytes": path.stat().st_size,
                                  "jpeg_sha256": auth.sha(path.read_bytes())})
    candidate = {"schema": "A24R1FrozenCandidate/v1", "scope_sha256": digest(plan), "dependencies": [
        {"path": p, "bytes": (ROOT/p).stat().st_size, "sha256": auth.sha((ROOT/p).read_bytes())} for p in REQUIRED]}
    refs = {k: put(root/(k+".json"), v) for k, v in {"candidate": candidate, "plan": plan,
            "request": request, "crop_manifest": crops}.items()}
    refs["schema_profile"] = None if unbound else put(root/"schema.json", profile)
    refs["author_release"] = None if author_release is None else put(root/"author-release.json", author_release)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start, end = (now-timedelta(seconds=2)).isoformat(), (now+timedelta(seconds=850)).isoformat()
    common = {"task": "A24", "mode": "SYNTHETIC", "run_id": "A24-first-save-r1-test", "role": "AUTHOR_SAVE",
        "coordinator": auth.COORDINATOR, "executor": auth.AUTHOR, "scope_sha256": digest(plan),
        "candidate_sha256": refs["candidate"]["sha256"], "plan_sha256": refs["plan"]["sha256"],
        "request_sha256": refs["request"]["sha256"], "crop_manifest_sha256": refs["crop_manifest"]["sha256"],
        "schema_profile_sha256": None if unbound else refs["schema_profile"]["sha256"],
        "author_release_sha256": None, "not_before": start, "expires_at": end}
    if author_release is not None:
        common.update(role="INDEPENDENT_REOPEN", executor=auth.REVIEWER, run_id="A24-first-save-r1-reopen-test",
                      author_release_sha256=refs["author_release"]["sha256"])
    refs["decision"] = put(root/"decision.json", dict(common, schema="A24FirstSaveUserDecision/v1", live_authorized=True,
        authorization_basis="USER_REQUESTED_A24_FIRST_SAVE_BOUND_TO_THIS_EXACT_SCOPE", credential_submission_authorized=False,
        credential_config_access_authorized=False, tls_exception_authorized=True, upload_origin=plan["upload_host"]))
    refs["independent_report"] = put(root/"independent.json", dict(common, schema="A24FirstSaveIndependentAcceptance/v1",
        reviewer=auth.REVIEWER, result="ACCEPTED_OFFLINE_ONLY"))
    data = {"schema": "A24FirstSaveOwnerAuthority/v1", "task": "A24", "mode": "SYNTHETIC", "role": "AUTHOR_SAVE",
        "run_id": common["run_id"], "coordinator": auth.COORDINATOR, "executor": auth.AUTHOR,
        "profile_fingerprint": auth.PROFILE, "not_before": start, "expires_at": end, "scope_sha256": digest(plan),
        "refs": refs, "output_directory": str(root/common["run_id"]), "ignore_https_errors": True,
        "original_and_crop_roots": [str(root/"crop")], "old_budgets_restored": False}
    if author_release is not None:
        data.update(role=common["role"], executor=common["executor"], output_directory=str(root/common["run_id"]))
    reference = put(root/"authority.json", data)
    return auth.verify_authority(reference["path"], reference["sha256"], ROOT, synthetic_root=root), data


class SentinelIO(FakeIO):
    def request_once(self, method, path, **kwargs):
        response = super().request_once(method, path, **kwargs)
        if method == "POST":
            body = json.loads(response["body"])
            body["unapproved_session_material"] = SENTINEL
            if self.behavior == "bad_receipt":
                body["question_order"] = None
            response["body"] = json.dumps(body)
        return response


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a24-r1-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        home = patch.object(Path, "home", return_value=self.root/"isolated-home")
        home.start()
        self.addCleanup(home.stop)
        self.request, self.initial, self.fact, self.profile = fixture(self.root)

    def seal(self, unbound=False):
        self.profile["session"].update(executor=auth.AUTHOR, reviewer=auth.REVIEWER, session_id="A24-first-save-r1-test")
        proto = {"frames": self.fact["frames"], "approved_parts": self.fact["parts"], "source_bindings": self.request["bindings"],
            "insert_after_order": 9, "action": {"expected_after": {"directory_id": "target-a"}}}
        self.request["approval"]["payload_hash"] = digest(wire.build_payload(proto, self.profile))
        bind_profile(self.request, self.profile, self.root)
        self.cap, self.data = authority_fixture(self.root, self.request, self.profile, unbound=unbound)
        return self.cap

    def test_receipt_extra_is_projected_before_journal_and_private_intent_resolves(self):
        self.seal()
        fake = SentinelIO(self.initial, self.fact, actor=auth.AUTHOR, session_id=self.profile["session"]["session_id"])
        journal = Journal(self.root/"journal", offline=True)
        vault = ControlledVault(self.cap)
        report = apply(self.request, self.root, journal, UsenseTransport(fake), private_vault=vault)
        self.assertEqual(report["questions"][self.fact["question_id"]]["state"], "APPLIED_SYNTHETIC_WIRE")
        events = journal.read()
        self.assertNotIn(SENTINEL, json.dumps(events))
        stored = next(e["data"] for e in events if e["kind"] == "INTENT")
        self.assertNotIn("payload", stored)
        self.assertIn("payload", resolve_intent(stored, vault))
        self.assertTrue(report["private_author_evidence_ref"])

    def test_bad_receipt_unknown_hash_only_and_existing_claim_prevents_resend(self):
        self.seal()
        fake = SentinelIO(self.initial, self.fact, behavior="bad_receipt", actor=auth.AUTHOR, session_id=self.profile["session"]["session_id"])
        journal = Journal(self.root/"journal", offline=True)
        report = apply(self.request, self.root, journal, UsenseTransport(fake), private_vault=ControlledVault(self.cap))
        self.assertEqual(report["questions"][self.fact["question_id"]]["state"], "UNKNOWN")
        event = next(e["data"] for e in journal.read() if e["kind"] == "BUSINESS_RECEIPT")
        self.assertEqual(event["status"], "UNKNOWN")
        self.assertNotIn("receipt", event)
        self.assertNotIn(SENTINEL, json.dumps(journal.read()))
        with self.assertRaises(PilotError):
            apply(self.request, self.root, journal, UsenseTransport(fake))
        self.assertEqual(sum(c["method"] == "POST" for c in fake.calls), 1)

    def test_query_values_absent_from_plan_ledger_and_journal(self):
        for spec in self.profile["reads"].values():
            spec["params"]["username"] = SENTINEL
        self.seal()
        fake = FakeIO(self.initial, self.fact, actor=auth.AUTHOR, session_id=self.profile["session"]["session_id"])
        journal = Journal(self.root/"journal", offline=True)
        vault = ControlledVault(self.cap)
        transport = UsenseTransport(fake)
        result = apply(self.request, self.root, journal, transport, private_vault=vault)
        self.assertEqual(result["questions"][self.fact["question_id"]]["state"], "APPLIED_SYNTHETIC_WIRE")
        self.assertNotIn(SENTINEL, json.dumps(transport._ledger))
        self.assertNotIn(SENTINEL, json.dumps(journal.read()))
        intent = resolve_intent(next(e["data"] for e in journal.read() if e["kind"] == "INTENT"), vault)
        self.assertNotIn(SENTINEL, json.dumps(intent["plan"]))
        self.assertIn("query_hash", transport._ledger[0])

    def test_authority_mutation_fails_before_backend_or_profile(self):
        self.seal()
        for key, changed in (("schema", "A24ReadonlyActivation/v1"), ("old_budgets_restored", True), ("scope_sha256", "0"*64)):
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data[key] = changed
                ref = put(self.root/(key+"-bad.json"), data)
                with patch.object(owner, "WindowsBackend", side_effect=AssertionError("MUST_NOT_ACQUIRE")) as backend:
                    with self.assertRaises(PilotError):
                        auth.verify_authority(ref["path"], ref["sha256"], ROOT, synthetic_root=self.root)
                    backend.assert_not_called()
        self.cap.request["mutation"] = True
        with self.assertRaises(PilotError): self.cap.check()

    def test_raw_dependency_tamper_and_expired_window_rejected(self):
        self.seal()
        data = copy.deepcopy(self.data)
        candidate = copy.deepcopy(self.cap.candidate)
        candidate["dependencies"][0]["sha256"] = "0"*64
        data["refs"]["candidate"] = put(self.root/"bad-candidate.json", candidate)
        for key in ("decision", "independent_report"):
            doc = json.loads(Path(data["refs"][key]["path"]).read_bytes())
            doc["candidate_sha256"] = data["refs"]["candidate"]["sha256"]
            data["refs"][key] = put(self.root/(key+"-bad-candidate.json"), doc)
        ref = put(self.root/"bad-dep-auth.json", data)
        with self.assertRaises(PilotError): auth.verify_authority(ref["path"], ref["sha256"], ROOT, synthetic_root=self.root)
        with self.assertRaises(PilotError): self.cap.check(datetime.now(timezone.utc)+timedelta(days=1))

    def test_plan_boolean_counts_rejected(self):
        self.seal()
        plan = copy.deepcopy(self.cap.plan)
        plan["business_get_counts"]["baseline"] = True
        with self.assertRaises(PilotError): auth.validate_plan(plan)

    def test_old_raw_annotation_change_is_rejected(self):
        before, after = copy.deepcopy(self.initial), copy.deepcopy(self.initial)
        before["view"]["wire_annotations"] = {"old-a": [{"raw": "kept"}]}
        after["view"]["wire_annotations"] = {"old-a": [{"raw": "changed"}]}
        with self.assertRaises(PilotError): check_preservation(before, after)

    def test_natural_export_requires_qualified_route_without_metadata_fabrication(self):
        codec = {"schema": "A24NaturalExportCodec/v1", "question_fields": {k: [k] for k in
            ("platform_question_id", "question_type", "parts", "wire_zones", "question_info", "rect_ids")},
            "qualification": {"schema": "A24FullBodyRouteQualification/v1", "status": "UNKNOWN"}}
        row = {"platform_question_id": "old-a", "question_type": "ordinary_choice", "parts": [{"text": "old"}],
            "wire_zones": dict.fromkeys(wire.ZONES), "question_info": {}, "rect_ids": ["r"]}
        with self.assertRaises(PilotError): wire.decode_complete_export(json.dumps(row), codec, [{"platform_question_id": "old-a"}])
        codec["qualification"].update(status="VERIFIED", route=wire.EXPORT, book_id=wire.BOOK,
            authoritative_catalog_complete=True, all_business_fields_covered=True, zones=list(wire.ZONES),
            state_binding="SYNTHETIC_ONLY", evidence_refs=["SYNTHETIC_ROUTE"])
        contents, coverage = wire.decode_complete_export(json.dumps(row), codec, [{"platform_question_id": "old-a"}])
        self.assertTrue(coverage["complete"])
        self.assertEqual(contents["old-a"]["rect_ids"], ["r"])
        self.assertIn("raw_record_hash", contents["old-a"])

    def test_generic_adapter_cannot_bypass_owner_authority(self):
        with self.assertRaises(PilotError):
            asyncio.run(apply_current_context({}, self.root, page=None, context=None, guard=None, binding={}))

    def test_fixed_accepted_model_refs_match_native_conversion_without_new_model_call(self):
        path = Path("D:/1800/.local/stages/a24-first-save-r1-inputs/author-content-v1/request-accepted-content-v2.json")
        request = json.loads(path.read_bytes())
        crops = json.loads((ROOT/"docs/evidence/A24/first-save-wire-r1/crop-bindings.json").read_bytes())
        self.assertTrue(auth.validate_fixed_content(request, crops, [Path("D:/1800").resolve()]))

    def setup_upload(self, status):
        from PIL import Image
        self.request["approval"]["operations"].append("UPLOAD_CROPS")
        self.profile["limits"].update(upload=6, signature=1)
        self.profile["proofs"]["upload_plan"] = "a24-proof-upload_plan"
        self.profile["uploads"] = []
        for i, row in enumerate(self.profile["wire"]["rows"]):
            path = self.root/("upload-"+str(i)+".jpg")
            Image.new("RGB", (30, 8), (i*20, 40, 60)).save(path, format="JPEG")
            key = "approved/"+path.name
            row["fields"]["image_path"] = row["crop"]["image_path"] = "https://synthetic.invalid/"+key
            self.profile["uploads"].append({"fragment_id": row["fragment_id"], "rect_id": row["fields"]["rect_id"],
                "key": key, "resource": {"path": path.name, "sha256": auth.sha(path.read_bytes()), "media_type": "image/jpeg"},
                "width": 30, "height": 8})
        self.profile["signature"] = {"host": "https://synthetic.invalid", "dir": "approved/", "minimum_expire": 5000000000,
            "policy_sha256": auth.sha(b"PRIVATE_POLICY"), "response_path": ["data"]}
        self.seal()
        class UploadIO(SentinelIO):
            uploads = 0
            def request_once(inner, method, path, **kwargs):
                if path == wire.SIGNATURE:
                    inner.calls.append({"method": method, "path": path})
                    return inner.response({"data": {"accessid": "PRIVATE_ACCESS", "host": "https://synthetic.invalid",
                        "policy": "PRIVATE_POLICY", "signature": "PRIVATE_SIGNATURE", "dir": "approved/", "expire": 5000000001}})
                return super().request_once(method, path, **kwargs)
            def upload_once(inner, host, *, fields, content):
                inner.uploads += 1
                return {"http_status": status, "request_id": "upload-"+str(inner.uploads), "session_id": inner.session_id,
                    "fresh": True, "cache": False, "response_hash": auth.sha(b"")}
        fake = UploadIO(self.initial, self.fact, actor=auth.AUTHOR, session_id=self.profile["session"]["session_id"])
        journal = Journal(self.root/"upload-journal", offline=True)
        result = apply(self.request, self.root, journal, UsenseTransport(fake), private_vault=ControlledVault(self.cap))
        return fake, journal, result

    def test_native_http_upload_ack_needs_no_invented_host_key_echo(self):
        fake, journal, report = self.setup_upload(204)
        self.assertEqual(fake.uploads, 6)
        self.assertEqual(report["questions"][self.fact["question_id"]]["state"], "APPLIED_SYNTHETIC_WIRE")
        events = [e["data"] for e in journal.read() if e["kind"] == "UPLOAD_RECEIPT"]
        self.assertEqual(len(events), 6)
        self.assertNotIn("PRIVATE_SIGNATURE", json.dumps(journal.read()))

    def test_native_http403_burns_object_without_resign_or_commit(self):
        fake, journal, report = self.setup_upload(403)
        self.assertEqual(fake.uploads, 1)
        self.assertEqual(sum(c["path"] == wire.SIGNATURE for c in fake.calls), 1)
        self.assertEqual(sum(c["method"] == "POST" for c in fake.calls), 0)
        self.assertEqual(report["questions"][self.fact["question_id"]]["state"], "UNKNOWN")

    def test_supervisor_job_assignment_and_identity_failures_always_close_owned_handles(self):
        self.seal()
        for behavior in ("success", "assignment_failure", "identity_mismatch"):
            with self.subTest(behavior=behavior):
                state = {"killed": False, "handle_closed": False, "job_closed": False, "identity": 0}
                class Handle:
                    def __int__(inner): return 123
                    def Close(inner): state["handle_closed"] = True
                child = SimpleNamespace(_handle=Handle(), stdin=io.BytesIO(), stdout=io.BytesIO(), stderr=io.BytesIO(), returncode=None)
                def communicate(**kwargs):
                    self.assertTrue(state.get("assigned"))
                    child.returncode = 0
                    return json.dumps({"schema": "A24FirstSaveStageResult/v1", "stage": behavior,
                        "status": "PREWRITE_BLOCKED_NO_EFFECT", "released": True}).encode(), b""
                child.communicate = communicate
                child.poll = lambda: child.returncode
                def kill(): state["killed"] = True; child.returncode = 2
                child.kill = kill
                child.wait = lambda **kw: child.returncode
                class API:
                    def held_identity(inner, handle):
                        state["identity"] += 1
                        return {"pid": 100, "created_filetime": 200+(1 if behavior == "identity_mismatch" and state["identity"] == 2 else 0),
                            "exit_observed": child.returncode is not None, "exit_code": child.returncode}
                class Job:
                    def assign(inner, proc):
                        if behavior == "assignment_failure": raise OSError(SENTINEL)
                        state["assigned"] = True
                    def active(inner): return 0
                    def terminate(inner): kill()
                    def close(inner): state["job_closed"] = True
                framework = SimpleNamespace(load_native=lambda: (API, None), OwnedJob=Job)
                with patch.object(owner.subprocess, "Popen", return_value=child):
                    result = owner.supervise(self.cap, framework, ["SYNTHETIC"], behavior, b"SYNTHETIC", limit=10)
                self.assertTrue(state["handle_closed"] and state["job_closed"])
                self.assertEqual(result["released"], behavior != "identity_mismatch")
                self.assertEqual(result["stage_success"], behavior == "success")
                if behavior == "assignment_failure": self.assertTrue(state["killed"])
                self.assertNotIn(SENTINEL, json.dumps(result))


class DataPage(Page):
    def __init__(self, context, fake):
        super().__init__(context)
        self.fake = fake

    async def evaluate(self, script, args=None):
        from annotation.source.usense.current_readonly.context_query import PREPARE_JS, official_endpoint
        if script == PREPARE_JS:
            return {"status": "PREPARED", "endpoint": official_endpoint(SENTINEL, "worker")}
        if isinstance(args, str):
            result = await self.emit_request("GET", "https://www.usense.com"+args)
            return dict(result, context_status="BOUND_CONTEXT_UNCHANGED")
        return await super().evaluate(script, args)

    async def emit_request(self, method, url, raw=None, headers=None, kind="Fetch"):
        # Fixed helper still exercises both real guard barriers and native bytes.
        original = json.dumps
        parsed = urlsplit(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        payload = json.loads(raw) if raw and kind != "Document" else None
        phase = self.guard.wire_active[0] if self.guard.wire_active else "refresh"
        if parsed.path in ("/qieti/annotateUnified",) or phase == "acquire":
            body = {"code": 0, "synthetic_current_schema": "UNKNOWN"}
        else:
            body = json.loads(self.fake.request_once(method, parsed.path, params=params, payload=payload, phase=phase)["body"])
        with patch("browser_helpers.json.dumps", side_effect=lambda value, *a, **kw:
                   original(body if value == {"code": 0, "SYNTHETIC": True} else value, *a, **kw)):
            return await super().emit_request(method, url, raw, headers, kind)


class FakeBackend:
    def __init__(self, cap, root, initial, fact, *, fail=None):
        self.cap, self.asset_root, self.fail = cap, root, fail
        self.profile_path = root/"synthetic-profile"
        self.profile_path.mkdir(parents=True)
        self.fake = FakeIO(initial, fact, actor=cap.data["executor"], session_id=cap.data["run_id"])
        self.log = []
    def profile(self):
        self.log.append("profile")
        if self.fail == "profile": raise ValueError(SENTINEL)
        return self.profile_path
    def occupancy(self, *args): self.log.append("occupancy")
    async def open(self, profile, binding):
        self.log.append("install-before-online-bootstrap")
        self.context = Context()
        self.page = DataPage(self.context, self.fake)
        self.guard = make_first_save_guard(BaseGuard, self.context, self.page, Policy(), binding)
        self.guard.owner_authority_hash = self.cap.raw_hash
        self.page.guard = self.guard
        return self.page, self.context, self.guard
    async def close(self):
        self.log.append("close")
        if self.fail == "close": raise ValueError(SENTINEL)
        return {"released": True, "context_closed": True, "runtime_stopped": True, "callback_pending": 0}
    def author_inputs(self):
        return self.cap.author_release["frozen_author_inputs"]


class OwnerTests(unittest.TestCase):
    setUp = Tests.setUp
    seal = Tests.seal
    def test_owner_calls_actual_async_adapter_and_current_page_io_then_outer_close(self):
        self.seal()
        backend = FakeBackend(self.cap, self.root, self.initial, self.fact)
        result = asyncio.run(owner.run_owned_worker(self.cap, backend))
        self.assertEqual(result["status"], "AUTHOR_EVIDENCE_PENDING_REVIEW", result)
        self.assertEqual(backend.log[-1], "close")
        self.assertEqual(sum(c["method"] == "POST" for c in backend.fake.calls), 1)
        self.assertTrue(result["release"]["released"])
        self.assertNotIn(SENTINEL, json.dumps(result))

    def test_unbound_schema_four_actual_io_reads_zero_writes(self):
        self.seal(unbound=True)
        backend = FakeBackend(self.cap, self.root, self.initial, self.fact)
        result = asyncio.run(owner.run_owned_worker(self.cap, backend))
        self.assertEqual(result["status"], "PREWRITE_BLOCKED_NO_EFFECT", result)
        self.assertEqual(len(backend.page.calls), 4)
        self.assertTrue(all(method == "GET" for method, url in backend.page.calls))
        self.assertEqual(result["steps"]["adapter"], "NOT_RUN")
        self.assertNotIn(SENTINEL, json.dumps(result))

    def test_profile_error_and_close_error_preserved_without_message_leak(self):
        self.seal()
        backend = FakeBackend(self.cap, self.root, self.initial, self.fact, fail="profile")
        result = asyncio.run(owner.run_owned_worker(self.cap, backend))
        self.assertEqual(result["status"], "ERROR_STOPPED_NO_RETRY")
        self.assertEqual(backend.log, ["profile", "close"])
        self.assertNotIn(SENTINEL, json.dumps(result))

    def test_close_failure_becomes_unproven_and_is_written(self):
        self.seal(unbound=True)
        backend = FakeBackend(self.cap, self.root, self.initial, self.fact, fail="close")
        result = asyncio.run(owner.run_owned_worker(self.cap, backend))
        self.assertEqual(result["status"], "OWNER_RELEASE_UNPROVEN")
        self.assertTrue((self.cap.output/"worker-result.json").exists())

    def test_concrete_windows_open_installs_new_guard_before_online_and_navigation(self):
        self.seal()
        log = []
        page = SimpleNamespace(url="about:blank", set_default_timeout=lambda value: None, on=lambda *a: None)
        async def goto(url, **kwargs): log.append("navigate"); page.url = url
        page.goto = goto
        context = SimpleNamespace(pages=[page], on=lambda *a: None)
        async def online(value):
            self.assertFalse(value)
            self.assertIn("guard-installed", log)
            log.append("online")
        context.set_offline = online
        async def launch(profile, **kwargs):
            self.assertTrue(kwargs["offline"])
            self.assertEqual(kwargs["service_workers"], "block")
            log.append("context-offline")
            return context
        runtime = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch))
        async def start(): log.append("runtime"); return runtime
        async def install(): log.append("guard-installed")
        guard = SimpleNamespace(install=install, auth=SimpleNamespace(arm_navigation=lambda target: None), response=lambda value: None)
        async def complete(*args): log.append("bootstrap")
        framework = SimpleNamespace(CurrentGuard=BaseGuard, complete_current_session=complete, admit_current_viewer=complete)
        backend = object.__new__(owner.WindowsBackend)
        backend.authority, backend.framework = self.cap, framework
        backend.runtime = backend.context = backend.guard = None
        module = SimpleNamespace(async_playwright=lambda: SimpleNamespace(start=start))
        with patch.dict(sys.modules, {"playwright": SimpleNamespace(), "playwright.async_api": module}), \
             patch("annotation.delivery.live_pilot.usense.make_first_save_guard", return_value=guard):
            asyncio.run(backend.open(self.root, owner.base_binding(self.cap)))
        self.assertEqual(log[:5], ["runtime", "context-offline", "guard-installed", "online", "navigate"])

    def test_aggregate_compiler_is_exactly17_or20_and_refuses_old32(self):
        self.seal()
        plan, profile = copy.deepcopy(self.cap.plan), copy.deepcopy(self.profile)
        profile["aggregate_readback"] = {"mode": "ALL_ZONES_AND_INFO", "rows_path": ["view", "wire_annotations"]}
        profile["limits"].update(upload=6, signature=1)
        for phase, count in plan["business_get_counts"].items():
            profile["reads"][phase] = {"requests": [{}]*count}
        self.assertEqual(sum(auth.validate_bound_counts(plan, profile).values()), 17)
        plan["readback_strategy"] = "AUTHORITATIVE_AGGREGATE_PLUS_INFO"
        plan["business_get_counts"].update(get=4, refresh=4, reopen=5)
        profile["aggregate_readback"]["mode"] = "ALL_ZONES_INFO_GET"
        self.assertEqual(sum(auth.validate_bound_counts(plan, profile).values()), 20)
        profile["reads"]["get"]["requests"].extend([{}, {}])
        with self.assertRaises(PilotError): auth.validate_bound_counts(plan, profile)

    def test_same_reviewer_fresh_readonly_owner_reopens_without_any_post(self):
        self.seal()
        author = FakeBackend(self.cap, self.root, self.initial, self.fact)
        result = asyncio.run(owner.run_owned_worker(self.cap, author))
        evidence = ControlledVault(self.cap).load(result["adapter"]["private_author_evidence_ref"])
        review_root = self.root/"independent"
        review_root.mkdir()
        cap, data = authority_fixture(review_root, self.request, self.profile, author_release=evidence)
        reader = FakeBackend(cap, self.root/"review-assets", author.fake.state, self.fact)
        reader.fake.payload = copy.deepcopy(author.fake.payload)
        # The identical hash-bound synthetic asset set is shared read-only.
        reader.asset_root = self.root
        reopened = asyncio.run(owner.run_owned_worker(cap, reader))
        self.assertEqual(reopened["status"], "INDEPENDENT_EVIDENCE_PENDING_FORMAL_REVIEW", reopened)
        self.assertTrue(all(call["method"] == "GET" for call in reader.fake.calls))
        self.assertEqual(reopened["adapter"]["independent_acceptance"], "PENDING")
        self.assertIn("observation_ref", reopened["adapter"])
        self.assertNotIn("observation", reopened["adapter"])
