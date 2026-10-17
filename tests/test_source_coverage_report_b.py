import json
import tempfile
import unittest
from pathlib import Path

from tools.report_source_coverage_b import DEFAULT_DESCRIPTOR, DEFAULT_EVALUATION, build_report


class SourceCoverageReportTests(unittest.TestCase):
    def test_fixed_evidence_keeps_prefix_and_denominator_limits_explicit(self):
        report = build_report(DEFAULT_DESCRIPTOR, DEFAULT_EVALUATION)
        coverage = report["coverage"]
        self.assertEqual(report["evidence"]["base_identity_status"], "RECORDS_MATCH")
        self.assertEqual(coverage["declared_observed_full_page_asset_count"], 5)
        self.assertEqual(coverage["prefix_only_asset_count"], 1)
        self.assertEqual(coverage["chapter_or_book_denominator"], "UNKNOWN")
        sixth = next(row for row in coverage["asset_records"] if row["asset_id"] == "resource-173")
        self.assertEqual(sixth["observed_scope"], "PREFIX_CROP_ONLY")
        self.assertEqual(sixth["read_status"], "PREFIX_OBSERVED_FULL_PAGE_UNREAD")

    def test_ledger_reconciles_but_keeps_nineteen_unassigned(self):
        report = build_report(DEFAULT_DESCRIPTOR, DEFAULT_EVALUATION)
        ledger = report["answer_source_ledger"]
        self.assertEqual(ledger["counts"], {"EXCLUDED": 29, "CONSUMED": 154, "UNASSIGNED": 19})
        self.assertEqual(ledger["raw_line_count"], 202)
        self.assertTrue(ledger["count_reconciles_to_raw_lines"])
        self.assertEqual(ledger["unassigned_identity_count"], 19)
        self.assertIn("UNKNOWN", ledger["unassigned_public_identities"])

    def test_missing_inputs_report_unknown_instead_of_inventing_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            absent = Path(directory) / "absent.json"
            report = build_report(absent, absent)
        self.assertEqual(report["book_id"], "UNKNOWN")
        self.assertEqual(report["coverage"]["chapter_or_book_denominator"], "UNKNOWN")
        self.assertEqual(report["coverage"]["asset_records"], "UNKNOWN")
        self.assertEqual(report["answer_source_ledger"]["counts"], "UNKNOWN")

    def test_descriptor_sha_conflict_suppresses_full_page_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = json.loads(DEFAULT_DESCRIPTOR.read_text(encoding="utf-8"))
            changed["assets"][0]["sha256"] = "0" * 64
            descriptor = Path(directory) / "descriptor.json"
            descriptor.write_text(json.dumps(changed), encoding="utf-8")
            report = build_report(descriptor, DEFAULT_EVALUATION)
        self.assertEqual(report["evidence"]["base_identity_status"], "CONFLICT_OR_UNKNOWN")
        self.assertEqual(report["book_id"], "UNKNOWN")
        self.assertEqual(report["scope_id"], "UNKNOWN")
        self.assertIn("SHA-256 differs for base asset viewer-10", report["evidence"]["base_identity_conflicts"])
        self.assertEqual(report["coverage"]["declared_observed_full_page_asset_count"], "UNKNOWN")
        self.assertEqual(report["coverage"]["prefix_only_asset_count"], "UNKNOWN")
        self.assertEqual(report["coverage"]["asset_records"][0]["observed_scope"], "UNKNOWN_IDENTITY_CONFLICT")
        self.assertEqual(report["answer_source_ledger"]["status"], "UNKNOWN")
        self.assertEqual(report["answer_source_ledger"]["counts"], "UNKNOWN")
        self.assertEqual(report["evidence"]["descriptor"], "external:descriptor.json")

    def test_default_evidence_paths_are_repository_relative(self):
        report = build_report(DEFAULT_DESCRIPTOR, DEFAULT_EVALUATION)
        self.assertFalse(Path(report["evidence"]["descriptor"]).is_absolute())
        self.assertFalse(Path(report["evidence"]["evaluation"]).is_absolute())


if __name__ == "__main__":
    unittest.main()
