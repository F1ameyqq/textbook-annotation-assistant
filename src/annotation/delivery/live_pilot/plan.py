"""Single-action C01 plans with book-wide append facts, never directory-local max."""
from dataclasses import replace
import json

from annotation.contracts import artifact_ref, assert_plan_ready, policy_ref, seal_artifact, validate_bundle
from annotation.quality.targetcheck import resolve_artifact
from annotation.quality.live_pilot import check_target, require, state_facts
from annotation.runtime.storage.common import digest

VERSION = "a11-offline-core-1"


def envelope(kind, identity, admission, payload, inputs):
    graph = admission.graph
    return seal_artifact({"schema_version": graph.schema_version, "artifact_id": identity, "revision": 1,
        "kind": kind, "run_id": graph.run_id, "book_id": graph.book_id, "scope_id": graph.scope_id,
        "input_refs": [artifact_ref(item) for item in inputs], "created_at": graph.created_at,
        "producer": {"module": "a11-live-pilot", "implementation_version": VERSION,
            "config_version": admission.input_hash, "policy_versions": [policy_ref(admission.policy)],
            "model_version": None, "prompt_version": None,
            "evidence_mode": "SYNTHETIC" if admission.offline else "OBSERVED"}, "payload": payload})


def create_live_plan(admission, request, question_id, observation):
    """Actual PLATFORM eligibility remains unreachable until a verified adapter exists."""
    fact = next((q for q in admission.questions if q["question_id"] == question_id), None)
    require(fact is not None, "QUESTION_NOT_AUTHORIZED")
    maximum = check_target(replace(admission, questions=(fact,)), request, observation)
    base = resolve_artifact(admission.bundle, request["refs"]["snapshot"], "PlatformSnapshot")
    graph = admission.graph
    source = resolve_artifact(admission.bundle, graph.payload.source, "SourceBundle")
    pre = resolve_artifact(admission.bundle, request["refs"]["precheck"], "CheckReport")
    require(pre.payload.snapshot is None, "PRECHECK_TARGET_COUPLING")
    token = digest({"input": admission.input_hash, "question": question_id,
                    "baseline": state_facts(observation)})[:24]
    target = observation["view"]["target"]
    sp = base.payload.model_dump(mode="json")
    sp.update(observed_at=graph.created_at, observed_version=str(observation["read_sequence"]),
              observed_hash=digest(state_facts(observation)), directories=target["directories"],
              questions=target["questions"], frames=[{k: f[k] for k in
                  ("platform_frame_id", "platform_question_id", "box", "platform_role")} for f in target["frames"]])
    snapshot = envelope("PlatformSnapshot", "a11-snapshot-" + token, admission, sp, [source])
    target_report = envelope("CheckReport", "a11-target-" + token, admission,
        {"stage": "TARGET", "subject": artifact_ref(graph), "graph": artifact_ref(graph),
         "policy": policy_ref(admission.policy), "snapshot": artifact_ref(snapshot), "receipt": None,
         "coverage": pre.payload.coverage.model_dump(mode="json"),
         "checks": [{"check_id": key, "outcome": "PASS", "evidence_refs": sp["evidence_refs"],
                     "reason": "A11 recomputed OFFLINE fixture facts; no platform proof"}
                    for key in ("target_version", "authorized_scope", "capabilities", "policy")],
         "issues": [], "decision": "PASS", "reason": "explicit offline target computation"}, [graph, snapshot])
    directory = request["directory_map"][fact["directory_id"]]
    action = {"action_id": "a11-create-" + token,
        "target": {"target_id": base.payload.target_id, "question_id": question_id, "platform_question_id": None},
        "source_entity_ids": [question_id] + [f["fragment_id"] for f in fact["frames"]],
        "operation": "CREATE_FRAMES", "depends_on": [],
        "expected_before": {"question_exists": False, "platform_question_id": None,
            "directory_id": directory, "frame_count": 0,
            "frames_hash": digest({"frames": []}), "global_max": maximum,
            "whole_book_hash": digest(state_facts(observation))},
        "expected_after": {"question_exists": True, "directory_id": directory,
            "platform_order": maximum + 1,
            "frames": json.dumps(fact["frames"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))}}
    plan = envelope("ApplyPlan", "a11-plan-" + token, admission,
        {"graph": artifact_ref(graph), "precheck": artifact_ref(pre), "targetcheck": artifact_ref(target_report),
         "snapshot": artifact_ref(snapshot), "policy": policy_ref(admission.policy), "readiness": "READY",
         "execution_mode": "SIMULATED" if admission.offline else "PLATFORM",
         "session_mode": "SAME_SESSION_HANDOFF",
         "required_capabilities": ["frame_readback", "content_readback", "same_session_handoff"],
         "actions": [action], "blocked_issue_ids": [], "previous_receipt": None, "final_submission": "HUMAN_ONLY"},
        [graph, pre, target_report, snapshot])
    data = admission.bundle.model_dump(mode="json")
    data["artifacts"].extend([snapshot, target_report, plan])
    checked = validate_bundle(data)
    assert_plan_ready(checked, artifact_ref(plan), artifact_ref(snapshot))
    return {"kind": "A11SingleQuestionPlan", "mode": "OFFLINE" if admission.offline else "PLATFORM",
            "version": VERSION, "input_hash": admission.input_hash, "approval_hash": admission.approval_hash,
            "policy": policy_ref(admission.policy), "action": action, "c01_plan": plan,
            "c01_exchange": data, "baseline": observation, "approved_parts": fact["parts"],
            "frames": fact["frames"], "insert_after_order": maximum,
            "source_bindings": request["bindings"], "submission_status": "NOT_SUBMITTED"}


def verify_plan(admission, request, plan, observation):
    rebuilt = create_live_plan(admission, request, plan["action"]["target"]["question_id"], observation)
    require(rebuilt == plan, "PLAN_CHANGED")
    return rebuilt
