"""Single-action C01 plans with book-wide append facts, never directory-local max."""
from dataclasses import replace
import json

from annotation.contracts import artifact_ref, assert_plan_ready, policy_ref, seal_artifact, validate_bundle
from annotation.quality.targetcheck import resolve_artifact
from annotation.quality.live_pilot import check_target, require, state_facts
from annotation.runtime.storage.common import digest

VERSION = "a11-offline-core-1"
WIRE_VERSION = "a24-first-save-wire-1"


def envelope(kind, identity, admission, payload, inputs):
    graph = admission.graph
    return seal_artifact({"schema_version": graph.schema_version, "artifact_id": identity, "revision": 1,
        "kind": kind, "run_id": graph.run_id, "book_id": graph.book_id, "scope_id": graph.scope_id,
        "input_refs": [artifact_ref(item) for item in inputs], "created_at": graph.created_at,
        "producer": {"module": "a11-live-pilot", "implementation_version": WIRE_VERSION if admission.wire is not None else VERSION,
            "config_version": admission.input_hash, "policy_versions": [policy_ref(admission.policy)],
            "model_version": None, "prompt_version": None,
            "evidence_mode": "SYNTHETIC" if admission.offline else "OBSERVED"}, "payload": payload})


def create_live_plan(admission, request, question_id, observation):
    """Only a registered complete current target can yield a wire-ready plan."""
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
              questions=target["questions"], frames=[] if admission.wire is not None else [{k: f[k] for k in
                  ("platform_frame_id", "platform_question_id", "box", "platform_role")} for f in target["frames"]])
    # The wire C01 action concerns an ABSENT new question (zero existing frames).
    # Full OLD frame records remain verbatim in plan.baseline/state_facts and
    # check_preservation; do not invent ImageInfo for unacquired old-book pages.
    snapshot = envelope("PlatformSnapshot", "a11-snapshot-" + token, admission, sp, [source])
    target_report = envelope("CheckReport", "a11-target-" + token, admission,
        {"stage": "TARGET", "subject": artifact_ref(snapshot), "graph": artifact_ref(graph),
         "policy": policy_ref(admission.policy), "snapshot": artifact_ref(snapshot), "receipt": None,
         "coverage": pre.payload.coverage.model_dump(mode="json"),
         "checks": [{"check_id": key, "outcome": "PASS", "evidence_refs": sp["evidence_refs"],
                     "reason": ("A24 registered current target, hash-bound proof and request manifest" if
                                admission.wire is not None and not admission.offline else
                                "SYNTHETIC target computation; no platform proof")}
                    for key in ("target_version", "authorized_scope", "capabilities", "policy")],
         "issues": [], "decision": "PASS", "reason": "evidence-bound target computation"}, [graph, snapshot])
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
            "platform_order": None if admission.wire is not None else maximum + 1,
            "frames": json.dumps(fact["frames"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))}}
    wire_fields = {}
    if admission.wire is not None:
        from annotation.delivery.live_pilot.wire import build_payload, write_set, upload_manifest, public_read_manifest
        profile = admission.wire.profile
        proto = {"action": action, "frames": fact["frames"], "approved_parts": fact["parts"],
                 "source_bindings": request["bindings"], "insert_after_order": maximum}
        payload = build_payload(proto, profile)
        uploads = upload_manifest(dict(proto, payload=payload), profile)
        writes = write_set(payload, uploads)
        action["expected_after"].update(content_operation="CREATE_QUESTION_CONTENT", content_hash=digest(fact["parts"]),
                                        write_set_hash=digest(writes), payload_hash=digest(payload))
        wire_fields = {"payload": payload, "write_set": writes, "upload_manifest": uploads,
                       "c01_snapshot_scope": "NEW_QUESTION_ABSENCE; FULL_OLD_RAW_FRAME_BASELINE_BOUND_SEPARATELY",
                       "signature_contract": profile.get("signature"), "wire_profile_hash": digest(profile),
                       "required_proofs": profile["proofs"],
                       "exact_read_manifest": public_read_manifest(profile["reads"]),
                       "request_counts": {"baseline_get": 1, "prewrite_get": 1, "save_post": 1,
                                           "get_get": 6, "refresh_get": 6, "refresh_action": 1,
                                           "independent_reopen_get": 6, "upload": len(uploads),
                                           "signature_get": int(bool(uploads)), "ocr": 0, "login": 0},
                       "server_question_order": None, "independent_acceptance": "PENDING"}
        counts = wire_fields["request_counts"]
        if profile.get("aggregate_readback"):
            extra = profile["new_read_count"]
            for key in ("get_get", "refresh_get", "independent_reopen_get"):
                counts[key] = 1 + extra
        for phase, key in (("baseline", "baseline_get"), ("prewrite", "prewrite_get"), ("get", "get_get"),
                           ("refresh", "refresh_get"), ("reopen", "independent_reopen_get")):
            spec = profile["reads"][phase]
            counts[key] += len(spec["requests"]) - 1 if "requests" in spec else 0
            counts[key] += int("export" in spec)
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
            "version": WIRE_VERSION if admission.wire is not None else VERSION,
            "input_hash": admission.input_hash, "approval_hash": admission.approval_hash,
            "policy": policy_ref(admission.policy), "action": action, "c01_plan": plan,
            "c01_exchange": data, "baseline": observation, "approved_parts": fact["parts"],
            "frames": fact["frames"], "insert_after_order": maximum,
            "source_bindings": request["bindings"], "submission_status": "NOT_SUBMITTED", **wire_fields}


def verify_plan(admission, request, plan, observation):
    rebuilt = create_live_plan(admission, request, plan["action"]["target"]["question_id"], observation)
    require(rebuilt == plan, "PLAN_CHANGED")
    return rebuilt
