"""Pre-freeze source/quality checks: zero targets, plans, effects, full trials."""
import runpy
import tempfile
import unittest
from pathlib import Path

from annotation.quality.q4_offline import pre_apply, approved_frames, compare_approved_frames
from annotation.source.b_q4.reader import build_source, load_inputs, APPROVAL_SHA, sha

ROOT = Path(__file__).resolve().parents[1]


class Q4Static(unittest.TestCase):
    def test_observed_source_and_one_resealed_type_counterexample(self):
        inputs = load_inputs(ROOT / ".local/a09/inputs/stage.zip", ROOT / ".local/a09/inputs/proposal.json",
            ROOT / ".local/a09/inputs/approval.json", ROOT / ".local/a09/inputs/input-registry.json", ROOT / "config/policies/a09-q4-offline-v1.json")
        counterexample = runpy.run_path(str(ROOT / "examples/a09/semantics.py"))["image_as_text"]
        with tempfile.TemporaryDirectory(prefix="a09-source-gate-") as tmp:
            bundle, facts = build_source(inputs, tmp, "static", "2026-10-19T10:40:00+00:00")
            checked, report = pre_apply(bundle, inputs, tmp, "static", "2026-10-19T10:40:00+00:00")
            self.assertEqual(sha(inputs.approval_raw), APPROVAL_SHA)
            self.assertEqual(report["payload"]["decision"], "PASS")
            self.assertEqual([c["check_id"] for c in report["payload"]["checks"]], ["source_integrity", "structure", "answer_matching", "coverage", "policy"])
            self.assertEqual([a.producer.evidence_mode for a in checked.artifacts], ["OBSERVED"] * 4)
            frames = approved_frames(facts)
            self.assertEqual([f["platform_type"] for f in frames], ["image", "text", "text", "text"])
            self.assertEqual([f["platform_role"] for f in frames], ["Q", "Q", "Q", "A"])
            self.assertEqual(compare_approved_frames(frames, facts), [])
        with tempfile.TemporaryDirectory(prefix="a09-type-gate-") as tmp:
            bundle, _ = build_source(inputs, tmp, "type", "2026-10-19T10:40:00+00:00")
            legally_resealed = counterexample(bundle, tmp)
            _, report = pre_apply(legally_resealed, inputs, tmp, "type", "2026-10-19T10:40:00+00:00")
            outcomes = {c["check_id"]: c["outcome"] for c in report["payload"]["checks"]}
            self.assertEqual(report["payload"]["decision"], "HOLD")
            self.assertEqual(outcomes, {"source_integrity": "PASS", "structure": "FAIL", "answer_matching": "PASS", "coverage": "PASS", "policy": "FAIL"})
            self.assertIn("types_match_approval=False", report["payload"]["checks"][1]["reason"])


if __name__ == "__main__":
    unittest.main()
