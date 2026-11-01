"""New A27 synthetic checks only. Never start a browser, network or real ledger."""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from annotation.runtime.usense_live import update, postsave, release, config
from annotation.runtime.usense_live.core import sha, BindingError, profile_identity, write_new, canonical
from annotation.runtime.usense_live.revision import verify_previous_acceptance
import run_usense_reviewed_batch as batch_entry
import run_usense_postsave_readback as recovery


def fixture_module(name):
    spec = importlib.util.spec_from_file_location("a27_fixture_" + name, ROOT / "tests" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


basic = fixture_module("test_usense_live_update")
batch_fixture = fixture_module("test_a25_batch")
writer_fixture = fixture_module("test_usense_live_writer_review")
order_fixture = fixture_module("test_a25_created_zone_reconciliation")


def raw(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def flat(snapshot, q=3):
    return {"directory": snapshot["directory"], "frames": snapshot["frames"],
            f"q{q}_annotations": snapshot["annotations"], f"q{q}_info": snapshot["info"],
            **{f"q{q}_{z}": v for z, v in snapshot["zones"].items()},
            "source": basic.response({"synthetic": True}), "page_3": basic.response({"page": 3}),
            "page_4": basic.response({"page": 4})}


def event_bytes(names, writer):
    events = [{"layer": layer, "method": "GET", "allowed": True,
               "url_sha256": sha((postsave.ORIGIN + path).encode())}
              for layer in ("context", "native") for path in names.values()]
    for layer in (("context", "native") if writer else ("native",)):
        events.append({"layer": layer, "method": "GET", "allowed": True, "url_sha256": sha(postsave.TARGET.encode())})
    if writer:
        for layer in ("context", "native"):
            events.append({"layer": layer, "method": "POST", "allowed": True,
                "url_sha256": sha((postsave.ORIGIN + "/qieti/api/annotate_pic/commit_unified_submit").encode())})
    return raw(events)


def process_bytes(result, start, end, pid, code):
    stdout, stderr = raw(result) + b"\n", b""
    process = raw({"pid": pid, "timed_out": False, "exit_code": code, "started_at": start, "finished_at": end,
                   "result": result, "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr)})
    return process, stdout, stderr


class SyntheticBundle:
    def __init__(self, root):
        self.root = root
        self.profile = root / "synthetic-profile"
        self.profile.mkdir()
        self.ledger = root / "usense-existing-ledger"
        self.ledger.mkdir()
        before, target = basic.fixture(3)
        self.plan = update.make_plan(before, target, {"question": basic.review("updated $x^2$ <img src='synthetic-image-3'>")})
        t = datetime.now(timezone.utc) - timedelta(minutes=5)
        at = lambda n: (t + timedelta(seconds=n)).isoformat()
        cfgpath = root / "writer-config.json"
        old_output = root / "old-output"
        old_output.mkdir()
        config.configure(profile=self.profile, output_root=old_output, config_path=cfgpath, coordinator="synthetic",
            executor="synthetic-executor", reviewer="synthetic-reviewer", authorization_reference="synthetic",
            tls_approval_reference="synthetic", orders=[3], pages=[3, 4], source=True, now=t)
        cfg = update.loads(cfgpath.read_bytes())
        self.names = config.capture_endpoints(SimpleNamespace(data=cfg))
        receipt = {"code": 0, "message": "success", "data": {"inserted": False, "question_order": 3,
            "inserted_question_node": None, "success": True, "append_at_global_end": False}}
        plan_raw = raw(self.plan)
        w = {"run_id": cfg["run_id"], "plan_sha256": self.plan["plan_sha256"], "plan_file_sha256": sha(plan_raw),
            "target": target, "ledger_key": self.plan["ledger_key"], "intent_key": self.plan["ledger_key"],
            "status": "RELEASE_UNPROVEN_NO_RETRY", "business_status_before_release": "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK",
            "config_sha256": sha(cfgpath.read_bytes()), "native_body_sha256": "a" * 64, "send_intent_at": at(4),
            "finished_at": at(9), "receipt_sha256": sha(raw(receipt)), "http_status": 200, "response_code": 0,
            "post_attempts": 1, "post_layers": {"context": 1, "native": 1},
            "release": {"context_closed": False, "runtime_stopped": False, "pending_callbacks": 0,
                "errors": [{"phase": "context_close", "type": "TimeoutError"}], "context_runtime_release_confirmed": False}}
        wp, stdout, stderr = process_bytes(w, at(1), at(10), 101, 2)
        intent = {k: w[k] for k in ("run_id", "target", "ledger_key", "plan_sha256", "native_body_sha256", "intent_key")}
        intent.update(state="INTENT_REQUIRES_INDEPENDENT_READBACK", automatic_retry_allowed=False,
                      previous_acceptance_sha256=None, intent_at=at(4))
        send = dict(w, status="SEND_INTENT_RECORDED")
        created = int(((t + timedelta(seconds=2)) - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10000000)
        holder = {"schema": "A25OwnedWindowsProcess/v1", "started_at": at(0), "process_finished_at": at(11),
            "finished_at": at(12), "errors": [], "job_active_processes_after": 0,
            "observed_processes": [{"pid": 101, "creation_filetime": created, "observed_at": at(3),
                "exit_code": 2, "exit_signaled": True, "handle_closed": True}]}
        holder.update({key: True for key in ("resumed", "job_assigned_before_resume", "launcher_exit_signaled",
                "thread_handle_closed", "process_handle_closed", "job_handle_closed", "owned_os_release_confirmed")})
        self.raw = {"plan": plan_raw, "execution": raw(w), "writer_process": wp, "writer_stdout": stdout,
            "writer_stderr": stderr, "writer_config": cfgpath.read_bytes(), "receipt": raw(receipt),
            "intent": raw(intent), "send_intent": raw(send), "holder": raw(holder),
            "writer_events": event_bytes(self.names, True), "before": {k: raw(v) for k, v in flat(before).items()}}
        self.intent = self.ledger / (self.plan["ledger_key"] + ".json")
        self.intent.write_bytes(self.raw["intent"])

    def reader(self, cfgraw=None):
        cfg = update.loads(cfgraw or self.raw["writer_config"])
        if cfgraw is None:
            cfg["run_id"] = "usense-readonly-synthetic-new-reader"
        cfgraw = cfgraw or raw(cfg)
        t = datetime.now(timezone.utc)
        at = lambda n: (t + timedelta(seconds=n)).isoformat()
        captures = {k: raw(v) for k, v in flat(self.plan["expected"]).items()}
        r = {"run_id": cfg["run_id"], "status": "NATIVE_GETS_CAPTURED", "config_sha256": sha(cfgraw),
            "save_attempts": 0, "finished_at": at(2),
            "release": {"context_closed": True, "runtime_stopped": True, "pending_callbacks": 0,
                        "errors": [], "context_runtime_release_confirmed": True},
            "captures": {n: {"filename": n + ".json", "sha256": sha(v), "bytes": len(v), "status": 200,
                "request_counts": {"context": 1, "native": 1}, "observed_at": at(1)} for n, v in captures.items()}}
        process, stdout, stderr = process_bytes(r, at(0), at(3), 202, 0)
        return {"summary": raw(r), "config": cfgraw, "process": process, "stdout": stdout, "stderr": stderr,
                "captures": captures, "events": event_bytes(self.names, False)}

    def request(self):
        saved = self.root / "frozen"
        saved.mkdir()
        def ref(name, value):
            path = saved / name
            path.write_bytes(value)
            return {"path": str(path), "sha256": sha(value)}
        refs = {key: ({n: ref("before-" + n, v) for n, v in value.items()} if key == "before" else ref(key, value))
                for key, value in self.raw.items()}
        request = {"schema": "UsensePostsaveReadbackRequest/v1", "writer_evidence": refs,
                   "output_root": str(self.root / "recovery-out"), "ledger_snapshot": recovery.ledger_snapshot(self.ledger)}
        self.request_path, self.authority_path = self.root / "request.json", self.root / "authority.json"
        self.request_path.write_bytes(raw(request))
        now = datetime.now(timezone.utc)
        authority = {"schema": "UsensePostsaveReadbackAuthority/v1", "operation": "READONLY_POSTSAVE_RECOVERY",
            "status": "AUTHORIZED", "authority_id": "synthetic-only-one-authority", "request_sha256": sha(raw(request)),
            "not_before": (now - timedelta(seconds=1)).isoformat(), "expires_at": (now + timedelta(seconds=120)).isoformat(),
            "limits": {"readers": 1, "contexts": 1, "posts": 0, "login": 0, "business_gets": 12, "retries": 0}}
        self.authority_path.write_bytes(raw(authority))
        return (self.request_path, sha(raw(request)), self.authority_path, sha(raw(authority)))

    def child(self, args, record):
        self.calls.append(args[0])
        cfgpath = Path(args[args.index("--config") + 1])
        if args[0] == "configure":
            result = config.configure(profile=self.profile, output_root=Path(record).parent, config_path=cfgpath,
                coordinator="synthetic", executor="synthetic-executor", reviewer="synthetic-reviewer", authorization_reference=str(self.authority_path),
                tls_approval_reference=str(self.authority_path), orders=[3], pages=[3, 4], source=True, seconds=60)
            if self.after_configure:
                self.after_configure()
            return {"exit_code": 0, "result": result}
        assert args[0] == "capture", "NO WRITER OR OTHER COMMAND PERMITTED"
        if self.fail_reader:
            raise BindingError("SYNTHETIC_READER_FAILED")
        evidence = self.reader(cfgpath.read_bytes())
        summary = update.loads(evidence["summary"])
        rd = Path(record).parent / summary["run_id"]
        rd.mkdir()
        for name, value in evidence["captures"].items():
            (rd / (name + ".json")).write_bytes(value)
        (rd / "capture-summary.json").write_bytes(evidence["summary"])
        (rd / "network-events.json").write_bytes(evidence["events"])
        Path(record).write_bytes(evidence["process"])
        Path(record).with_suffix(".stdout").write_bytes(evidence["stdout"])
        Path(record).with_suffix(".stderr").write_bytes(evidence["stderr"])
        if getattr(self, "after_capture", None): self.after_capture()
        return update.loads(evidence["process"])


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("A27_OUTPUT"))
        self.root = Path(self.tmp.name)
        self.bundle = SyntheticBundle(self.root)
        self.bundle.calls, self.bundle.after_configure, self.bundle.fail_reader = [], None, False

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_recovery_keeps_original_failed_release_and_cannot_be_revision(self):
        old = postsave.verify_writer(self.bundle.raw)
        result = postsave.verify_reader(old, self.bundle.reader())
        self.assertEqual(result["status"], "READBACK_MATCHED_AFTER_OS_RELEASE")
        self.assertFalse(result["original_framework_release"]["context_runtime_release_confirmed"])
        self.assertFalse(result["revision_predecessor_eligible"])
        self.assertFalse(result["new_standard_accepted_marker"])

    def test_request_builder_uses_stopped_batch_files_and_grants_no_authority(self):
        bundle = self.bundle
        old = postsave.verify_writer(bundle.raw)
        qdir = self.root / "old-output" / "target-synthetic"
        wd = qdir.parent / old["writer"]["run_id"]
        qdir.mkdir(); wd.mkdir()
        for key, name in (("plan", "plan.json"), ("writer_config", "writer-config.json"),
                ("writer_process", "writer-process-result.json"), ("writer_stdout", "writer-process-result.stdout"),
                ("writer_stderr", "writer-process-result.stderr")):
            (qdir/name).write_bytes(bundle.raw[key])
        for key, name in (("plan", "plan.json"), ("execution", "execution-result.json"),
                ("receipt", "native-receipt.json"), ("send_intent", "send-intent.json"), ("writer_events", "network-events.json")):
            (wd/name).write_bytes(bundle.raw[key])
        for name, value in bundle.raw["before"].items(): (wd/("before-"+name+".json")).write_bytes(value)
        holder = self.root/"holder.json"; holder.write_bytes(bundle.raw["holder"])
        snapshot = recovery.ledger_snapshot(bundle.ledger)
        result = recovery.prepare_request(qdir, holder, sha(holder.read_bytes()), self.root/"new-output", self.root/"new-request.json")
        self.assertEqual(result["status"], "PREPARED_NO_AUTHORITY_NO_DISPATCH")
        request = update.loads((self.root/"new-request.json").read_bytes())
        self.assertEqual(postsave.verify_writer(recovery.bound_inputs(request))["writer"]["run_id"], old["writer"]["run_id"])
        self.assertEqual(recovery.ledger_snapshot(bundle.ledger), snapshot)
        self.assertFalse((self.root/"new-output").exists())
        self.assertEqual(bundle.calls, [])

    def test_writer_receipt_intent_guard_and_exact_os_identity_counterexamples(self):
        mutations = [
            ("receipt", lambda x: x["data"].update(success=1)),
            ("intent", lambda x: x.update(native_body_sha256="b" * 64)),
            ("send_intent", lambda x: x.update(plan_sha256="c" * 64)),
            ("writer_events", lambda x: x.append(copy.deepcopy(x[-1]))),
            ("writer_events", lambda x: x[0].update(allowed=False)),
            ("holder", lambda x: x.update(job_active_processes_after=True)),
            ("holder", lambda x: x.update(job_active_processes_after=1)),
            ("holder", lambda x: x.update(errors=["UNKNOWN"])),
            ("holder", lambda x: x.update(job_assigned_before_resume=False)),
            ("holder", lambda x: x["observed_processes"][0].update(pid=303)),
            ("holder", lambda x: x["observed_processes"][0].update(exit_signaled=False)),
            ("holder", lambda x: x["observed_processes"][0].update(handle_closed=False)),
            ("holder", lambda x: x["observed_processes"][0].update(creation_filetime=1)),
            ("holder", lambda x: x["observed_processes"].append(copy.deepcopy(x["observed_processes"][0]))),
        ]
        for key, mutation in mutations:
            with self.subTest(key=key, mutation=mutations.index((key, mutation))):
                values = copy.deepcopy(self.bundle.raw)
                item = update.loads(values[key]); mutation(item); values[key] = raw(item)
                with self.assertRaises(ValueError): postsave.verify_writer(values)

    def test_unknown_business_cannot_use_receipt_or_release_booleans(self):
        for status, error in (("UNKNOWN_DO_NOT_RETRY", False), ("RELEASE_UNPROVEN_NO_RETRY", True)):
            values = copy.deepcopy(self.bundle.raw)
            w = update.loads(values["execution"])
            w["business_status_before_release"] = status
            if error: w["error_code"] = "POST_BARRIERS_NOT_CONFIRMED"
            values["execution"] = raw(w)
            p = update.loads(values["writer_process"])
            values["writer_process"], values["writer_stdout"], values["writer_stderr"] = process_bytes(
                w, p["started_at"], p["finished_at"], p["pid"], p["exit_code"])
            with self.assertRaisesRegex(ValueError, "RECOVERY_UNKNOWN_BUSINESS_NO_RETRY"):
                postsave.verify_writer(values)

    def test_reader_raw_full_content_and_guard_counterexamples(self):
        old = postsave.verify_writer(self.bundle.raw)
        mutations = [
            ("q3_question", lambda x: x["data"].update(ocr_result="changed")),
            ("q3_info", lambda x: x["data"]["unknown_info"].update(type_sensitive=[1, True, 1.0])),
            ("frames", lambda x: x["data"].reverse()),
            ("source", lambda x: x["data"].update(extra=True)),
            ("page_3", lambda x: x["data"].update(page=4)),
        ]
        for name, mutation in mutations:
            with self.subTest(name=name):
                values = self.bundle.reader()
                content = update.loads(values["captures"][name]); mutation(content)
                values["captures"][name] = raw(content)
                # Rebind raw metadata so this reaches full-state comparison.
                summary = update.loads(values["summary"])
                summary["captures"][name].update(bytes=len(raw(content)), sha256=sha(raw(content)))
                self.rebind_reader(values, summary)
                with self.assertRaisesRegex(ValueError, "RECOVERY_FULL_READBACK_MISMATCH"):
                    postsave.verify_reader(old, values)
        values = self.bundle.reader()
        events = update.loads(values["events"]); events.append(events[-1]); values["events"] = raw(events)
        with self.assertRaisesRegex(ValueError, "RECOVERY_NETWORK_COUNTS"):
            postsave.verify_reader(old, values)

    def rebind_reader(self, values, summary, **process_changes):
        p = update.loads(values["process"]); p.update(process_changes)
        values["summary"] = raw(summary)
        values["process"], values["stdout"], values["stderr"] = process_bytes(
            summary, p["started_at"], p["finished_at"], p["pid"], p["exit_code"])

    def test_reader_independence_release_time_and_typed_capture_fields(self):
        old = postsave.verify_writer(self.bundle.raw)
        for change in (lambda s: s.update(save_attempts=False),
                       lambda s: s["release"].update(context_closed=False),
                       lambda s: s["captures"]["directory"].update(status=True),
                       lambda s: s["captures"]["directory"].update(observed_at=old["holder"]["started_at"]),
                       lambda s: s["captures"].pop("source")):
            values = self.bundle.reader(); summary = update.loads(values["summary"]); change(summary)
            self.rebind_reader(values, summary)
            with self.assertRaises(ValueError): postsave.verify_reader(old, values)
        for changes in ({"pid": 101}, {"started_at": old["holder"]["finished_at"]}):
            values = self.bundle.reader()
            self.rebind_reader(values, update.loads(values["summary"]), **changes)
            with self.assertRaises(ValueError): postsave.verify_reader(old, values)

    def test_real_recovery_entry_dispatches_configure_capture_only_once_and_keeps_ledger(self):
        args = self.bundle.request()
        before = recovery.ledger_snapshot(self.bundle.ledger)
        result = recovery.execute(*args, run_child=self.bundle.child, observe=lambda p: {"synthetic": True})
        self.assertEqual(result["status"], "READBACK_MATCHED_AFTER_OS_RELEASE", result)
        self.assertEqual(self.bundle.calls, ["configure", "capture"])
        self.assertEqual(recovery.ledger_snapshot(self.bundle.ledger), before)
        self.assertEqual(len(list(self.root.glob("*.spent.json"))), 1)
        with self.assertRaises(ValueError):
            recovery.execute(*args, run_child=self.bundle.child, observe=lambda p: {"synthetic": True})
        self.assertEqual(self.bundle.calls, ["configure", "capture"])

    def test_configuration_time_input_change_stops_before_reader(self):
        args = self.bundle.request()
        request = update.loads(self.bundle.request_path.read_bytes())
        target = Path(request["writer_evidence"]["receipt"]["path"])
        self.bundle.after_configure = lambda: target.write_bytes(target.read_bytes() + b" ")
        result = recovery.execute(*args, run_child=self.bundle.child, observe=lambda p: {})
        self.assertEqual(result["status"], "STOPPED_NO_RETRY")
        self.assertEqual(result["error_code"], "RECOVERY_FILE_CHANGED")
        self.assertEqual(self.bundle.calls, ["configure"])

    def test_input_change_during_read_cannot_be_promoted(self):
        args = self.bundle.request()
        request = update.loads(self.bundle.request_path.read_bytes())
        target = Path(request["writer_evidence"]["holder"]["path"])
        self.bundle.after_capture = lambda: target.write_bytes(target.read_bytes() + b" ")
        result = recovery.execute(*args, run_child=self.bundle.child, observe=lambda p: {})
        self.assertEqual(result["status"], "STOPPED_NO_RETRY")
        self.assertEqual(result["error_code"], "RECOVERY_FILE_CHANGED")
        self.assertFalse((self.root/"recovery-out"/"readonly-recovery.json").exists())
        self.assertEqual(self.bundle.calls, ["configure", "capture"])

    def test_reader_failure_stops_and_spends_without_retry(self):
        args = self.bundle.request(); self.bundle.fail_reader = True
        result = recovery.execute(*args, run_child=self.bundle.child, observe=lambda p: {})
        self.assertEqual(result["status"], "STOPPED_NO_RETRY")
        self.assertEqual(result["error_code"], "SYNTHETIC_READER_FAILED")
        self.assertEqual(self.bundle.calls, ["configure", "capture"])
        self.assertEqual(list(self.bundle.ledger.glob("*.accepted.json")), [])

    def test_unauthorized_or_profile_occupied_stops_before_configure(self):
        args = self.bundle.request()
        observer = Mock(side_effect=BindingError("RECOVERY_PROFILE_IN_USE"))
        with self.assertRaisesRegex(ValueError, "RECOVERY_PROFILE_IN_USE"):
            recovery.execute(*args, run_child=self.bundle.child, observe=observer)
        self.assertEqual(self.bundle.calls, [])
        authority = update.loads(self.bundle.authority_path.read_bytes()); authority["limits"]["posts"] = 1
        self.bundle.authority_path.write_bytes(raw(authority))
        with self.assertRaisesRegex(ValueError, "RECOVERY_EXACT_NEW_AUTHORITY_REQUIRED"):
            recovery.execute(*args[:3], sha(raw(authority)), run_child=self.bundle.child, observe=lambda p: {})
        self.assertEqual(self.bundle.calls, [])

    def test_profile_observation_unknown_and_occupied_reject_without_browser(self):
        for row in ({"ProcessId": 1, "CreationDate": "synthetic", "CommandLine": None},
                    {"ProcessId": 1, "CreationDate": "synthetic", "CommandLine": 'edge --user-data-dir="' + str(self.bundle.profile) + '"'}):
            run = Mock(return_value=SimpleNamespace(returncode=0, stdout=raw([row])))
            with self.assertRaises(ValueError): recovery.exclusive_profile(self.bundle.profile, run=run)
        run = Mock(return_value=SimpleNamespace(returncode=0, stdout=b"[]"))
        self.assertEqual(recovery.exclusive_profile(self.bundle.profile, run=run)["matching_profile_processes"], 0)


class CloseTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_resistant_close_and_stop_are_bounded_separate_failures(self):
        finish = asyncio.Event(); tasks = []
        async def stubborn():
            tasks.append(asyncio.current_task())
            try: await finish.wait()
            except asyncio.CancelledError: await finish.wait()
        runtime = SimpleNamespace(close=stubborn, stop=stubborn)
        started = time.monotonic()
        result = await release.close_framework(runtime, runtime, set(), close_seconds=.02, stop_seconds=.02)
        self.assertLess(time.monotonic() - started, .5)
        self.assertEqual(result["errors"], [{"phase": "context_close", "type": "TimeoutError"},
                                            {"phase": "runtime_stop", "type": "TimeoutError"}])
        self.assertFalse(result["context_runtime_release_confirmed"])
        self.assertEqual(result["os_process_release"], "REQUIRES_OUTER_HOLDER")
        finish.set(); await asyncio.gather(*tasks)

    async def test_callback_timeout_cannot_be_hidden_by_successful_framework_close(self):
        finish = asyncio.Event()
        async def callback():
            try: await finish.wait()
            except asyncio.CancelledError: await finish.wait()
        async def done(): pass
        task = asyncio.create_task(callback()); await asyncio.sleep(0)
        result = await release.close_framework(SimpleNamespace(close=done), SimpleNamespace(stop=done), {task}, callback_seconds=.02)
        self.assertTrue(result["context_closed"] and result["runtime_stopped"])
        self.assertFalse(result["context_runtime_release_confirmed"])
        self.assertEqual(result["pending_callbacks"], 1)
        finish.set(); await task

    async def test_clean_framework_release_records_os_as_separate(self):
        async def done(): pass
        result = await release.close_framework(SimpleNamespace(close=done), SimpleNamespace(stop=done), set())
        self.assertTrue(result["context_runtime_release_confirmed"])
        self.assertEqual(result["unfinished_cleanup_tasks"], 0)
        self.assertEqual(result["os_process_release"], "REQUIRES_OUTER_HOLDER")


class IntegrationTests(unittest.TestCase):
    def test_writer_records_exact_receipt_before_failed_release_and_never_resends(self):
        fixture = writer_fixture.WriterIndependentTests()
        fixture.setUp()
        try:
            result, browser = fixture.run_fake(release_error=True)
            self.assertEqual(result["status"], "RELEASE_UNPROVEN_NO_RETRY")
            self.assertEqual(result["business_status_before_release"], "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK")
            self.assertTrue(result["receipt_exact_success"])
            self.assertFalse(result["save_success"])
            self.assertEqual(browser.send_calls, 1)
            with self.assertRaisesRegex(ValueError, "EXISTING_INTENT_READBACK_REQUIRED_NO_RETRY"):
                fixture.run_fake()
        finally: fixture.tearDown()

    def test_standalone_loop_does_not_join_stubborn_task_after_recording_release(self):
        code = '''import asyncio,sys
sys.path.insert(0,sys.argv[1])
from annotation.runtime.usense_live.release import close_framework,run_owned_writer
class R:
 async def close(self):
  try: await asyncio.Future()
  except asyncio.CancelledError: await asyncio.Future()
 async def stop(self): pass
async def main():
 r=R()
 result=await close_framework(r,r,set(),close_seconds=.02)
 print(result['context_runtime_release_confirmed'],flush=True)
run_owned_writer(main())
'''
        p = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(ROOT / "src")], capture_output=True, timeout=3)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), b"False")

    def test_normal_comparison_accepts_only_new_question_answer_order_and_preserves_strict(self):
        plan, after = order_fixture.A25CreatedZoneReconciliationTests().example()
        hashes = update.digest(plan), update.digest(after)
        result = update.compare_batch_readback(plan, after)
        self.assertTrue(result["match"])
        self.assertFalse(result["reconciliation"]["strict_comparison"]["match"])
        self.assertEqual((update.digest(plan), update.digest(after)), hashes)
        for mutate in (lambda x: x["zones"]["question"]["data"].update(success=1),
                       lambda x: x["zones"]["question"]["data"]["rect_ids"].reverse(),
                       lambda x: x["zones"]["answer"]["data"].update(extra=None),
                       lambda x: x["info"]["data"].update(tihao="changed")):
            changed = copy.deepcopy(after); mutate(changed)
            self.assertFalse(update.compare_batch_readback(plan, changed)["match"])

    def test_normal_comparison_does_not_expand_rule_to_other_created_zone(self):
        before, target = basic.fixture(3)
        before["zones"]["analysis"] = basic.response(copy.deepcopy(update.ABSENT))
        plan = update.make_plan(before, target, {"analysis": basic.review("new analysis")})
        after = copy.deepcopy(plan["expected"]); data = after["zones"]["analysis"]["data"]
        after["zones"]["analysis"]["data"] = {key: data[key] for key in ("success", "ocr_result", "rect_ids")}
        self.assertTrue(update.reconcile_first_created_zone_key_order(plan, after)["match"])
        self.assertFalse(update.compare_batch_readback(plan, after)["match"])

    def test_normal_batch_continues_serially_but_limited_result_is_not_standard_predecessor(self):
        temporary = Path(os.environ.get("A27_OUTPUT", tempfile.gettempdir()))
        (temporary / "tests").mkdir(exist_ok=True)
        fixture = batch_fixture.A25BatchTests()
        with patch.object(batch_fixture, "ROOT", temporary): fixture.setUp()
        try:
            fixture.manifest["targets"] = fixture.manifest["targets"][:2]
            fixture.native["q18_question"] = basic.response(copy.deepcopy(update.ABSENT))
            fixture.save_baseline()
            prepared = fixture.prepare(); out = fixture.root / "batch"; out.mkdir()
            calls, configured = [], {}
            t = datetime.now(timezone.utc)
            def child(args, record):
                nonlocal t
                calls.append(args[0]); start = t.isoformat(); t += timedelta(seconds=1); end = t.isoformat()
                if args[0] == "configure":
                    configured[str(args[args.index("--config")+1])] = args[args.index("--orders")+1]
                    return {"exit_code": 0, "result": {"sha256": "a"*64}}
                q = configured[str(args[args.index("--config")+1])]
                plan = next(i["plan"] for i in prepared["targets"] if i["target"]["question_order"] == q)
                run = "synthetic-" + str(q) + args[0].strip("-")
                if args[0] == "--writer":
                    (fixture.ledger / (plan["ledger_key"]+".json")).write_bytes(b"{}")
                    result = {"status": "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK", "run_id": run,
                        "release": {"context_runtime_release_confirmed": True}, "post_attempts": 1, "intent_key": plan["ledger_key"]}
                else:
                    rd = out/run; rd.mkdir(); after = copy.deepcopy(plan["expected"])
                    if q == 18:
                        data = after["zones"]["question"]["data"]
                        after["zones"]["question"]["data"] = {k:data[k] for k in ("success","ocr_result","rect_ids")}
                    values = {"directory": after["directory"], "frames": after["frames"],
                        f"q{q}_annotations":after["annotations"], f"q{q}_info":after["info"],
                        **{f"q{q}_{k}":v for k,v in after["zones"].items()},
                        **{k:fixture.native[k] for k in ("source","page_12","page_173")}}
                    for name,value in values.items(): (rd/(name+".json")).write_bytes(raw(value))
                    result = {"status":"NATIVE_GETS_CAPTURED","run_id":run,"save_attempts":0,
                        "release":{"context_runtime_release_confirmed":True},"captures":{k:{"observed_at":end} for k in values}}
                t += timedelta(seconds=1)
                return {"exit_code":0,"result":result,"pid":len(calls),"started_at":start,"finished_at":end}
            result = batch_entry.execute(prepared,out,fixture.baseline,fixture.profile,"synthetic","synthetic",child)
            self.assertEqual(result["status"],"ALL_ACCEPTED",result)
            self.assertEqual(calls,["configure","--writer","configure","capture"]*2)
            self.assertEqual([r["status"] for r in result["results"]],["ACCEPTED_CREATED_ZONE_ORDER","ACCEPTED"])
            self.assertEqual(len(list(fixture.ledger.glob("*.accepted.json"))),1)
            acceptance = prepared["targets"][0]["qout"] / "acceptance.json"
            with self.assertRaisesRegex(ValueError,"PREVIOUS_ACCEPTANCE_NOT_SUCCESS"):
                verify_previous_acceptance(acceptance,prepared["targets"][0]["plan"],{},fixture.ledger)
        finally: fixture.tearDown()


if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=True)
