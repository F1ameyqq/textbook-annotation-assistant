"""A25 synthetic boundary checks only; no browser or first-lesson replay."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.runtime.usense_live import batch
from annotation.runtime.usense_live.config import ZONES, endpoints
from annotation.runtime.usense_live.core import sha, BindingError
from annotation.runtime.usense_live.update import ABSENT, UpdateError, text_digest

spec = importlib.util.spec_from_file_location("a25_batch_entry", ROOT / "tools/run_usense_reviewed_batch.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


def raw(value):
    return json.dumps(value, ensure_ascii=True).encode()


def response(data):
    return {"code": 0, "message": "success", "data": data}


class A25BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "tests")
        self.root = Path(self.tmp.name)
        self.baseline = self.root / "baseline"
        self.profile = self.root / "synthetic-profile"
        self.ledger = self.root / "usense-existing-ledger"
        for path in (self.baseline, self.profile, self.ledger):
            path.mkdir()
        # Inserted Q7 variant occupies a native slot. Semantic lesson 2 is
        # intentionally still under the server's first-lesson parent.
        nodes = [{"id": f"synthetic-node-{q}", "isQuestion": True, "order_in_level": str(q)} for q in range(1, 24)]
        directory = response({"directory_data": [{"id": "synthetic-real-parent", "label": "Lesson 1", "children": nodes}]})
        frames = [{"file_id": "46007447", "rect_id": f"synthetic-rect-{q}-{z}", "directory_id": "synthetic-real-parent",
                   "belong_to_level": "question_level", "order_in_level": str(q), "type": z,
                   "page_index": 12 if z == "question" else 173, "image_order_in_annotation_zone": 0}
                  for q in range(1, 24) for z in ("question", "answer")]
        self.native = {"directory": directory, "frames": response(frames), "source": response({"synthetic": True}),
                       "page_12": response({"page": 12}), "page_173": response({"page": 173})}
        self.manifest = {"schema": batch.SCHEMA, "book_id": "46007447", "baseline": {}, "targets": []}
        for q in range(18, 23):
            target = {"book_id": "46007447", "lesson_directory_id": "synthetic-real-parent",
                      "node_id": f"synthetic-node-{q}", "info_id": f"synthetic-info-{q}", "question_order": q}
            selected = [f for f in frames if f["order_in_level"] == str(q)]
            self.native[f"q{q}_annotations"] = response(selected)
            self.native[f"q{q}_info"] = response({"id": target["info_id"], "file_id": "46007447", "order_in_level": str(q),
                "tishi": "single", "tilei": None, "tihao": "", "updated_at": "2026-10-23T00:00:00"})
            for z in ZONES:
                self.native[f"q{q}_{z}"] = response({"success": True, "rect_ids": [f"synthetic-rect-{q}-{z}"], "ocr_result": "old"}
                    if z in ("question", "answer") else copy.deepcopy(ABSENT))
            source, review, candidate = [self.root / f"synthetic-{q}-{kind}.json" for kind in ("source", "review", "candidate")]
            source.write_bytes(raw({"synthetic_source_page": 12}))
            review.write_bytes(raw({"synthetic_review": q, "text": "updated"}))
            candidate.write_bytes(raw({"target": target, "approved_changes": {"question": {"text": "updated",
                "source_ref": str(source), "source_sha256": sha(source.read_bytes()), "review_ref": str(review),
                "reviewed_text_sha256": text_digest("updated")}}}))
            self.manifest["targets"].append({"printed_question": q - 1, "semantic_lesson": "Lesson 2",
                "target": target, "source_pages": [12, 173], "candidate": {"path": str(candidate), "sha256": sha(candidate.read_bytes())},
                "review_evidence": {str(source): sha(source.read_bytes()), str(review): sha(review.read_bytes())}, "previous_acceptance": None})
        self.manifest_path = self.root / "manifest.json"
        self.save_baseline()

    def tearDown(self):
        self.tmp.cleanup()

    def save_baseline(self):
        caps = {}
        for name, value in self.native.items():
            value = raw(value)
            (self.baseline / (name + ".json")).write_bytes(value)
            caps[name] = {"filename": name + ".json", "sha256": sha(value), "bytes": len(value), "status": 200,
                          "request_counts": {"context": 1, "native": 1}}
        summary = {"status": "NATIVE_GETS_CAPTURED", "book_id": "46007447", "save_attempts": 0, "captures": caps,
                   "transport": {"mode": "DIRECT", "proxy_server": None},
                   "release": {"context_runtime_release_confirmed": True}}
        summary_raw = raw(summary)
        (self.baseline / "capture-summary.json").write_bytes(summary_raw)
        self.manifest["baseline"] = {"capture_summary_sha256": sha(summary_raw), "files": {k: v["sha256"] for k, v in caps.items()}}

    def prepare(self):
        self.manifest_path.write_bytes(raw(self.manifest))
        return batch.prepare(self.manifest_path, sha(self.manifest_path.read_bytes()), self.baseline, self.profile, "SYNTHETIC_ONLY")

    def change_candidate(self, item, change):
        path = Path(item["candidate"]["path"])
        value = json.loads(path.read_bytes())
        change(value)
        path.write_bytes(raw(value))
        item["candidate"]["sha256"] = sha(path.read_bytes())

    def test_reordered_lesson_two_targets_use_stable_ids_and_actual_parent(self):
        result = self.prepare()
        self.assertEqual([p["printed_question"] for p in result["targets"]], list(range(17, 22)))
        self.assertEqual([p["target"]["question_order"] for p in result["targets"]], list(range(18, 23)))
        self.assertTrue(all(p["plan"]["payload_candidate"]["target_directory_id"] == "synthetic-real-parent" for p in result["targets"]))
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_old_native_order_is_rejected_even_with_matching_candidate(self):
        item = self.manifest["targets"][0]
        item["target"]["question_order"] = 17
        self.change_candidate(item, lambda c: c["target"].update(question_order=17))
        # A stale order cannot be smuggled in by supplying a full old q17 map.
        for name in list(self.native):
            if name.startswith("q18_"):
                self.native[name.replace("q18_", "q17_")] = copy.deepcopy(self.native[name])
        self.save_baseline()
        with self.assertRaisesRegex(UpdateError, "FRONTEND_ORDER_MISMATCH"):
            self.prepare()

    def test_stable_info_mismatch_rejected(self):
        item = self.manifest["targets"][0]
        item["target"]["info_id"] = "synthetic-wrong-info"
        self.change_candidate(item, lambda c: c["target"].update(info_id="synthetic-wrong-info"))
        with self.assertRaisesRegex(UpdateError, "INFO_IDENTITY_MISMATCH"):
            self.prepare()

    def test_candidate_node_mismatch_rejected(self):
        self.change_candidate(self.manifest["targets"][0], lambda c: c["target"].update(node_id="synthetic-other"))
        with self.assertRaisesRegex(BindingError, "BATCH_CANDIDATE_TARGET_MISMATCH"):
            self.prepare()

    def test_duplicate_stable_target_and_alias_order_rejected(self):
        for key in ("node_id", "info_id", "question_order"):
            original = copy.deepcopy(self.manifest)
            self.manifest["targets"][1]["target"][key] = self.manifest["targets"][0]["target"][key]
            with self.subTest(key=key), self.assertRaisesRegex(BindingError, "BATCH_DUPLICATE_TARGET"):
                self.prepare()
            self.manifest = original

    def test_fifth_missing_candidate_stops_before_any_child(self):
        Path(self.manifest["targets"][-1]["candidate"]["path"]).unlink()
        self.manifest_path.write_bytes(raw(self.manifest))
        out = self.root / "no-writes"
        with patch.object(entry, "child") as child, self.assertRaises(BindingError):
            entry.main(["--manifest", str(self.manifest_path), "--manifest-sha256", sha(self.manifest_path.read_bytes()),
                "--baseline", str(self.baseline), "--profile", str(self.profile), "--out", str(out),
                "--authorization-reference", "SYNTHETIC_ONLY", "--tls-approval-reference", "SYNTHETIC_ONLY"])
        child.assert_not_called()
        self.assertEqual(json.loads((out / "batch-summary.json").read_bytes())["all_targets"], "NOT_RUN")
        self.assertEqual([r["status"] for r in json.loads((out / "batch-summary.json").read_bytes())["results"]], ["NOT_RUN"] * 5)
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_later_missing_review_and_page_block_entire_preflight(self):
        item = self.manifest["targets"][-1]
        review = next(p for p in item["review_evidence"] if "-review.json" in p)
        Path(review).unlink()
        with self.assertRaises(BindingError):
            self.prepare()

    def test_missing_source_page_rejected(self):
        del self.native["page_173"]
        self.save_baseline()
        with self.assertRaisesRegex(BindingError, "BATCH_SOURCE_OR_TARGET_INPUT_MISSING"):
            self.prepare()

    def test_unknown_intent_in_any_revision_branch_cannot_be_bypassed(self):
        plan = self.prepare()["targets"][0]["plan"]
        path = self.ledger / (plan["ledger_key"] + "-revision-" + "a" * 64 + ".json")
        path.write_bytes(raw({"status": "UNKNOWN_DO_NOT_RETRY"}))
        before = path.read_bytes()
        with self.assertRaisesRegex(BindingError, "BATCH_EXISTING_IDENTITY_REQUIRES_ACCEPTED_PREDECESSOR"):
            self.prepare()
        self.assertEqual(path.read_bytes(), before)

    def test_predecessor_reference_is_hash_bound(self):
        item = self.manifest["targets"][0]
        previous = self.root / "acceptance.json"
        previous.write_bytes(raw({"status": "ACCEPTED"}))
        item["previous_acceptance"] = {"path": str(previous), "sha256": "0" * 64}
        with self.assertRaisesRegex(BindingError, "BATCH_INPUT_HASH_MISMATCH"):
            self.prepare()

    def test_source_review_candidate_and_manifest_bytes_cannot_change(self):
        result = self.prepare()
        path = Path(self.manifest["targets"][-1]["candidate"]["path"])
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(BindingError, "BATCH_PREPARED_INPUT_CHANGED"):
            batch.recheck(result, result["targets"])

    def test_new_pending_ledger_stops_before_next_process(self):
        result = self.prepare()
        plan = result["targets"][-1]["plan"]
        (self.ledger / (plan["ledger_key"] + ".json")).write_bytes(b"{}")
        with self.assertRaisesRegex(BindingError, "BATCH_PENDING_LEDGER_CHANGED_NO_RETRY"):
            batch.recheck(result, result["targets"])

    def test_writer_unknown_stops_reader_and_marks_all_successors_not_run(self):
        prepared = self.prepare()
        out = self.root / "run"
        out.mkdir()
        calls = []
        def fail_writer(args, record):
            calls.append(args[0])
            if args[0] == "configure":
                return {"exit_code": 0, "result": {"sha256": "a" * 64}}
            return {"exit_code": 2, "result": {"status": "UNKNOWN_DO_NOT_RETRY", "release": {"context_runtime_release_confirmed": True}}}
        result = entry.execute(prepared, out, self.baseline, self.profile, "SYNTHETIC_ONLY", "SYNTHETIC_ONLY", fail_writer)
        self.assertEqual(calls, ["configure", "--writer"])
        self.assertEqual([r["status"] for r in result["results"]], ["STOPPED_NO_RETRY"] + ["NOT_RUN"] * 4)
        self.assertEqual(list(self.ledger.iterdir()), [])

    def test_generated_plan_cannot_change_after_configuration(self):
        prepared = self.prepare()
        out = self.root / "plan-change"
        out.mkdir()
        calls = []
        def tamper(args, record):
            calls.append(args[0])
            plan = next(out.glob("target-*/plan.json"))
            plan.write_bytes(plan.read_bytes() + b" ")
            return {"exit_code": 0, "result": {"sha256": "a" * 64}}
        result = entry.execute(prepared, out, self.baseline, self.profile, "SYNTHETIC_ONLY", "SYNTHETIC_ONLY", tamper)
        self.assertEqual(calls, ["configure"])
        self.assertEqual(result["error_code"], "BATCH_PREPARED_INPUT_CHANGED")
        self.assertEqual([r["status"] for r in result["results"]], ["STOPPED_NO_RETRY"] + ["NOT_RUN"] * 4)

    def test_successful_batch_preserves_serial_writer_then_new_reader(self):
        prepared = self.prepare()
        out = self.root / "synthetic-success"
        out.mkdir()
        calls, configs = [], {}
        clock = datetime(2026, 10, 23, tzinfo=timezone.utc)
        def child(args, record):
            nonlocal clock
            calls.append(args[0])
            clock += timedelta(seconds=1)
            started = clock.isoformat()
            clock += timedelta(seconds=1)
            finished = clock.isoformat()
            if args[0] == "configure":
                order = args[args.index("--orders") + 1]
                cfg = Path(args[args.index("--config") + 1])
                configs[str(cfg)] = order
                return {"exit_code": 0, "result": {"sha256": "a" * 64}}
            cfg = str(args[args.index("--config") + 1])
            order = configs[cfg]
            item = next(p for p in prepared["targets"] if p["target"]["question_order"] == order)
            plan = item["plan"]
            run_id = f"synthetic-{args[0].strip('-')}-{order}"
            if args[0] == "--writer":
                (self.ledger / (plan["ledger_key"] + ".json")).write_bytes(raw({"synthetic_intent": True}))
                result = {"status": "RECEIPT_CAPTURED_REQUIRES_INDEPENDENT_READBACK", "run_id": run_id,
                    "release": {"context_runtime_release_confirmed": True}, "post_attempts": 1, "finished_at": finished,
                    "intent_key": plan["ledger_key"]}
            else:
                rd = out / run_id
                rd.mkdir()
                after = plan["expected"]
                values = {"directory": after["directory"], "frames": after["frames"],
                    f"q{order}_annotations": after["annotations"], f"q{order}_info": after["info"],
                    **{f"q{order}_{z}": value for z, value in after["zones"].items()},
                    **{name: self.native[name] for name in ("source", "page_12", "page_173")}}
                for name, value in values.items():
                    (rd / (name + ".json")).write_bytes(raw(value))
                result = {"status": "NATIVE_GETS_CAPTURED", "run_id": run_id, "save_attempts": 0,
                    "release": {"context_runtime_release_confirmed": True},
                    "captures": {name: {"observed_at": finished} for name in values}}
            return {"exit_code": 0, "result": result, "pid": len(calls), "started_at": started, "finished_at": finished}
        result = entry.execute(prepared, out, self.baseline, self.profile, "SYNTHETIC_ONLY", "SYNTHETIC_ONLY", child)
        self.assertEqual(result["status"], "ALL_ACCEPTED", result)
        self.assertEqual(calls, ["configure", "--writer", "configure", "capture"] * 5)
        self.assertEqual(len(list(self.ledger.glob("*.accepted.json"))), 5)
        self.assertTrue(all(item["checks"]["different_processes"] for item in result["results"]))

    def test_proxy_transport_is_forwarded_to_writer_configuration(self):
        server = "http://127.0.0.1:7897"
        summary_path = self.baseline / "capture-summary.json"
        summary = json.loads(summary_path.read_bytes())
        summary["transport"] = {"mode": "HTTP_CONNECT_PROXY", "proxy_server": server}
        summary_path.write_bytes(raw(summary))
        self.manifest["baseline"]["capture_summary_sha256"] = sha(summary_path.read_bytes())
        prepared = self.prepare()
        out = self.root / "proxy-forward"
        out.mkdir()
        calls = []
        def child(args, record):
            calls.append(args)
            if args[0] == "configure":
                self.assertEqual(args[args.index("--proxy-server") + 1], server)
                return {"result": {"sha256": "a" * 64}, "exit_code": 0}
            return {"result": {"status": "UNKNOWN_DO_NOT_RETRY"}, "exit_code": 2}
        result = entry.execute(prepared, out, self.baseline, self.profile, "SYNTHETIC_ONLY", "SYNTHETIC_ONLY", child, server)
        self.assertEqual([call[0] for call in calls], ["configure", "--writer"])
        self.assertEqual(result["status"], "STOPPED_NO_RETRY")

    def test_changed_transport_stops_before_first_configuration(self):
        prepared = self.prepare()
        out = self.root / "proxy-mismatch"
        out.mkdir()
        child = Mock()
        result = entry.execute(prepared, out, self.baseline, self.profile, "SYNTHETIC_ONLY", "SYNTHETIC_ONLY", child,
                               "http://127.0.0.1:7897")
        child.assert_not_called()
        self.assertEqual(result["error_code"], "BATCH_TRANSPORT_MUST_MATCH_CURRENT_CAPTURE")
        self.assertEqual([r["status"] for r in result["results"]], ["NOT_RUN"] * 5)


class PortableEntryA25Tests(unittest.TestCase):
    def test_actual_entry_beats_conflicting_installed_regular_package_from_other_cwd(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as tmp:
            conflict = Path(tmp) / "annotation"
            conflict.mkdir()
            (conflict / "__init__.py").write_text("raise RuntimeError('foreign package imported')", encoding="ascii")
            boot = "import sys,runpy;sys.path.insert(0,sys.argv[1]);entry=sys.argv[2];sys.argv=[entry,'--help'];runpy.run_path(entry,run_name='__main__')"
            result = subprocess.run([sys.executable, "-B", "-c", boot, tmp, str(ROOT / "tools/run_usense_live.py")],
                                    cwd=tmp, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b"configure", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
