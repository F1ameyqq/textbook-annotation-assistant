"""A02 target checks. Pure, synthetic-only; no target mutation or I/O."""
from dataclasses import asdict, dataclass
from typing import Dict, Tuple

from annotation.contracts import (
    ContractError, artifact_ref, content_digest, policy_ref, seal_artifact,
    validate_bundle,
)

VERSION = "a02-1"


@dataclass(frozen=True)
class SimulationConfig:
    """Local simulation authorization, not an extension of the C01 contract.

    Directory namespaces are connected explicitly here, never by string equality.
    The entire configuration is bound by CheckReport/ApplyPlan producer.config_version.
    """
    book_id: str
    target_id: str
    scope_id: str
    directory_map: Dict[str, str]
    session_mode: str = "SAME_SESSION_HANDOFF"
    allowed_operations: Tuple[str, ...] = ("CREATE_FRAMES",)

    @property
    def version(self):
        return "a02-config-" + content_digest(asdict(self))


def reject(code, message, path="$.a02"):
    raise ContractError([{"path": path, "code": code, "message": message}])


def resolve_artifact(bundle, reference, kind=None):
    ref = reference.model_dump(mode="json") if hasattr(reference, "model_dump") else reference
    for item in bundle.artifacts:
        if artifact_ref(item) == ref and (kind is None or item.kind == kind):
            return item
    reject("MISSING_REFERENCE", "exact artifact reference not found: " + str(ref))


def resolve_policy(bundle, reference):
    ref = reference.model_dump(mode="json") if hasattr(reference, "model_dump") else reference
    for item in bundle.policies:
        if policy_ref(item) == ref:
            return item
    reject("POLICY_CONFLICT", "exact policy reference not found")


def make_artifact(kind, identity, anchor, payload, dependencies, config_version,
                  module, created_at, run_id=None):
    """Seal using C01's single structural authority; no local contract definitions."""
    payload = dict(payload)
    if anchor.schema_version == "1.1.0-a-recovery-proposal" and kind == "CheckReport":
        payload.setdefault("recovery_refs", [])
    refs = [artifact_ref(item) for item in dependencies]
    refs = list({(r["artifact_id"], r["revision"]): r for r in refs}.values())
    policies = [payload["policy"]] if "policy" in payload else [
        p.model_dump(mode="json") for p in anchor.producer.policy_versions]
    return seal_artifact({
        "schema_version": anchor.schema_version, "artifact_id": identity,
        "revision": 1, "kind": kind, "run_id": run_id or anchor.run_id,
        "book_id": anchor.book_id, "scope_id": anchor.scope_id, "input_refs": refs,
        "producer": {"module": module, "implementation_version": VERSION,
                     "config_version": config_version, "policy_versions": policies,
                     "model_version": None, "prompt_version": None,
                     "evidence_mode": "SYNTHETIC"},
        "created_at": created_at, "payload": payload,
    })


def append_artifacts(bundle, *artifacts, asset_root=None):
    if asset_root is None:
        asset_root = getattr(bundle, "asset_root", None)
    data = bundle.model_dump(mode="json")
    data["artifacts"].extend(artifacts)
    return validate_bundle(data, asset_root=asset_root)


def coverage_for(bundle, graph):
    source = resolve_artifact(bundle, graph.payload.source, "SourceBundle")
    evidence = resolve_artifact(bundle, graph.payload.evidence, "EvidenceBundle")
    owned = {f for q in graph.payload.questions for f in q.fragment_ids + q.shared_fragment_ids}
    owned.update(f for r in graph.payload.answer_relations for f in r.selected_fragment_ids)
    assigned = {r for f in graph.payload.fragments if f.fragment_id in owned for r in f.region_ids}
    unassigned = {r for c in evidence.payload.coverage_clues if c.disposition == "UNASSIGNED"
                  for r in c.region_ids}
    unassigned.update(r.region_id for r in evidence.payload.regions if r.region_id not in assigned)
    coverage = {"scope_id": graph.scope_id, "pages_expected": source.payload.pages_expected,
                "pages_checked": source.payload.pages_acquired,
                "clue_ids": [c.clue_id for c in evidence.payload.coverage_clues],
                "unassigned_region_ids": sorted(unassigned)}
    complete = (set(source.payload.scope_manifest) == {q.question_id for q in graph.payload.questions}
                and set(source.payload.pages_expected) == set(source.payload.pages_acquired)
                and not unassigned
                and all(c.disposition != "UNASSIGNED" for c in evidence.payload.coverage_clues))
    return coverage, complete


