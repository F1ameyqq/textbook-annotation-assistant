"""R1 offline regressions for references into a plan's platform snapshot.

Each mutation starts from the portable synthetic normal fixture, retains its
resources, and reseals every dependency. Existing mappings change in both graph
revisions so the printed-label ReviewPatch remains a valid derivation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from annotation.contracts import (
    ContractError, artifact_ref, assert_plan_ready, load_bundle, validate_bundle,
)
from test_contracts import FIXTURES, ROOT, artifact, fixture, graph, reseal


def artifact_path(bundle, item):
    return "$.artifacts[{}].payload".format(
        next(i for i, candidate in enumerate(bundle["artifacts"])
             if candidate is item))


def snapshot(bundle):
    return artifact(bundle, "PlatformSnapshot")["payload"]


def add_platform_question(bundle, platform_id="platform-alpha", order=17,
                          directory_id=None):
    target = snapshot(bundle)
    if directory_id is None:
        directory_id = target["directories"][0]
    target["questions"].append({
        "platform_question_id": platform_id,
        "directory_id": directory_id,
        "platform_order": order,
    })


def map_question(bundle, question_id="question-alpha",
                 platform_id="platform-alpha", order=17):
    """Keep the mapping stable across the fixture's immutable patch chain."""
    for item in bundle["artifacts"]:
        if item["kind"] == "QuestionGraph":
            question = next(q for q in item["payload"]["questions"]
                            if q["question_id"] == question_id)
            question["external_refs"].update(
                platform_question_id=platform_id, platform_order=order)
    for action in artifact(bundle, "ApplyPlan")["payload"]["actions"]:
        if action["target"]["question_id"] == question_id:
            action["target"]["platform_question_id"] = platform_id


