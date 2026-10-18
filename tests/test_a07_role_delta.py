"""A07-F01: exactly two PRE_APPLY role checks, no target or dispatch."""
import copy
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest

from annotation.contracts import artifact_ref, policy_ref, seal_artifact, seal_policy, validate_bundle
from annotation.quality.q1_offline import pre_apply
from annotation.source.b_q1.reader import build_source, load_inputs


def rebind_policy(bundle, option_role):
    """A valid freshly sealed counterexample must reach the semantic role gate."""
    data = bundle.model_dump(mode="json")
    old_policy_ref = policy_ref(data["policies"][0])
    new_policy = copy.deepcopy(data["policies"][0])
    new_policy["role_mapping"]["option"] = option_role
    new_policy = seal_policy(new_policy)
    replacements = [(old_policy_ref, policy_ref(new_policy))]

    def rebind(value):
        if isinstance(value, dict):
            for old, new in replacements:
                if value == old:
                    return copy.deepcopy(new)
            return {k: rebind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rebind(v) for v in value]
        return value

    artifacts = []
    for old in data["artifacts"]:
        new = seal_artifact(rebind(old))
        replacements.append((artifact_ref(old), artifact_ref(new)))
        artifacts.append(new)
    data.update(policies=[new_policy], artifacts=artifacts)
    return data


class RoleDeltaGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = Path(os.environ.get("A07_INPUT_DIR", ".local/a07/inputs"))
        cls.inputs = load_inputs(src / "base.zip", src / "candidate.zip", src / "history.json", src / "approval.json", "config/policies/a07-q1-offline-v1.json")
        cls.basis = runpy.run_path("examples/a07/role_delta_check.py")["rule_basis"]()
        cls.calls = []

    @classmethod
    def tearDownClass(cls):
        path = os.environ.get("A07_ROLE_GATE_EVIDENCE")
        if path:
            dest = Path(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps({"pid": os.getpid(), "rule_basis": cls.basis, "calls": cls.calls,
                "targets_created": 0, "complete_business_attempts": 0, "business_dispatches": 0,
                "successful_closures": 0}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def check_role(self, option_role):
        with tempfile.TemporaryDirectory(prefix="a07-f01-gate-") as root:
            run_id, now = "a07-f01-gate", "2026-10-18T12:30:00+00:00"
            source, _facts = build_source(self.inputs, root, run_id, now)
            data = rebind_policy(source, option_role)
            valid = validate_bundle(data, asset_root=root)
            self.assertEqual(valid.policies[0].role_mapping["shared_material"], "W")
            _checked, report = pre_apply(valid, self.inputs, root, run_id, now)
            results = {c["check_id"]: c["outcome"] for c in report["payload"]["checks"]}
            roles = [valid.policies[0].role_mapping[f.role] for f in valid.artifacts[-1].payload.fragments]
            record = {"option_role": option_role, "actual_mapped_roles": roles,
                "expected_roles_from_original_rules": self.basis["expected_roles"], "checks": results,
                "decision": report["payload"]["decision"], "C01_resealed_input_valid": True,
                "reached_layer": "PRE_APPLY.policy.ordinary_choice_role_mapping", "zero_target_change": True}
            self.calls.append(record)
            self.assertTrue(all(results[k] == "PASS" for k in results if k != "policy"))
            return record, report

    def test_correct_ordinary_choice_roles(self):
        record, _report = self.check_role("W")
        self.assertEqual(record["actual_mapped_roles"], self.basis["expected_roles"])
        self.assertEqual(record["checks"]["policy"], "PASS")
        self.assertEqual(record["decision"], "PASS")

    def test_old_incorrect_roles_reach_semantic_gate(self):
        record, report = self.check_role("Q")
        self.assertEqual(record["checks"]["policy"], "FAIL")
        self.assertEqual(record["decision"], "HOLD")
        self.assertIn("ordinary_choice_role_mapping=False", next(c["reason"] for c in report["payload"]["checks"] if c["check_id"] == "policy"))
        self.assertEqual(len(report["payload"]["issues"]), 1)
        self.assertEqual(report["payload"]["issues"][0]["blocks"], ["PLAN", "APPLY"])


if __name__ == "__main__":
    unittest.main()
