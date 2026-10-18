"""Finite negative checks and planning only: no successful business dispatch."""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from dataclasses import replace

from annotation.contracts import artifact_ref, seal_artifact, validate_bundle
from annotation.delivery.q1_offline import MemoryTarget, prepare, execute
from annotation.source.b_q1.reader import Q1Error, authorize, encode, load_inputs, sha


def changed_candidate(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files = {n: z.read(n) for n in z.namelist()}
    candidate = json.loads(files["candidate.json"])
    candidate["payload"]["candidate_content"]["answer_text"] = "C"
    candidate["content_hash"] = sha(encode(candidate["payload"]))
    files["candidate.json"] = encode(candidate)
    manifest = json.loads(files["manifest.json"])
    for entry in manifest["files"]:
        entry.update(bytes=len(files[entry["path"]]), sha256=sha(files[entry["path"]]))
    files["manifest.json"] = encode(manifest)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, value in files.items():
            z.writestr(name, value)
    return out.getvalue()


class Q1FiniteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = Path(os.environ.get("A07_INPUT_DIR", ".local/a07/inputs"))
        cls.inputs = load_inputs(src / "base.zip", src / "candidate.zip", src / "history.json", src / "approval.json", "config/policies/a07-q1-offline-v1.json")
        cls.temp = tempfile.TemporaryDirectory(prefix="a07-unit-")
        cls.root = Path(cls.temp.name)
        cls.target = MemoryTarget()
        cls.run_id, cls.now = "a07-unit", "2026-10-18T12:00:00+00:00"
        cls.bundle, cls.plan, cls.facts = prepare(cls.inputs, cls.target, cls.root, cls.run_id, cls.now)
        cls.calls = []

    @classmethod
    def tearDownClass(cls):
        output = os.environ.get("A07_UNIT_EVIDENCE")
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(json.dumps({"calls": cls.calls, "complete_business_attempts": 0,
                "business_dispatches": 0, "successful_closures": 0, "final_target": cls.target.snapshot_view()}, indent=2) + "\n", encoding="utf-8")
        cls.temp.cleanup()

    def refused(self, name, inputs=None, target=None, bundle=None, expected=None):
        target = target or self.target
        before = target.snapshot_view()
        with self.assertRaises(Q1Error) as caught:
            execute(inputs or self.inputs, target, bundle or self.bundle, artifact_ref(self.plan), self.root, self.run_id, self.now)
        error = caught.exception
        self.assertEqual(error.code, expected)
        self.assertEqual(before, target.snapshot_view())
        self.calls.append({"case": name, "layer": error.layer, "code": error.code, "zero_target_change": True, "business_dispatches": 0})

    def test_missing_approval(self):
        self.refused("missing approval", inputs=replace(self.inputs, approval_raw=b""), expected="APPROVAL_MISSING")

    def test_forged_approval(self):
        doc = json.loads(self.inputs.approval_raw)
        doc["book_id"] = "46006966"
        self.refused("forged approval", inputs=replace(self.inputs, approval_raw=encode(doc)), expected="APPROVAL_FORGED")

    def test_changed_candidate_after_valid_envelope(self):
        changed = replace(self.inputs, candidate_raw=changed_candidate(self.inputs.candidate_raw))
        changed.documents()  # The semantic authorization check must be reached after valid transport.
        self.refused("rehashed candidate/repacked manifest", inputs=changed, expected="INPUT_BINDING")

    def test_changed_associated_history(self):
        h = json.loads(self.inputs.history_raw)
        h["revision"] = 2
        self.refused("changed associated history", inputs=replace(self.inputs, history_raw=encode(h)), expected="INPUT_BINDING")

    def test_platform_mode(self):
        before = self.target.snapshot_view()
        with self.assertRaises(Q1Error) as caught:
            prepare(self.inputs, self.target, self.root, self.run_id, self.now, execution_mode="PLATFORM")
        self.assertEqual(caught.exception.code, "PLATFORM_MODE_FORBIDDEN")
        self.assertEqual(before, self.target.snapshot_view())
        self.calls.append({"case": "platform mode", "layer": caught.exception.layer, "code": caught.exception.code, "zero_target_change": True, "business_dispatches": 0})

    def test_wrong_target(self):
        self.refused("wrong target", target=MemoryTarget(target_id="wrong-target"), expected="TARGET_IDENTITY")

    def test_outside_scope(self):
        self.refused("outside authorized scope", target=MemoryTarget(scope_id="other-scope"), expected="TARGET_IDENTITY")

    def test_changed_current_target(self):
        target = MemoryTarget()
        target._state["epoch"] = 1
        self.refused("target currentness drift", target=target, expected="TARGET_CHANGED")

    def test_resealed_plan_effect(self):
        data = self.bundle.model_dump(mode="json")
        plan = copy.deepcopy(self.plan)
        plan["payload"]["actions"][0]["expected_after"]["frame_count"] = 7
        plan = seal_artifact(plan)
        data["artifacts"][-1] = plan
        validate_bundle(data, asset_root=self.root)  # Structurally valid/resealed, still not write authority.
        self.refused("resealed plan effect outside six-frame scope", bundle=data, expected="PLAN_RECOMPUTATION")

    def test_observed_planning_only(self):
        self.assertEqual([a.producer.evidence_mode for a in self.bundle.artifacts[:4]], ["OBSERVED"]*4)
        self.assertEqual(self.plan["payload"]["readiness"], "READY")
        self.assertEqual(self.plan["payload"]["execution_mode"], "SIMULATED")
        self.assertEqual(len(self.plan["payload"]["actions"]), 1)
        self.assertEqual(self.plan["payload"]["actions"][0]["expected_after"]["frame_count"], 6)
        self.assertEqual(self.facts["provenance"]["original_unassigned_ledger_count"], 19)
        self.assertEqual(self.target.snapshot_view()["target"]["frames"], [])


if __name__ == "__main__":
    unittest.main()