class PlatformReferenceTests(unittest.TestCase):
    def accepted(self, bundle):
        reseal(bundle)
        model = validate_bundle(bundle, asset_root=FIXTURES / "normal")
        plan = artifact(bundle, "ApplyPlan")
        current = artifact(bundle, "PlatformSnapshot")
        eligible = assert_plan_ready(model, artifact_ref(plan), artifact_ref(current))
        self.assertEqual(eligible.artifact_id, plan["artifact_id"])
        return model

    def rejected(self, bundle, code, path):
        reseal(bundle)
        with self.assertRaises(ContractError) as caught:
            validate_bundle(bundle, asset_root=FIXTURES / "normal")
        self.assertEqual([(issue["code"], issue["path"])
                          for issue in caught.exception.issues], [(code, path)])
        # Eligibility must not accept the same closed, resealed invalid input.
        plan = artifact(bundle, "ApplyPlan")
        current = artifact(bundle, "PlatformSnapshot")
        with self.assertRaises(ContractError) as eligibility:
            assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(current))
        self.assertEqual([(issue["code"], issue["path"])
                          for issue in eligibility.exception.issues], [(code, path)])

    def action_path(self, bundle, index=0):
        return (artifact_path(bundle, artifact(bundle, "ApplyPlan")) +
                ".actions[{}].target.platform_question_id".format(index))

    def mapped_path(self, bundle, field="platform_question_id", index=0):
        return (artifact_path(bundle, graph(bundle)) +
                ".questions[{}].external_refs.{}".format(index, field))

    def test_snapshot_question_in_its_declared_directory_is_valid(self):
        bundle = fixture()
        add_platform_question(bundle)
        self.accepted(bundle)

    def test_existing_target_has_explicit_mapping_and_snapshot_entry(self):
        bundle = fixture()
        add_platform_question(bundle)
        map_question(bundle)
        self.accepted(bundle)

    def test_internal_and_platform_directory_namespaces_remain_independent(self):
        bundle = fixture()
        snapshot(bundle)["directories"] = ["platform-directory-a"]
        add_platform_question(bundle, directory_id="platform-directory-a")
        map_question(bundle)
        self.assertEqual(graph(bundle)["payload"]["questions"][0]["directory_id"],
                         "directory-a")
        self.accepted(bundle)

    def test_new_question_keeps_null_target_in_empty_snapshot(self):
        bundle = fixture()
        self.assertEqual(snapshot(bundle)["questions"], [])
        self.assertIsNone(artifact(bundle, "ApplyPlan")["payload"]["actions"][0]
                          ["target"]["platform_question_id"])
        self.accepted(bundle)

    def test_new_question_keeps_null_target_in_nonempty_snapshot(self):
        bundle = fixture()
        add_platform_question(bundle, platform_id="platform-unrelated")
        self.assertTrue(all(action["target"]["platform_question_id"] is None
                            for action in artifact(bundle, "ApplyPlan")
                            ["payload"]["actions"]))
        self.accepted(bundle)

    def test_existing_mapping_without_known_order_is_valid(self):
        bundle = fixture()
        add_platform_question(bundle)
        map_question(bundle, order=None)
        self.accepted(bundle)

    def test_parent_and_child_can_share_an_explicit_platform_projection(self):
        bundle = fixture()
        add_platform_question(bundle)
        map_question(bundle)
        map_question(bundle, question_id="question-child")
        child = graph(bundle)["payload"]["questions"][1]
        self.assertEqual(child["parent_question_id"], "question-alpha")
        self.accepted(bundle)

    def test_f1_snapshot_question_missing_directory_is_rejected_at_field(self):
        bundle = fixture()
        add_platform_question(bundle, directory_id="platform-directory-not-present")
        path = (artifact_path(bundle, artifact(bundle, "PlatformSnapshot")) +
                ".questions[0].directory_id")
        self.rejected(bundle, "MISSING_REFERENCE", path)

    def test_f2_nonnull_action_must_exist_in_its_snapshot(self):
        # Empty string is a non-null target too; it cannot mean a new question.
        for platform_id in ("platform-question-not-present", ""):
            with self.subTest(platform_id=platform_id):
                bundle = fixture()
                action = artifact(bundle, "ApplyPlan")["payload"]["actions"][0]
                action["target"]["platform_question_id"] = platform_id
                self.rejected(bundle, "MISSING_REFERENCE", self.action_path(bundle))

    def test_existing_action_target_requires_its_internal_questions_mapping(self):
        bundle = fixture()
        add_platform_question(bundle)
        action = artifact(bundle, "ApplyPlan")["payload"]["actions"][0]
        action["target"]["platform_question_id"] = "platform-alpha"
        self.rejected(bundle, "PLATFORM_MAPPING_REQUIRED", self.action_path(bundle))

    def test_action_cannot_select_a_different_existing_platform_question(self):
        bundle = fixture()
        add_platform_question(bundle)
        add_platform_question(bundle, platform_id="platform-beta", order=18)
        map_question(bundle)
        map_question(bundle, question_id="question-beta", platform_id="platform-beta", order=18)
        action = artifact(bundle, "ApplyPlan")["payload"]["actions"][0]
        action["target"]["platform_question_id"] = "platform-beta"
        self.rejected(bundle, "PLATFORM_MAPPING_CONFLICT", self.action_path(bundle))

    def test_null_target_cannot_bypass_an_existing_mapping(self):
        bundle = fixture()
        add_platform_question(bundle)
        map_question(bundle)
        action = artifact(bundle, "ApplyPlan")["payload"]["actions"][0]
        action["target"]["platform_question_id"] = None
        self.rejected(bundle, "PLATFORM_MAPPING_CONFLICT", self.action_path(bundle))

    def test_existing_graph_mapping_must_exist_in_plan_snapshot(self):
        bundle = fixture()
        map_question(bundle)
        self.rejected(bundle, "MISSING_REFERENCE", self.mapped_path(bundle))

    def test_empty_graph_mapping_is_not_a_new_question(self):
        bundle = fixture()
        map_question(bundle, platform_id="", order=None)
        self.rejected(bundle, "MISSING_REFERENCE", self.mapped_path(bundle))

    def test_known_mapped_order_must_match_the_snapshot(self):
        bundle = fixture()
        add_platform_question(bundle, order=18)
        map_question(bundle, order=17)
        self.rejected(bundle, "PLATFORM_MAPPING_CONFLICT",
                      self.mapped_path(bundle, field="platform_order"))

    def test_f1_and_f2_default_loader_and_cli_reject_resealed_complete_inputs(self):
        for case in ("missing-directory", "missing-platform-question"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                copied = Path(folder) / "sample with spaces"
                shutil.copytree(FIXTURES / "normal", copied)
                bundle = fixture()
                if case == "missing-directory":
                    add_platform_question(bundle, directory_id="platform-directory-not-present")
                    path = (artifact_path(bundle, artifact(bundle, "PlatformSnapshot")) +
                            ".questions[0].directory_id")
                else:
                    action = artifact(bundle, "ApplyPlan")["payload"]["actions"][0]
                    action["target"]["platform_question_id"] = "platform-question-not-present"
                    path = self.action_path(bundle)
                reseal(bundle)
                target = copied / "input.json"
                target.write_text(json.dumps(bundle), encoding="utf-8")
                with self.assertRaises(ContractError) as caught:
                    load_bundle(target)
                self.assertEqual([(issue["code"], issue["path"])
                                  for issue in caught.exception.issues],
                                 [("MISSING_REFERENCE", path)])
                env = dict(os.environ)
                env["PYTHONPATH"] = str(ROOT / "src")
                completed = subprocess.run(
                    [sys.executable, "-m", "annotation.contracts", "validate", str(target)],
                    cwd=folder, env=env, text=True, capture_output=True, timeout=30)
                self.assertNotEqual(completed.returncode, 0, completed.stdout)
                result = json.loads(completed.stderr)
                self.assertFalse(result["valid"])
                self.assertEqual([(issue["code"], issue["path"])
                                  for issue in result["issues"]],
                                 [("MISSING_REFERENCE", path)])


if __name__ == "__main__":
    unittest.main()
