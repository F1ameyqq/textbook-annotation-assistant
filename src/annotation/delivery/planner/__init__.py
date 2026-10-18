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


def _plain(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def action_facts(action, observed_target_view):
    """The accepted A02 relevant-state rule, shared by all target adapters."""
    action = _plain(action)
    view = _plain(observed_target_view)
    before = action["expected_before"]
    directory = before["directory_id"]
    pid = action["target"]["platform_question_id"]
    if pid is None:
        pid = view["internal_bindings"].get(action["target"]["question_id"])
    question = next((q for q in view["target"]["questions"] if q["platform_question_id"] == pid), None)
    frames = [f for f in view["target"]["frames"] if f["platform_question_id"] == pid] if question else []
    facts = {"question_exists": question is not None, "platform_question_id": pid,
             "directory_id": question["directory_id"] if question else directory,
             "frame_count": len(frames), "frames_hash": frame_facts(frames)}
    if "platform_order" in before:
        facts["platform_order"] = question["platform_order"] if question else None
    if "next_order" in before:
        facts["next_order"] = max([q["platform_order"] for q in view["target"]["questions"]
                                   if q["directory_id"] == directory] + [0]) + 1
    return facts


class PublicRecord(dict):
    """Public value record. It is evidence, never a runtime permission."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _view(observation):
    value = _plain(observation)
    return value.get("view", value.get("state", value))


def compare_action_effect(action, before_observation, after_observation, *, comparator_version="a02-facts-1"):
    """Pure A02 comparison; transport responses never determine an outcome.

    Recovery observations additionally require full scope and unique platform IDs.
    Legacy observations retain their original representation and outcome rules.
    """
    if comparator_version != "a02-facts-1":
        reject("COMPARATOR_VERSION_UNSUPPORTED", "unsupported shared action comparator")
    action = _plain(action)
    before, after = _plain(before_observation), _plain(after_observation)
    digest = content_digest(action)
    recovery = "observation_id" in after
    result = PublicRecord(comparator_version=comparator_version, action_id=action["action_id"],
                          action_digest=digest, platform_ids=[], effect_match="INDETERMINATE",
                          outcome="UNKNOWN", identity_checks={}, reasons=[],
                          expected_effect_digest=content_digest(action["expected_after"]),
                          actual_digest=None, relevant_scope_completeness=False,
                          before_observation_ref=before.get("resource"),
                          after_observation_ref=after.get("resource"),
                          before_read_sequence=before.get("read_sequence"),
                          after_read_sequence=after.get("read_sequence"))
    def finish(match, ids, reason):
        result.update(effect_match=match, platform_ids=ids, reasons=[reason], reason=reason,
                      outcome={"MATCH": "APPLIED", "ABSENT": "NOT_APPLIED"}.get(match, "UNKNOWN"))
        return result
    if after.get("read_status", "OK") != "OK":
        return finish("INDETERMINATE", [], "readback unavailable, contradictory or truncated")
    if recovery:
        fields = ("store_id", "target_session_id", "target_key", "scope_id", "source_ref")
        checks = {name: before.get(name) == after.get(name) and name in before for name in fields}
        checks["action_target"] = after.get("target_key", {}).get("target_id") == action["target"]["target_id"]
        result["identity_checks"] = checks
        if not all(checks.values()):
            reject("OBSERVATION_BINDING_MISMATCH", "before/after observation identity differs")
        if (not isinstance(after.get("read_sequence"), int) or
                not isinstance(before.get("read_sequence"), int) or
                after["read_sequence"] <= before["read_sequence"]):
            reject("OBSERVATION_NOT_FRESH", "comparison needs a new actual monotonic target read")
        if not before.get("relevant_scope_completeness", before.get("scope_complete", False)) or not after.get("relevant_scope_completeness", after.get("scope_complete", False)):
            return finish("INDETERMINATE", [], "independent relevant scope is incomplete")
    result["relevant_scope_completeness"] = True
    oldview, view = _view(before), _view(after)
    if not isinstance(view, dict) or not all(k in view for k in ("target", "internal_bindings", "frame_projections")):
        return finish("INDETERMINATE", [], "target view is missing")
    questions, allframes = view["target"]["questions"], view["target"]["frames"]
    if recovery and (len({q["platform_question_id"] for q in questions}) != len(questions) or
                     len({f["platform_frame_id"] for f in allframes}) != len(allframes)):
        return finish("CONFLICT", [], "duplicate platform identity")
    if recovery:
        from annotation.contracts import target_state_digest
        if (target_state_digest(oldview) != before.get("target_state_hash") or
                target_state_digest(view) != after.get("target_state_hash")):
            reject("OBSERVATION_BINDING_MISMATCH", "independent business-state digest differs from observation")
    pid = action["target"]["platform_question_id"] or view["internal_bindings"].get(action["target"]["question_id"])
    question = next((q for q in questions if q["platform_question_id"] == pid), None)
    frames = [f for f in allframes if f["platform_question_id"] == pid] if question else []
    projected = [view["frame_projections"].get(f["platform_frame_id"]) for f in frames]
    expected = action["expected_after"]
    result["actual_digest"] = content_digest({"question": question, "frames": frames, "projections": projected})
    if (question and question["directory_id"] == expected["directory_id"] and
            question["platform_order"] == expected["platform_order"] and
            encoded(projected) == expected["frames"] and frames and
            all(p is not None and f["box"] == p["box"] and f["platform_role"] == p["platform_role"]
                for f, p in zip(frames, projected))):
        return finish("MATCH", [pid] + [f["platform_frame_id"] for f in frames],
                      "independent target readback matches all projected frames")
    facts_before, facts_after = action_facts(action, oldview), action_facts(action, view)
    if facts_after == facts_before and facts_after["frame_count"] == 0:
        return finish("ABSENT", [], "explicit readback proves projected frames ABSENT and relevant target unchanged")
    return finish("CONFLICT", [], "effect is partial, changed, or lacks a provable ABSENT baseline")


def snapshot_state_equivalent(planned_snapshot, observed_snapshot, *, planned_target_state, observed_target_state, bridge_context=None):
    from annotation.contracts import target_state_digest
    planned, observed = _plain(planned_snapshot), _plain(observed_snapshot)
    old, new = _plain(planned_target_state), _plain(observed_target_state)
    if planned["schema_version"] not in ("1.1.0-a-recovery-proposal", "1.4.0-a03-native-proposal") or observed["schema_version"] != planned["schema_version"]:
        reject("RECOVERY_VERSION_UNSUPPORTED", "state bridge is limited to recovery contracts")
    if planned['schema_version'] == '1.4.0-a03-native-proposal':
        from annotation.contracts.a03_native import require_context
        require_context(bridge_context)
    for name in ("target_key", "source_ref", "scope_id", "target_session_id"):
        if old.get(name) != new.get(name) or name not in old:
            reject("OBSERVATION_BINDING_MISMATCH", "state bridge fixed identity differs: " + name)
    hashes = (target_state_digest(old), target_state_digest(new))
    if hashes != (planned["payload"]["observed_hash"], observed["payload"]["observed_hash"]):
        reject("OBSERVATION_BINDING_MISMATCH", "snapshot digest does not bind the actual compared business state")
    versions = (planned["payload"]["observed_version"], observed["payload"]["observed_version"])
    equivalent = hashes[0] == hashes[1] and versions[0] == versions[1]
    return PublicRecord(equivalent=equivalent, planned_snapshot_ref=artifact_ref(planned),
                        observed_snapshot_ref=artifact_ref(observed), planned_state_hash=hashes[0],
                        observed_state_hash=hashes[1], planned_state_version=versions[0], observed_state_version=versions[1],
                        reasons=["business state matches" if equivalent else "business state changed"])


def bind_plan_observation(bundle, plan_ref, action_id, fresh_observation, config, *, prepared_before, progress_refs=(), bridge_context=None):
    """Bridge fresh observations using exact generated actions and target effect delta.

    Runtime separately supplies and verifies the committed prefix refs. This pure
    bridge checks their action results against the independently read target.
    """
    bundle = validate_bundle(bundle, bridge_context=bridge_context)
    plan = resolve_artifact(bundle, plan_ref, "ApplyPlan")
    if plan.schema_version not in ("1.1.0-a-recovery-proposal", "1.4.0-a03-native-proposal"):
        reject("RECOVERY_VERSION_UNSUPPORTED", "fresh observation bridge requires recovery version")
    observation = _plain(fresh_observation)
    actions = [_plain(a) for a in plan.payload.actions]
    index = next((i for i, a in enumerate(actions) if a["action_id"] == action_id), None)
    if index is None:
        reject("ACTION_DIGEST_MISMATCH", "action is absent from plan")
    action = actions[index]
    if observation.get("read_status") != "OK" or not observation.get("relevant_scope_completeness"):
        reject("CONCLUSIVE_READBACK_REQUIRED", "preparation needs complete actual target read")
    if observation.get("scope_id") != plan.scope_id or observation.get("target_key", {}).get("book_id") != plan.book_id:
        reject("TARGET_IDENTITY_MISMATCH", "observation book/scope differs from plan")
    verify_generated_plan(bundle, plan, plan.payload.snapshot, config, bridge_context=bridge_context)
    if action_facts(action, _view(observation)) != action["expected_before"]:
        reject("TARGET_CHANGED", "current relevant action facts differ from planned precondition")
    snapshot = resolve_artifact(bundle, plan.payload.snapshot, "PlatformSnapshot")
    effects = observation.get("effect_log", [])
    baseline_epoch = observation.get("plan_baseline_epoch", 0)
    delta = [e for e in effects if e.get("epoch", 0) > baseline_epoch]
    if len(delta) != index:
        reject("TARGET_CHANGED", "independent target effect-log delta is not the exact applied prefix")
    if index and not progress_refs:
        reject("DEPENDENCY_UNRESOLVED", "later action needs complete committed APPLIED prefix refs")
    if index:
        progress = [resolve_artifact(bundle, ref, "ExecutionProgress") for ref in progress_refs]
        if any(_plain(p.payload.plan_ref) != artifact_ref(plan) or p.scope_id != plan.scope_id for p in progress):
            reject("RECOVERY_CHAIN_INVALID", "applied prefix refs bind a different plan/scope")
        latest = max(progress, key=lambda p: p.payload.journal_head_sequence)
        prefix_items = [_plain(item) for item in latest.payload.actions]
        if [item["action_id"] for item in prefix_items] != [a["action_id"] for a in actions]:
            reject("RECOVERY_CHAIN_INVALID", "progress does not enumerate exact complete plan")
        for item in prefix_items[:index]:
            if (item["effective_outcome"] != "APPLIED" or item["attempt_fact"] != "ATTEMPTED" or
                    item["intent_ref"] is None or item["result_fact"] is None):
                reject("DEPENDENCY_UNRESOLVED", "predecessor lacks a committed sufficient APPLIED fact")
        if any(item["attempt_fact"] != "NOT_ATTEMPTED" for item in prefix_items[index:]):
            reject("PLAN_INTERRUPTED", "old attempted/interrupted plan tail cannot resume")
    for expected_action, effect in zip(actions[:index], delta):
        if (effect.get("action_id") != expected_action["action_id"] or
                effect.get("action_digest") != content_digest(expected_action) or
                effect.get("plan_ref") != artifact_ref(plan) or effect.get("effect_fault") not in ("applied", "response_lost_readable", "lost_response", "after_effect_exit")):
            reject("TARGET_CHANGED", "independent effect log contains unexplained change")
        check = compare_action_effect(expected_action, _view(observation), {"read_status": "OK", "view": _view(observation)})
        if check.effect_match != "MATCH":
            reject("DEPENDENCY_UNRESOLVED", "predecessor is not fully APPLIED in actual target")
    if index and delta[-1].get("target_state_hash") != observation.get("target_state_hash"):
        reject("TARGET_CHANGED", "target state changed after the committed applied prefix")
    if not index and (snapshot.payload.observed_hash != observation.get("target_state_hash") or
                      snapshot.payload.observed_version != observation.get("target_state_version")):
        reject("TARGET_CHANGED", "first dispatch actual business state differs from planned snapshot")
    return PublicRecord(plan_ref=artifact_ref(plan), action_id=action_id,
                        action_digest=content_digest(action), before_snapshot_ref=_plain(plan.payload.snapshot),
                        observed_snapshot_ref=observation.get("snapshot_ref"),
                        observation_id=observation["observation_id"], read_sequence=observation["read_sequence"],
                        target_key=observation["target_key"], source_ref=observation["source_ref"],
                        target_session_id=observation["target_session_id"], scope_id=plan.scope_id,
                        baseline_state_hash=snapshot.payload.observed_hash, current_state_hash=observation["target_state_hash"],
                        baseline_state_version=snapshot.payload.observed_version, current_state_version=observation["target_state_version"],
                        prepared_before=prepared_before, applied_prefix=list(progress_refs),
                        effect_log_delta=observation.get("effect_log_resource"), comparator_version="a02-facts-1")


def create_plan(bundle, graph_ref, precheck_ref, targetcheck_ref, snapshot_ref,
                current_snapshot_ref, policy_reference, config, *, artifact_id,
                created_at, run_id=None, operation="CREATE_FRAMES", previous_receipt=None, bridge_context=None):
    """Return a new validated bundle. Invalid/missing bindings raise ContractError.

    A valid failed-check chain yields a BLOCKED diagnostic plan with no actions.
    UPDATE is explicitly unsupported, including when a C01 baseline is provided.
    """
    bundle = validate_bundle(bundle, bridge_context=bridge_context)
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
    computed = analyze_target(bundle, graph_ref, snapshot_ref, current_snapshot_ref, policy_reference, config, bridge_context=bridge_context)
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
    if graph.schema_version == '1.4.0-a03-native-proposal':
        from annotation.contracts.a03_native import require_context
        require_context(bridge_context, bundle)('creation_anchor', bridge_context, bundle=bundle, config=config,
            artifact_id=artifact_id, created_at=created_at, run_id=run_id or graph.run_id)
    plan = make_artifact("ApplyPlan", artifact_id, graph, payload, [graph, pre, target, snapshot],
                         config.version, "a02-planner", created_at, run_id, bridge_context=bridge_context)
    output = append_artifacts(bundle, plan, bridge_context=bridge_context)
    if ready:
        assert_plan_ready(output, artifact_ref(plan), artifact_ref(current), bridge_context=getattr(output, "bridge_context", bridge_context))
    return output


def verify_generated_plan(bundle, plan, current_ref, config, *, observation_binding=None, bridge_context=None):
    """Recompute supported projection/facts before mock dispatch; refuse edited actions."""
    bundle = validate_bundle(bundle, bridge_context=bridge_context)
    if plan.schema_version == '1.4.0-a03-native-proposal':
        from annotation.contracts.a03_native import require_context
        return require_context(bridge_context, bundle)('verify_creation_anchor', bridge_context, bundle=bundle,
            plan=plan, current_ref=current_ref, config=config, observation_binding=observation_binding)
    payload = plan.payload
    if observation_binding is not None:
        binding = _plain(observation_binding)
        if plan.schema_version not in ("1.1.0-a-recovery-proposal", "1.4.0-a03-native-proposal"):
            reject("RECOVERY_VERSION_UNSUPPORTED", "observation bridge is recovery-version only")
        if (binding.get("plan_ref") != artifact_ref(plan) or
                binding.get("before_snapshot_ref") != _plain(payload.snapshot) or
                binding.get("observed_snapshot_ref") != _plain(current_ref)):
            reject("OBSERVATION_BINDING_MISMATCH", "fresh observation bridge does not bind exact plan/current refs")
        current_ref = payload.snapshot
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
    if plan.schema_version == "1.1.0-a-recovery-proposal":
        # This is an internal historical derivation, after validating the full
        # package above. Runtime result evidence that is not consumed by any
        # retained upstream Artifact must not refer back into the intentionally
        # removed plan/descendants. Retain the complete formal evidence closure
        # of every retained Artifact; never filter history in the admitted
        # bundle, return this view, or use it as current write eligibility.
        from pathlib import Path
        records = {record["evidence_id"]: record for record in data["evidence"]}
        needed, seen_resources = set(), set()
        root = Path(bundle.asset_root)
        evidence_fields = {"evidence_refs", "before_evidence_refs", "after_evidence_refs", "submission_evidence_refs"}

        def consume_evidence(evidence_id):
            if evidence_id in needed:
                return
            if evidence_id not in records:
                reject("MISSING_REFERENCE", "upstream formal evidence ID is absent")
            needed.add(evidence_id)
            consume(records[evidence_id]["resource"])

        def consume(value):
            if isinstance(value, list):
                for member in value:
                    consume(member)
            elif isinstance(value, dict):
                if {"path", "sha256", "media_type"}.issubset(value):
                    key = (value["path"], value["sha256"], value["media_type"])
                    if key not in seen_resources and value["media_type"] == "application/json":
                        seen_resources.add(key)
                        # Full validation already checked safe paths, bytes,
                        # all ordinary refs and mixed-resource cycle freedom.
                        consume(json.loads((root / value["path"]).read_text(encoding="utf-8")))
                else:
                    for name, child in value.items():
                        if name in evidence_fields and isinstance(child, list):
                            for member in child:
                                if isinstance(member, str):
                                    consume_evidence(member)
                        consume(child)

        for upstream_artifact in data["artifacts"]:
            consume(upstream_artifact)
        data["evidence"] = [record for record in data["evidence"] if record["evidence_id"] in needed]
    upstream = validate_bundle(data, asset_root=getattr(bundle, "asset_root", None))
    generated = create_plan(upstream, payload.graph, payload.precheck, payload.targetcheck,
                            payload.snapshot, current_ref, payload.policy, config,
                            artifact_id=plan.artifact_id, created_at=plan.created_at, run_id=plan.run_id)
    rebuilt = generated.artifacts[-1]
    if rebuilt != plan:
        reject("PLAN_CHANGED", "plan does not equal generated supported projection")
