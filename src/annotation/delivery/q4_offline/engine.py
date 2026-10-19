"""One-plan Q4 delivery with fresh recomputation and actual memory readback."""
import copy
import threading
import uuid

from annotation.contracts import artifact_ref, assert_plan_ready, content_digest, policy_ref, validate_bundle
from annotation.delivery.mock import apply_synthetic_action
from annotation.delivery.planner import action_facts, compare_action_effect, encoded, frame_facts
from annotation.quality.targetcheck import projection_frames
from annotation.quality.q4_offline import pre_apply, target_check, compare_approved_frames
from annotation.source.b_q4.reader import (
    BOOK, QUESTION, SCOPE, DIRECTORY, TARGET, APPROVAL_SHA, POLICY_SHA,
    artifact, build_source, encode, need, write_once, authorize,
)


class MemoryTarget:
    """Own in-process state only; observation never receives a plan or projection."""
    operations = ("CREATE_FRAMES",)
    session_mode = "SAME_SESSION_HANDOFF"
    supports_readback = True

    def __init__(self, *, book_id=BOOK, target_id=TARGET, scope_id=SCOPE):
        self.book_id, self.target_id, self.scope_id = book_id, target_id, scope_id
        self.instance_id = "memory-" + uuid.uuid4().hex
        self._state = {"target": {"target_id": target_id, "directories": [DIRECTORY], "questions": [], "frames": []},
                       "internal_bindings": {}, "frame_projections": {}, "epoch": 0}
        self._sequence = 0
        self._consumed = set()
        self.held = False
        self.lock = threading.Lock()

    @property
    def version(self):
        return self.instance_id + ":" + str(self._state["epoch"])

    def snapshot_view(self):
        return copy.deepcopy(self._state)

    def observe(self):
        self._sequence += 1
        view = self.snapshot_view()
        return {"read_status": "OK", "view": view, "read_sequence": self._sequence,
                "instance_id": self.instance_id, "book_id": self.book_id, "scope_id": self.scope_id,
                "target_id": self.target_id, "target_state_hash": content_digest(view), "execution_mode": "SIMULATED"}

    def inject_external_change_for_refusal(self):
        """Explicit synthetic stale-state fixture; no business effect or reset."""
        with self.lock:
            self._state["epoch"] += 1


