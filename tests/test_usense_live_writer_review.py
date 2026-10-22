"""Independent synthetic-only writer tests. No browser, account or network use.

The fake browser records one SEND invocation and exercises the real writer's
intent, native snapshot, receipt and release code. It is not real-platform proof.
"""
import asyncio
import base64
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


def load_writer():
    try:
        from annotation.runtime.usense_live import writer
        return writer
    except ModuleNotFoundError:
        stages = Path(__file__).resolve().parents[2]
        package = types.ModuleType("independent_writer_review")
        package.__path__ = [str(stages / stage / "src/annotation/runtime/usense_live")
                            for stage in ("writer-stage", "runtime-stage", "update-stage")]
        sys.modules[package.__name__] = package
        import importlib
        return importlib.import_module(package.__name__ + ".writer")


writer = load_writer()
update = sys.modules[writer.__package__ + ".update"]


def response(data):
    return {"code": 0, "message": "success", "data": data}


def fixture():
    target = {"book_id": "46007447", "lesson_directory_id": "synthetic-lesson",
              "node_id": "synthetic-node-2", "info_id": "synthetic-info-2", "question_order": 2}
    nodes = [{"id": f"synthetic-node-{i}", "label": str(i), "isQuestion": True,
              "order_in_level": str(i), "unknown": {"preserve": False}} for i in (1, 2, 3)]
    frames = [{"type": zone, "rect_id": f"synthetic-{i}-{zone}", "file_id": "46007447",
               "directory_id": "synthetic-lesson", "belong_to_level": "question_level",
               "order_in_level": str(i), "image_order_in_annotation_zone": 0,
               "rect_bbox": "1,2,3,4", "page_index": 10, "image_path": "synthetic-source",
               "unknown": {"types": [False, 1, 1.0]}}
              for i in (1, 2, 3) for zone in ("question", "choice", "answer")]
    zones = {zone: response(copy.deepcopy(update.ABSENT)) for zone in update.ZONES}
    for zone in ("question", "answer"):
        zones[zone] = response({"rect_ids": [f"synthetic-2-{zone}"], "ocr_result": "synthetic old " + zone,
                                "success": True, "unknown": {"preserve": None}})
    snapshot = {"directory": response({"directory_data": [{"id": "synthetic-lesson", "children": nodes}]}),
                "frames": response(frames),
                "annotations": response([copy.deepcopy(f) for f in frames if f["order_in_level"] == "2"]),
                "info": response({"id": target["info_id"], "file_id": "46007447", "order_in_level": "2",
                                  "tishi": "xuanze", "tilei": None, "tihao": None,
                                  "updated_at": "2026-10-15T00:00:00", "unknown": False}), "zones": zones}
    return snapshot, target


class FixtureFiles:
    def __init__(self, root, noop=False):
        self.root = root
        self.baseline = root / "baseline"
        self.ledger = root / "usense-existing-ledger"
        self.baseline.mkdir()
        self.ledger.mkdir()
        self.source = root / "synthetic-source.txt"
        self.source.write_bytes(b"SYNTHETIC SOURCE BYTES; NOT A REAL SCAN")
        self.review = root / "synthetic-review.json"
        self.review.write_text('{"synthetic":true,"reviewed":true}', encoding="utf-8")
        before, target = fixture()
        text = before["zones"]["question"]["data"]["ocr_result"] if noop else "synthetic approved $a^2+b^2$"
        change = {"text": text, "source_ref": str(self.source), "source_sha256": writer.sha(self.source.read_bytes()),
                  "review_ref": str(self.review), "reviewed_text_sha256": update.text_digest(text)}
        self.plan = update.make_plan(before, target, {"question": change})
        self.native = {"directory": before["directory"], "frames": before["frames"],
                       "q2_annotations": before["annotations"], "q2_info": before["info"],
                       **{"q2_" + key: val for key, val in before["zones"].items()},
                       "page_10": response({"url": "synthetic-page", "unknown": [1, True]})}
        # Existing endpoint builder is exercised separately in the runtime tests.
        self.endpoints = {name: "/synthetic/" + name for name in self.native}
        for name, val in self.native.items():
            (self.baseline / (name + ".json")).write_text(json.dumps(val, ensure_ascii=False), encoding="utf-8")
        self.plan_path = root / "plan.json"
        self.plan_path.write_text(json.dumps(self.plan, ensure_ascii=False), encoding="utf-8")
        self.plan_sha = writer.sha(self.plan_path.read_bytes())
        self.claim = self.ledger / (self.plan["ledger_key"] + ".json")


class FakeBinding:
    def __init__(self, root):
        self.output = root / "synthetic-run"
        self.data = {"profile": {"directory": str(root.resolve() / "synthetic-profile")}}
        self.calls = 0
    def check(self, **kwargs):
        self.calls += 1
        return self


