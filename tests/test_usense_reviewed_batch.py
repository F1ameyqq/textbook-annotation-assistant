"""Synthetic batch admission/resume tests. No browser, credentials or network."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from annotation.runtime.usense_live import batch, batch_runner, update
from annotation.runtime.usense_live.revision import revision_key, verify_previous_acceptance
import test_usense_live_writer_review as writer_fixture
from test_usense_live_revision import accepted_predecessor


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return batch.file_ref(path)


RELEASE = {"context_closed": True, "runtime_stopped": True, "pending_callbacks": 0,
           "errors": [], "context_runtime_release_confirmed": True}


def captured(root, native, now):
    root.mkdir(exist_ok=True)
    rows = {}
    for name, value in native.items():
        ref = dump(root / (name + ".json"), value)
        rows[name] = {"filename": name + ".json", "sha256": ref["sha256"], "bytes": (root / (name + ".json")).stat().st_size,
                      "status": 200, "request_counts": {"context": 1, "native": 1},
                      "observed_at": (now - timedelta(seconds=2)).isoformat()}
    return dump(root / "capture-summary.json", {"schema": "UsenseNativeCapture/v1", "book_id": update.BOOK,
                "status": "NATIVE_GETS_CAPTURED", "save_attempts": 0, "release": RELEASE,
                "finished_at": (now - timedelta(seconds=1)).isoformat(), "captures": rows})


def good_predecessor(files):
    """Convert the old lossy synthetic history fixture into a current valid plan.

    Also add source metadata and update every raw/hash/process binding. This is
    synthetic fixture construction, never a modification of production evidence.
    """
    acceptance_path, old = accepted_predecessor(files)
    qdir, root = acceptance_path.parent, acceptance_path.parent.parent
    before = copy.deepcopy(old["before"])
    before["zones"]["question"] = writer_fixture.fixture()[0]["zones"]["question"]
    prior = update.make_plan(before, old["target"], old["approved_changes"])
    wp = batch.read(qdir / "writer-process-result.json")
    rp = batch.read(qdir / "reader-process-result.json")
    w, r = wp["result"], rp["result"]
    wd, rd = root / w["run_id"], root / r["run_id"]
    prior_ref = dump(qdir / "plan.json", prior)
    dump(wd / "plan.json", prior)
    dump(wd / "before-q2_question.json", before["zones"]["question"])
    source = {"code": 0, "message": "success", "data": {"synthetic_source": True}}
    dump(wd / "before-source.json", source)
    ref = dump(rd / "source.json", source)
    r["captures"]["source"] = {"filename": "source.json", "sha256": ref["sha256"], "bytes": (rd / "source.json").stat().st_size,
                                "status": 200, "observed_at": "2026-10-23T00:00:06+00:00", "request_counts": {"context": 1, "native": 1}}
    path = "/qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre"
    for label, result in (("writer", w), ("independent-reader", r)):
        cfg_path = qdir / (label + "-config.json")
        cfg = batch.read(cfg_path)
        cfg["allowed_get"].append({"url": writer_fixture.writer.ORIGIN + path, "resource_types": ["fetch", "xhr"], "max_requests": 1})
        result["config_sha256"] = dump(cfg_path, cfg)["sha256"]
    for run in (wd, rd):
        events = batch.read(run / "network-events.json")
        events += [{"method": "GET", "layer": layer, "url_sha256": batch.sha((writer_fixture.writer.ORIGIN + path).encode()),
                    "allowed": True} for layer in ("context", "native")]
        dump(run / "network-events.json", events)
    w.update(plan_sha256=prior["plan_sha256"], plan_file_sha256=prior_ref["sha256"])
    dump(wd / "execution-result.json", w); dump(rd / "capture-summary.json", r)
    dump(qdir / "writer-process-result.json", wp); dump(qdir / "reader-process-result.json", rp)
    intent_path = files.ledger / (prior["ledger_key"] + ".json")
    intent = batch.read(intent_path); intent["plan_sha256"] = prior["plan_sha256"]; dump(intent_path, intent)
    send = batch.read(wd / "send-intent.json"); send["plan_sha256"] = prior["plan_sha256"]; dump(wd / "send-intent.json", send)
    after = {name: batch.read(rd / (name + ".json")) for name in r["captures"]}
    comparison = update.compare_readback(prior, update.from_captured_map(after, "q2_"))
    acceptance = batch.read(acceptance_path)
    acceptance.update(plan_file_sha256=prior_ref["sha256"], comparison=comparison)
    asha = dump(acceptance_path, acceptance)["sha256"]
    dump(files.ledger / (prior["ledger_key"] + ".accepted.json"), {"plan_sha256": prior["plan_sha256"],
         "writer_run": w["run_id"], "reader_run": r["run_id"], "acceptance_sha256": asha})
    current = update.make_plan(update.from_captured_map(after, "q2_"), prior["target"], prior["approved_changes"])
    verify_previous_acceptance(acceptance_path, current, after, files.ledger)
    return acceptance_path, prior, after


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.now = datetime.now(timezone.utc)
        self.ledger = self.root / "usense-existing-ledger"
        self.ledger.mkdir()
        self.source = self.root / "source.txt"
        self.source.write_text("synthetic source only", encoding="utf-8")
        self.review = self.root / "review.json"
        dump(self.review, {"synthetic": True})
        nodes = [{"id": f"node-{q}", "isQuestion": True, "order_in_level": str(q)} for q in range(1, 21)]
        frames = [{"type": zone, "rect_id": f"rect-{q}-{zone}", "file_id": update.BOOK,
                   "directory_id": "lesson-two", "belong_to_level": "question_level", "order_in_level": str(q),
                   "image_order_in_annotation_zone": 0, "page_index": 12} for q in range(1, 21) for zone in ("question", "answer")]
        response = lambda data: {"code": 0, "message": "success", "data": data}
        self.native = {"directory": response({"directory_data": [{"id": "lesson-two", "children": nodes}]}),
                       "frames": response(frames), "source": response({"synthetic": True}), "page_12": response({"synthetic": True})}
        self.items = []
        for q, printed in ((18, "17"), (19, "18")):
            target = {"book_id": update.BOOK, "lesson_directory_id": "lesson-two", "node_id": f"node-{q}",
                      "info_id": f"info-{q}", "question_order": q}
            self.native[f"q{q}_annotations"] = response([copy.deepcopy(f) for f in frames if f["order_in_level"] == str(q)])
            self.native[f"q{q}_info"] = response({"id": f"info-{q}", "file_id": update.BOOK, "order_in_level": str(q),
                                                "tishi": "xuanze", "tilei": None, "tihao": None, "updated_at": "2026-10-15T00:00:00"})
            for zone in update.ZONES:
                data = {"rect_ids": [f"rect-{q}-{zone}"], "ocr_result": "old " + zone, "success": True} if zone in ("question", "answer") else copy.deepcopy(update.ABSENT)
                self.native[f"q{q}_{zone}"] = response(data)
            review = {"text": "synthetic new question", "source_ref": str(self.source), "source_sha256": batch.sha(self.source.read_bytes()),
                      "review_ref": str(self.review), "reviewed_text_sha256": update.text_digest("synthetic new question")}
            candidate = dump(self.root / f"candidate-{q}.json", {"target": target, "approved_changes": {"question": review}})
            self.items.append({"item_id": f"printed-{printed}", "printed_number": printed, "variant": "main", "native_order": q,
                               "node_id": f"node-{q}", "info_id": f"info-{q}", "candidate": candidate,
                               "pages": [12], "previous_acceptance": None})
        self.manifest = {"schema": batch.MANIFEST, "book_id": update.BOOK, "source_lesson": "lesson2",
                         "lesson_directory_id": "lesson-two", "scope_review": {},
                         "captures": [captured(self.root / "capture", self.native, self.now)], "items": self.items}
        self.save()

    def save(self, scope_status="CONFIRMED"):
        self.manifest["scope_review"] = dump(self.root / "scope.json", {"schema": "b-usense-batch-scope-review/0.1", "book_id": update.BOOK,
                    "source_lesson": self.manifest["source_lesson"], "lesson_directory_id": self.manifest["lesson_directory_id"],
                    "directory_membership": scope_status, "mapping": [{k: item[k] for k in batch.MAPPING} for item in self.items]})
        self.manifest_ref = dump(self.root / "manifest.json", self.manifest)

    def prepare(self):
        return batch.prepare(self.manifest_ref["path"], self.manifest_ref["sha256"], self.ledger, now=self.now)

    def blocked(self, code, fn=None):
        with self.assertRaises(ValueError) as cm:
            (fn or self.prepare)()
        self.assertEqual(getattr(cm.exception, "code", str(cm.exception)), code)

    def test_reordered_printed_17_binds_native_18_and_next_cursor(self):
        plan = self.prepare()
        self.assertEqual(plan["items"][0]["plan"]["target"]["question_order"], 18)
        state = batch.inspect_state(plan, self.root / "execution", now=self.now)
        self.assertEqual((state["status"], state["next_item_id"], state["platform_requests"]), ("READY", "printed-17", 0))

    def test_duplicate_stable_ids_orders_and_printed_mapping_rejected(self):
        for key in ("item_id", "node_id", "info_id", "native_order", "printed_number"):
            with self.subTest(key=key):
                old = self.items[1][key]
                self.items[1][key] = self.items[0][key]
                self.save()
                self.blocked("BATCH_DUPLICATE_IDENTITY_OR_MAPPING")
                self.items[1][key] = old

    def test_scope_conflict_is_not_silently_migrated(self):
        self.save("CONFLICT")
        self.blocked("BATCH_SCOPE_REVIEW_CONFLICT_OR_MISMATCH")

    def test_old_order_in_candidate_is_never_remapped(self):
        ref = self.items[0]["candidate"]
        value = batch.read(ref["path"])
        value["target"]["question_order"] = 17
        self.items[0]["candidate"] = dump(ref["path"], value)
        self.save()
        self.blocked("BATCH_CANDIDATE_IDENTITY_MISMATCH")

    def test_directory_node_and_info_disagree_even_with_consistent_candidate(self):
        self.items[0]["node_id"] = "node-17"
        ref = self.items[0]["candidate"]
        value = batch.read(ref["path"]); value["target"]["node_id"] = "node-17"
        self.items[0]["candidate"] = dump(ref["path"], value)
        self.save()
        self.blocked("FRONTEND_ORDER_MISMATCH")

    def test_wrong_info_id_rejected_by_existing_updater(self):
        self.native["q18_info"]["data"]["id"] = "ambiguous-other-info"
        self.manifest["captures"] = [captured(self.root / "capture", self.native, self.now)]
        self.save()
        self.blocked("INFO_IDENTITY_MISMATCH")

    def test_duplicate_info_id_in_capture_is_ambiguous(self):
        self.native["q19_info"]["data"]["id"] = self.native["q18_info"]["data"]["id"]
        self.manifest["captures"] = [captured(self.root / "capture", self.native, self.now)]
        self.save()
        self.blocked("BATCH_AMBIGUOUS_CAPTURED_INFO_ID")

    def test_wrong_lesson_parent_rejected(self):
        self.native["directory"]["data"]["directory_data"][0]["id"] = "actual-lesson-one"
        self.manifest["captures"] = [captured(self.root / "capture", self.native, self.now)]
        self.save()
        self.blocked("WRONG_LESSON_DIRECTORY")

    def test_stale_and_future_baselines_rejected(self):
        for delta in (-901, 4):
            self.manifest["captures"] = [captured(self.root / "capture", self.native, self.now + timedelta(seconds=delta))]
            self.save()
            self.blocked("BATCH_BASELINE_STALE_OR_FUTURE")

    def test_capture_missing_zone_source_or_page_rejected(self):
        for name in ("q19_answer", "source", "page_12"):
            native = {k: v for k, v in self.native.items() if k != name}
            self.manifest["captures"] = [captured(self.root / "capture", native, self.now)]
            self.save()
            self.blocked("BATCH_NATIVE_EVIDENCE_MISSING")

    def test_overlapping_capture_requires_identical_bytes(self):
        other = copy.deepcopy(self.native)
        other["directory"]["data"]["unknown"] = True
        self.manifest["captures"].append(captured(self.root / "other-capture", other, self.now))
        self.save()
        self.blocked("BATCH_CAPTURE_OVERLAP_CHANGED")

    def test_boolean_request_count_is_not_an_integer_guard_proof(self):
        ref = self.manifest["captures"][0]
        summary = batch.read(ref["path"])
        summary["captures"]["directory"]["request_counts"]["context"] = True
        self.manifest["captures"][0] = dump(ref["path"], summary)
        self.save()
        self.blocked("BATCH_CAPTURE_ROW_INVALID")

    def test_unknown_stable_or_revision_intent_blocks_planning(self):
        plan = self.prepare()
        stable = plan["items"][0]["plan"]["ledger_key"]
        for key in (stable, revision_key(stable, "d" * 64)):
            path = self.ledger / (key + ".json")
            dump(path, {"state": "UNKNOWN_DO_NOT_RETRY", "ledger_key": stable})
            self.blocked("BATCH_EXISTING_IDENTITY_INTENT_REQUIRES_PREDECESSOR")
            path.unlink()

    def test_forged_accepted_marker_does_not_authorize_new_plan(self):
        stable = self.prepare()["items"][0]["plan"]["ledger_key"]
        dump(self.ledger / (stable + ".accepted.json"), {"status": "ACCEPTED"})
        self.blocked("BATCH_EXISTING_IDENTITY_INTENT_REQUIRES_PREDECESSOR")

    def test_missing_or_changed_source_stops_before_output(self):
        self.source.write_bytes(b"changed")
        self.blocked("BATCH_EVIDENCE_HASH_CHANGED")

    def test_review_drift_and_raw_drift_reject_prepared_plan(self):
        plan = self.prepare()
        self.review.write_bytes(b"changed")
        self.blocked("BATCH_EVIDENCE_HASH_CHANGED", lambda: batch.validate_batch(plan))

    def test_prepared_baseline_raw_drift_rejected(self):
        plan = self.prepare()
        (self.root / "capture/q18_info.json").write_bytes(b"{}")
        self.blocked("BATCH_EVIDENCE_HASH_CHANGED", lambda: batch.validate_batch(plan))

    def test_plan_tamper_and_code_drift_rejected(self):
        plan = self.prepare()
        with patch.object(batch, "implementation_digest", return_value="changed"):
            self.blocked("BATCH_IMPLEMENTATION_CHANGED", lambda: batch.validate_batch(plan))
        plan["items"][0]["mapping"]["native_order"] = 17
        self.blocked("BATCH_PLAN_CHANGED", lambda: batch.validate_batch(plan))

    def test_partial_directory_and_unknown_dispatch_are_never_retried(self):
        for dispatch in (False, True):
            with self.subTest(dispatch=dispatch):
                plan = self.prepare()
                root = self.root / ("execution-" + str(dispatch))
                qdir = root / "printed-17"; qdir.mkdir(parents=True)
                if dispatch:
                    dump(qdir / "dispatch.json", {"batch_sha256": plan["batch_sha256"], "intent_key": plan["items"][0]["intent_key"]})
                result = batch.inspect_state(plan, root, now=self.now)
                self.assertEqual(result["status"], "BLOCKED_NO_RETRY")
                self.assertIsNone(result["next_item_id"])

    def test_new_unknown_intent_blocks_existing_plan_status(self):
        plan = self.prepare()
        dump(self.ledger / (plan["items"][0]["intent_key"] + ".json"), {"state": "UNKNOWN"})
        state = batch.inspect_state(plan, self.root / "execution", now=self.now)
        self.assertEqual(state["status"], "BLOCKED_NO_RETRY")

    def test_stale_resume_returns_no_next_item(self):
        plan = self.prepare()
        state = batch.inspect_state(plan, self.root / "execution", now=self.now + timedelta(seconds=901))
        self.assertEqual(state["status"], "BLOCKED_NO_RETRY")
        self.assertIsNone(state["next_item_id"])

    def test_reject_all_items_before_creating_prepare_output(self):
        self.items[1]["info_id"] = self.items[0]["info_id"]
        self.save()
        out = self.root / "plan-out"
        with patch("builtins.print"):
            code = batch.main(["prepare", "--manifest", self.manifest_ref["path"], "--sha256", self.manifest_ref["sha256"],
                               "--ledger-root", str(self.ledger), "--out", str(out)])
        self.assertEqual(code, 2)
        self.assertFalse(out.exists())

    def test_cli_prepare_status_from_unrelated_cwd_no_playwright(self):
        tool = Path(__file__).resolve().parents[1] / "tools/run_usense_reviewed_batch.py"
        out = self.root / "prepared"
        proc = subprocess.run([sys.executable, "-B", str(tool), "prepare", "--manifest", self.manifest_ref["path"],
              "--sha256", self.manifest_ref["sha256"], "--ledger-root", str(self.ledger), "--out", str(out)],
              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        proc = subprocess.run([sys.executable, "-B", str(tool), "status", "--plan", result["plan"], "--sha256", result["sha256"],
                               "--execution-root", str(self.root / "execution")], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["next_item_id"], "printed-17")

    def test_legacy_orders_refused(self):
        with self.assertRaises(SystemExit) as cm, patch("sys.stderr"):
            batch.main(["--orders", "17"])
        self.assertEqual(cm.exception.code, 2)

    def test_run_refuses_profile_ledger_mismatch_without_children(self):
        args = SimpleNamespace(execution_root=str(self.root / "execution"), profile=str(self.root / "other/profile"), authorization_reference="synthetic")
        with patch.object(batch_runner, "child") as child:
            self.blocked("BATCH_PROFILE_LEDGER_MISMATCH", lambda: batch_runner.run_batch(self.prepare(), args))
        child.assert_not_called()

    def test_execution_root_cannot_be_reused_for_another_batch(self):
        plan = self.prepare()
        root = self.root / "other-batch"; root.mkdir()
        dump(root / "batch-binding.json", {"batch_sha256": "d" * 64})
        self.blocked("BATCH_EXECUTION_ROOT_ALREADY_BOUND", lambda: batch.inspect_state(plan, root, now=self.now))

    def test_leftover_lock_blocks_new_dispatch_and_offline_status(self):
        plan = self.prepare()
        root = self.root / "locked-execution"; root.mkdir()
        (root / "batch-running.lock").write_text(plan["batch_sha256"], encoding="utf-8")
        self.blocked("BATCH_EXECUTION_LOCK_REQUIRES_OPERATOR_REVIEW", lambda: batch.inspect_state(plan, root, now=self.now))
        args = SimpleNamespace(execution_root=str(root), profile=str(self.root / "profile"), authorization_reference="synthetic")
        with patch.object(batch_runner, "child") as child:
            self.blocked("BATCH_EXECUTION_LOCK_REQUIRES_OPERATOR_REVIEW", lambda: batch_runner.run_batch(plan, args))
        child.assert_not_called()

    def test_no_change_is_offline_only_and_never_dispatched(self):
        for item in self.items:
            ref = item["candidate"]
            value = batch.read(ref["path"])
            value["approved_changes"]["question"]["text"] = "old question"
            value["approved_changes"]["question"]["reviewed_text_sha256"] = update.text_digest("old question")
            item["candidate"] = dump(ref["path"], value)
        self.save()
        plan = self.prepare()
        args = SimpleNamespace(execution_root=str(self.root / "execution"), profile=str(self.root / "profile"), authorization_reference="synthetic")
        with patch.object(batch_runner, "child") as child:
            state = batch_runner.run_batch(plan, args)
        child.assert_not_called()
        self.assertEqual(state["status"], "COMPLETE_OFFLINE_AUDIT")
        self.assertTrue(all(row["status"] == "NO_CHANGE_OFFLINE" for row in state["items"]))

    def test_runner_stops_unknown_and_preserves_dispatch(self):
        plan = self.prepare()
        args = SimpleNamespace(execution_root=str(self.root / "execution"), profile=str(self.root / "profile"),
                               authorization_reference="synthetic", tls_approval_reference=None, dependency_dir=None)
        calls = []
        def fake(args, record, deps):
            calls.append(args)
            if args[0] == "configure":
                return 0, {"sha256": "a" * 64}
            return 2, {"status": "UNKNOWN_DO_NOT_RETRY", "release": RELEASE}
        with patch.object(batch_runner, "child", side_effect=fake):
            self.blocked("BATCH_WRITER_UNKNOWN_OR_FAILED_NO_RETRY", lambda: batch_runner.run_batch(plan, args))
            self.blocked("BATCH_RESUME_BLOCKED_NO_RETRY", lambda: batch_runner.run_batch(plan, args))
        self.assertEqual(len(calls), 2)
        self.assertTrue((Path(args.execution_root) / "printed-17/dispatch.json").exists())
        self.assertFalse((Path(args.execution_root) / "printed-18").exists())


class CompletedResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.files = writer_fixture.FixtureFiles(self.root)
        self.acceptance, self.prior, self.after = good_predecessor(self.files)

    def completed_batch(self):
        """Wrap the existing complete independent predecessor fixture unchanged."""
        item = {"mapping": {"item_id": "q2", "native_order": 2, "printed_number": "2", "variant": "main",
                            "node_id": self.prior["target"]["node_id"], "info_id": self.prior["target"]["info_id"]},
                "plan": self.prior, "pages": [10], "intent_key": self.prior["ledger_key"], "previous_acceptance": None,
                "baseline_files": {}}
        plan = {"schema": batch.PLAN, "implementation_sha256": batch.implementation_digest(), "evidence_file_sha256": {},
                "ledger_root": str(self.files.ledger), "items": [item], "oldest_observed_at": "2026-10-23T00:00:00+00:00"}
        plan["batch_sha256"] = update.digest(plan)
        dump(self.acceptance.parent / "dispatch.json", {"batch_sha256": plan["batch_sha256"], "intent_key": item["intent_key"]})
        return plan

    def test_complete_independent_evidence_is_skipped_without_replay(self):
        plan = self.completed_batch()
        state = batch.inspect_state(plan, self.acceptance.parent.parent)
        self.assertEqual(state["status"], "COMPLETE_OFFLINE_AUDIT")
        self.assertEqual(state["items"][0]["status"], "ACCEPTED")
        self.assertIsNone(state["next_item_id"])
        args = SimpleNamespace(execution_root=str(self.acceptance.parent.parent), profile=str(self.root / "synthetic-profile"), authorization_reference="synthetic")
        with patch.object(batch_runner, "child") as child:
            result = batch_runner.run_batch(plan, args)
        child.assert_not_called()
        self.assertEqual(result["status"], "COMPLETE_OFFLINE_AUDIT")

    def test_resume_does_not_trust_a_handwritten_accepted_status(self):
        plan = self.completed_batch()
        raw = batch.read(self.acceptance)
        raw["checks"] = {"handwritten_success": True}
        dump(self.acceptance, raw)
        state = batch.inspect_state(plan, self.acceptance.parent.parent)
        self.assertEqual(state["status"], "BLOCKED_NO_RETRY")

    def test_unknown_prior_writer_blocks_resume(self):
        plan = self.completed_batch()
        path = self.acceptance.parent / "writer-process-result.json"
        value = batch.read(path); value["result"]["status"] = "UNKNOWN_DO_NOT_RETRY"; dump(path, value)
        state = batch.inspect_state(plan, self.acceptance.parent.parent)
        self.assertEqual(state["status"], "BLOCKED_NO_RETRY")

    def test_unknown_branch_cannot_hide_behind_accepted_ancestor(self):
        plan = self.completed_batch()
        stable = self.prior["ledger_key"]
        dump(self.files.ledger / (revision_key(stable, "d" * 64) + ".json"), {"state": "UNKNOWN", "ledger_key": stable})
        state = batch.inspect_state(plan, self.acceptance.parent.parent)
        self.assertEqual(state["status"], "BLOCKED_NO_RETRY")

    def test_explicit_accepted_revision_is_verified_during_prepare(self):
        now = datetime.now(timezone.utc)
        capture_ref = captured(self.root / "fresh-current", self.after, now)
        candidate = copy.deepcopy(self.prior["approved_changes"])
        candidate["question"]["text"] += " synthetic explicit revision"
        candidate["question"]["reviewed_text_sha256"] = update.text_digest(candidate["question"]["text"])
        target = self.prior["target"]
        candidate_ref = dump(self.root / "revision-candidate.json", {"target": target, "approved_changes": candidate})
        item = {"item_id": "existing-q2", "native_order": 2, "printed_number": "2", "variant": "main",
                "node_id": target["node_id"], "info_id": target["info_id"], "candidate": candidate_ref,
                "pages": [10], "previous_acceptance": batch.file_ref(self.acceptance)}
        scope = {"schema": "b-usense-batch-scope-review/0.1", "book_id": update.BOOK, "source_lesson": "synthetic-lesson",
                 "lesson_directory_id": target["lesson_directory_id"], "directory_membership": "CONFIRMED",
                 "mapping": [{k: item[k] for k in batch.MAPPING}]}
        manifest = {"schema": batch.MANIFEST, "book_id": update.BOOK, "source_lesson": "synthetic-lesson",
                    "lesson_directory_id": target["lesson_directory_id"], "scope_review": dump(self.root / "scope.json", scope),
                    "captures": [capture_ref], "items": [item]}
        ref = dump(self.root / "manifest.json", manifest)
        plan = batch.prepare(ref["path"], ref["sha256"], self.files.ledger, now=now)
        self.assertEqual(plan["items"][0]["intent_key"], revision_key(self.prior["ledger_key"], self.prior["plan_sha256"]))
        self.assertEqual(batch.inspect_state(plan, self.root / "revision-run", now=now)["status"], "READY")


if __name__ == "__main__":
    unittest.main()