def prepare(inputs, target, root, run_id, created_at, *, execution_mode="SIMULATED"):
    need(execution_mode == "SIMULATED", "TARGET", "PLATFORM_MODE_FORBIDDEN", "A09 authorizes simulation only")
    bundle, facts = build_source(inputs, root, run_id, created_at)
    bundle, pre = pre_apply(bundle, inputs, root, run_id, created_at)
    graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    policy = bundle.policies[0]
    view = target.snapshot_view()
    descriptor = {"instance_id": target.instance_id, "version": target.version, "view": view,
        "book_id": target.book_id, "scope_id": target.scope_id, "target_id": target.target_id,
        "operations": list(target.operations), "session_mode": target.session_mode,
        "frame_readback": target.supports_readback, "approval_sha256": APPROVAL_SHA, "policy_sha256": POLICY_SHA,
        "execution_mode": "SIMULATED", "submission_status": "NOT_SUBMITTED"}
    resource = write_once(root, "assets/target-" + content_digest(descriptor) + ".json", encode(descriptor))
    data = bundle.model_dump(mode="json")
    data["evidence"].append({"evidence_id": "ev-target-descriptor", "resource": resource, "description": "Actual new memory target state/identity and implemented capabilities, simulation only", "mode": "SYNTHETIC"})
    snapshot = artifact("PlatformSnapshot", "a09-snapshot-" + run_id, {
        "target_id": target.target_id, "platform_version": "a09-memory-v1", "observed_at": created_at,
        "observed_version": target.version, "observed_hash": content_digest(view), "authorized_scope_id": target.scope_id,
        "directories": view["target"]["directories"], "questions": view["target"]["questions"], "frames": view["target"]["frames"],
        "capabilities": [{"name": n, "status": "VERIFIED" if ok else "UNSUPPORTED", "platform_version": "a09-memory-v1", "evidence_refs": ["ev-target-descriptor"]}
            for n, ok in (("frame_readback", target.supports_readback), ("same_session_handoff", target.session_mode == "SAME_SESSION_HANDOFF"))],
        "evidence_refs": ["ev-target-descriptor"]}, [], policy, run_id, created_at, "SYNTHETIC")
    data["artifacts"].append(snapshot)
    bundle = validate_bundle(data, asset_root=root)
    bundle, target_report = target_check(bundle, target, snapshot, root, run_id, created_at, execution_mode)
    need(pre["payload"]["decision"] == target_report["payload"]["decision"] == "PASS", "PLAN", "GATES_NOT_READY", "computed PRE_APPLY and TARGET must both pass")
    question = graph.payload.questions[0]
    frames = projection_frames(bundle, graph, question, policy)
    regions = {r.region_id: r for a in bundle.artifacts if a.kind == "EvidenceBundle" for r in a.payload.regions}
    # The public memory effect copies these content values into frame_projections.
    # Base C01 target frames themselves carry only role/box; readback checks both.
    frames = [dict(f, text=regions[f["region_id"]].text) for f in frames]
    need(len(frames) == 4, "PLAN", "FRAME_SCOPE", "exact four projected frames required")
    need(not compare_approved_frames(frames, facts), "PLAN", "APPROVED_FRAME_MISMATCH", "projected role/type/content/order/geometry differs from approved table")
    action = {"action_id": "a09-create-" + content_digest({"graph": artifact_ref(graph), "snapshot": artifact_ref(snapshot)})[:24],
        "target": {"target_id": TARGET, "question_id": QUESTION, "platform_question_id": None},
        "source_entity_ids": [QUESTION] + [f.fragment_id for f in graph.payload.fragments],
        "expected_before": {"question_exists": False, "platform_question_id": None, "directory_id": DIRECTORY,
                            "frame_count": 0, "frames_hash": frame_facts([]), "next_order": 1},
        "operation": "CREATE_FRAMES", "expected_after": {"question_exists": True, "directory_id": DIRECTORY,
                            "platform_order": 1, "frame_count": len(frames), "frames": encoded(frames)}, "depends_on": []}
    need(action_facts(action, view) == action["expected_before"], "PLAN", "BEFORE_FACTS", "actual target differs before planning")
    plan = artifact("ApplyPlan", "a09-plan-" + run_id, {"graph": artifact_ref(graph), "precheck": artifact_ref(pre), "targetcheck": artifact_ref(target_report),
        "snapshot": artifact_ref(snapshot), "policy": policy_ref(policy), "readiness": "READY", "execution_mode": "SIMULATED",
        "session_mode": "SAME_SESSION_HANDOFF", "required_capabilities": ["frame_readback", "same_session_handoff"], "actions": [action],
        "blocked_issue_ids": [], "previous_receipt": None, "final_submission": "HUMAN_ONLY"}, list(bundle.artifacts), policy, run_id, created_at, "SYNTHETIC")
    data = bundle.model_dump(mode="json")
    data["artifacts"].append(plan)
    bundle = validate_bundle(data, asset_root=root)
    assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(snapshot))
    return bundle, plan, facts