def projection_frames(bundle, graph, question, policy):
    """Project owned/selected original regions; never select candidate answers by label."""
    evidence = resolve_artifact(bundle, graph.payload.evidence, "EvidenceBundle")
    regions = {r.region_id: r for r in evidence.payload.regions}
    selected = {f for rel in graph.payload.answer_relations if rel.question_id == question.question_id
                for f in rel.selected_fragment_ids}
    direct = set(question.fragment_ids + question.shared_fragment_ids)
    fragments = [f for f in graph.payload.fragments
                 if (f.fragment_id in selected or
                     (f.fragment_id in direct and f.role not in ("answer", "explanation")))]
    frames = []
    for fragment in sorted(fragments, key=lambda f: (f.reading_order, f.fragment_id)):
        for region_id in fragment.region_ids:
            region = regions[region_id]
            frames.append({"fragment_id": fragment.fragment_id, "region_id": region_id,
                           "box": region.box.model_dump(mode="json"),
                           "platform_role": policy.role_mapping[fragment.role],
                           "platform_type": "text" if fragment.content_type == "formula" else fragment.content_type})
    return frames


def analyze_target(bundle, graph_ref, snapshot_ref, current_snapshot_ref, policy_reference, config):
    """Compute TARGET payload from facts, independent of any input CheckReport decision."""
    bundle = validate_bundle(bundle)
    graph = resolve_artifact(bundle, graph_ref, "QuestionGraph")
    snapshot = resolve_artifact(bundle, snapshot_ref, "PlatformSnapshot")
    current = resolve_artifact(bundle, current_snapshot_ref, "PlatformSnapshot")
    policy = resolve_policy(bundle, policy_reference)
    source = resolve_artifact(bundle, graph.payload.source, "SourceBundle")
    evidence = resolve_artifact(bundle, graph.payload.evidence, "EvidenceBundle")
    proof = list(snapshot.payload.evidence_refs)
    coverage, complete = coverage_for(bundle, graph)
    checks, issues = [], []
    token = content_digest({"graph": artifact_ref(graph), "snapshot": artifact_ref(snapshot),
                            "current": artifact_ref(current), "config": config.version,
                            "policy": policy_ref(policy)})[:20]

    def check(name, problems, code, strategy="HUMAN_REVIEW"):
        checks.append({"check_id": name, "outcome": "FAIL" if problems else "PASS",
                       "evidence_refs": proof, "reason": "; ".join(problems) if problems else
                       "SYNTHETIC facts checked by A02: " + name})
        if problems:
            issues.append({"issue_id": "issue-a02-" + token + "-" + name,
                           "code": code, "scope_type": "scope", "scope_id": graph.scope_id,
                           "evidence_refs": proof, "severity": "blocking", "blocks": ["PLAN", "APPLY"],
                           "suggested_strategy": {"strategy_id": strategy, "max_attempts": 0, "max_cost": 0.0},
                           "reason": "; ".join(problems)})

    target_problems = []
    if artifact_ref(snapshot) != artifact_ref(current):
        target_problems.append("current snapshot revision/hash differs from checked snapshot")
    platform = {q.platform_question_id: q for q in snapshot.payload.questions}
    mapped = []
    for q in graph.payload.questions:
        ext = q.external_refs
        if ext.platform_question_id is not None:
            existing = platform.get(ext.platform_question_id)
            mapped.append(ext.platform_question_id)
            if not ext.platform_question_id or existing is None:
                target_problems.append(q.question_id + ": mapped platform question ID absent/empty")
            elif ext.platform_order is not None and ext.platform_order != existing.platform_order:
                target_problems.append(q.question_id + ": mapped platform order differs")
            elif config.directory_map.get(q.directory_id) != existing.directory_id:
                target_problems.append(q.question_id + ": explicit directory mapping differs")
        elif ext.platform_order is not None:
            target_problems.append(q.question_id + ": unmapped new question cannot claim an existing order")
    if len(set(mapped)) != len(mapped):
        target_problems.append("multiple internal questions share one platform ID; projection unsupported")
    if graph.schema_version == "1.1.0-a-recovery-proposal":
        from annotation.contracts import effective_recovery_outcomes
        # Namespace is fixed by the actual runtime target. Same-scope public
        # eligibility can infer it only from exact locally bound intent inputs.
        keys = [a.payload.target_key.model_dump(mode="json") for a in bundle.artifacts
                if a.kind == "WriteIntent" and a.book_id == graph.book_id and a.scope_id == graph.scope_id
                and a.payload.target_key.target_id == snapshot.payload.target_id]
        if len({content_digest(k) for k in keys}) > 1:
            reject("TARGET_IDENTITY_MISMATCH", "same target has conflicting canonical namespace bindings")
        unknown = (effective_recovery_outcomes(bundle, target_key=keys[0], scope_id=graph.scope_id).paused
                   if keys else any(a.kind == "ExecutionReceipt" and a.book_id == graph.book_id and
                                    any(r.outcome == "UNKNOWN" for r in a.payload.results) for a in bundle.artifacts))
    else:
        unknown = any(a.kind == "ExecutionReceipt" and a.book_id == graph.book_id and
                      any(r.outcome == "UNKNOWN" for r in a.payload.results) for a in bundle.artifacts)
    if unknown:
        target_problems.append("same book has unresolved UNKNOWN history; reconciliation interface missing")
    check("target_version", target_problems, "TARGET_CHANGED", "RECHECK_TARGET")

    auth_problems = []
    if (config.book_id != graph.book_id or config.book_id != snapshot.book_id or
            config.target_id != snapshot.payload.target_id or config.scope_id != graph.scope_id or
            config.scope_id != snapshot.scope_id or config.scope_id != snapshot.payload.authorized_scope_id):
        auth_problems.append("authorization book/target/scope differs from graph or snapshot")
    if "CREATE_FRAMES" not in config.allowed_operations:
        auth_problems.append("CREATE_FRAMES is not authorized")
    for q in graph.payload.questions:
        if config.directory_map.get(q.directory_id) not in snapshot.payload.directories:
            auth_problems.append(q.question_id + ": explicit platform directory not authorized/present")
    check("authorized_scope", auth_problems, "TARGET_CHANGED")

    cap_problems = []
    if config.session_mode not in ("PERSISTENT", "SAME_SESSION_HANDOFF"):
        cap_problems.append("unsupported session_mode")
    required = ["frame_readback", "persistent_draft" if config.session_mode == "PERSISTENT" else "same_session_handoff"]
    caps = {c.name: c for c in snapshot.payload.capabilities}
    for name in required:
        cap = caps.get(name)
        if cap is None or cap.status != "VERIFIED" or not cap.evidence_refs:
            cap_problems.append(name + ": capability not VERIFIED with evidence")
        elif cap.platform_version != snapshot.payload.platform_version:
            cap_problems.append(name + ": capability applies to a different platform version")
    check("capabilities", cap_problems, "TARGET_CHANGED")

    policy_problems = []
    if policy.confirmation_status == "UNRESOLVED":
        policy_problems.append("policy confirmation is UNRESOLVED")
    if any(a.producer.evidence_mode != "SYNTHETIC" for a in (graph, snapshot, source, evidence)):
        policy_problems.append("A02 only supports SYNTHETIC inputs")
    for q in graph.payload.questions:
        if q.question_type not in ("free_response", "ordinary_choice") or q.parent_question_id is not None:
            policy_problems.append(q.question_id + ": unsupported combination/seven-choice/parent-child projection")
        if q.question_type == "ordinary_choice" and not (
                policy.confirmation_status == "SYNTHETIC_ASSUMPTION" and
                policy.applicability == "SYNTHETIC_ONLY" and policy.option_grouping == "SEPARATE"):
            policy_problems.append(q.question_id + ": choice needs explicit synthetic SEPARATE assumption")
        if q.question_type == "free_response" and any(f.role == "option" for f in graph.payload.fragments
                                                       if f.fragment_id in q.fragment_ids):
            policy_problems.append(q.question_id + ": free-response option projection unsupported")
        relations = [r for r in graph.payload.answer_relations if r.question_id == q.question_id]
        if not relations or any(r.status != "SELECTED" or not r.selected_fragment_ids for r in relations):
            policy_problems.append(q.question_id + ": selected answer closure required")
        if q.external_refs.platform_question_id is not None and any(
                f.platform_question_id == q.external_refs.platform_question_id for f in snapshot.payload.frames):
            policy_problems.append(q.question_id + ": existing frames need UPDATE_FRAMES; A02 delta unsupported")
    unresolved_policy = policy.confirmation_status == "UNRESOLVED" or (
        policy.option_grouping == "UNRESOLVED" and
        any(q.question_type == "ordinary_choice" for q in graph.payload.questions))
    check("policy", policy_problems, "POLICY_UNRESOLVED" if unresolved_policy else "UNSUPPORTED_LAYOUT")
    check("coverage", [] if complete else ["independent scope/pages/clues are incomplete"], "UNASSIGNED_CONTENT")
    decision = "PASS" if not issues else "EXCEPTION" if policy_problems or not complete else "HOLD"
    result = {"stage": "TARGET", "subject": artifact_ref(snapshot), "graph": artifact_ref(graph),
            "policy": policy_ref(policy), "snapshot": artifact_ref(snapshot), "receipt": None,
            "coverage": coverage, "checks": checks, "issues": issues, "decision": decision,
            "reason": "SYNTHETIC target conditions computed by A02; no algorithm or platform acceptance"}
    if graph.schema_version == "1.1.0-a-recovery-proposal":
        result["recovery_refs"] = []
    return result


def check_target(bundle, graph_ref, snapshot_ref, current_snapshot_ref, policy_reference, config,
                 *, artifact_id, created_at, run_id=None):
    bundle = validate_bundle(bundle)
    graph = resolve_artifact(bundle, graph_ref, "QuestionGraph")
    snapshot = resolve_artifact(bundle, snapshot_ref, "PlatformSnapshot")
    current = resolve_artifact(bundle, current_snapshot_ref, "PlatformSnapshot")
    payload = analyze_target(bundle, graph_ref, snapshot_ref, current_snapshot_ref, policy_reference, config)
    report = make_artifact("CheckReport", artifact_id, graph, payload, [graph, snapshot, current],
                           config.version, "a02-targetcheck", created_at, run_id)
    return append_artifacts(bundle, report)
