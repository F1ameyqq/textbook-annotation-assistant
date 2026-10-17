"""A02 pure planner. No filesystem, session mutation, browser or model access."""
import json

from annotation.contracts import (
    artifact_ref, assert_plan_ready, content_digest, policy_ref, validate_bundle,
)
from annotation.quality.targetcheck import (
    analyze_target, append_artifacts, make_artifact, projection_frames, reject,
    resolve_artifact, resolve_policy,
)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def frame_facts(frames):
    return content_digest({"frames": frames})


def create_plan(bundle, graph_ref, precheck_ref, targetcheck_ref, snapshot_ref,
                current_snapshot_ref, policy_reference, config, *, artifact_id,
                created_at, run_id=None, operation="CREATE_FRAMES", previous_receipt=None):
    """Return a new validated bundle. Invalid/missing bindings raise ContractError.

    A valid failed-check chain yields a BLOCKED diagnostic plan with no actions.
    UPDATE is explicitly unsupported, including when a C01 baseline is provided.
    """
    bundle = validate_bundle(bundle)
    graph = resolve_artifact(bundle, graph_ref, "QuestionGraph")
    pre = resolve_artifact(bundle, precheck_ref, "CheckReport")
    target = resolve_artifact(bundle, targetcheck_ref, "CheckReport")
    snapshot = resolve_artifact(bundle, snapshot_ref, "PlatformSnapshot")
    current = resolve_artifact(bundle, current_snapshot_ref, "PlatformSnapshot")
    policy = resolve_policy(bundle, policy_reference)
    if operation != "CREATE_FRAMES" or previous_receipt is not None:
        reject("UPDATE_UNSUPPORTED", "A02 supports no delta shape; need old APPLIED receipt, frame_update and future implementation")
    if pre.payload.stage != "PRE_APPLY" or target.payload.stage != "TARGET":
        reject("TWO_CHECK_STAGES", "distinct PRE_APPLY and TARGET required")
    for report in (pre, target):
        if artifact_ref(graph) != report.payload.graph.model_dump(mode="json") or policy_ref(policy) != report.payload.policy.model_dump(mode="json"):
            reject("VERSION_CONFLICT", "report graph/policy differs from requested plan")
        if report.payload.snapshot is not None and report.payload.snapshot.model_dump(mode="json") != artifact_ref(snapshot):
            reject("TARGET_CHANGED", "report binds a different snapshot")
    if artifact_ref(snapshot) != artifact_ref(current):
        reject("TARGET_CHANGED", "explicit current snapshot changed; recheck target")
    if snapshot.payload.authorized_scope_id != graph.scope_id:
        reject("AUTHORIZED_SCOPE", "snapshot authorization differs; diagnostic plan not representable in C01")
    computed = analyze_target(bundle, graph_ref, snapshot_ref, current_snapshot_ref, policy_reference, config)
    if (target.producer.module != "a02-targetcheck" or target.producer.config_version != config.version or
            target.payload.model_dump(mode="json") != computed):
        reject("TARGET_CHECK_STALE", "target report does not equal recomputed conditions/current authorization")
    ready = pre.payload.decision == target.payload.decision == "PASS"
    actions = []
    required = ["frame_readback", "persistent_draft" if config.session_mode == "PERSISTENT" else "same_session_handoff"]
    if ready:
        platform = {q.platform_question_id: q for q in snapshot.payload.questions}
        next_orders = {d: max([q.platform_order for q in snapshot.payload.questions if q.directory_id == d] + [0]) + 1
                       for d in snapshot.payload.directories}
        for question in graph.payload.questions:
            qid = question.question_id
            pid = question.external_refs.platform_question_id
            directory = config.directory_map[question.directory_id]
            existing = platform.get(pid)
            order = existing.platform_order if existing else next_orders[directory]
            frames = [f.model_dump(mode="json") for f in snapshot.payload.frames if f.platform_question_id == pid] if existing else []
            before = {"question_exists": existing is not None, "platform_question_id": pid,
                      "directory_id": directory, "frame_count": len(frames), "frames_hash": frame_facts(frames)}
            if existing:
                before["platform_order"] = order
            else:
                before["next_order"] = order
                next_orders[directory] += 1
            projected = projection_frames(bundle, graph, question, policy)
            if not projected:
                reject("EMPTY_PROJECTION", "question has no frame projection: " + qid)
            action_id = "action-a02-" + content_digest({"plan_id": artifact_id, "question_id": qid,
                                                        "graph": artifact_ref(graph), "snapshot": artifact_ref(snapshot)})[:32]
            actions.append({"action_id": action_id,
                            "target": {"target_id": snapshot.payload.target_id, "question_id": qid, "platform_question_id": pid},
                            "source_entity_ids": [qid] + list(dict.fromkeys(f["fragment_id"] for f in projected)),
                            "expected_before": before, "operation": "CREATE_FRAMES",
                            "expected_after": {"question_exists": True, "directory_id": directory,
                                               "platform_order": order, "frames": encoded(projected)},
                            "depends_on": [actions[-1]["action_id"]] if actions else []})
    issues = [i.issue_id for report in (pre, target) for i in report.payload.issues if i.blocks]
    payload = {"graph": artifact_ref(graph), "precheck": artifact_ref(pre), "targetcheck": artifact_ref(target),
               "snapshot": artifact_ref(snapshot), "policy": policy_ref(policy),
               "readiness": "READY" if ready else "BLOCKED", "execution_mode": "SIMULATED",
               "session_mode": config.session_mode, "required_capabilities": required, "actions": actions,
               "blocked_issue_ids": list(dict.fromkeys(issues)), "previous_receipt": None, "final_submission": "HUMAN_ONLY"}
    plan = make_artifact("ApplyPlan", artifact_id, graph, payload, [graph, pre, target, snapshot],
                         config.version, "a02-planner", created_at, run_id)
    output = append_artifacts(bundle, plan)
    if ready:
        assert_plan_ready(output, artifact_ref(plan), artifact_ref(current))
    return output


def verify_generated_plan(bundle, plan, current_ref, config):
    """Recompute supported projection/facts before mock dispatch; refuse edited actions."""
    payload = plan.payload
    if plan.producer.config_version != config.version:
        reject("AUTHORIZATION_CHANGED", "current authorization/config differs from planned version")
    # Rebuild without this plan or its descendants; retain upstream history so UNKNOWN stays visible.
    data = bundle.model_dump(mode="json")
    remove = {(plan.artifact_id, plan.revision)}
    while True:
        previous_count = len(remove)
        for item in data["artifacts"]:
            if any((r["artifact_id"], r["revision"]) in remove for r in item["input_refs"]):
                remove.add((item["artifact_id"], item["revision"]))
        if len(remove) == previous_count:
            break
    data["artifacts"] = [a for a in data["artifacts"] if (a["artifact_id"], a["revision"]) not in remove]
    upstream = validate_bundle(data)
    generated = create_plan(upstream, payload.graph, payload.precheck, payload.targetcheck,
                            payload.snapshot, current_ref, payload.policy, config,
                            artifact_id=plan.artifact_id, created_at=plan.created_at, run_id=plan.run_id)
    rebuilt = generated.artifacts[-1]
    if rebuilt != plan:
        reject("PLAN_CHANGED", "plan does not equal generated supported projection")