def execute(inputs, target, bundle, plan_ref, root, run_id, created_at):
    """Rebuild admission/target/plan from real inputs inside the mutation lock."""
    with target.lock:
        authorize(inputs)
        need(not target.held, "EXECUTION", "TARGET_HELD", "unknown/failed target cannot continue")
        need(not target._consumed, "EXECUTION", "PLAN_REPLAY", "the only plan has already been consumed")
        need(target.book_id == BOOK and target.target_id == TARGET and target.scope_id == SCOPE,
             "TARGET", "TARGET_IDENTITY", "fixed book, target and scope required")
        current = target.snapshot_view()
        need(current["epoch"] == 0 and not current["target"]["frames"] and not current["target"]["questions"],
             "TARGET", "TARGET_CHANGED", "target is no longer the planned new empty instance")
        candidate = validate_bundle(bundle, asset_root=root)
        expected, plan, facts = prepare(inputs, target, root, run_id, created_at)
        need(candidate.model_dump(mode="json") == expected.model_dump(mode="json") and plan_ref == artifact_ref(plan),
             "EXECUTION", "PLAN_RECOMPUTATION", "caller plan/reports/source differ from actual full recomputation")
        snap = next(a for a in expected.artifacts if a.kind == "PlatformSnapshot")
        assert_plan_ready(candidate, plan_ref, artifact_ref(snap))
        before = target.observe()
        action = plan["payload"]["actions"][0]
        need(action_facts(action, before["view"]) == action["expected_before"], "EXECUTION", "TARGET_CHANGED", "fresh prewrite facts differ")
        before_resource = write_once(root, "assets/before.json", encode(before))
        target._consumed.add(plan["content_hash"])
        try:
            apply_synthetic_action(target._state, copy.deepcopy(action))
            after = target.observe()  # Reads the target's actual state; no plan argument.
            after_resource = write_once(root, "assets/readback.json", encode(after))
            need(after["read_sequence"] > before["read_sequence"] and after["instance_id"] == before["instance_id"],
                 "READBACK", "FRESHNESS", "readback must be a new read of the same target")
            comparison = compare_action_effect(action, before, after)
            actual_frames = after["view"]["target"]["frames"]
            actual_projections = [after["view"]["frame_projections"][f["platform_frame_id"]] for f in actual_frames]
            # This oracle comes from the raw user approval, never from plan frames.
            approved_differences = compare_approved_frames(actual_projections, facts)
            approved = not approved_differences and len(after["view"]["target"]["questions"]) == 1 and len(actual_frames) == 4
            approved = approved and all(f["box"] == p["box"] and f["platform_role"] == p["platform_role"] for f, p in zip(actual_frames, actual_projections))
            comparison.update(approval_differences=approved_differences, actual_content_and_type_readback=actual_projections,
                              approval_table_match=approved, submission_status="NOT_SUBMITTED", content_check_status="PENDING")
            matched = comparison["effect_match"] == "MATCH" and approved
            target.held = not matched
            result = {"action_id": action["action_id"], "outcome": "APPLIED" if matched else "UNKNOWN",
                "platform_ids": comparison["platform_ids"] if matched else [], "before_evidence_refs": ["ev-execution-before"],
                "after_evidence_refs": ["ev-execution-after"], "readback": after_resource,
                "effect_match": "MATCH" if matched else "INDETERMINATE", "next_step": "POSTCHECK" if matched else "RECONCILE",
                "replay_allowed": False, "reason": comparison["reason"]}
            data = candidate.model_dump(mode="json")
            for name, resource in (("before", before_resource), ("after", after_resource)):
                data["evidence"].append({"evidence_id": "ev-execution-" + name, "resource": resource,
                    "description": "Independent actual memory target observation " + name, "mode": "SYNTHETIC"})
            receipt = artifact("ExecutionReceipt", "a09-receipt-" + run_id, {"plan": plan_ref, "execution_mode": "SIMULATED",
                "results": [result], "unresolved_issue_ids": [] if matched else ["a09-readback-unknown"],
                "write_disposition": "POSTCHECK" if matched else "PAUSE_RECONCILE"}, list(candidate.artifacts), candidate.policies[0], run_id, created_at, "SYNTHETIC")
            data["artifacts"].append(receipt)
            final = validate_bundle(data, asset_root=root)
            return final, receipt, before, after, dict(comparison)
        except BaseException:
            target.held = True
            raise
