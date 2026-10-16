"""Portable CLI integration: resume, cache, corrupt outputs and fail-closed audit.

Only small generated images are processed. A fresh process forbids network
connections and OCR imports while running the default geometric CLI.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from annotation.recognition.baseline import digest
from run_batch_b import BatchCLIError, execute, main


def fake_report(*, complete=False, failed=0):
    payload = dict(counts=dict(declared=3, done=3 if complete else 1, pending=0 if complete else 2-failed,
        failed=failed, invalidated=0, cache_hits=0), batch_complete=complete, decision="HOLD",
        business_acceptance=False, transcription_verified=False, platform_actions=[],
        recognizer=dict(execution_kind="SYNTHETIC_TEST"))
    return dict(artifact_id="batch-report-fixture", revision=1, run_id="batch-run-fixture",
        content_hash=digest(payload), payload=payload)


def fake_check(accepted=True):
    payload = dict(accepted=accepted, decision="HOLD", business_acceptance=False,
        transcription_verified=False, platform_actions=[], issues=[] if accepted else
        [dict(code="INDEPENDENT_FIXTURE_FAULT", severity="ERROR")])
    return dict(schema_version="b-batch-check-trial/0.1", artifact_id="batch-check-fixture",
        revision=1, content_hash=digest(payload), payload=payload)


class FixedFailOnceWorker:
    """Declared synthetic backend; no model inference or engine dependency."""
    cache_identity = {"fixture": "cli-fixed-page/0.1", "fail_once_asset": "page-1"}

    def __init__(self):
        self.failed = False

    def __call__(self, source_path, *, use_ocr=False):
        source = json.loads(Path(source_path).read_text(encoding="utf-8"))
        asset = source["assets"][0]
        if asset["asset_id"] == "page-1" and not self.failed:
            self.failed = True
            raise RuntimeError("declared synthetic one-time worker failure")
        crop = asset["asset_id"] + "-fixed-crop"
        page = dict(asset_id=asset["asset_id"], source=asset,
            crop_transforms=[dict(crop_id=crop, asset_id=asset["asset_id"],
                original_bbox=[0, 0, asset["width"], asset["height"]],
                crop_to_original=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])],
            regions=[dict(region_id="synthetic-region-" + digest(source)[:24], asset_id=asset["asset_id"],
                bbox=[20, 20, asset["width"]-20, asset["height"]-20], crop_id=crop,
                role_candidate=None, content_type="unknown", confidence=None, text_hint="",
                text_hint_is_final_transcription=False, verification_status="UNVERIFIED")],
            ocr_lines=[], issues=[], coverage_evidence={"method": "SYNTHETIC_TEST"})
        payload = dict(pages=[page], quality_decision="NOT_EVALUATED", limitations=["SYNTHETIC_TEST"])
        return dict(schema_version="b-evidence-trial/0.1", kind="EvidenceBundleTrial",
            artifact_id="synthetic-page-" + digest(source)[:24], revision=1,
            book_id=source["book_id"], scope_id=source["scope_id"],
            input_refs=[dict(artifact_id=source["artifact_id"], content_hash=digest(source))],
            producer=dict(module="test_b_batch_cli.FixedFailOnceWorker", ocr_enabled=use_ocr),
            content_hash=digest(payload), payload=payload), {}


class BatchCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_dir = self.root / "source with spaces"
        self.source_dir.mkdir()
        self.workdir = self.root / "batch"
        assets = []
        for index in range(3):
            path = self.source_dir / f"page-{index}.png"
            image = Image.new("RGB", (700, 340), "white")
            draw = ImageDraw.Draw(image)
            for y in (30, 60, 90, 170, 200, 230):
                draw.rectangle((30 + index, y, 620 - index, y + 9), fill="black")
            image.save(path)
            assets.append(dict(asset_id=f"page-{index}", path=path.name, width=700, height=340,
                reading_order=index, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        self.manifest = dict(schema_version="b-source-trial/0.1", artifact_id="source-cli-fixture",
            book_id="fixture-book", scope_id="declared-three-pages", assets=assets)
        self.source = self.source_dir / "source.json"
        self.save_source()

    def save_source(self):
        self.source.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def cli(self, *extra, expected=0):
        completed = subprocess.run([sys.executable, str(ROOT / "tools/run_batch_b.py"),
            "--source", str(self.source), "--workdir", str(self.workdir), *extra],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)

    def report(self, result):
        matches = []
        for path in (self.workdir / "objects").glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                # Fault tests deliberately retain an old damaged cache file;
                # current report lookup must follow its independent reference.
                continue
            if value.get("artifact_id") == result["report_ref"]["artifact_id"]:
                matches.append(value)
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_partial_resume_and_repeated_cache_keep_full_declared_scope(self):
        partial = self.cli("--max-items", "1")
        self.assertEqual(partial["batch_state"], "PARTIAL")
        self.assertEqual(partial["counts"]["declared"], 3)
        self.assertEqual(partial["counts"]["done"], 1)
        self.assertEqual(partial["counts"]["pending"], 2)
        self.assertFalse(partial["batch_complete"])
        self.assertIsNone(self.report(partial)["payload"]["bundle"])
        first_check = (self.workdir / partial["check"]["path"]).read_bytes()
        resumed = self.cli()
        self.assertEqual(resumed["batch_state"], "READY")
        self.assertEqual(resumed["counts"]["done"], 3)
        self.assertEqual(resumed["counts"]["cache_hits"], 1)
        self.assertIsNotNone(self.report(resumed)["payload"]["bundle"])
        cached = self.cli()
        self.assertEqual(cached["counts"]["cache_hits"], 3)
        self.assertEqual(cached["decision"], "HOLD")
        self.assertTrue(cached["integrity_accepted"])
        self.assertFalse(cached["business_acceptance"])
        self.assertFalse(cached["transcription_verified"])
        self.assertEqual((self.workdir / partial["check"]["path"]).read_bytes(), first_check)
        self.assertEqual(len(list((self.workdir / "checks").glob("*.json"))), 3)

    def test_changed_single_asset_reuses_two_and_keeps_old_objects_immutable(self):
        before = self.cli()
        old_objects = {p.name: p.read_bytes() for p in (self.workdir / "objects").glob("*.json")}
        asset = self.manifest["assets"][1]
        path = self.source_dir / asset["path"]
        with Image.open(path) as image:
            image = image.convert("RGB")
        ImageDraw.Draw(image).rectangle((40, 270, 510, 279), fill="black")
        image.save(path)
        asset["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.save_source()
        after = self.cli()
        self.assertEqual(after["counts"]["cache_hits"], 2)
        self.assertEqual(after["counts"]["done"], 3)
        self.assertNotEqual(before["report_ref"], after["report_ref"])
        first, second = self.report(before), self.report(after)
        keys1 = {i["asset_id"]: i["item_key"] for i in first["payload"]["items"]}
        keys2 = {i["asset_id"]: i["item_key"] for i in second["payload"]["items"]}
        self.assertEqual([aid for aid in keys1 if keys1[aid] != keys2[aid]], ["page-1"])
        for name, original in old_objects.items():
            self.assertEqual((self.workdir / "objects" / name).read_bytes(), original)

    def test_corrupt_cached_object_is_not_silently_reused(self):
        before = self.cli()
        old = self.report(before)
        artifact = old["payload"]["items"][1]["artifact"]
        path = self.workdir / artifact["path"]
        path.write_bytes(b"corrupt-cache-fixture")
        after = self.cli()
        self.assertEqual(after["counts"]["cache_hits"], 2)
        self.assertEqual(after["counts"]["invalidated"], 1)
        self.assertTrue(after["integrity_accepted"])
        self.assertEqual(after["batch_state"], "READY")
        current = self.report(after)["payload"]["items"][1]
        self.assertEqual(current["attempt_count"], 2)
        self.assertNotEqual(current["artifact"], artifact)

    def test_changed_source_without_manifest_hash_is_explicit_failure(self):
        self.cli("--max-items", "1")
        path = self.source_dir / self.manifest["assets"][2]["path"]
        Image.new("RGB", (700, 340), "white").save(path)
        result = self.cli(expected=1)
        self.assertEqual(result["batch_state"], "FAILED")
        self.assertFalse(result["integrity_accepted"])
        self.assertFalse(result["audit_performed"])
        self.assertEqual(result["error"]["stage"], "RUN_FAILED")
        self.assertEqual(result["decision"], "HOLD")

    def test_forged_report_reference_and_coordinated_finish_event_are_rejected(self):
        from annotation.recognition.batch_quality import audit_batch
        result = self.cli()
        report = self.report(result)
        forged = json.loads(json.dumps(report))
        forged["artifact_id"] = "batch-report-fabricated-reference"
        check = audit_batch(self.source, self.workdir, forged)
        self.assertFalse(check["payload"]["accepted"])
        # Repair the caller-editable SQL reference too. The immutable report
        # object remains the independent source, so this still must fail.
        with contextlib.closing(sqlite3.connect(self.workdir / "batch.sqlite3")) as connection:
            with connection:
                for event_id, details_text in connection.execute(
                        "SELECT event_id,details_json FROM events WHERE event_type='RUN_FINISHED'"):
                    details = json.loads(details_text)
                    if details["run_id"] == forged["run_id"]:
                        details["report_ref"] = {key: forged[key] for key in ("artifact_id", "revision", "content_hash")}
                        connection.execute("UPDATE events SET details_json=? WHERE event_id=?",
                            (json.dumps(details), event_id))
        check = audit_batch(self.source, self.workdir, forged)
        self.assertFalse(check["payload"]["accepted"])
        self.assertIn("BATCH_REPORT_RECEIPT_MISMATCH", [i["code"] for i in check["payload"]["issues"]])

    def test_default_cli_fresh_process_forbids_ocr_imports_and_network(self):
        script = r'''
import importlib.abc, json, runpy, socket, sys
class DenyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'rapidocr_onnxruntime','onnxruntime','torch','paddle','paddleocr','requests','httpx','aiohttp'}:
            raise AssertionError('forbidden default import: '+fullname)
sys.meta_path.insert(0,DenyImports())
class NoNetworkSocket(socket.socket):
    def connect(self,*args,**kwargs): raise AssertionError('network connect forbidden')
    def connect_ex(self,*args,**kwargs): raise AssertionError('network connect_ex forbidden')
socket.socket=NoNetworkSocket
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network connection forbidden'))
tool, source, workdir=sys.argv[1:]
sys.argv=[tool,'--source',source,'--workdir',workdir]
runpy.run_path(tool,run_name='__main__')
'''
        completed = subprocess.run([sys.executable, "-c", script, str(ROOT / "tools/run_batch_b.py"),
            str(self.source), str(self.workdir)], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["recognition_mode"], "GEOMETRIC")
        report = self.report(result)
        self.assertEqual(report["payload"]["recognizer"]["execution_kind"], "BASELINE_GEOMETRY")
        self.assertFalse(report["payload"]["recognizer"]["use_ocr"])

    def test_network_urls_and_shares_are_rejected_before_runner(self):
        for value in ("https://example.invalid/source.json", "file:///tmp/source.json", "//server/share/source.json", r"\\server\share\source.json"):
            with self.subTest(value=value), patch("run_batch_b.execute") as runner, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(["--source", value, "--workdir", str(self.workdir)])
                self.assertEqual(cm.exception.code, 2)
                runner.assert_not_called()

    def test_invalid_worker_limit_is_rejected_before_runner(self):
        for value in ("0", "-1", "1.5"):
            with self.subTest(value=value), patch("run_batch_b.execute") as runner, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(["--source", str(self.source), "--workdir", str(self.workdir), "--max-items", value])
                self.assertEqual(cm.exception.code, 2)
                runner.assert_not_called()

    def test_ocr_is_only_forwarded_when_explicitly_requested(self):
        for args, expected in (([], False), (["--ocr"], True)):
            with self.subTest(args=args), patch("run_batch_b.execute", return_value={"exit_code": 0}) as runner, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--source", str(self.source), "--workdir", str(self.workdir), *args]), 0)
                self.assertIs(runner.call_args.kwargs["use_ocr"], expected)

    def test_independent_rejection_is_persisted_and_returns_failure(self):
        report, check = fake_report(complete=True), fake_check(False)
        seen = []
        def runner(source, workdir, **kwargs):
            seen.append((source, workdir, kwargs))
            return report
        def auditor(source, workdir, actual):
            self.assertIs(actual, report)
            seen.append("audited")
            return check
        result = execute(self.source, self.workdir, max_items=2, runner=runner, auditor=auditor)
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["integrity_accepted"])
        self.assertEqual(result["issues"], check["payload"]["issues"])
        self.assertEqual(seen[0][2], dict(use_ocr=False, max_items=2))
        self.assertEqual(seen[-1], "audited")
        self.assertEqual(json.loads((self.workdir / result["check"]["path"]).read_text(encoding="utf-8")), check)

    def test_recorded_worker_failure_is_audited_but_not_execution_success(self):
        report, check = fake_report(failed=1), fake_check()
        result = execute(self.source, self.workdir, runner=lambda *a, **k: report,
            auditor=lambda *a: check)
        self.assertTrue(result["audit_performed"])
        self.assertTrue(result["integrity_accepted"])
        self.assertEqual(result["batch_state"], "FAILED")
        self.assertEqual(result["exit_code"], 1)

    def test_real_journal_fixed_worker_failure_and_retry_stays_synthetic(self):
        from annotation.recognition.batch import run_batch
        worker = FixedFailOnceWorker()
        def runner(source, workdir, **kwargs):
            return run_batch(source, workdir, worker=worker, **kwargs)
        failed = execute(self.source, self.workdir, runner=runner)
        self.assertEqual(failed["batch_state"], "FAILED")
        self.assertEqual(failed["counts"]["failed"], 1)
        self.assertEqual(failed["exit_code"], 1)
        self.assertTrue(failed["integrity_accepted"])
        self.assertEqual(failed["execution_kind"], "SYNTHETIC_TEST")
        self.assertIsNone(self.report(failed)["payload"]["bundle"])
        resumed = execute(self.source, self.workdir, runner=runner)
        self.assertEqual(resumed["batch_state"], "READY")
        self.assertEqual(resumed["counts"]["cache_hits"], 2)
        self.assertEqual(resumed["counts"]["failed"], 0)
        self.assertEqual(resumed["execution_kind"], "SYNTHETIC_TEST")
        self.assertEqual(resumed["decision"], "HOLD")
        item = self.report(resumed)["payload"]["items"][1]
        self.assertEqual(item["attempt_count"], 2)

    def test_auditor_cannot_promote_business_or_transcription_status(self):
        for field in ("business_acceptance", "transcription_verified"):
            with self.subTest(field=field):
                report, check = fake_report(), fake_check()
                check["payload"][field] = True
                with self.assertRaises(BatchCLIError) as cm:
                    execute(self.source, self.workdir, runner=lambda *a, **k: report, auditor=lambda *a: check)
                self.assertEqual(cm.exception.stage, "AUDIT_FAILED")
                self.assertFalse((self.workdir / "checks").exists())

    def test_malformed_rejected_report_does_not_escape_as_unhandled_keyerror(self):
        report = fake_report()
        report["payload"].pop("counts")
        with self.assertRaises(BatchCLIError) as cm:
            execute(self.source, self.workdir, runner=lambda *a, **k: report,
                auditor=lambda *a: fake_check(False))
        self.assertEqual(cm.exception.stage, "AUDIT_FAILED")

    def test_immutable_check_conflict_is_not_overwritten(self):
        report, check = fake_report(), fake_check()
        kwargs = dict(runner=lambda *a, **k: report, auditor=lambda *a: check)
        first = execute(self.source, self.workdir, **kwargs)
        path = self.workdir / first["check"]["path"]
        original = path.read_bytes()
        # Idempotent same bytes are allowed; different review cannot replace
        # an existing run receipt under its original path.
        self.assertEqual(execute(self.source, self.workdir, **kwargs)["check"], first["check"])
        check["payload"]["accepted"] = False
        with self.assertRaises(BatchCLIError) as cm:
            execute(self.source, self.workdir, **kwargs)
        self.assertEqual(cm.exception.stage, "RECEIPT_FAILED")
        self.assertEqual(path.read_bytes(), original)

    def test_failure_has_explicit_hold_json_on_stdout(self):
        for stage in ("RUN_FAILED", "AUDIT_FAILED", "RECEIPT_FAILED"):
            with self.subTest(stage=stage), patch("run_batch_b.execute", side_effect=BatchCLIError(stage, ValueError("fixture failure"))):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["--source", str(self.source), "--workdir", str(self.workdir)])
                result = json.loads(output.getvalue())
                self.assertEqual(code, 1)
                self.assertEqual(result["decision"], "HOLD")
                self.assertFalse(result["integrity_accepted"])
                self.assertFalse(result["business_acceptance"])
                self.assertEqual(result["error"]["stage"], stage)


if __name__ == "__main__":
    unittest.main()
