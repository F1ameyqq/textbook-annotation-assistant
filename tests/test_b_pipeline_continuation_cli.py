"""Continuation CLI: local paths, explicit scope and immutable audit receipts.

Argument/interface cases use declared injected reports. Integration cases use
generated source pixels and synthetic OCR observations; no model or site runs.
"""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools"), str(ROOT / "tests")]
from run_pipeline_b import execute, main

STAGES = ("continuation_prepare", "continuation_proof", "continuation_apply", "continuation_quality")


class ContinuationCLIArguments(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workdir = self.root / "work"
        self.package = self.root / "continuation-package.json"
        self.adjacent = self.root / "adjacent.png"

    def args(self, *extra, cached=True):
        args = ["--source", str(self.root / "source.json"), "--context", str(self.root / "context.json"),
            "--review", str(self.root / "review.json"), "--workdir", str(self.workdir)]
        if cached:
            args += ["--evidence", str(self.root / "evidence.json")]
        return [*args, *extra]

    def pair(self):
        return ["--continuation", str(self.package), "--adjacent-source", str(self.adjacent)]

    def assert_argparse(self, args):
        with patch("run_pipeline_b.execute") as runner, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(args)
            self.assertEqual(error.exception.code, 2)
            runner.assert_not_called()

    def test_continuation_and_original_adjacent_image_must_be_explicitly_paired(self):
        self.assert_argparse(self.args("--continuation", str(self.package)))
        self.assert_argparse(self.args("--adjacent-source", str(self.adjacent)))
        self.assertFalse(self.workdir.exists())

    def test_each_new_stop_requires_a_continuation_package(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                self.assert_argparse(self.args("--stop-after", stage))

    def test_new_stops_parse_with_the_pair_without_enabling_ocr(self):
        for stage in STAGES:
            with self.subTest(stage=stage), patch("run_pipeline_b.execute", return_value={"exit_code": 0}) as runner, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(self.args(*self.pair(), "--stop-after", stage)), 0)
                kwargs = runner.call_args.kwargs
                self.assertEqual(kwargs["continuation_path"], self.package)
                self.assertEqual(kwargs["adjacent_source_path"], self.adjacent)
                self.assertEqual(kwargs["stop_after"], stage)
                self.assertFalse(kwargs["use_ocr"])

    def test_cached_and_recovery_argument_restrictions_are_preserved(self):
        for flags in (("--ocr",), ("--max-items", "1"), ("--stop-after", "refine"), ("--stop-after", "recover")):
            with self.subTest(flags=flags):
                self.assert_argparse(self.args(*self.pair(), *flags))

    def test_both_new_paths_reject_urls_and_network_shares_before_running(self):
        for flag in ("--continuation", "--adjacent-source"):
            for value in ("https://example.invalid/input", "//server/share/input", "\\\\server\\share\\input"):
                args = self.args(*self.pair())
                args[args.index(flag)+1] = value
                with self.subTest(flag=flag, value=value):
                    self.assert_argparse(args)

    def test_execute_passes_both_paths_to_core_and_independent_auditor(self):
        seen = []
        report = dict(artifact_id="synthetic-continuation-interface-report", revision=1, content_hash="1"*64,
            run_id="synthetic-continuation-interface-run", payload=dict(pipeline_state="READY", mode="CACHED_INPUT",
                counts={}, decision="HOLD", business_acceptance=False, transcription_verified=False, platform_actions=[]))
        check = dict(schema_version="b-pipeline-check-trial/0.1", artifact_id="synthetic-continuation-interface-check",
            revision=1, content_hash="2"*64, payload=dict(accepted=True, issues=[], decision="HOLD",
                business_acceptance=False, transcription_verified=False, platform_actions=[]))
        def runner(*args, **kwargs):
            seen.append(("core", kwargs))
            return report
        def auditor(*args, **kwargs):
            seen.append(("auditor", kwargs))
            return check
        result = execute(self.root / "source.json", self.root / "context.json", self.root / "review.json", self.workdir,
            continuation_path=str(self.package), adjacent_source_path=str(self.adjacent),
            stop_after="continuation_apply", runner=runner, auditor=auditor)
        self.assertEqual([name for name, _ in seen], ["core", "auditor"])
        for _, kwargs in seen:
            self.assertEqual(kwargs["continuation_path"], self.package)
            self.assertEqual(kwargs["adjacent_source_path"], self.adjacent)
            self.assertIsNone(kwargs["recovery_path"])
        self.assertEqual(seen[0][1]["stop_after"], "continuation_apply")
        self.assertEqual(result["schema_version"], "b-pipeline-cli-result-trial/0.1")
        self.assertEqual(result["decision"], "HOLD")
        self.assertTrue(result["audit_performed"])
        self.assertTrue((self.workdir / result["check"]["path"]).is_file())

    def test_latest_integrity_rejection_cannot_be_released_as_ready_success(self):
        report = dict(artifact_id="synthetic-latest-report", revision=1, content_hash="1"*64,
            run_id="synthetic-latest-run", payload=dict(pipeline_state="READY", mode="CACHED_INPUT",
                counts={}, decision="HOLD", business_acceptance=False, transcription_verified=False, platform_actions=[]))
        check = dict(schema_version="b-pipeline-check-trial/0.1", artifact_id="synthetic-latest-check", revision=1,
            content_hash="2"*64, payload=dict(accepted=False, issues=[{"code": "SYNTHETIC_CONTINUATION_INTEGRITY_FAILURE"}],
                decision="HOLD", business_acceptance=False, transcription_verified=False, platform_actions=[]))
        result = execute(self.root / "source.json", self.root / "context.json", self.root / "review.json", self.workdir,
            continuation_path=self.package, adjacent_source_path=self.adjacent,
            runner=lambda *args, **kwargs: report, auditor=lambda *args, **kwargs: check)
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["integrity_accepted"])
        self.assertFalse(result["business_acceptance"])
        self.assertEqual(result["decision"], "HOLD")
        self.assertTrue((self.workdir / result["check"]["path"]).is_file())


