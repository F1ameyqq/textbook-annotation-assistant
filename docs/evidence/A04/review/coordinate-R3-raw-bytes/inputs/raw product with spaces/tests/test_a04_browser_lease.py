"""Offline profile lifecycle failure injection, using only temporary profiles."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from annotation.runtime.browser.guard import BrowserSafetyError
from annotation.runtime.browser.lease import CHROMIUM_LOCKS, LEASE_NAME, ProfileLease
from annotation.runtime.browser.lease import windows_profile_process_count


class ProfileLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a04 lease offline ")
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name) / "dedicated profile"
        self.profile.mkdir()

    def lease(self, checker=lambda _: 0):
        return ProfileLease(self.profile, process_checker=checker)

    def test_normal_acquire_release_and_reacquire_reports_counts_only(self):
        lease = self.lease().acquire()
        report = lease.report()
        self.assertTrue(lease.held)
        self.assertTrue(report["acquired"])
        self.assertTrue(report["owned_lease_present"])
        self.assertEqual({"process_count": 0, "chromium_lock_count": 0,
                          "lease_present": False}, report["pre"])
        self.assertNotIn(str(self.profile), json.dumps(report))
        self.assertTrue(lease.release()["released"])
        self.assertFalse(lease.held)
        self.assertFalse((self.profile / LEASE_NAME).exists())
        lease.acquire()
        self.assertTrue(lease.release()["released"])

    def test_competing_a04_lease_is_never_removed(self):
        first = self.lease().acquire()
        self.addCleanup(first.release)
        content = (self.profile / LEASE_NAME).read_bytes()
        with self.assertRaises(BrowserSafetyError) as error:
            self.lease().acquire()
        self.assertEqual("PROFILE_LEASE_CONFLICT", error.exception.code)
        self.assertEqual(content, (self.profile / LEASE_NAME).read_bytes())

    def test_existing_process_is_conflict_without_creating_lease(self):
        with self.assertRaises(BrowserSafetyError) as error:
            self.lease(lambda _: 2).acquire()
        self.assertEqual("PROFILE_IN_USE", error.exception.code)
        self.assertFalse((self.profile / LEASE_NAME).exists())
        self.assertNotIn(str(self.profile), str(error.exception))

    def test_all_chromium_lock_names_preserved(self):
        for name in CHROMIUM_LOCKS:
            with self.subTest(name=name):
                lock = self.profile / name
                lock.write_text("foreign marker")
                with self.assertRaises(BrowserSafetyError) as error:
                    self.lease().acquire()
                self.assertEqual("PROFILE_LOCK_CONFLICT", error.exception.code)
                self.assertEqual("foreign marker", lock.read_text())
                self.assertFalse((self.profile / LEASE_NAME).exists())
                lock.unlink()  # Test-created marker only, never a real profile.

    def test_process_race_after_atomic_acquire_cleans_only_owned_lease(self):
        observations = iter((0, 1, 1))
        lease = self.lease(lambda _: next(observations))
        with self.assertRaises(BrowserSafetyError) as error:
            lease.acquire()
        self.assertEqual("PROFILE_IN_USE", error.exception.code)
        self.assertFalse((self.profile / LEASE_NAME).exists())
        self.assertFalse(lease.held)
        self.assertFalse(lease.report()["released"])
        self.assertEqual(1, lease.report()["post"]["process_count"])
        self.lease().acquire().release()

    def test_lock_race_after_atomic_acquire_preserves_foreign_lock(self):
        counter = [0]
        lock = self.profile / CHROMIUM_LOCKS[0]
        def checker(_):
            counter[0] += 1
            if counter[0] == 2:
                lock.write_text("foreign")
            return 0
        with self.assertRaises(BrowserSafetyError) as error:
            self.lease(checker).acquire()
        self.assertEqual("PROFILE_LOCK_CONFLICT", error.exception.code)
        self.assertEqual("foreign", lock.read_text())
        self.assertFalse((self.profile / LEASE_NAME).exists())

    def test_body_failure_releases_and_next_session_can_acquire(self):
        lease = self.lease()
        with self.assertRaisesRegex(RuntimeError, "injected offline failure"):
            with lease:
                raise RuntimeError("injected offline failure")
        self.assertTrue(lease.report()["released"])
        with self.lease():
            pass

    def test_process_checker_failures_are_sanitized(self):
        def checker(_):
            raise RuntimeError("secret profile and command line")
        with self.assertRaises(BrowserSafetyError) as error:
            self.lease(checker).acquire()
        self.assertEqual("PROCESS_CHECK_FAILED:process_check", str(error.exception))
        self.assertFalse((self.profile / LEASE_NAME).exists())

    def test_checker_failure_after_lease_creation_cleans_for_next_acquire(self):
        count = [0]
        def checker(_):
            count[0] += 1
            if count[0] == 2:
                raise RuntimeError("secret")
            return 0
        with self.assertRaises(BrowserSafetyError) as error:
            self.lease(checker).acquire()
        self.assertEqual("PROCESS_CHECK_FAILED", error.exception.code)
        self.assertFalse((self.profile / LEASE_NAME).exists())
        self.lease().acquire().release()

    def test_partial_lease_write_failure_cleans_created_file(self):
        with patch("annotation.runtime.browser.lease.os.fsync", side_effect=OSError("secret")):
            with self.assertRaises(BrowserSafetyError) as error:
                self.lease().acquire()
        self.assertEqual("LEASE_WRITE_FAILED:acquire", str(error.exception))
        self.assertFalse((self.profile / LEASE_NAME).exists())
        self.lease().acquire().release()

    def test_release_does_not_delete_replaced_foreign_lease(self):
        lease = self.lease().acquire()
        marker = self.profile / LEASE_NAME
        marker.write_text("foreign replacement")
        with self.assertRaises(BrowserSafetyError) as error:
            lease.release()
        self.assertEqual("LEASE_OWNERSHIP_LOST", error.exception.code)
        self.assertEqual("foreign replacement", marker.read_text())
        self.assertFalse(lease.report()["released"])
        self.assertTrue(lease.report()["post"]["lease_present"])

    def test_release_process_check_failure_records_no_false_proof(self):
        count = [0]
        def checker(_):
            count[0] += 1
            if count[0] >= 3:
                raise RuntimeError("secret command")
            return 0
        lease = self.lease(checker).acquire()
        with self.assertRaises(BrowserSafetyError) as error:
            lease.release()
        self.assertEqual("PROCESS_CHECK_FAILED", error.exception.code)
        report = lease.report()
        self.assertFalse(report["released"])
        self.assertFalse(report["owned_lease_present"])
        self.assertIsNone(report["post"])
        self.assertEqual("PROCESS_CHECK_FAILED", report["post_error"]["code"])
        self.assertNotIn("secret", json.dumps(report))

    def test_disappeared_lease_retains_ownership_failure_even_when_profile_is_idle(self):
        lease = self.lease().acquire()
        (self.profile / LEASE_NAME).unlink()  # Simulated interference in temp only.
        with self.assertRaises(BrowserSafetyError) as error:
            lease.release()
        self.assertEqual("LEASE_OWNERSHIP_LOST", error.exception.code)
        self.assertFalse(lease.report()["released"])
        self.assertEqual("LEASE_OWNERSHIP_LOST", lease.report()["release_error"]["code"])

    def test_remaining_process_after_close_is_not_false_release(self):
        observations = iter((0, 0, 1))
        lease = self.lease(lambda _: next(observations)).acquire()
        with self.assertRaises(BrowserSafetyError) as error:
            lease.release()
        self.assertEqual("PROFILE_NOT_RELEASED", error.exception.code)
        self.assertFalse(lease.report()["released"])
        self.assertEqual(1, lease.report()["post"]["process_count"])
        self.assertFalse((self.profile / LEASE_NAME).exists())


    def test_remaining_foreign_lock_after_close_is_preserved(self):
        lease = self.lease().acquire()
        lock = self.profile / CHROMIUM_LOCKS[1]
        lock.write_text("foreign")
        with self.assertRaises(BrowserSafetyError) as error:
            lease.release()
        self.assertEqual("PROFILE_NOT_RELEASED", error.exception.code)
        self.assertEqual("foreign", lock.read_text())
        self.assertFalse((self.profile / LEASE_NAME).exists())


class WindowsProcessCheckTests(unittest.TestCase):
    def test_cim_receives_profile_in_environment_and_returns_count_only(self):
        fake = type("Result", (), {"returncode": 0, "stdout": "2", "stderr": ""})()
        with patch("annotation.runtime.browser.lease.os.name", "nt"), \
             patch("annotation.runtime.browser.lease.subprocess.run", return_value=fake) as run:
            self.assertEqual(2, windows_profile_process_count(Path.cwd()))
        args, kwargs = run.call_args
        self.assertNotIn(str(Path.cwd()), str(args))
        self.assertEqual(str(Path.cwd().resolve()), kwargs["env"]["USENSE_A04_PROFILE"])
        self.assertTrue(kwargs["capture_output"])

    def test_cim_failure_or_unreadable_output_is_sanitized(self):
        for returncode, stdout in ((1, "secret"), (0, "secret"), (0, "-1"), (0, "")):
            fake = type("Result", (), {"returncode": returncode, "stdout": stdout, "stderr": "secret"})()
            with self.subTest(returncode=returncode, stdout=stdout), \
                 patch("annotation.runtime.browser.lease.os.name", "nt"), \
                 patch("annotation.runtime.browser.lease.subprocess.run", return_value=fake):
                with self.assertRaises(BrowserSafetyError) as error:
                    windows_profile_process_count(Path.cwd())
                self.assertEqual("PROCESS_CHECK_FAILED:process_check", str(error.exception))

if __name__ == "__main__":
    unittest.main()
