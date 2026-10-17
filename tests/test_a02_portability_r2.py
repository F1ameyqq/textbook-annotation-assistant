"""Bounded R2 identity tests; true noGit children and separately labelled call fault simulations."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "examples/a02/R1/identity.py"
PROBE = ROOT / "examples/a02/portability-R2/probe.py"
HEAD = "abcdef0123456789abcdef0123456789abcdef0123"


def load_identity(path=IDENTITY):
    spec = importlib.util.spec_from_file_location("a02_portability_r2_identity", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A02PortabilityR2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raw = Path(self.temp.name) / "raw export no Git"
        self.raw.mkdir()
        self.identity_path = self.raw / "identity.py"
        self.identity_path.write_bytes(IDENTITY.read_bytes())
        self.empty_path = Path(self.temp.name) / "no executable tools"
        self.empty_path.mkdir()
        self.identity = load_identity(self.identity_path)

    def assert_unknown(self, result):
        self.assertIsNone(result["checkout_commit"])
        self.assertIn("unknown", result["status"])
        self.assertNotIn("verified", result["status"])

    def child(self, operation):
        env = dict(os.environ, PATH=str(self.empty_path), PYTHONDONTWRITEBYTECODE="1")
        self.assertIsNone(shutil.which("git", path=env["PATH"]))
        args = [sys.executable, "-B", str(PROBE), "--identity-file", str(self.identity_path),
                "--source-root", str(self.raw), "--operation", operation]
        if operation == "binding":
            args += ["--declared-commit", HEAD, "--identity-repo", str(self.raw)]
        result = subprocess.run(args, cwd=self.raw, env=env, capture_output=True, text=True)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        environment = events[0]
        self.assertEqual(environment["event"], "environment")
        self.assertIsNone(environment["git_executable"])
        self.assertFalse(environment["has_dot_git"])
        self.assertEqual(Path(environment["identity_import"]).resolve(), self.identity_path.resolve())
        self.assertEqual(environment["identity_sha256"], hashlib.sha256(IDENTITY.read_bytes()).hexdigest())
        return result, events

    def test_actual_raw_child_without_git_returns_unknown(self):
        result, events = self.child("identity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_unknown(events[-1]["result"])

    def test_actual_no_git_binding_exits_nonzero_without_success_result(self):
        result, events = self.child("binding")
        self.assertEqual(result.returncode, 1)
        self.assertIn("identity repository must be an actual Git top-level", result.stderr)
        self.assertFalse(any(e["event"] == "result" for e in events))

    def test_simulated_initial_spawn_missing_or_denied_returns_unknown(self):
        for error in (FileNotFoundError("git missing"), PermissionError("git execution denied")):
            with self.subTest(error=type(error).__name__), patch.object(self.identity.subprocess, "run", side_effect=error), \
                    patch.object(self.identity.subprocess, "check_output") as head:
                self.assert_unknown(self.identity.git_identity(self.raw))
                head.assert_not_called()

    def test_simulated_verified_toplevel_then_second_spawn_missing_is_unknown(self):
        result = subprocess.CompletedProcess([], 0, stdout=str(self.raw.resolve()))
        with patch.object(self.identity.subprocess, "run", return_value=result) as top, \
                patch.object(self.identity.subprocess, "check_output", side_effect=FileNotFoundError("git removed between calls")) as head:
            self.assert_unknown(self.identity.git_identity(self.raw))
            self.assertEqual(top.call_count, 1)
            self.assertEqual(head.call_count, 1)

    def test_simulated_second_call_nonzero_or_denied_is_unknown(self):
        for error in (subprocess.CalledProcessError(128, ["git", "rev-parse", "HEAD"]), PermissionError("HEAD unavailable")):
            with self.subTest(error=type(error).__name__), \
                    patch.object(self.identity.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=str(self.raw.resolve()))), \
                    patch.object(self.identity.subprocess, "check_output", side_effect=error):
                self.assert_unknown(self.identity.git_identity(self.raw))

    def test_simulated_valid_top_and_head_keep_existing_verified_result(self):
        with patch.object(self.identity.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=str(self.raw.resolve()))) as top, \
                patch.object(self.identity.subprocess, "check_output", return_value=HEAD + "\n") as head:
            result = self.identity.git_identity(self.raw)
            self.assertEqual(result["checkout_commit"], HEAD)
            self.assertEqual(result["status"], "source Git top-level verified")
            self.assertEqual(top.call_args.args[0], ["git", "rev-parse", "--show-toplevel"])
            self.assertEqual(head.call_args.args[0], ["git", "rev-parse", "HEAD"])

    def test_simulated_parent_toplevel_or_nonzero_never_requests_head(self):
        for returned in (subprocess.CompletedProcess([], 0, stdout=str(self.raw.parent)), subprocess.CompletedProcess([], 128, stdout="")):
            with self.subTest(result=returned), patch.object(self.identity.subprocess, "run", return_value=returned), \
                    patch.object(self.identity.subprocess, "check_output") as head:
                self.assert_unknown(self.identity.git_identity(self.raw))
                head.assert_not_called()

    def test_simulated_empty_head_is_not_verified(self):
        with patch.object(self.identity.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=str(self.raw.resolve()))), \
                patch.object(self.identity.subprocess, "check_output", return_value="\n"):
            self.assert_unknown(self.identity.git_identity(self.raw))

    def test_binding_still_propagates_blob_command_failure(self):
        with patch.object(self.identity, "git_identity", return_value={"checkout_commit": HEAD}), \
                patch.object(self.identity.subprocess, "check_output", side_effect=FileNotFoundError("Git disappeared after identity")):
            with self.assertRaises(FileNotFoundError):
                self.identity.source_binding(self.raw, HEAD, self.raw)

    def test_binding_still_rejects_different_raw_source_bytes(self):
        source = self.raw / "src/annotation/__init__.py"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"changed source\n")
        with patch.object(self.identity, "git_identity", return_value={"checkout_commit": HEAD}), \
                patch.object(self.identity.subprocess, "check_output", side_effect=["src/annotation/__init__.py\n", b"expected source\n"]):
            with self.assertRaisesRegex(AssertionError, "source differs from declared raw Git blob"):
                self.identity.source_binding(self.raw, HEAD, self.raw)


if __name__ == "__main__":
    unittest.main()