class ContinuationCLIIntegration(unittest.TestCase):
    def setUp(self):
        # The producer-owned helper creates local image bytes and explicitly
        # synthetic observations, never fake real-book file hashes.
        from test_b_continuation_stage import make_continuation_fixture
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = make_continuation_fixture(self.root)
        for name in ("source_path", "context_path", "review_path", "evidence_path", "package_path", "adjacent_source_path"):
            setattr(self, name, Path(self.fixture[name]))
        self.workdir = self.root / "pipeline"

    def args(self, *extra, cached=True, continuation=True):
        args = ["--source", str(self.source_path), "--context", str(self.context_path),
            "--review", str(self.review_path), "--workdir", str(self.workdir)]
        if cached:
            args += ["--evidence", str(self.evidence_path)]
        if continuation:
            args += ["--continuation", str(self.package_path), "--adjacent-source", str(self.adjacent_source_path)]
        return [*args, *extra]

    def cli(self, *extra, cached=True, continuation=True, expected=0, script=None):
        prefix = [sys.executable, "-c", script] if script else [sys.executable]
        completed = subprocess.run([*prefix, str(ROOT / "tools/run_pipeline_b.py"),
            *self.args(*extra, cached=cached, continuation=continuation)], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", timeout=45)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)

    def report(self, result):
        for path in (self.workdir / "objects").glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if all(value.get(k) == v for k, v in result["report_ref"].items()):
                return value
        self.fail("the CLI report reference has no actual immutable object")

    def stages(self, result):
        return {stage["stage_id"]: stage for stage in self.report(result)["payload"]["stages"]}

    def stage_result(self, stage):
        path = (self.workdir / stage["output"]["path"]).resolve()
        self.assertTrue(path.is_relative_to(self.workdir.resolve()))
        return json.loads(path.read_text(encoding="utf-8"))["payload"]["result"]

    def ref(self, value):
        return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}

    def assert_hold(self, result):
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["business_acceptance"])
        self.assertFalse(result["transcription_verified"])

    def test_all_four_stops_resume_to_latest_graph_and_keep_previous_receipts(self):
        original_files = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        previous_checks = {}
        for index, stage in enumerate(STAGES):
            with self.subTest(stage=stage):
                result = self.cli("--stop-after", stage)
                rows = self.stages(result)
                self.assertEqual(list(rows)[-4:], list(STAGES))
                self.assertEqual(rows[stage]["state"], "DONE")
                for earlier in STAGES[:index]:
                    self.assertTrue(rows[earlier]["cached"], earlier)
                for later in STAGES[index+1:]:
                    self.assertEqual(rows[later]["state"], "WAITING")
                self.assertEqual(result["pipeline_state"], "READY" if index == 3 else "PARTIAL")
                if index < 3:
                    self.assertIsNone(self.report(result)["payload"]["final_outputs"])
                self.assertTrue(result["integrity_accepted"])
                self.assert_hold(result)
                check = self.workdir / result["check"]["path"]
                previous_checks[check] = check.read_bytes()
        final = self.cli()
        rows = self.stages(final)
        self.assertTrue(all(rows[name]["cached"] for name in STAGES))
        graph = self.stage_result(rows["continuation_apply"])["payload"]["graph"]
        check = self.stage_result(rows["continuation_quality"])
        prepared_evidence = self.stage_result(rows["continuation_prepare"])["payload"]["evidence"]
        final_payload = self.report(final)["payload"]
        self.assertEqual(final_payload["final_outputs"], dict(evidence_ref=self.ref(prepared_evidence),
            graph_ref=self.ref(graph), quality_ref=self.ref(check)))
        self.assertFalse(final_payload["continuation_scope"]["full_adjacent_page_ocr"])
        self.assertFalse(final_payload["continuation_scope"]["viewer_page_mapping_verified"])
        self.assertEqual(graph["schema_version"], "b-graph-trial/0.4")
        self.assertEqual(check["schema_version"], "b-check-trial/0.4")
        self.assertIn(self.ref(graph), check["input_refs"])
        self.assertEqual(check["payload"]["decision"], "HOLD")
        self.assertFalse(graph["payload"]["business_acceptance"])
        self.assertTrue(any(answer.get("structural_complete") and answer["complete"] is False
            for answer in graph["payload"]["answers"]))
        for path, content in {**original_files, **previous_checks}.items():
            self.assertEqual(path.read_bytes(), content, str(path))

    def test_without_explicit_continuation_the_old_chain_does_not_add_stages(self):
        result = self.cli(continuation=False)
        self.assertEqual(set(self.stages(result)), {"evidence", "assemble", "quality"})
        self.assertEqual(result["pipeline_state"], "READY")
        self.assert_hold(result)

    def test_fresh_workdirs_keep_business_references_stable_without_changing_input_archives(self):
        originals = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        first = self.cli()
        first_report = self.report(first)
        first_rows = self.stages(first)
        assembled = self.stage_result(first_rows["assemble"])
        self.assertNotIn("created_at", assembled)
        self.assertIn("created_at", self.stage_result(first_rows["evidence"]))
        self.workdir = self.root / "another-pipeline"
        second = self.cli()
        second_report = self.report(second)
        self.assertNotEqual(first_report["created_at"], second_report["created_at"])
        self.assertEqual(first_report["payload"]["final_outputs"], second_report["payload"]["final_outputs"])
        self.assertNotEqual(first["report_ref"], second["report_ref"])
        self.assertTrue(second["integrity_accepted"])
        self.assert_hold(second)
        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content, str(path))

    def test_review_only_rechecks_quality_and_keeps_the_continuation_projection(self):
        first = self.cli()
        before = self.stages(first)
        review = json.loads(self.review_path.read_text(encoding="utf-8"))
        review["synthetic_cli_note"] = "Changed review metadata; no source fact or answer expectation changed"
        self.review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
        second = self.cli()
        after = self.stages(second)
        for name in ("evidence", "assemble", "continuation_prepare", "continuation_proof", "continuation_apply"):
            self.assertTrue(after[name]["cached"], name)
            self.assertEqual(after[name]["result_ref"], before[name]["result_ref"])
        for name in ("quality", "continuation_quality"):
            self.assertFalse(after[name]["cached"], name)
        self.assertEqual(second["pipeline_state"], "READY")
        self.assert_hold(second)

    def test_current_evidence_identity_is_rebuilt_instead_of_using_a_frozen_graph(self):
        current = json.loads(self.evidence_path.read_text(encoding="utf-8"))
        current["artifact_id"] = "new-synthetic-current-base"
        current["revision"] += 1
        self.evidence_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        result = self.cli()
        rows = self.stages(result)
        imported = self.stage_result(rows["evidence"])
        self.assertEqual(imported, current)
        prepared = self.stage_result(rows["continuation_prepare"])
        self.assertIn(self.ref(current), prepared["input_refs"])
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertTrue(result["integrity_accepted"])

    def test_live_geometry_does_not_enable_ocr_or_reach_continuation(self):
        result = self.cli(cached=False)
        rows = self.stages(result)
        self.assertEqual(result["pipeline_state"], "PARTIAL")
        self.assertEqual(rows["recognition"]["state"], "DONE")
        self.assertEqual(rows["refine"]["reason"], "OCR_REQUIRED")
        self.assertTrue(all(rows[name]["state"] == "WAITING" for name in STAGES))
        self.assert_hold(result)

    def test_cached_fresh_process_blocks_ocr_runtimes_and_network(self):
        script = r'''
import importlib.abc,runpy,socket,sys
class NoModels(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','torch','paddle','requests','httpx','aiohttp'}:
            raise AssertionError('forbidden continuation import: '+fullname)
sys.meta_path.insert(0,NoModels())
class OfflineSocket(socket.socket):
    def connect(self,*a,**k):raise AssertionError('network forbidden')
    def connect_ex(self,*a,**k):raise AssertionError('network forbidden')
socket.socket=OfflineSocket
socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
tool=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(tool,run_name='__main__')
'''
        result = self.cli(script=script)
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertTrue(result["integrity_accepted"])
        self.assertEqual(self.stage_result(self.stages(result)["continuation_apply"])["payload"]["graph"]["schema_version"],
            "b-graph-trial/0.4")

    def test_changed_adjacent_original_is_explicitly_rejected(self):
        original = self.adjacent_source_path.read_bytes()
        self.adjacent_source_path.write_bytes(original+b" ")
        result = self.cli(expected=1)
        self.assertEqual(result["pipeline_state"], "FAILED")
        self.assertFalse(result["integrity_accepted"])
        self.assertNotEqual(result.get("error", {}).get("stage"), "SETUP_FAILED")
        self.assert_hold(result)
        self.assertEqual(self.adjacent_source_path.read_bytes(), original+b" ")

    def test_exported_package_replays_with_only_copied_relative_inputs(self):
        exported_temp = tempfile.TemporaryDirectory()
        self.addCleanup(exported_temp.cleanup)
        exported = Path(exported_temp.name)/"inputs"
        original_root = self.root
        original_paths = list(original_root.rglob("*"))
        shutil.copytree(original_root, exported)
        for name in ("source_path", "context_path", "review_path", "evidence_path", "package_path", "adjacent_source_path"):
            setattr(self, name, exported/getattr(self, name).relative_to(original_root))
        self.workdir = exported/"pipeline"
        # Disable every original generated file to catch accidental absolute
        # paths or a reader resolving captures against an earlier package root.
        for path in original_paths:
            if path.is_file():
                path.write_bytes(b"unavailable original synthetic export input")
        result = self.cli()
        self.assertEqual(result["pipeline_state"], "READY")
        self.assertTrue(result["integrity_accepted"])
        self.assert_hold(result)

    def test_package_changed_after_apply_has_terminal_audit_and_explicit_resume(self):
        from annotation.recognition import pipeline
        publish = pipeline.batch._put_object
        changed = []
        def publish_then_change(workdir, value):
            output = publish(workdir, value)
            if value.get("kind") == "PipelineStageTrial" and value["payload"]["stage_id"] == "continuation_apply" and not changed:
                self.package_path.write_bytes(self.package_path.read_bytes()+b" ")
                changed.append(True)
            return output
        with patch("annotation.recognition.pipeline.batch._put_object", new=publish_then_change):
            result = execute(self.source_path, self.context_path, self.review_path, self.workdir,
                evidence_path=self.evidence_path, continuation_path=self.package_path,
                adjacent_source_path=self.adjacent_source_path)
        self.assertEqual(changed, [True])
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["pipeline_state"], "FAILED")
        self.assertFalse(result["integrity_accepted"])
        self.assertTrue(result["audit_performed"])
        self.assertTrue(self.report(result)["payload"]["run_error"])
        self.assertTrue((self.workdir / result["check"]["path"]).is_file())
        resumed = self.cli()
        self.assertEqual(resumed["pipeline_state"], "READY")
        self.assertTrue(self.stages(resumed)["evidence"]["cached"])
        self.assertFalse(self.stages(resumed)["continuation_prepare"]["cached"])

    def test_corrupt_apply_object_is_rejected_then_only_apply_and_latest_quality_recover(self):
        from annotation.recognition.pipeline_quality import audit_pipeline
        first = self.cli()
        before = self.stages(first)
        report = self.report(first)
        path = self.workdir / before["continuation_apply"]["output"]["path"]
        path.write_bytes(path.read_bytes()+b" ")
        audited = audit_pipeline(self.source_path, self.context_path, self.review_path, report, self.workdir,
            evidence_path=self.evidence_path, continuation_path=self.package_path,
            adjacent_source_path=self.adjacent_source_path)
        self.assertFalse(audited["payload"]["accepted"])
        second = self.cli()
        after = self.stages(second)
        for name in ("evidence", "assemble", "quality", "continuation_prepare", "continuation_proof"):
            self.assertTrue(after[name]["cached"], name)
        self.assertFalse(after["continuation_apply"]["cached"])
        self.assertFalse(after["continuation_quality"]["cached"])
        self.assertEqual(second["pipeline_state"], "READY")
        self.assert_hold(second)


if __name__ == "__main__":
    unittest.main()
