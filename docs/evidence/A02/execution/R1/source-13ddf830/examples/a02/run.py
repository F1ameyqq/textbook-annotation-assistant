"""Offline A02 demo: input -> computed target check -> plan -> mutation -> readback.

All inputs are SYNTHETIC and all execution is SIMULATED. Output must be a NEW directory.
The summary is a demo consumer, not a production postcheck/runtime implementation.
"""
import argparse
import json
from pathlib import Path
import shutil

from annotation.contracts import artifact_ref, load_bundle, policy_ref, write_bundle
from annotation.delivery.mock import FAULTS, MockSession
from annotation.delivery.planner import create_plan
from annotation.quality.targetcheck import (
    SimulationConfig, append_artifacts, check_target, coverage_for, make_artifact, resolve_artifact,
)

TIME = "2026-10-16T00:00:00Z"


def read_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["allowed_operations"] = tuple(data["allowed_operations"])
    return SimulationConfig(**data)


def summarize(bundle, receipt_ref, statuses, config):
    """Consume INDEPENDENT source.scope_manifest, including omitted/exception/skipped items."""
    receipt = resolve_artifact(bundle, receipt_ref, "ExecutionReceipt")
    plan = resolve_artifact(bundle, receipt.payload.plan, "ApplyPlan")
    graph = resolve_artifact(bundle, plan.payload.graph, "QuestionGraph")
    source = resolve_artifact(bundle, graph.payload.source, "SourceBundle")
    coverage, _ = coverage_for(bundle, graph)
    action_questions = {a.action_id: a.target.question_id for a in plan.payload.actions}
    states = {q: statuses.get(q, "PENDING") for q in source.payload.scope_manifest}
    for result in receipt.payload.results:
        if result.outcome == "UNKNOWN":
            states[action_questions[result.action_id]] = "UNKNOWN"
    all_applied = bool(receipt.payload.results) and all(r.outcome == "APPLIED" for r in receipt.payload.results)
    unknown = any(r.outcome == "UNKNOWN" for r in receipt.payload.results)
    frames = "PASS" if all_applied else "UNAVAILABLE" if unknown or not receipt.payload.results else "FAIL"
    evidence_refs = receipt.payload.results[-1].after_evidence_refs if receipt.payload.results else [bundle.evidence[0].evidence_id]
    wait_issue = {"issue_id": "issue-a02-content-" + receipt.artifact_id, "code": "CONTENT_MISMATCH",
                  "scope_type": "scope", "scope_id": graph.scope_id, "evidence_refs": evidence_refs,
                  "severity": "blocking", "blocks": ["COMPLETE"],
                  "suggested_strategy": {"strategy_id": "WAIT_CONTENT", "max_attempts": 0, "max_cost": 0.0},
                  "reason": "SYNTHETIC demo has no OCR/final content readback; content remains PENDING"}
    post = make_artifact("CheckReport", "demo-post-" + receipt.artifact_id, graph,
                         {"stage": "POST_APPLY", "subject": artifact_ref(receipt), "graph": artifact_ref(graph),
                          "policy": plan.payload.policy.model_dump(mode="json"), "snapshot": None, "receipt": artifact_ref(receipt),
                          "coverage": coverage, "checks": [
                              {"check_id": "frame_structure", "outcome": frames, "evidence_refs": evidence_refs,
                               "reason": "SIMULATED per-action independent readback comparison; no platform acceptance"},
                              {"check_id": "final_content", "outcome": "UNAVAILABLE", "evidence_refs": evidence_refs,
                               "reason": "final text/formula/image content not verified"}],
                          "issues": [wait_issue], "decision": "HOLD", "reason": "SYNTHETIC demo comparison; final content pending"},
                         [graph, receipt], config.version, "a02-demo-summary", TIME)
    unresolved = list(dict.fromkeys(receipt.payload.unresolved_issue_ids + [wait_issue["issue_id"]]))
    state = ("NEEDS_RECONCILIATION" if unknown else "CONTENT_PENDING" if all_applied and
             not any(s in ("EXCEPTION", "SKIPPED") for s in states.values()) else "NEEDS_REVIEW")
    batch = make_artifact("BatchReport", "demo-batch-" + receipt.artifact_id, graph,
                          {"source": artifact_ref(source), "graph": artifact_ref(graph), "receipt": artifact_ref(receipt),
                           "postcheck": artifact_ref(post), "scope_manifest": list(source.payload.scope_manifest),
                           "questions": [{"question_id": q, "state": states[q],
                                          "reason": "SYNTHETIC independent scope item; frames/content/submission kept distinct"}
                                         for q in source.payload.scope_manifest],
                           "total_expected": len(source.payload.scope_manifest), "coverage": coverage,
                           "cost": {"model_calls": 0, "amount": 0.0, "currency": "USD", "billing_status": "KNOWN", "human_minutes": 0.0},
                           "unresolved_issue_ids": unresolved, "submission_status": "NOT_SUBMITTED", "submission_evidence_refs": [],
                           "content_check_status": "PENDING", "frame_check_status": frames, "state": state},
                          [source, graph, receipt, post], config.version, "a02-demo-summary", TIME)
    return append_artifacts(bundle, post, batch)


