"""A02 author regression suite, entirely SYNTHETIC/SIMULATED.

These are execution evidence only. Independent acceptance must construct other inputs.
"""
import copy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from annotation.contracts import (
    ContractError, artifact_ref, assert_plan_ready, load_bundle, policy_ref,
    seal_artifact, seal_policy, validate_bundle, write_bundle,
)
from annotation.delivery.mock import MockSession
from annotation.delivery.planner import create_plan
from annotation.quality.targetcheck import (
    append_artifacts, check_target, resolve_artifact,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/a02"
TIME = "2026-10-16T00:00:00Z"
spec = importlib.util.spec_from_file_location("a02_demo", ROOT / "examples/a02/run.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def get(bundle, kind):
    return next(a for a in bundle.artifacts if a.kind == kind)


def reseal(data):
    """Mutate only synthetic test inputs; follow explicit immutable references in order."""
    policies = {}
    for index, item in enumerate(data["policies"]):
        sealed = seal_policy(item)
        data["policies"][index] = sealed
        policies[(item["policy_id"], item["revision"])] = policy_ref(sealed)
    artifacts = {}

    def refs(value):
        if isinstance(value, list):
            return [refs(v) for v in value]
        if isinstance(value, dict):
            if set(value) == {"artifact_id", "revision", "kind", "content_hash"}:
                return artifacts.get((value["artifact_id"], value["revision"]), value)
            if set(value) == {"policy_id", "revision", "content_hash"}:
                return policies[(value["policy_id"], value["revision"])]
            return {k: refs(v) for k, v in value.items()}
        return value

    for index, item in enumerate(data["artifacts"]):
        sealed = seal_artifact(refs(item))
        data["artifacts"][index] = sealed
        artifacts[(item["artifact_id"], item["revision"])] = artifact_ref(sealed)
    return data


class A02Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "exchange"
        shutil.copytree(FIXTURES / "normal", self.root)
        self.bundle = load_bundle(self.root / "input.json")
        self.config = demo.read_config(self.root / "config.json")

    def use_case(self, name):
        self.root = Path(self.temp.name) / name
        shutil.copytree(FIXTURES / name, self.root)
        self.bundle = load_bundle(self.root / "input.json")
        self.config = demo.read_config(self.root / "config.json")

    def mutate(self, callback):
        data = self.bundle.model_dump(mode="json")
        callback(data)
        self.bundle = validate_bundle(reseal(data), asset_root=self.root)
        return self.bundle

    def prepare(self, config=None, plan_id="test-plan"):
        config = config or self.config
        graph, snapshot, pre = (get(self.bundle, k) for k in ("QuestionGraph", "PlatformSnapshot", "CheckReport"))
        pref = policy_ref(self.bundle.policies[0])
        output = check_target(self.bundle, artifact_ref(graph), artifact_ref(snapshot), artifact_ref(snapshot), pref,
                              config, artifact_id="test-target", created_at=TIME)
        target = output.artifacts[-1]
        output = create_plan(output, artifact_ref(graph), artifact_ref(pre), artifact_ref(target), artifact_ref(snapshot),
                             artifact_ref(snapshot), pref, config, artifact_id=plan_id, created_at=TIME)
        return output, output.artifacts[-1], target

    def execute(self, fault="applied", index=0, config=None):
        output, plan, target = self.prepare(config)
        session = MockSession()
        session.register_target(self.bundle, artifact_ref(get(self.bundle, "PlatformSnapshot")), asset_root=self.root)
        faults = {plan.payload.actions[index].action_id: fault} if plan.payload.actions else {}
        output = session.execute(output, artifact_ref(plan), config or self.config, asset_root=self.root,
                                 receipt_id="test-receipt", created_at=TIME, faults=faults)
        return output, session, plan, get(output, "ExecutionReceipt")

    def assert_rejected(self, code, callback):
        with self.assertRaises(ContractError) as error:
            callback()
        self.assertIn(code, [i["code"] for i in error.exception.issues])

    def add_existing(self, data, *, mapped=False, order=17):
        snapshot = next(a for a in data["artifacts"] if a["kind"] == "PlatformSnapshot")
        snapshot["payload"]["questions"].append({"platform_question_id": "existing-alpha", "directory_id": "platform-unit-a", "platform_order": order})
        if mapped:
            graph = next(a for a in data["artifacts"] if a["kind"] == "QuestionGraph")
            graph["payload"]["questions"][0]["external_refs"].update(platform_question_id="existing-alpha", platform_order=order)

    def test_public_contract_inputs_and_portable_roundtrip(self):
        for name in ("normal", "choice", "exceptions"):
            model = load_bundle(FIXTURES / name / "input.json")
            self.assertTrue(all(a.producer.evidence_mode == "SYNTHETIC" for a in model.artifacts))
            self.assertFalse(any(a.kind in ("ApplyPlan", "ExecutionReceipt") for a in model.artifacts))
        write_bundle(self.bundle, self.root / "roundtrip.json")
        self.assertEqual(load_bundle(self.root / "roundtrip.json"), self.bundle)

    def test_target_and_planner_are_pure(self):
        before = self.bundle.model_dump_json()
        output, plan, target = self.prepare()
        self.assertEqual(self.bundle.model_dump_json(), before)
        self.assertEqual(target.payload.decision, "PASS")
        self.assertEqual(plan.payload.readiness, "READY")
        self.assertEqual(len(plan.payload.actions), 3)
        self.assertEqual(plan.payload.execution_mode, "SIMULATED")

    def test_manual_original_projection_cross_page_shared_and_selected_answers(self):
        output, plan, _ = self.prepare()
        alpha, child, beta = plan.payload.actions
        frames = json.loads(alpha.expected_after["frames"])
        self.assertEqual([f["region_id"] for f in frames], ["region-alpha-start", "region-shared", "region-alpha-end", "region-alpha-answer"])
        self.assertEqual([f["platform_role"] for f in frames], ["Q", "Q", "Q", "A"])
        self.assertEqual(frames[-1]["box"]["bbox"], [5.0, 25.0, 65.0, 35.0])
        self.assertEqual(frames[-1]["box"]["image"]["asset_id"], "asset-page-a2")
        self.assertEqual(frames[-1]["platform_type"], "text")
        self.assertIn("fragment-shared", child.source_entity_ids)
        self.assertNotIn("fragment-alpha-answer", beta.source_entity_ids)
        self.assertEqual(child.depends_on, [alpha.action_id])
        self.assertEqual(beta.depends_on, [child.action_id])

    def test_repeated_printed_number_internal_identity_and_serial_next_order(self):
        output, session, plan, receipt = self.execute()
        self.assertEqual(len({a.action_id for a in plan.payload.actions}), 3)
        self.assertEqual([r.outcome for r in receipt.payload.results], ["APPLIED"] * 3)
        state = session.read_target(plan.book_id)["target"]
        self.assertEqual([q["platform_order"] for q in state["questions"]], [1, 2, 1])
        self.assertEqual(len(state["frames"]), 9)
        self.assertEqual([q["directory_id"] for q in state["questions"]], ["platform-unit-a", "platform-unit-a", "platform-unit-b"])

    def test_synthetic_choice_separate_projection_only(self):
        self.use_case("choice")
        output, session, plan, receipt = self.execute()
        frames = json.loads(plan.payload.actions[-1].expected_after["frames"])
        self.assertEqual(sum(f["platform_role"] == "W" for f in frames), 2)
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["frames"]), 11)

    def test_new_question_null_target_in_nonempty_snapshot_does_not_guess(self):
        self.mutate(lambda d: self.add_existing(d))
        output, session, plan, receipt = self.execute()
        self.assertTrue(all(a.target.platform_question_id is None for a in plan.payload.actions))
        self.assertEqual(plan.payload.actions[0].expected_before["next_order"], 18)
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["questions"]), 4)

    def test_explicit_existing_mapping_uses_platform_directory_and_order(self):
        self.mutate(lambda d: self.add_existing(d, mapped=True))
        output, session, plan, receipt = self.execute()
        self.assertEqual(plan.payload.actions[0].target.platform_question_id, "existing-alpha")
        self.assertEqual(plan.payload.actions[0].expected_before["platform_order"], 17)
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["questions"]), 3)
        self.assertEqual(receipt.payload.results[0].platform_ids[0], "existing-alpha")

    def test_existing_mapping_with_unknown_order_reads_actual_order(self):
        def change(d):
            self.add_existing(d, mapped=True)
            next(a for a in d["artifacts"] if a["kind"] == "QuestionGraph")["payload"]["questions"][0]["external_refs"]["platform_order"] = None
        self.mutate(change)
        _, plan, _ = self.prepare()
        self.assertEqual(plan.payload.actions[0].expected_before["platform_order"], 17)

    def test_missing_mapping_and_empty_string_are_blocked(self):
        for bad in ("does-not-exist", ""):
            with self.subTest(mapping=bad):
                original = self.bundle
                self.mutate(lambda d: next(a for a in d["artifacts"] if a["kind"] == "QuestionGraph")["payload"]["questions"][0]["external_refs"].update(platform_question_id=bad))
                _, plan, target = self.prepare()
                self.assertEqual(target.payload.decision, "HOLD")
                self.assertEqual(plan.payload.actions, [])
                self.bundle = original

    def test_wrong_existing_order_is_blocked(self):
        def change(d):
            self.add_existing(d, mapped=True)
            next(a for a in d["artifacts"] if a["kind"] == "QuestionGraph")["payload"]["questions"][0]["external_refs"]["platform_order"] = 18
        self.mutate(change)
        _, plan, target = self.prepare()
        self.assertEqual(plan.payload.readiness, "BLOCKED")
        self.assertIn("order differs", target.payload.checks[0].reason)

    def test_snapshot_missing_directory_is_contract_rejected(self):
        data = self.bundle.model_dump(mode="json")
        self.add_existing(data)
        next(a for a in data["artifacts"] if a["kind"] == "PlatformSnapshot")["payload"]["directories"] = []
        self.assert_rejected("MISSING_REFERENCE", lambda: validate_bundle(reseal(data), asset_root=self.root))

    def test_wrong_explicit_directory_mapping_is_blocked(self):
        self.mutate(lambda d: self.add_existing(d, mapped=True))
        _, plan, target = self.prepare(replace(self.config, directory_map={"directory-a": "platform-unit-b", "directory-b": "platform-unit-b"}))
        self.assertEqual(plan.payload.readiness, "BLOCKED")
        self.assertIn("directory mapping differs", target.payload.checks[0].reason)

    def test_unmapped_platform_order_is_not_an_identity(self):
        self.mutate(lambda d: next(a for a in d["artifacts"] if a["kind"] == "QuestionGraph")["payload"]["questions"][0]["external_refs"].update(platform_order=1))
        _, plan, _ = self.prepare()
        self.assertEqual(plan.payload.readiness, "BLOCKED")

    def test_authorization_wrong_book_target_scope_operation_and_directory(self):
        for changed in (replace(self.config, book_id="other-book"), replace(self.config, target_id="other-target"),
                        replace(self.config, scope_id="other-scope"), replace(self.config, allowed_operations=()),
                        replace(self.config, directory_map={})):
            with self.subTest(config=changed):
                _, plan, target = self.prepare(changed)
                self.assertEqual(plan.payload.actions, [])
                self.assertNotEqual(target.payload.decision, "PASS")

    def test_capability_unknown_missing_and_wrong_platform_version_block(self):
        for mode in ("UNKNOWN", "MISSING", "VERSION"):
            with self.subTest(mode=mode):
                original = self.bundle
                def change(d):
                    caps = next(a for a in d["artifacts"] if a["kind"] == "PlatformSnapshot")["payload"]["capabilities"]
                    cap = next(c for c in caps if c["name"] == "frame_readback")
                    if mode == "MISSING":
                        caps.remove(cap)
                    elif mode == "VERSION":
                        cap["platform_version"] = "other-platform"
                    else:
                        cap.update(status="UNKNOWN", evidence_refs=[])
                self.mutate(change)
                _, plan, target = self.prepare()
                self.assertEqual(plan.payload.actions, [])
                self.assertIn("frame_readback", target.payload.checks[2].reason)
                self.bundle = original

    def test_persistent_mode_requires_persistent_draft(self):
        _, plan, _ = self.prepare(replace(self.config, session_mode="PERSISTENT"))
        self.assertEqual(plan.payload.readiness, "BLOCKED")

    def test_missing_report_wrong_stage_and_nonpass_are_not_ready(self):
        output, plan, target = self.prepare()
        graph, pre, snapshot = (get(self.bundle, k) for k in ("QuestionGraph", "CheckReport", "PlatformSnapshot"))
        def call(pre_ref, target_ref):
            return create_plan(output, artifact_ref(graph), pre_ref, target_ref, artifact_ref(snapshot), artifact_ref(snapshot),
                               policy_ref(self.bundle.policies[0]), self.config, artifact_id="another-plan", created_at=TIME)
        missing = dict(artifact_ref(pre), artifact_id="missing-report")
        self.assert_rejected("MISSING_REFERENCE", lambda: call(missing, artifact_ref(target)))
        self.assert_rejected("TWO_CHECK_STAGES", lambda: call(artifact_ref(target), artifact_ref(target)))
        self.assert_rejected("TWO_CHECK_STAGES", lambda: call(artifact_ref(pre), artifact_ref(pre)))
        self.use_case("exceptions")
        _, plan, target = self.prepare()
        self.assertEqual(plan.payload.readiness, "BLOCKED")

    def test_unresolved_and_combined_choice_policies_block(self):
        self.use_case("choice")
        for mode in ("UNRESOLVED", "COMBINED"):
            original = self.bundle
            self.mutate(lambda d: d["policies"][0].update(option_grouping=mode)) if mode != "UNRESOLVED" else None
            if mode == "UNRESOLVED":
                # A non-PASS PRE_APPLY is needed to keep this input contract-valid.
                def change(d):
                    d["policies"][0]["option_grouping"] = mode
                    pre = next(a for a in d["artifacts"] if a["kind"] == "CheckReport")
                    pre["payload"]["decision"] = "EXCEPTION"
                    pre["payload"]["checks"][-1]["outcome"] = "FAIL"
                    pre["payload"]["issues"] = [{"issue_id": "issue-policy-unresolved", "code": "POLICY_UNRESOLVED",
                        "scope_type": "scope", "scope_id": pre["scope_id"], "evidence_refs": ["proof-checks"],
                        "severity": "blocking", "blocks": ["PLAN"], "suggested_strategy": {"strategy_id": "HUMAN_REVIEW", "max_attempts": 0, "max_cost": 0.0}, "reason": "unresolved"}]
                self.mutate(change)
            _, plan, target = self.prepare()
            self.assertEqual(plan.payload.readiness, "BLOCKED")
            self.bundle = original

    def test_unsupported_combination_seven_choice_and_parent_are_explicit(self):
        for kind, parent in (("combination", None), ("seven_choice", None), ("unsupported", None), ("free_response", "question-alpha")):
            original = self.bundle
            self.mutate(lambda d: next(a for a in d["artifacts"] if a["kind"] == "QuestionGraph")["payload"]["questions"][1].update(question_type=kind, parent_question_id=parent))
            _, plan, target = self.prepare()
            self.assertEqual(plan.payload.readiness, "BLOCKED")
            self.assertTrue(any(i.code == "UNSUPPORTED_LAYOUT" for i in target.payload.issues))
            self.bundle = original

    def test_unresolved_policy_confirmation_blocks_even_nonchoice(self):
        self.mutate(lambda d: d["policies"][0].update(confirmation_status="UNRESOLVED", applicability="PROPOSAL_ONLY"))
        _, plan, target = self.prepare()
        self.assertEqual(plan.payload.readiness, "BLOCKED")
        self.assertTrue(any(i.code == "POLICY_UNRESOLVED" for i in target.payload.issues))

    def test_graph_and_policy_new_revision_cannot_reuse_old_reports(self):
        for kind in ("graph", "policy"):
            output, plan, target = self.prepare()
            graph, pre, snapshot = (get(self.bundle, k) for k in ("QuestionGraph", "CheckReport", "PlatformSnapshot"))
            pref = policy_ref(self.bundle.policies[0])
            if kind == "graph":
                newer = graph.model_dump(mode="json")
                newer["revision"] += 1
                newer["payload"]["identity_notes"] += " new revision"
                newer = seal_artifact(newer)
                output = append_artifacts(output, newer)
                graph_ref = artifact_ref(newer)
            else:
                data = output.model_dump(mode="json")
                newer = data["policies"][0].copy()
                newer.update(revision=2, source_notes=["SYNTHETIC changed policy"])
                newer = seal_policy(newer)
                data["policies"].append(newer)
                output = validate_bundle(data)
                pref = policy_ref(newer)
                graph_ref = artifact_ref(graph)
            self.assert_rejected("VERSION_CONFLICT", lambda: create_plan(output, graph_ref, artifact_ref(pre), artifact_ref(target),
                artifact_ref(snapshot), artifact_ref(snapshot), pref, self.config, artifact_id="stale-plan", created_at=TIME))

    def test_forged_target_pass_and_stale_authorization_are_recomputed(self):
        output, plan, target = self.prepare()
        graph, pre, snapshot = (get(self.bundle, k) for k in ("QuestionGraph", "CheckReport", "PlatformSnapshot"))
        self.assert_rejected("TARGET_CHECK_STALE", lambda: create_plan(output, artifact_ref(graph), artifact_ref(pre), artifact_ref(target),
            artifact_ref(snapshot), artifact_ref(snapshot), policy_ref(output.policies[0]), replace(self.config, book_id="other"),
            artifact_id="bad-auth-plan", created_at=TIME))
        changed = target.model_dump(mode="json")
        changed.update(artifact_id="fabricated-target")
        changed["payload"]["checks"][0]["reason"] = "trust fabricated PASS"
        changed = seal_artifact(changed)
        output = append_artifacts(output, changed)
        self.assert_rejected("TARGET_CHECK_STALE", lambda: create_plan(output, artifact_ref(graph), artifact_ref(pre), artifact_ref(changed),
            artifact_ref(snapshot), artifact_ref(snapshot), policy_ref(output.policies[0]), self.config, artifact_id="forged-plan", created_at=TIME))

    def test_target_changed_at_plan_and_execution_gates(self):
        output, plan, target = self.prepare()
        session = MockSession()
        snapshot = get(self.bundle, "PlatformSnapshot")
        session.register_target(self.bundle, artifact_ref(snapshot), asset_root=self.root)
        session.inject_external_change(plan.book_id)
        current = session.read_snapshot(plan.book_id)
        output = append_artifacts(output, current)
        graph, pre = get(self.bundle, "QuestionGraph"), get(self.bundle, "CheckReport")
        self.assert_rejected("TARGET_CHANGED", lambda: create_plan(output, artifact_ref(graph), artifact_ref(pre), artifact_ref(target),
            artifact_ref(snapshot), artifact_ref(current), policy_ref(output.policies[0]), self.config, artifact_id="stale", created_at=TIME))
        before = session.read_target(plan.book_id)
        self.assert_rejected("TARGET_CHANGED", lambda: session.execute(output, artifact_ref(plan), self.config, asset_root=self.root, receipt_id="late", created_at=TIME))
        self.assertEqual(session.read_target(plan.book_id), before)
        self.assertFalse(any(e["event"] == "intent" for e in session.action_log))

    def test_authorization_changed_at_execution_has_no_mutation(self):
        output, plan, _ = self.prepare()
        session = MockSession()
        session.register_target(self.bundle, artifact_ref(get(self.bundle, "PlatformSnapshot")), asset_root=self.root)
        before = session.read_target(plan.book_id)
        self.assert_rejected("AUTHORIZATION_CHANGED", lambda: session.execute(output, artifact_ref(plan), replace(self.config, scope_id="other"),
            asset_root=self.root, receipt_id="bad-auth", created_at=TIME))
        self.assertEqual(before, session.read_target(plan.book_id))

    def test_plan_facts_cannot_be_edited_and_resealed_to_execute(self):
        output, plan, _ = self.prepare()
        data = output.model_dump(mode="json")
        changed = next(a for a in data["artifacts"] if a["kind"] == "ApplyPlan")
        changed["payload"]["actions"][0]["expected_after"]["frames"] = "[]"
        changed = seal_artifact(changed)
        data["artifacts"][-1] = changed
        output = validate_bundle(data)
        session = MockSession()
        session.register_target(self.bundle, artifact_ref(get(self.bundle, "PlatformSnapshot")), asset_root=self.root)
        self.assert_rejected("PLAN_CHANGED", lambda: session.execute(output, artifact_ref(changed), self.config,
            asset_root=self.root, receipt_id="tampered", created_at=TIME))
        self.assertEqual(session.read_target(plan.book_id)["target"]["frames"], [])

    def test_null_and_wrong_action_targets_cannot_bypass_mapping(self):
        self.mutate(lambda d: self.add_existing(d, mapped=True))
        output, plan, _ = self.prepare()
        for pid in (None, "", "wrong"):
            data = output.model_dump(mode="json")
            changed = next(a for a in data["artifacts"] if a["kind"] == "ApplyPlan")
            changed["payload"]["actions"][0]["target"]["platform_question_id"] = pid
            data["artifacts"][-1] = seal_artifact(changed)
            with self.assertRaises(ContractError):
                validate_bundle(data)

    def test_update_never_downgrades_to_create_even_with_baseline_argument(self):
        output, plan, target = self.prepare()
        graph, pre, snapshot = (get(self.bundle, k) for k in ("QuestionGraph", "CheckReport", "PlatformSnapshot"))
        for kwargs in ({"operation": "UPDATE_FRAMES"}, {"previous_receipt": {"fake": "baseline"}}):
            self.assert_rejected("UPDATE_UNSUPPORTED", lambda: create_plan(output, artifact_ref(graph), artifact_ref(pre), artifact_ref(target),
                artifact_ref(snapshot), artifact_ref(snapshot), policy_ref(output.policies[0]), self.config,
                artifact_id="update-plan", created_at=TIME, **kwargs))

    def test_existing_frames_require_explicit_unsupported_update(self):
        def change(d):
            self.add_existing(d, mapped=True)
            snapshot = next(a for a in d["artifacts"] if a["kind"] == "PlatformSnapshot")
            evidence = next(a for a in d["artifacts"] if a["kind"] == "EvidenceBundle")
            snapshot["payload"]["frames"].append({"platform_frame_id": "history-frame", "platform_question_id": "existing-alpha",
                                                   "box": evidence["payload"]["regions"][0]["box"], "platform_role": "Q"})
            snapshot["input_refs"].append(artifact_ref(next(a for a in d["artifacts"] if a["kind"] == "SourceBundle")))
        self.mutate(change)
        output, session, plan, receipt = self.execute()
        self.assertEqual(plan.payload.readiness, "BLOCKED")
        self.assertEqual(receipt.payload.execution_mode, "NOT_EXECUTED")
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["frames"]), 1)

    def test_not_applied_absence_no_automatic_replay_and_no_book_pause(self):
        output, session, plan, receipt = self.execute("not_applied")
        self.assertEqual([r.outcome for r in receipt.payload.results], ["NOT_APPLIED"] * 3)
        self.assertEqual(receipt.payload.write_disposition, "RECHECK_TARGET")
        self.assertFalse(session.is_paused(plan.book_id))
        self.assertEqual(session.read_target(plan.book_id)["target"]["frames"], [])
        self.assertEqual(sum(e["event"] == "intent" for e in session.action_log), 1)
        self.assert_rejected("REPLAY_FORBIDDEN", lambda: session.execute(output, artifact_ref(plan), self.config,
            asset_root=self.root, receipt_id="replay", created_at=TIME))

    def test_not_applied_can_only_follow_new_target_check_and_new_plan(self):
        output, session, plan, receipt = self.execute("not_applied")
        graph, snapshot, pre = (get(self.bundle, k) for k in ("QuestionGraph", "PlatformSnapshot", "CheckReport"))
        output = check_target(output, artifact_ref(graph), artifact_ref(snapshot), artifact_ref(session.read_snapshot(plan.book_id)),
                              policy_ref(output.policies[0]), self.config, artifact_id="fresh-target", created_at=TIME)
        output = create_plan(output, artifact_ref(graph), artifact_ref(pre), artifact_ref(output.artifacts[-1]), artifact_ref(snapshot),
                             artifact_ref(session.read_snapshot(plan.book_id)), policy_ref(output.policies[0]), self.config,
                             artifact_id="fresh-plan", created_at=TIME)
        fresh = output.artifacts[-1]
        output = session.execute(output, artifact_ref(fresh), self.config, asset_root=self.root, receipt_id="fresh-receipt", created_at=TIME)
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["frames"]), 9)
        self.assertEqual(len(session.receipt_history(plan.book_id)), 2)

    def test_lost_response_changes_actual_target_but_is_unknown_when_read_fails(self):
        output, session, plan, receipt = self.execute("lost_response")
        self.assertEqual(receipt.payload.results[0].outcome, "UNKNOWN")
        self.assertEqual(receipt.payload.write_disposition, "PAUSE_RECONCILE")
        self.assertTrue(session.is_paused(plan.book_id))
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["frames"]), 4)
        self.assertEqual(sum(e["event"] == "intent" for e in session.action_log), 1)
        self.assertTrue(receipt.payload.unresolved_issue_ids)

    def test_lost_response_with_conclusive_independent_readback_is_applied(self):
        output, session, plan, receipt = self.execute("response_lost_readable")
        self.assertEqual([r.outcome for r in receipt.payload.results], ["APPLIED"] * 3)
        self.assertTrue(any(e.get("response", {}).get("status") == "TIMEOUT" for e in session.action_log))
        self.assertFalse(session.is_paused(plan.book_id))

    def test_partial_contradictory_and_failed_readback_remain_unknown(self):
        for fault in ("partial", "contradictory", "readback_failure"):
            with self.subTest(fault=fault):
                output, session, plan, receipt = self.execute(fault)
                self.assertEqual(receipt.payload.results[0].outcome, "UNKNOWN")
                self.assertTrue(session.is_paused(plan.book_id))

    def test_fault_in_second_action_preserves_first_expected_effect(self):
        output, session, plan, receipt = self.execute("lost_response", index=1)
        self.assertEqual([r.outcome for r in receipt.payload.results], ["APPLIED", "UNKNOWN", "NOT_APPLIED"])
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["frames"]), 7)

    def test_unknown_cannot_bypass_with_omitted_history_new_ids_question_or_scope(self):
        output, session, plan, receipt = self.execute("lost_response")
        prior = session.read_target(plan.book_id)
        history = session.receipt_history(plan.book_id)
        for scope in ("synthetic-scope", "other-scope"):
            data = self.bundle.model_dump(mode="json")  # Intentionally omit UNKNOWN from caller input.
            for a in data["artifacts"]:
                a["run_id"] = "another-run"
                a["scope_id"] = scope
                if a["kind"] == "PlatformSnapshot":
                    a["payload"]["authorized_scope_id"] = scope
                if a["kind"] == "CheckReport":
                    a["payload"]["coverage"]["scope_id"] = scope
                if a["kind"] == "SourceBundle":
                    a["payload"]["scope_manifest"][0] = "question-different"
                if a["kind"] == "QuestionGraph":
                    a["payload"]["questions"][0]["question_id"] = "question-different"
                    a["payload"]["answer_relations"][0]["question_id"] = "question-different"
            fresh = validate_bundle(reseal(data))
            old_bundle = self.bundle
            self.bundle = fresh
            fresh_config = replace(self.config, scope_id=scope)
            candidate, another, _ = self.prepare(fresh_config, plan_id="another-plan")
            self.bundle = old_bundle
            self.assertNotEqual(another.payload.actions[1].action_id, plan.payload.actions[1].action_id)
            self.assertEqual(another.payload.actions[0].target.question_id, "question-different")
            self.assert_rejected("BOOK_WRITE_PAUSED", lambda: session.execute(candidate, artifact_ref(another), fresh_config,
                asset_root=self.root, receipt_id="another-receipt", created_at=TIME))
        self.assertEqual(session.read_target(plan.book_id), prior)
        self.assertEqual(session.receipt_history(plan.book_id), history)
        copied = session.receipt_history(plan.book_id)
        copied[0]["artifacts"].clear()
        self.assertTrue(session.is_paused(plan.book_id))
        self.assertTrue(session.receipt_history(plan.book_id)[0]["artifacts"])

    def test_unknown_other_book_remains_independent(self):
        output, session, plan, receipt = self.execute("lost_response")
        original = self.bundle
        self.mutate(lambda d: [a.update(book_id="other-book") for a in d["artifacts"]])
        config = replace(self.config, book_id="other-book")
        fresh, other_plan, _ = self.prepare(config)
        session.register_target(self.bundle, artifact_ref(get(self.bundle, "PlatformSnapshot")), asset_root=self.root)
        fresh = session.execute(fresh, artifact_ref(other_plan), config, asset_root=self.root, receipt_id="other-receipt", created_at=TIME)
        self.assertEqual([r.outcome for r in get(fresh, "ExecutionReceipt").payload.results], ["APPLIED"] * 3)
        self.assertTrue(session.is_paused(original.artifacts[0].book_id))
        self.assertFalse(session.is_paused("other-book"))

    def test_public_gate_sees_full_unknown_history(self):
        output, session, plan, receipt = self.execute("lost_response")
        self.assert_rejected("BOOK_WRITE_PAUSED", lambda: assert_plan_ready(output, artifact_ref(plan), artifact_ref(get(self.bundle, "PlatformSnapshot"))))

    def test_all_outcomes_replay_false_conclusive_results_have_readback_ids(self):
        for fault in ("applied", "not_applied", "lost_response"):
            output, session, plan, receipt = self.execute(fault)
            for result in receipt.payload.results:
                self.assertFalse(result.replay_allowed)
                self.assertIsNotNone(result.readback)
                if result.outcome == "APPLIED":
                    self.assertTrue(result.platform_ids)
                resource = result.readback
                raw = json.loads((self.root / resource.path).read_text(encoding="utf-8"))
                self.assertEqual(raw["provenance"], "SYNTHETIC")
            validate_bundle(output, asset_root=self.root)

    def test_normal_summary_keeps_content_pending_and_not_submitted(self):
        output, session, plan, receipt = self.execute()
        final = demo.summarize(output, artifact_ref(receipt), {}, self.config)
        batch = get(final, "BatchReport").payload
        self.assertEqual((batch.state, batch.content_check_status, batch.submission_status), ("CONTENT_PENDING", "PENDING", "NOT_SUBMITTED"))
        self.assertEqual(batch.total_expected, 3)
        self.assertTrue(all(q.state == "PENDING" for q in batch.questions))
        self.assertEqual(batch.frame_check_status, "PASS")

    def test_exception_skip_and_missing_graph_item_remain_in_denominator(self):
        self.use_case("exceptions")
        output, session, plan, receipt = self.execute()
        statuses = json.loads((self.root / "scope-statuses.json").read_text())["statuses"]
        final = demo.summarize(output, artifact_ref(receipt), statuses, self.config)
        batch = get(final, "BatchReport").payload
        self.assertEqual(batch.total_expected, 4)
        self.assertEqual(batch.state, "NEEDS_REVIEW")
        self.assertEqual({q.question_id: q.state for q in batch.questions},
                         {"question-alpha": "EXCEPTION", "question-child": "PENDING", "question-beta": "SKIPPED", "question-missing": "EXCEPTION"})
        self.assertEqual(session.read_target(plan.book_id)["target"]["frames"], [])

    def test_unknown_summary_preserves_unknown_question_and_pause(self):
        output, session, plan, receipt = self.execute("lost_response")
        final = demo.summarize(output, artifact_ref(receipt), {}, self.config)
        batch = get(final, "BatchReport").payload
        self.assertEqual(batch.state, "NEEDS_RECONCILIATION")
        self.assertEqual(batch.questions[0].state, "UNKNOWN")
        self.assertEqual(batch.content_check_status, "PENDING")
        self.assertEqual(batch.submission_status, "NOT_SUBMITTED")

    def test_state_and_log_reads_do_not_allow_history_mutation(self):
        output, session, plan, receipt = self.execute()
        view = session.read_target(plan.book_id)
        view["target"]["frames"].clear()
        log = session.action_log
        log[0].clear()
        self.assertEqual(len(session.read_target(plan.book_id)["target"]["frames"]), 9)
        self.assertTrue(session.action_log[0])
        self.assert_rejected("TARGET_ALREADY_REGISTERED", lambda: session.register_target(self.bundle,
            artifact_ref(get(self.bundle, "PlatformSnapshot")), asset_root=self.root))

    def test_post_mutation_snapshot_has_original_source_binding(self):
        output, session, plan, receipt = self.execute()
        current = session.read_snapshot(plan.book_id)
        closed = append_artifacts(output, current, asset_root=self.root)
        self.assertEqual(len(closed.artifacts[-1].payload.frames), 9)
        self.assertTrue(any(r.kind == "SourceBundle" for r in closed.artifacts[-1].input_refs))
        self.assert_rejected("TARGET_CHANGED", lambda: assert_plan_ready(closed, artifact_ref(plan), artifact_ref(current)))

    def test_cli_demo_copy_output_reloads_all_resource_bytes(self):
        destination = Path(self.temp.name) / "portable-demo"
        final, session = demo.run(FIXTURES / "normal/input.json", destination, "lost_response")
        self.assertEqual(load_bundle(destination / "final.json"), final)
        self.assertTrue((destination / "target-state.json").exists())
        self.assertTrue((destination / "action-log.json").exists())
        with self.assertRaises(FileExistsError):
            demo.run(FIXTURES / "normal/input.json", destination)


if __name__ == "__main__":
    unittest.main()
