"""A27 R1: Windows directory aliases through the actual recovery entry; offline."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a27_r1_fixtures", ROOT / "tests/test_a27_stability.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
recovery, BindingError, raw = fixtures.recovery, fixtures.BindingError, fixtures.raw


def observer(commandline):
    rows = [{"ProcessId": 54321, "CreationDate": "synthetic-only", "CommandLine": commandline}]
    process = Mock(return_value=SimpleNamespace(returncode=0, stdout=raw(rows)))
    return lambda profile: recovery.exclusive_profile(profile, run=process)


class ProfileEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("A27_OUTPUT"))
        self.root = Path(self.tmp.name)
        self.bundle = fixtures.SyntheticBundle(self.root)
        self.bundle.calls, self.bundle.after_configure, self.bundle.fail_reader = [], None, False

    def tearDown(self):
        self.tmp.cleanup()

    def test_dot_segment_blocks_actual_recovery_before_configure_or_capture(self):
        args = self.bundle.request()
        profile = self.bundle.profile
        alias = str(profile.parent) + "\\.\\" + profile.name
        observed = observer('"C:\\synthetic\\msedge.exe" --user-data-dir="' + alias + '"')
        code = None
        result = None
        try:
            result = recovery.execute(*args, run_child=self.bundle.child, observe=observed)
        except BindingError as exc:
            code = exc.code
        print(json.dumps({"case": "dot_segment_actual_entry", "error_code": code,
                          "dispatched": self.bundle.calls, "returned_status": None if result is None else result["status"]}))
        self.assertEqual(code, "RECOVERY_PROFILE_IN_USE")
        self.assertEqual(self.bundle.calls, [])
        self.assertFalse((self.root / "recovery-out").exists())
        self.assertEqual(list(self.root.glob("*.spent.json")), [])

    def test_equivalent_absolute_directory_forms_are_occupied(self):
        p = self.bundle.profile
        forms = [str(p), str(p.parent) + "\\.\\" + p.name, str(p) + "\\.",
                 str(p.parent) + "\\unused-component\\..\\" + p.name,
                 str(p).replace("\\", "/"), str(p).upper(), str(p) + "\\",
                 "\\\\?\\" + str(p)]
        for alias in forms:
            with self.subTest(alias=alias):
                with self.assertRaisesRegex(BindingError, "RECOVERY_PROFILE_IN_USE"):
                    observer(subprocess.list2cmdline(["msedge.exe", "--user-data-dir=" + alias]))(p)

    def test_windows_quoting_and_separate_switch_value_with_spaces(self):
        profile = self.root / "Synthetic Profile With Spaces"
        profile.mkdir()
        alias = str(profile.parent) + "\\.\\" + profile.name
        for commandline in ['"C:\\Program Files\\Edge\\msedge.exe" --user-data-dir="' + alias + '"',
                            'msedge.exe --user-data-dir "' + alias + '"',
                            'msedge.exe "--user-data-dir=' + alias + '"']:
            with self.subTest(commandline=commandline):
                with self.assertRaisesRegex(BindingError, "RECOVERY_PROFILE_IN_USE"):
                    observer(commandline)(profile)

    def test_distinct_existing_profile_with_same_prefix_is_not_occupied(self):
        other = self.bundle.profile.with_name(self.bundle.profile.name + "-other")
        other.mkdir()
        result = observer('msedge.exe --user-data-dir="' + str(other) + '"')(self.bundle.profile)
        self.assertEqual(result["matching_profile_processes"], 0)

    def test_ambiguous_missing_relative_or_unreadable_profile_arguments_fail_closed(self):
        for commandline in ['msedge.exe --user-data-dir', 'msedge.exe --user-data-dir=',
                            'msedge.exe --user-data-dir=relative-profile',
                            'msedge.exe --user-data-dir=C:relative-profile',
                            'msedge.exe --user-data-dir=\\\\unresolved-server\\share\\profile',
                            'msedge.exe --user-data-dir="' + str(self.root / "missing") + '"',
                            'msedge.exe --user-data-dir="' + str(self.bundle.profile) + '" --user-data-dir="' + str(self.root) + '"']:
            with self.subTest(commandline=commandline):
                with self.assertRaises(BindingError): observer(commandline)(self.bundle.profile)

    def test_equivalent_profile_appearing_at_second_gate_blocks_capture(self):
        args = self.bundle.request()
        p = self.bundle.profile
        occupied = observer('msedge.exe --user-data-dir="' + str(p.parent) + "\\.\\" + p.name + '"')
        observations = []
        def observe(profile):
            observations.append(profile)
            return {"synthetic": True} if len(observations) == 1 else occupied(profile)
        result = recovery.execute(*args, run_child=self.bundle.child, observe=observe)
        self.assertEqual(result["status"], "STOPPED_NO_RETRY")
        self.assertEqual(result["error_code"], "RECOVERY_PROFILE_IN_USE")
        self.assertEqual(self.bundle.calls, ["configure"])
        self.assertEqual(len(list(self.root.glob("*.spent.json"))), 1)

    def test_no_edge_processes_still_allows_existing_configure_capture_path(self):
        args = self.bundle.request()
        process = Mock(return_value=SimpleNamespace(returncode=0, stdout=b"[]"))
        result = recovery.execute(*args, run_child=self.bundle.child,
                                  observe=lambda p: recovery.exclusive_profile(p, run=process))
        self.assertEqual(result["status"], "READBACK_MATCHED_AFTER_OS_RELEASE", result)
        self.assertEqual(self.bundle.calls, ["configure", "capture"])

    def test_unreadable_edge_commandline_remains_fail_closed(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                with self.assertRaisesRegex(BindingError, "RECOVERY_PROCESS_IDENTITY_UNKNOWN"):
                    observer(value)(self.bundle.profile)


if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=True)
