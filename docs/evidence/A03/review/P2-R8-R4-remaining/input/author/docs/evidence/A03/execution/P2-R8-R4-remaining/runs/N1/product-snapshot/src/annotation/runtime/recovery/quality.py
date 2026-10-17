"""Synthetic recovery report projection; no target I/O or store authority.

Reports are new immutable consumers of complete validated receipts and exact
resolution heads. Partial progress and unknown/empty denominators remain
diagnostic values. Frame evidence never verifies final content or submission.
"""
import copy
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from annotation.contracts import (artifact_ref, content_digest, effective_recovery_outcomes,
    load_archive_bundle, seal_artifact, validate_recovery_bundle)
from annotation.quality.targetcheck import coverage_for, make_artifact, reject, resolve_artifact


@dataclass(frozen=True)
class QualityResult:
    bundle: object
    diagnostic: dict
    postcheck_ref: object = None
    batch_ref: object = None


def _plain(value):
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return copy.deepcopy(value)


def _head_results(bundle, plan):
    items = [a for a in bundle.artifacts if a.kind == "ReconciliationResult" and
             a.book_id == plan.book_id and a.scope_id == plan.scope_id and
             _plain(a.payload.plan_ref) == artifact_ref(plan)]
    ref_key = lambda ref: tuple(ref[key] for key in ("artifact_id", "revision", "kind", "content_hash"))
    previous = {ref_key(_plain(a.payload.previous_resolution_ref)) for a in items
                if a.payload.previous_resolution_ref is not None}
    heads = [a for a in items if ref_key(artifact_ref(a)) not in previous]
    heads.sort(key=lambda a: next(i for i, action in enumerate(plan.payload.actions)
                                  if action.action_id == a.payload.action_id))
    return heads


def _source_states(source, graph, statuses, outcomes, action_questions):
    manifest = source.payload.scope_manifest
    if manifest is None:
        return []
    statuses = dict(statuses or {})
    if set(statuses) - set(manifest):
        reject("DENOMINATOR_CHANGED", "status input names a question outside the exact source scope")
    if any(state not in ("PENDING", "EXCEPTION", "SKIPPED") for state in statuses.values()):
        reject("COMPLETION_GUARD", "caller statuses cannot manufacture content verification or save outcomes")
    graph_questions = {q.question_id for q in graph.payload.questions} if graph is not None else set()
    values = []
    for question_id in manifest:
        state = statuses.get(question_id, "PENDING" if question_id in graph_questions else "EXCEPTION")
        if any(outcome == "UNKNOWN" and action_questions.get(action_id) == question_id for action_id, outcome in outcomes.items()):
            state = "UNKNOWN"
        reason = ("source scope item is absent from the graph and remains counted" if question_id not in graph_questions else
                  "actual save remains unresolved" if state == "UNKNOWN" else
                  "synthetic scope item; final content and human submission remain unverified")
        values.append({"question_id": question_id, "state": state, "reason": reason})
    return values


def _diagnostic(source, graph, statuses, outcomes, action_questions, *, state, paused=False,
                unresolved=(), progress_ref=None, recovery_refs=()):
    manifest = _plain(source.payload.scope_manifest)
    return {"format_version": "a03-quality-diagnostic-1", "origin": "SYNTHETIC",
            "execution_mode": "SIMULATED", "authority": "DIAGNOSTIC_ONLY",
            "source_ref": artifact_ref(source), "scope_manifest": manifest,
            "total_expected": None if manifest is None else len(manifest),
            "questions": _source_states(source, graph, statuses, outcomes, action_questions),
            "effective_outcomes": copy.deepcopy(outcomes), "state": state,
            "scope_paused": paused, "pause_authority": "SAME_SCOPE_CONTRACT_ONLY",
            "unresolved": _plain(list(unresolved)), "progress_ref": _plain(progress_ref),
            "recovery_refs": _plain(list(recovery_refs)), "postcheck_ref": None, "batch_ref": None,
            "content_check_status": "PENDING", "submission_status": "NOT_SUBMITTED",
            "completion_ratio": None, "model_calls": 0, "platform_actions": 0}