def run(input_path, output, fault="applied", fault_index=0):
    input_path, output = Path(input_path), Path(output)
    if output.exists():
        raise FileExistsError("output must be a new directory; history is never overwritten")
    # Load/verify before copying, then verify portable resources again in the new root.
    load_bundle(input_path)
    shutil.copytree(input_path.parent, output)
    bundle = load_bundle(output / input_path.name)
    config = read_config(output / "config.json")
    statuses = json.loads((output / "scope-statuses.json").read_text(encoding="utf-8"))["statuses"]
    graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    snapshot = next(a for a in bundle.artifacts if a.kind == "PlatformSnapshot")
    pre = next(a for a in bundle.artifacts if a.kind == "CheckReport" and a.payload.stage == "PRE_APPLY")
    policy = bundle.policies[0]
    session = MockSession()
    session.register_target(bundle, artifact_ref(snapshot), asset_root=output)
    bundle = check_target(bundle, artifact_ref(graph), artifact_ref(snapshot), artifact_ref(session.read_snapshot(graph.book_id)),
                          policy_ref(policy), config, artifact_id="a02-targetcheck", created_at=TIME)
    target = bundle.artifacts[-1]
    bundle = create_plan(bundle, artifact_ref(graph), artifact_ref(pre), artifact_ref(target), artifact_ref(snapshot),
                         artifact_ref(session.read_snapshot(graph.book_id)), policy_ref(policy), config, artifact_id="a02-plan", created_at=TIME)
    plan = bundle.artifacts[-1]
    write_bundle(bundle, output / "planned.json")
    faults = {}
    if plan.payload.actions:
        if not 0 <= fault_index < len(plan.payload.actions):
            raise ValueError("fault-index is outside plan actions")
        faults[plan.payload.actions[fault_index].action_id] = fault
    bundle = session.execute(bundle, artifact_ref(plan), config, asset_root=output,
                             receipt_id="a02-receipt", created_at=TIME, faults=faults)
    receipt = next(a for a in bundle.artifacts if a.kind == "ExecutionReceipt" and a.artifact_id == "a02-receipt")
    write_bundle(bundle, output / "executed.json")
    bundle = summarize(bundle, artifact_ref(receipt), statuses, config)
    write_bundle(bundle, output / "final.json")
    # Independent re-load including all original and newly recorded resource bytes.
    load_bundle(output / "final.json")
    batch = next(a for a in bundle.artifacts if a.kind == "BatchReport")
    summary = {"provenance": "SYNTHETIC", "execution_mode": "SIMULATED", "fault": fault,
               "readiness": plan.payload.readiness, "outcomes": [r.outcome for r in receipt.payload.results],
               "write_disposition": receipt.payload.write_disposition, "book_paused": session.is_paused(graph.book_id),
               "target_question_count": len(session.read_target(graph.book_id)["target"]["questions"]),
               "target_frame_count": len(session.read_target(graph.book_id)["target"]["frames"]),
               "batch": batch.payload.model_dump(mode="json"), "platform_actions": 0, "model_calls": 0,
               "reconciliation_interface": "MISSING; in-session pause only; persistence/restart recovery belongs to A03"}
    for name, value in (("summary", summary), ("target-state", session.read_target(graph.book_id)),
                        ("action-log", session.action_log), ("receipt-history", session.receipt_history(graph.book_id))):
        with (output / (name + ".json")).open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
    print(json.dumps({k: summary[k] for k in ("readiness", "outcomes", "write_disposition", "book_paused", "target_frame_count")}, ensure_ascii=False))
    return bundle, session


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[2] / "tests/fixtures/a02/normal/input.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fault", choices=sorted(FAULTS), default="applied")
    parser.add_argument("--fault-index", type=int, default=0)
    args = parser.parse_args()
    run(args.input, args.output, args.fault, args.fault_index)
