"""F01 narrow field checks only: 14 observed pairs, unknown version, wrong kind."""
import unittest

from annotation.source.b_handoff import HandoffError
from annotation.source.b_handoff.reader import _validate_stage_result


OBSERVED = [
    ("evidence", "EvidenceBundleTrial", "b-evidence-trial/0.2"),
    ("recover", "EvidenceBundleTrial", "b-evidence-trial/0.3"),
    ("assemble", "QuestionGraphTrial", "b-graph-trial/0.3"),
    ("recovery_review", "RecoveryReviewTrial", "b-recovery-review-trial/0.1"),
    ("quality", "CheckReportTrial", "b-check-trial/0.3"),
    ("continuation_prepare", "ContinuationScopeTrial", "b-continuation-scope-trial/0.1"),
    ("continuation_proof", "ContinuationProofStageTrial", "b-continuation-proof-stage-trial/0.1"),
    ("continuation_apply", "ContinuationApplyStageTrial", "b-continuation-apply-stage-trial/0.1"),
    ("continuation_quality", "CheckReportTrial", "b-check-trial/0.4"),
    ("inline_prepare", "InlinePreparationTrial", "b-inline-preparation-trial/0.1"),
    ("inline_apply", "InlineApplyStageTrial", "b-inline-apply-stage-trial/0.1"),
    ("inline_quality", "CheckReportTrial", "b-check-trial/0.5"),
    ("content_apply", "ContentRevisionApplicationTrial", "b-content-revision-application-trial/0.2"),
    ("content_quality", "CheckReportTrial", "b-check-trial/0.7"),
]


class StageResultTests(unittest.TestCase):
    def test_observed_pairs(self):
        for stage, kind, version in OBSERVED:
            with self.subTest(stage=stage):
                result = _validate_stage_result(stage, {"kind": kind, "schema_version": version}, "wrapper#/payload/result")
                self.assertEqual((result["kind"], result["schema_version"]), (kind, version))
                self.assertTrue(result["validated"])
                self.assertEqual(result["context"], "FIXED_STAGE_DIAGNOSTIC_ONLY")
                self.assertFalse(result["grants_current_top_level_support"])

    def test_unknown_version(self):
        with self.assertRaises(HandoffError) as error:
            _validate_stage_result("inline_apply", {"kind": "InlineApplyStageTrial", "schema_version": "b-inline-apply-stage-trial/9.9"}, "wrapper#/payload/result")
        self.assertEqual((error.exception.code, error.exception.layer, error.exception.path),
                         ("UNSUPPORTED_VERSION", "VERSION", "wrapper#/payload/result/schema_version"))

    def test_wrong_kind(self):
        with self.assertRaises(HandoffError) as error:
            _validate_stage_result("inline_apply", {"kind": "CheckReportTrial", "schema_version": "b-inline-apply-stage-trial/0.1"}, "wrapper#/payload/result")
        self.assertEqual((error.exception.code, error.exception.layer, error.exception.path),
                         ("UNSUPPORTED_KIND", "VERSION", "wrapper#/payload/result/kind"))


if __name__ == "__main__":
    unittest.main()