def _declare_consumed(artifact, evidence, root):
    """Declare this consumer's ordinary refs through its formal resource graph."""
    refs, visited = {}, set()
    records = {record["evidence_id"]: record for record in evidence}
    fields = {"evidence_refs", "before_evidence_refs", "after_evidence_refs", "submission_evidence_refs"}
    def walk(value):
        if isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, dict):
            if set(value) == {"artifact_id", "revision", "kind", "content_hash"}:
                refs[tuple(value[k] for k in ("artifact_id", "revision", "kind", "content_hash"))] = value
            elif {"path", "sha256", "media_type"}.issubset(value):
                key = (value["path"], value["sha256"], value["media_type"])
                if value["media_type"] == "application/json" and key not in visited:
                    visited.add(key)
                    walk(json.loads((Path(root) / value["path"]).read_text(encoding="utf-8")))
            else:
                for name, child in value.items():
                    if name in fields and isinstance(child, list):
                        for member in child:
                            if isinstance(member, str):
                                if member not in records:
                                    reject("MISSING_REFERENCE", "report formal evidence ID is absent")
                                walk(records[member]["resource"])
                    walk(child)
    # The envelope is not a reference to itself.
    walk(artifact["payload"])
    walk(artifact["input_refs"])
    artifact["input_refs"] = list(refs.values())
    return seal_artifact(artifact)