class FakeBrowser:
    def __init__(self, files, *, send_error=None, corrupt_receipt=False, fresh_change=None, release_error=False):
        self.files = files
        self.send_error = send_error
        self.corrupt_receipt = corrupt_receipt
        self.fresh_change = fresh_change
        self.release_error = release_error
        self.send_calls = self.prepare_calls = self.fetch_calls = 0
        self.policy = None
        self.body = None
        self.intent_observed_before_send = False
        self.closed = self.stopped = False
        self.pages = [self]
        self.chromium = self

    async def start(self): return self
    async def stop(self): self.stopped = True
    async def launch_persistent_context(self, *args, **kwargs): return self
    async def goto(self, *args, **kwargs): return None
    async def close(self):
        if self.release_error: raise RuntimeError("synthetic release failure")
        self.closed = True
    async def route(self, *args, **kwargs): return None
    async def route_web_socket(self, *args, **kwargs): return None
    async def new_cdp_session(self, *args, **kwargs): return self
    async def set_offline(self, *args, **kwargs): return None
    async def send(self, *args, **kwargs): return None
    def on(self, *args, **kwargs): return None

    async def evaluate(self, script, argument):
        if script == writer.FETCH:
            self.fetch_calls += 1
            for layer in ("context", "native"):
                assert self.policy.allow(layer, "GET", writer.ORIGIN + argument)
            name = next(name for name, path in self.files.endpoints.items() if path == argument)
            value = copy.deepcopy(self.files.native[name])
            if self.fresh_change:
                self.fresh_change(name, value)
            return self.encoded(value)
        if script == writer.PREPARE:
            self.prepare_calls += 1
            payload = copy.deepcopy(argument)
            payload["created_by"] = "synthetic-private-actor"
            self.body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            return {"sha256": writer.sha(self.body.encode()), "created_by_bound": True}
        if script == writer.SEND:
            self.send_calls += 1
            claim = json.loads(self.files.claim.read_bytes())
            self.intent_observed_before_send = (claim["ledger_key"] == self.files.plan["ledger_key"] and
                                               claim["automatic_retry_allowed"] is False and
                                               (self.files.root / "synthetic-run/send-intent.json").is_file())
            for layer in ("context", "native"):
                assert self.policy.allow(layer, "POST", writer.POST, self.body)
            if self.send_error: raise self.send_error
            receipt = {"code": 0, "message": "success", "data": {"inserted": False,
                       "question_order": 2, "inserted_question_node": None, "success": True,
                       "append_at_global_end": False}}
            if self.corrupt_receipt: receipt["data"]["inserted"] = True
            return self.encoded(receipt)
        raise AssertionError("Unexpected script")

    @staticmethod
    def encoded(value):
        return {"status": 200, "body_base64": base64.b64encode(json.dumps(value).encode()).decode()}


class WriterIndependentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.files = FixtureFiles(self.root)

    def tearDown(self): self.tmp.cleanup()

    def validate(self, *, ledger=None):
        return writer.validate_inputs(self.files.plan, self.files.baseline, self.files.endpoints,
                                      ledger or self.files.ledger, "synthetic-current-user-authorization")

    def assertBlocked(self, code, fn):
        with self.assertRaises(ValueError) as caught: fn()
        self.assertEqual(getattr(caught.exception, "code", None), code)

    def run_fake(self, *, ledger=None, **options):
        browser = FakeBrowser(self.files, **options)
        original = writer.ExactPolicy
        def policy_factory(binding, urls):
            browser.policy = original(binding, urls)
            return browser.policy
        api = types.ModuleType("playwright.async_api")
        api.async_playwright = lambda: browser
        with patch.dict(sys.modules, {"playwright.async_api": api}), \
             patch.object(writer, "load_binding", return_value=FakeBinding(self.root)), \
             patch.object(writer, "capture_endpoints", return_value=self.files.endpoints), \
             patch.object(writer, "tls_launch_arguments", return_value=[]), \
             patch.object(writer, "ExactPolicy", side_effect=policy_factory):
            result = asyncio.run(writer.execute(config_path="synthetic-config", config_sha256="a" * 64,
                plan_path=self.files.plan_path, plan_sha256=self.files.plan_sha,
                baseline=self.files.baseline, ledger_root=ledger or self.files.ledger,
                authorization_reference="synthetic-current-user-authorization"))
        return result, browser

    def test_source_exact_bytes_bound(self):
        self.validate()
        self.files.source.write_bytes(b"changed")
        self.assertBlocked("SOURCE_BYTES_CHANGED", self.validate)

    def test_missing_review_record_stops_before_browser(self):
        self.files.review.unlink()
        self.assertBlocked("REVIEW_RECORD_MISSING", self.validate)

    def test_full_baseline_unknown_field_change_rejected(self):
        value = copy.deepcopy(self.files.native["frames"])
        value["data"][0]["unknown"]["types"][0] = 0
        (self.files.baseline / "frames.json").write_text(json.dumps(value), encoding="utf-8")
        self.assertBlocked("BASELINE_PLAN_MISMATCH", self.validate)

    def test_old_stable_intent_stops_all_new_plans_at_same_ledger(self):
        self.files.claim.write_text('{"state":"UNKNOWN"}', encoding="utf-8")
        self.assertBlocked("EXISTING_INTENT_READBACK_REQUIRED_NO_RETRY", self.validate)

    def test_alternate_ledger_root_cannot_bypass_prior_intent(self):
        # Regression: execute now binds the canonical root to the hash-bound
        # dedicated profile parent before native validation or browser startup.
        self.files.claim.write_text('{"state":"UNKNOWN"}', encoding="utf-8")
        alternate = self.root / "different-empty-ledger"
        alternate.mkdir()
        self.assertBlocked("LEDGER_ROOT_MUST_BELONG_TO_BOUND_PROFILE", lambda: self.run_fake(ledger=alternate))

    def test_duplicate_exact_post_denied_on_both_layers(self):
        for layer in ("context", "native"):
            policy = writer.ExactPolicy(FakeBinding(self.root), [])
            policy.body_sha = writer.sha(b"exact synthetic body")
            policy.armed = True
            self.assertTrue(policy.allow(layer, "POST", writer.POST, "exact synthetic body"))
            self.assertFalse(policy.allow(layer, "POST", writer.POST, "exact synthetic body"))
            self.assertTrue(policy.blocked)

    def test_post_rejects_unarmed_changed_body_or_redirect(self):
        for armed, body, redirect in [(False, "exact", False), (True, "changed", False), (True, "exact", True)]:
            policy = writer.ExactPolicy(FakeBinding(self.root), [])
            policy.body_sha = writer.sha(b"exact")
            policy.armed = armed
            self.assertFalse(policy.allow("native", "POST", writer.POST, body, redirect))

    def test_success_is_one_send_after_durable_intent_and_still_pending_readback(self):
        result, browser = self.run_fake()
        self.assertEqual(result["status"], "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK")
        self.assertEqual(browser.send_calls, 1)
        self.assertTrue(browser.intent_observed_before_send)
        self.assertEqual(result["post_layers"], {"context": 1, "native": 1})
        self.assertFalse(result["save_success"])
        self.assertEqual(result["independent_readback"], "PENDING")
        self.assertTrue(result["release"]["context_runtime_release_confirmed"])
        self.assertBlocked("EXISTING_INTENT_READBACK_REQUIRED_NO_RETRY", self.validate)

    def test_send_timeout_is_unknown_without_retry(self):
        result, browser = self.run_fake(send_error=TimeoutError("synthetic response lost"))
        self.assertEqual(result["status"], "UNKNOWN_DO_NOT_RETRY")
        self.assertEqual(browser.send_calls, 1)
        self.assertTrue(self.files.claim.exists())
        self.assertBlocked("EXISTING_INTENT_READBACK_REQUIRED_NO_RETRY", self.validate)

    def test_bad_receipt_is_unknown_not_success(self):
        result, browser = self.run_fake(corrupt_receipt=True)
        self.assertEqual(result["status"], "UNKNOWN_DO_NOT_RETRY")
        self.assertEqual(result["error_code"], "RECEIPT_NOT_EXACT_SUCCESS")
        self.assertEqual(browser.send_calls, 1)

    def test_full_fresh_page_change_stops_before_intent(self):
        def change(name, value):
            if name == "page_10": value["data"]["unknown"][0] = 2
        result, browser = self.run_fake(fresh_change=change)
        self.assertEqual(result["status"], "BLOCKED_BEFORE_SEND")
        self.assertEqual(result["error_code"], "BEFORE_CHANGED_page_10")
        self.assertEqual(browser.send_calls, 0)
        self.assertFalse(self.files.claim.exists())

    def test_noop_reads_all_before_without_post_or_ledger_claim(self):
        self.tmp.cleanup()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.files = FixtureFiles(self.root, noop=True)
        result, browser = self.run_fake()
        self.assertEqual(result["status"], "NO_OP_CURRENT_STATE_CONFIRMED")
        self.assertEqual(browser.fetch_calls, len(self.files.endpoints))
        self.assertEqual((browser.prepare_calls, browser.send_calls), (0, 0))
        self.assertFalse(self.files.claim.exists())

    def test_release_failure_never_returns_success_status(self):
        result, browser = self.run_fake(release_error=True)
        self.assertEqual(result["status"], "RELEASE_UNPROVEN_NO_RETRY")
        self.assertEqual(browser.send_calls, 1)
        self.assertFalse(result["release"]["context_runtime_release_confirmed"])

    def test_plan_file_bytes_change_stops_before_runtime(self):
        self.files.plan_path.write_bytes(self.files.plan_path.read_bytes() + b"\n")
        self.assertBlocked("PLAN_FILE_CHANGED", self.run_fake)


if __name__ == "__main__": unittest.main()
