"""Task-local A04 entry tests: SYNTHETIC offline packages and mocked live entry.

The observed-provenance branch is tested with a mock, not relabelled synthetic
pixels or a claimed platform observation. No browser, profile or network runs.
"""
import copy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from annotation.contracts import load_bundle
from annotation.source.usense import cli
from annotation.source.usense.collector import sanitized_capture


REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "a04" / "source"


class OfflineEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="a04 CLI space ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "input package with spaces"
        shutil.copytree(FIXTURE, self.input)
        self.output = self.root / "output package with spaces"
        self.capture = json.loads((self.input / "capture.json").read_text(encoding="utf-8"))

    def save_capture(self):
        (self.input / "capture.json").write_text(json.dumps(self.capture), encoding="utf-8")

    def invoke(self, *, as_of=True):
        args = ["offline", "--input", str(self.input), "--output", str(self.output)]
        if as_of:
            args += ["--as-of", self.capture["observed_at"]]
        stream = io.StringIO()
        with mock.patch.object(cli, "collect_live", side_effect=AssertionError("offline must not collect")) as live, \
                mock.patch("annotation.source.usense.collector.HeadlessSession", side_effect=AssertionError("offline must not start a session")) as session, \
                redirect_stdout(stream):
            result = cli.main(args)
        live.assert_not_called()
        session.assert_not_called()
        return result, stream.getvalue()

    def test_public_module_offline_command_and_relocation_with_spaces(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(REPO / "src")
        result = subprocess.run([sys.executable, "-m", "annotation.source.usense", "offline",
                                 "--input", str(self.input), "--output", str(self.output),
                                 "--as-of", self.capture["observed_at"]],
                                cwd=self.root, env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ACCEPTANCE_NOT_ASSERTED", result.stdout)
        moved = self.root / "relocated evidence package with spaces"
        shutil.move(str(self.output), str(moved))
        bundle = load_bundle(moved / "bundle.json")
        self.assertEqual({a.kind for a in bundle.artifacts}, {"SourceBundle", "PlatformSnapshot"})
        source = next(a for a in bundle.artifacts if a.kind == "SourceBundle")
        self.assertEqual(len(source.payload.pages_acquired), 3)
        self.assertEqual(source.payload.metadata_page_count, 214)
        entry = json.loads((moved / "evidence/entry-result.json").read_text(encoding="utf-8"))
        self.assertFalse(entry["network_used"])
        self.assertEqual(entry["acceptance"], "NOT_ASSERTED")
        self.assertNotIn(str(self.root), (moved / "bundle.json").read_text(encoding="utf-8"))

    def test_offline_output_remains_synthetic_and_does_not_collect(self):
        result, message = self.invoke()
        self.assertEqual(result, 0, message)
        output_capture = json.loads((self.output / "capture.json").read_text(encoding="utf-8"))
        self.assertEqual((output_capture["evidence_mode"], output_capture["provenance"]), ("SYNTHETIC", "SYNTHETIC"))
        bundle = load_bundle(self.output / "bundle.json")
        self.assertTrue(all(a.producer.evidence_mode == "SYNTHETIC" for a in bundle.artifacts))

    def test_unknown_sensitive_input_fields_never_written(self):
        secret = "SYNTHETIC-SECRET-MUST-NOT-SURVIVE"
        self.capture["token"] = secret
        self.capture["cookie"] = secret
        self.capture["request_headers"] = {"Authorization": secret}
        self.capture["book"]["password"] = secret
        self.capture["source_metadata"]["data"]["raw_url"] = secret
        self.capture["directory"]["data"]["directory_data"][0]["authorization"] = secret
        self.capture["annotations"]["data"][0]["image_path"] = "https://invalid.test/?token=" + secret
        self.capture["pages"][0]["mapping_evidence"]["headers"] = secret
        self.capture["pages"][0]["source_response"]["data"]["pages"][0]["access_token"] = secret
        self.save_capture()
        result, message = self.invoke()
        self.assertEqual(result, 0, message)
        self.assertNotIn(secret, message)
        for path in self.output.rglob("*.json"):
            self.assertNotIn(secret, path.read_text(encoding="utf-8"), path.name)

    def test_stale_default_clock_refuses_before_any_output(self):
        self.capture["observed_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.save_capture()
        result, message = self.invoke(as_of=False)
        self.assertEqual(result, 2)
        self.assertEqual(message.strip(), "A04_FAILED:STALE_CAPTURE")
        self.assertFalse(self.output.exists())

    def test_incomplete_capture_refuses_before_output(self):
        self.capture["complete"] = False
        self.save_capture()
        result, message = self.invoke()
        self.assertEqual(result, 2)
        self.assertIn("INCOMPLETE_RESPONSE", message)
        self.assertFalse(self.output.exists())

    def test_wrong_book_cannot_be_overridden_or_silently_changed(self):
        self.capture["book"]["id"] = "46006966"
        self.save_capture()
        result, message = self.invoke()
        self.assertEqual(result, 2)
        self.assertIn("TARGET_MISMATCH", message)
        self.assertFalse(self.output.exists())

    def test_missing_page_scope_is_not_silently_shrunk(self):
        self.capture["pages"].pop()
        self.save_capture()
        result, message = self.invoke()
        self.assertEqual(result, 2)
        self.assertIn("SOURCE_MISSING", message)
        self.assertFalse(self.output.exists())

    def test_extra_page_scope_is_not_silently_expanded(self):
        extra = copy.deepcopy(self.capture["pages"][0])
        extra["viewer_page"] = 16
        self.capture["pages"].append(extra)
        self.save_capture()
        result, message = self.invoke()
        self.assertEqual(result, 2)
        self.assertIn("INVALID_SCOPE", message)
        self.assertFalse(self.output.exists())

    def test_existing_output_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "previous-evidence.txt"
        sentinel.write_text("immutable previous output", encoding="utf-8")
        result, message = self.invoke()
        self.assertEqual(result, 2)
        self.assertIn("OUTPUT_EXISTS", message)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "immutable previous output")

    def test_explicit_observed_replay_relabels_before_save_and_build_using_mock(self):
        # This is a synthetic control-flow fault injection, never a source bundle
        # claiming that these fixture pixels are observed platform originals.
        claimed = copy.deepcopy(self.capture)
        claimed.update(evidence_mode="OBSERVED", provenance="LIVE")
        recorded, built = [], []
        def record_save(path, data):
            recorded.append((Path(path).name, copy.deepcopy(data)))
        def record_build(capture, root, **kwargs):
            built.append(copy.deepcopy(capture))
            return SimpleNamespace(artifacts=[object(), object()])
        with mock.patch.object(cli, "parse_capture", return_value=SimpleNamespace(pages=[])), \
                mock.patch.object(cli.json, "loads", return_value=claimed), \
                mock.patch.object(cli, "save_json", side_effect=record_save), \
                mock.patch.object(cli, "build_exchange", side_effect=record_build):
            result, message = self.invoke()
        self.assertEqual(result, 0, message)
        exported = next(data for name, data in recorded if name == "capture.json")
        self.assertEqual(exported["provenance"], "HISTORICAL")
        self.assertEqual(built[0]["provenance"], "HISTORICAL")
        self.assertEqual(exported["observed_at"], self.capture["observed_at"])
        self.assertFalse(next(data for name, data in recorded if name == "entry-result.json")["network_used"])
        self.assertFalse((self.output / "bundle.json").exists())

    def test_sanitized_capture_does_not_promote_incomplete_or_historical(self):
        capture = copy.deepcopy(self.capture)
        capture.update(evidence_mode="OBSERVED", provenance="HISTORICAL", complete=False)
        safe = sanitized_capture(capture)
        self.assertFalse(safe["complete"])
        self.assertEqual(safe["provenance"], "HISTORICAL")
        self.assertEqual(safe["observed_at"], capture["observed_at"])


class MockedLiveEntryTests(unittest.TestCase):
    def test_reservation_gate_and_explicit_tls_option_without_session(self):
        with tempfile.TemporaryDirectory(prefix="a04 mock live ") as temporary:
            root = Path(temporary)
            state_path = root / "coordination-state.json"
            state = {"platform_session": {"book_id": "46006966", "reservation_task": "A04", "reservation_stage": "execution"}}
            state_path.write_text(json.dumps(state), encoding="utf-8")
            args = ["live", "--login-root", str(root / "never read login"),
                    "--output", str(root / "never create output"), "--coordination-state", str(state_path)]
            stream = io.StringIO()
            with mock.patch.object(cli, "collect_live") as collect, redirect_stdout(stream):
                self.assertEqual(cli.main(args), 2)
            collect.assert_not_called()
            self.assertIn("PROFILE_IN_USE", stream.getvalue())
            state["platform_session"]["book_id"] = "46007447"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            for flags, tls_opt_in in (([], False), (["--ignore-https-errors"], True)):
                with self.subTest(tls_opt_in=tls_opt_in):
                    stream = io.StringIO()
                    with mock.patch.object(cli, "collect_live", side_effect=RuntimeError("SYNTHETIC-secret-error")) as collect, \
                            redirect_stdout(stream):
                        self.assertEqual(cli.main(args + flags), 2)
                    self.assertEqual(collect.call_args.kwargs["ignore_https_errors"], tls_opt_in)
                    self.assertEqual(stream.getvalue().strip(), "A04_FAILED:A04_FAILED")
                    self.assertFalse((root / "never create output").exists())
            state["platform_session"]["reservation_stage"] = "review"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with mock.patch.object(cli, "collect_live", side_effect=RuntimeError("SYNTHETIC-secret-error")) as collect, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(args), 2)
            collect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