def build_quality_report(bundle, *, target_key, source_ref=None, receipt_ref=None, progress_ref=None,
                         statuses=None, config_version, postcheck_id, batch_id, created_at, asset_root=None):
    """Produce new POST_APPLY/BatchReport, or a complete diagnostic projection.

    This same-scope value projection cannot clear runtime book pauses. The
    caller retains runtime's current all-scope scan and writes a new bundle.
    """
    bundle = validate_recovery_bundle(bundle, asset_root=asset_root)
    plan = graph = receipt = progress = None
    if receipt_ref is not None:
        receipt = resolve_artifact(bundle, receipt_ref, "ExecutionReceipt")
        plan = resolve_artifact(bundle, receipt.payload.plan, "ApplyPlan")
    if progress_ref is not None:
        progress = resolve_artifact(bundle, progress_ref, "ExecutionProgress")
        progress_plan = resolve_artifact(bundle, progress.payload.plan_ref, "ApplyPlan")
        if plan is not None and artifact_ref(plan) != artifact_ref(progress_plan):
            reject("BATCH_BINDING", "progress and receipt bind different plans")
        plan = progress_plan
    if plan is not None:
        graph = resolve_artifact(bundle, plan.payload.graph, "QuestionGraph")
        source = resolve_artifact(bundle, graph.payload.source, "SourceBundle")
        if source_ref is not None and _plain(source_ref) != artifact_ref(source):
            reject("SOURCE_BINDING", "requested source differs from the exact plan graph")
        if config_version != plan.producer.config_version:
            reject("AUTHORIZATION_CHANGED", "report configuration differs from its exact plan")
        snapshot = resolve_artifact(bundle, plan.payload.snapshot, "PlatformSnapshot")
        if target_key["target_id"] != snapshot.payload.target_id:
            reject("TARGET_IDENTITY_MISMATCH", "report target differs from its exact snapshot")
    elif source_ref is not None:
        source = resolve_artifact(bundle, source_ref, "SourceBundle")
    else:
        reject("MISSING_REFERENCE", "source, complete receipt or progress ref is required")
    if source.book_id != target_key["book_id"]:
        reject("TARGET_IDENTITY_MISMATCH", "report canonical book key differs from source")
    if receipt is not None:
        for result in receipt.payload.results:
            if result.intent_ref is not None:
                intent = resolve_artifact(bundle, result.intent_ref, "WriteIntent")
                if _plain(intent.payload.target_key) != target_key:
                    reject("TARGET_IDENTITY_MISMATCH", "receipt intent canonical target namespace differs")
    view = effective_recovery_outcomes(bundle, target_key=target_key, scope_id=source.scope_id)
    action_questions = {action.action_id: action.target.question_id for a in bundle.artifacts
                        if a.kind == "ApplyPlan" and a.book_id == source.book_id and a.scope_id == source.scope_id
                        for action in a.payload.actions}
    heads = _head_results(bundle, plan) if plan is not None else []
    head_refs = [artifact_ref(head) for head in heads]
    state = ("UNKNOWN_DENOMINATOR" if source.payload.scope_manifest is None else "NO_ACTIONS" if not source.payload.scope_manifest
             else "NEEDS_RECONCILIATION" if view.paused else "PARTIAL_PROGRESS")
    diagnostic = _diagnostic(source, graph, statuses, dict(view.outcomes), action_questions, state=state,
        paused=view.paused, unresolved=view.unresolved, progress_ref=progress_ref, recovery_refs=head_refs)
    if receipt is None or not source.payload.scope_manifest:
        diagnostic["report_kind"] = "DIAGNOSTIC_ONLY"
        return QualityResult(bundle, diagnostic)
    # Frozen CheckReport has one snapshot and requires exact original-receipt
    # binding. Do not invent a combined observation or retrofit an original ref.
    if any(_plain(head.payload.original_receipt_ref) != artifact_ref(receipt) for head in heads):
        diagnostic.update(state="REPORT_CONTRACT_GAP", reason_code="RECOVERY_RECEIPT_BINDING_UNREPRESENTABLE")
        return QualityResult(bundle, diagnostic)
    observed_refs = [_plain(head.payload.observed_snapshot_ref) for head in heads]
    if observed_refs and any(ref != observed_refs[0] for ref in observed_refs):
        diagnostic.update(state="REPORT_CONTRACT_GAP", reason_code="MULTIPLE_RECOVERY_SNAPSHOTS_UNREPRESENTABLE")
        return QualityResult(bundle, diagnostic)
    if any(a.artifact_id in (postcheck_id, batch_id) for a in bundle.artifacts) or postcheck_id == batch_id:
        reject("DUPLICATE_ID", "quality output identities must be new and distinct")
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if created.tzinfo is None or any(created < datetime.fromisoformat(h.payload.observed_at.replace("Z", "+00:00")) for h in heads):
        reject("OBSERVATION_NOT_FRESH", "new report cannot predate its consumed current resolution head")
    effective = {result.action_id: result.outcome for result in receipt.payload.results}
    effective.update({head.payload.action_id: {"RESOLVED_APPLIED": "APPLIED", "RESOLVED_NOT_APPLIED": "NOT_APPLIED",
                                              "STILL_UNKNOWN": "UNKNOWN"}[head.payload.resolution] for head in heads})
    all_applied = bool(effective) and all(value == "APPLIED" for value in effective.values())
    unknown = "UNKNOWN" in effective.values() or view.paused
    frames = "PASS" if all_applied else "UNAVAILABLE" if unknown or not effective else "FAIL"
    coverage, _ = coverage_for(bundle, graph)
    evidence = _plain(bundle.evidence)
    proof = list(receipt.payload.results[-1].after_evidence_refs) if receipt.payload.results else list(snapshot.payload.evidence_refs)
    for head in heads:
        resource = _plain(head.payload.readback)
        if resource is not None:
            evidence_id = "proof-quality-" + content_digest({"postcheck": postcheck_id, "resource": resource})[:32]
            if not any(record["evidence_id"] == evidence_id for record in evidence):
                evidence.append({"evidence_id": evidence_id, "resource": resource, "mode": "SYNTHETIC",
                                 "description": "actual immutable recovery observation consumed by this new report"})
            proof.append(evidence_id)
    proof = list(dict.fromkeys(proof))
    if not proof:
        reject("MISSING_REFERENCE", "report requires actual receipt or observation evidence")
    token = content_digest({"postcheck": postcheck_id, "receipt": artifact_ref(receipt)})[:28]
    issues = [{"issue_id": "issue-quality-content-" + token, "code": "CONTENT_MISMATCH", "scope_type": "scope",
               "scope_id": graph.scope_id, "evidence_refs": proof, "severity": "blocking", "blocks": ["COMPLETE"],
               "suggested_strategy": {"strategy_id": "WAIT_CONTENT", "max_attempts": 0, "max_cost": 0.0},
               "reason": "synthetic frame evidence does not verify final text, formula, image content or human submission"}]
    if unknown:
        issues.append({"issue_id": "issue-quality-save-" + token, "code": "SAVE_UNKNOWN", "scope_type": "scope",
                       "scope_id": graph.scope_id, "evidence_refs": proof, "severity": "blocking", "blocks": ["APPLY", "COMPLETE"],
                       "suggested_strategy": {"strategy_id": "RECONCILE", "max_attempts": 0, "max_cost": 0.0},
                       "reason": "current same-scope unresolved save obligations remain counted; no replay is allowed"})
    report_snapshot = observed_refs[0] if observed_refs else None
    if not heads and receipt.payload.action_fact_refs:
        last_fact = json.loads((bundle.asset_root / receipt.payload.action_fact_refs[-1].path).read_text(encoding="utf-8"))
        report_snapshot = last_fact["observed_snapshot_ref"]
    if report_snapshot is not None:
        actual_snapshot = resolve_artifact(bundle, report_snapshot, "PlatformSnapshot")
        if created < datetime.fromisoformat(actual_snapshot.payload.observed_at.replace("Z", "+00:00")):
            reject("OBSERVATION_NOT_FRESH", "new report cannot predate its actual receipt readback")
    dependencies = [source, graph, plan, receipt] + heads
    if report_snapshot is not None:
        dependencies.append(resolve_artifact(bundle, report_snapshot, "PlatformSnapshot"))
    post = make_artifact("CheckReport", postcheck_id, plan,
        {"stage": "POST_APPLY", "subject": artifact_ref(receipt), "graph": artifact_ref(graph),
         "policy": _plain(plan.payload.policy), "snapshot": report_snapshot, "receipt": artifact_ref(receipt),
         "coverage": coverage, "checks": [
             {"check_id": "frame_structure", "outcome": frames, "evidence_refs": proof,
              "reason": "effective committed action facts and exact current recovery chain heads"},
             {"check_id": "final_content", "outcome": "UNAVAILABLE", "evidence_refs": proof,
              "reason": "final content has no independent verification"}],
         "issues": issues, "decision": "HOLD", "reason": "synthetic recovery projection; final content remains pending",
         "recovery_refs": head_refs}, dependencies, config_version, "a03-runtime-quality", created_at)
    post = _declare_consumed(post, evidence, bundle.asset_root)
    states = _source_states(source, graph, statuses, dict(view.outcomes), action_questions)
    batch_state = "NEEDS_RECONCILIATION" if unknown else "CONTENT_PENDING" if all_applied and not any(
        item["state"] in ("EXCEPTION", "SKIPPED") for item in states) else "NEEDS_REVIEW"
    unresolved = list(plan.payload.blocked_issue_ids) + [issue["issue_id"] for issue in issues]
    batch = make_artifact("BatchReport", batch_id, plan,
        {"source": artifact_ref(source), "graph": artifact_ref(graph), "receipt": artifact_ref(receipt),
         "postcheck": artifact_ref(post), "scope_manifest": list(source.payload.scope_manifest), "questions": states,
         "total_expected": len(source.payload.scope_manifest), "coverage": coverage,
         "cost": {"model_calls": 0, "amount": 0.0, "currency": "USD", "billing_status": "KNOWN", "human_minutes": 0.0},
         "unresolved_issue_ids": list(dict.fromkeys(unresolved)), "submission_status": "NOT_SUBMITTED",
         "submission_evidence_refs": [], "content_check_status": "PENDING", "frame_check_status": frames,
         "state": batch_state, "recovery_refs": head_refs, "progress_refs": [_plain(progress_ref)] if progress_ref else []},
        dependencies + [post] + ([progress] if progress is not None else []), config_version, "a03-runtime-quality", created_at)
    batch = _declare_consumed(batch, evidence, bundle.asset_root)
    data = bundle.model_dump()
    data["evidence"] = evidence
    data["artifacts"].extend([post, batch])
    output = validate_recovery_bundle(data, asset_root=bundle.asset_root)
    diagnostic.update(state=batch_state, postcheck_ref=artifact_ref(post), batch_ref=artifact_ref(batch),
                      effective_outcomes=effective, frame_check_status=frames)
    return QualityResult(output, diagnostic, artifact_ref(post), artifact_ref(batch))


