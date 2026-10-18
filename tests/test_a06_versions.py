"""Finite native version dispatch; no invented 0.6 positive package."""
import unittest

from annotation.source.b_handoff import HandoffError, version_policy


class VersionDispatchTests(unittest.TestCase):
    def test_archive_current_and_unsupported_matrix(self):
        for kind, prefix in (("QuestionGraphTrial", "b-graph-trial/"), ("CheckReportTrial", "b-check-trial/")):
            for version in ("0.4", "0.5"):
                with self.subTest(kind=kind, version=version):
                    self.assertEqual(version_policy(prefix + version, kind=kind, location="ARCHIVE", bound_archive=True), "ARCHIVE_ONLY")
                    with self.assertRaises(HandoffError) as current:
                        version_policy(prefix + version, kind=kind, location="CURRENT")
                    self.assertEqual(current.exception.code, "ARCHIVE_ONLY_NOT_CURRENT")
                    with self.assertRaises(HandoffError) as unbound:
                        version_policy(prefix + version, kind=kind, location="ARCHIVE")
                    self.assertEqual(unbound.exception.code, "UNBOUND_ARCHIVE")
            for version in ("0.6", "9.9"):
                with self.subTest(kind=kind, version=version):
                    with self.assertRaises(HandoffError) as unsupported:
                        version_policy(prefix + version, kind=kind, location="CURRENT")
                    self.assertEqual(unsupported.exception.code, "UNSUPPORTED_VERSION")
            self.assertEqual(version_policy(prefix + "0.7", kind=kind, location="CURRENT"), "READ_ONLY_HOLD")

    def test_unregistered_entry_shape(self):
        with self.assertRaises(HandoffError) as unsupported:
            version_policy("b-graph-trial/0.7", kind="ApproximateGraph", location="CURRENT")
        self.assertEqual(unsupported.exception.code, "UNSUPPORTED_ENTRY_SHAPE")


if __name__ == "__main__":
    unittest.main()