def describe_archived_source(archive, *, source_ref, statuses=None):
    """Unknown denominator stays an archive-only diagnostic, never admission."""
    if not isinstance(archive, dict) or archive.get("eligibility") != "ARCHIVE_ONLY":
        reject("ARCHIVE_REQUIRED", "use the explicit public archive loader")
    current = load_archive_bundle(archive["path"], verify_assets=True)
    if current.sha256 != archive.get("sha256"):
        reject("RESOURCE_HASH_MISMATCH", "archive bytes changed after selection")
    data = current.bundle
    if any(a["producer"]["evidence_mode"] != "SYNTHETIC" for a in data["artifacts"]) or any(
            item["mode"] != "SYNTHETIC" for item in data["evidence"]):
        reject("SYNTHETIC_ONLY", "this diagnostic scope is all synthetic")
    checked_resources = set()
    def synthetic(value):
        if isinstance(value, list):
            for member in value:
                synthetic(member)
        elif isinstance(value, dict):
            if (value.get("origin", "SYNTHETIC") != "SYNTHETIC" or
                    value.get("provenance", "SYNTHETIC") != "SYNTHETIC" or value.get("mode") == "OBSERVED" or
                    "execution_mode" in value and value["execution_mode"] not in ("SIMULATED", "NOT_EXECUTED") or
                    "region_id" in value and value.get("source", "SYNTHETIC") != "SYNTHETIC" or
                    "clue_id" in value and value.get("source", "SYNTHETIC") != "SYNTHETIC"):
                reject("SYNTHETIC_ONLY", "archive diagnostic cannot relabel real or observed material")
            if {"path", "sha256", "media_type"}.issubset(value) and value["media_type"] == "application/json":
                key = (value["path"], value["sha256"])
                if key not in checked_resources:
                    checked_resources.add(key)
                    synthetic(json.loads((Path(current.path).parent / value["path"]).read_text(encoding="utf-8")))
            for child in value.values():
                synthetic(child)
    synthetic(data)
    source = next((a for a in data["artifacts"] if artifact_ref(a) == _plain(source_ref) and a["kind"] == "SourceBundle"), None)
    if source is None:
        reject("MISSING_REFERENCE", "exact archived source is absent")
    manifest = source["payload"]["scope_manifest"]
    graphs = [a for a in data["artifacts"] if a["kind"] == "QuestionGraph" and
              a["book_id"] == source["book_id"] and a["scope_id"] == source["scope_id"] and
              a["payload"]["source"] == artifact_ref(source)]
    state = "UNKNOWN_DENOMINATOR" if manifest is None else "NO_ACTIONS" if not manifest else "ARCHIVED_SCOPE_ONLY"
    diagnostic = {"format_version": "a03-quality-diagnostic-1", "origin": "SYNTHETIC", "authority": "ARCHIVE_ONLY",
                  "state": state, "scope_manifest": copy.deepcopy(manifest), "total_expected": None if manifest is None else len(manifest),
                  "source_ref": artifact_ref(source), "completion_ratio": None, "postcheck_ref": None, "batch_ref": None,
                  "content_check_status": "PENDING", "submission_status": "NOT_SUBMITTED",
                  "questions": _source_states(source, graphs[0] if len(graphs) == 1 else None, statuses, {}, {}),
                  "provided_statuses": copy.deepcopy(statuses or {}), "model_calls": 0, "platform_actions": 0}
    return diagnostic
