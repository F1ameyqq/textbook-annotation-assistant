#!/usr/bin/env python3
"""Independent acceptance and negative tests for the real-Q1 A02 HOLD probe.

This script is intentionally read-only.  It validates the frozen mapping and
executed C01 bundle, then runs in-memory negative mutations through A's fixed
public contract/planner gates.  It never calls a platform, browser, OCR, or
model and never executes the historical Q22 fixture.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path


A_COMMIT = "37089f9e0229da76ae1c45461b7e63929590be56"
BOOK_ID = "46007447"
QID = "q-e92a499995ca1bbd570a2a09"
PIN_SHA256 = "3174f9981ffc336b3d576d78afe3e6932e042521011555272dc94d9b564e1fe0"


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref_dict(value) -> dict:
    return {key: getattr(value, key) for key in ("artifact_id", "revision", "kind", "content_hash")}


def exact(bundle, reference, kind: str | None = None):
    wanted = reference.model_dump(mode="json") if hasattr(reference, "model_dump") else reference
    matches = [item for item in bundle.artifacts
               if ref_dict(item) == wanted and (kind is None or item.kind == kind)]
    require(len(matches) == 1, f"exact {kind or 'artifact'} reference did not resolve uniquely: {wanted}")
    return matches[0]


def codes(error: BaseException) -> set[str]:
    return {item.get("code") for item in getattr(error, "issues", [])}


def expect_rejection(label, operation, expected_codes=()) -> dict:
    try:
        operation()
    except Exception as error:  # Pydantic can reject before ContractError exists.
        observed = sorted(code for code in codes(error) if code)
        if expected_codes and not set(expected_codes).intersection(observed):
            raise AuditFailure(
                f"{label} rejected, but not through an expected code; "
                f"expected={list(expected_codes)} observed={observed} error={error}"
            ) from error
        return {"label": label, "rejected": True, "codes": observed,
                "exception": type(error).__name__, "detail": str(error)}
    raise AuditFailure(label + " was incorrectly accepted")


def verify_a_pins(a_root: Path, pins_path: Path) -> int:
    require(sha256(pins_path) == PIN_SHA256, "A source pin file hash changed")
    pins = json.loads(pins_path.read_text(encoding="utf-8"))
    require(pins.get("a_commit") == A_COMMIT, "A source pin commit changed")
    expected = {row["path"]: row["sha256"] for row in pins["files"]}
    actual = {path.relative_to(a_root).as_posix(): sha256(path)
              for path in (a_root / "src").rglob("*")
              if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    require(actual == expected, "frozen A source inventory or bytes differ from the 76-file pin")
    return len(actual)


def verify_manifest(manifest_path: Path) -> int:
    """Verify the exact recursive inventory, excluding only the manifest itself."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = {row["path"]: row for row in manifest["files"]}
    base = manifest_path.parent
    actual = {
        path.relative_to(base).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in base.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    require(set(listed) == set(actual), "mapping manifest inventory is not exact")
    for relpath, observed in actual.items():
        require(listed[relpath]["bytes"] == observed["bytes"],
                f"mapping manifest size differs for {relpath}")
        require(listed[relpath]["sha256"] == observed["sha256"],
                f"mapping manifest digest differs for {relpath}")
    return len(actual)


def verify_portable_text_tree(root: Path) -> int:
    """Reject machine-local absolute paths in the portable mapping package."""
    pattern = re.compile(r"(?:[A-Za-z]:[\\/]|/Users/|/home/|\\.codex(?:[\\/]|$))")
    checked = 0
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md"}:
            checked += 1
            require(not pattern.search(path.read_text(encoding="utf-8")),
                    f"machine-local path leaked into portable mapping member {path.name}")
    return checked


def verify_append_only_chain(raw_bundles: list[dict]) -> None:
    for previous, current in zip(raw_bundles, raw_bundles[1:]):
        require(previous["format_version"] == current["format_version"],
                "format version changed across the stage chain")
        require(previous["policies"] == current["policies"],
                "policy bytes changed across the stage chain")
        require(current["evidence"][:len(previous["evidence"])] == previous["evidence"],
                "evidence history was rewritten across the stage chain")
        require(current["artifacts"][:len(previous["artifacts"])] == previous["artifacts"],
                "artifact history was rewritten across the stage chain")


def duplicate_geometry(regions) -> list[dict]:
    seen, duplicates = {}, []
    for region in regions:
        box = region.box if hasattr(region, "box") else region["box"]
        image = box.image if hasattr(box, "image") else box["image"]
        bbox = box.bbox if hasattr(box, "bbox") else box["bbox"]
        region_id = region.region_id if hasattr(region, "region_id") else region["region_id"]
        asset_id = image.asset_id if hasattr(image, "asset_id") else image["asset_id"]
        key = (asset_id, tuple(float(value) for value in bbox))
        if key in seen:
            duplicates.append({"asset_id": asset_id, "bbox": list(key[1]),
                               "region_ids": [seen[key], region_id]})
        else:
            seen[key] = region_id
    return duplicates


def minimal_bundle(bundle, artifacts: list[dict]) -> dict:
    return {"format_version": bundle.format_version,
            "evidence": [item.model_dump(mode="json") for item in bundle.evidence],
            "policies": [item.model_dump(mode="json") for item in bundle.policies],
            "artifacts": artifacts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a-root", type=Path, required=True)
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--mapping-manifest", type=Path, required=True)
    parser.add_argument("--expected-mapping-sha256", required=True)
    parser.add_argument("--executed", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--action-log", type=Path, required=True)
    parser.add_argument("--target-before", type=Path, required=True)
    parser.add_argument("--target-after", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    a_root = args.a_root.resolve()
    pins_path = args.pins.resolve()
    mapping_path = args.mapping.resolve()
    executed_path = args.executed.resolve()
    require(sha256(mapping_path) == args.expected_mapping_sha256.lower(),
            "mapping JSON differs from the independently frozen digest")
    pinned_count = verify_a_pins(a_root, pins_path)
    mapping_manifest_count = verify_manifest(args.mapping_manifest.resolve())
    portable_text_count = verify_portable_text_tree(mapping_path.parent)

    if any(name == "annotation" or name.startswith("annotation.") for name in sys.modules):
        raise AuditFailure("annotation was imported before the frozen A path was selected")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(a_root / "src"))

    from annotation.contracts import (  # pylint: disable=import-error,import-outside-toplevel
        artifact_ref, assert_plan_ready, load_bundle, policy_ref, seal_artifact,
        seal_policy, validate_bundle,
    )
    from annotation.delivery.planner import create_plan  # pylint: disable=import-error,import-outside-toplevel
    from annotation.quality.targetcheck import SimulationConfig  # pylint: disable=import-error,import-outside-toplevel

    stage_paths = [mapping_path,
                   executed_path.parent / "prechecked.json",
                   executed_path.parent / "targetchecked.json",
                   executed_path.parent / "planned.json",
                   executed_path]
    stage_bundles = [load_bundle(path, verify_assets=True) for path in stage_paths]
    raw_stage_bundles = [json.loads(path.read_text(encoding="utf-8")) for path in stage_paths]
    verify_append_only_chain(raw_stage_bundles)
    mapping = stage_bundles[0]
    final = stage_bundles[-1]
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    action_log = json.loads(args.action_log.read_text(encoding="utf-8"))
    before = json.loads(args.target_before.read_text(encoding="utf-8"))
    after = json.loads(args.target_after.read_text(encoding="utf-8"))

    plans = [item for item in final.artifacts if item.kind == "ApplyPlan"]
    require(len(plans) == 1, "executed bundle must contain one diagnostic ApplyPlan")
    plan = plans[0]
    graph = exact(final, plan.payload.graph, "QuestionGraph")
    pre = exact(final, plan.payload.precheck, "CheckReport")
    target = exact(final, plan.payload.targetcheck, "CheckReport")
    snapshot = exact(final, plan.payload.snapshot, "PlatformSnapshot")
    source = exact(final, graph.payload.source, "SourceBundle")
    evidence = exact(final, graph.payload.evidence, "EvidenceBundle")
    receipts = [item for item in final.artifacts if item.kind == "ExecutionReceipt"
                and item.payload.plan.model_dump(mode="json") == artifact_ref(plan)]
    require(len(receipts) == 1, "executed bundle must contain one receipt for the diagnostic plan")
    receipt = receipts[0]

    require(graph.book_id == source.book_id == evidence.book_id == BOOK_ID,
            "the mapping is not bound to book 46007447")
    require([question.question_id for question in graph.payload.questions] == [QID],
            "the graph is not the single intended Q1")
    require(all(item.producer.evidence_mode == "OBSERVED" for item in (source, evidence, graph, pre)),
            "real source/evidence/graph or B PRE_APPLY was relabelled synthetic")
    require(all(asset.provenance == "ORIGINAL" for asset in source.payload.assets),
            "real source asset provenance was relabelled")
    require(snapshot.producer.evidence_mode == "SYNTHETIC",
            "local diagnostic target must be explicitly synthetic")
    require(all(relation.status in ("UNRESOLVED", "AMBIGUOUS") and not relation.selected_fragment_ids
                for relation in graph.payload.answer_relations),
            "unapproved Q1 answer relation became SELECTED")
    require(not duplicate_geometry(evidence.payload.regions),
            "mapping contains exact duplicate region geometry under distinct IDs")

    pre_names = {check.check_id for check in pre.payload.checks}
    require(pre.payload.stage == "PRE_APPLY" and pre.payload.decision == "HOLD",
            "B diagnostic precheck is not PRE_APPLY/HOLD")
    require({"source_integrity", "structure", "answer_matching", "coverage", "policy"} <= pre_names,
            "B diagnostic precheck lacks a required five-check entry")
    require(pre.payload.issues and any(issue.blocks for issue in pre.payload.issues),
            "HOLD precheck lacks a specific blocking issue")
    require(target.payload.stage == "TARGET" and target.payload.decision != "PASS",
            "observed/unselected Q1 unexpectedly passed A02 TARGET")
    target_reasons = " ".join(issue.reason for issue in target.payload.issues)
    require("A02 only supports SYNTHETIC inputs" in target_reasons,
            "TARGET did not preserve A02's observed-input rejection")
    require("selected answer closure required" in target_reasons,
            "TARGET did not preserve the unresolved-answer rejection")

    blocked = list(dict.fromkeys(issue.issue_id for report in (pre, target)
                                 for issue in report.payload.issues if issue.blocks))
    require(plan.payload.readiness == "BLOCKED" and not plan.payload.actions,
            "diagnostic plan is executable or contains actions")
    require(plan.payload.blocked_issue_ids == blocked,
            "blocked plan does not carry the exact ordered blocking issue ledger")
    require(receipt.payload.execution_mode == "NOT_EXECUTED" and not receipt.payload.results
            and receipt.payload.write_disposition == "NOT_EXECUTED",
            "blocked receipt claims execution or results")
    require(action_log == [] and before == after,
            "blocked path changed target state or emitted an action log")
    require(summary.get("input_mapping_sha256") == args.expected_mapping_sha256.lower(),
            "summary does not bind the independently frozen mapping digest")
    require(summary.get("action_count") == summary.get("dispatch_count") == 0
            and summary.get("platform_requests") == summary.get("model_calls") == 0,
            "summary claims an action, dispatch, platform request, or model call")
    require(summary.get("business_acceptance") is False
            and summary.get("a_mapping_accepted") is False
            and summary.get("a_formal_pre_apply") is False
            and summary.get("positive_simulation_complete") is False,
            "summary overstates technical/business acceptance")

    negatives = []
    negatives.append(expect_rejection(
        "blocked plan eligibility",
        lambda: assert_plan_ready(final, artifact_ref(plan), artifact_ref(snapshot)),
        ("PLAN_BLOCKED",),
    ))

    # A different current snapshot invalidates the old target report/plan chain.
    changed_snapshot = snapshot.model_dump(mode="json")
    changed_snapshot["revision"] += 1
    changed_snapshot["payload"]["observed_version"] += "-qa-drift"
    changed_snapshot = seal_artifact(changed_snapshot)
    drift_data = final.model_dump(mode="json")
    drift_data["artifacts"].append(changed_snapshot)
    drift_bundle = validate_bundle(drift_data, asset_root=executed_path.parent)
    platform_directory = snapshot.payload.directories[0]
    config = SimulationConfig(book_id=BOOK_ID, target_id=snapshot.payload.target_id,
                              scope_id=graph.scope_id,
                              directory_map={q.directory_id: platform_directory
                                             for q in graph.payload.questions},
                              allowed_operations=())
    negatives.append(expect_rejection(
        "stale current snapshot",
        lambda: create_plan(drift_bundle, artifact_ref(graph), artifact_ref(pre), artifact_ref(target),
                            artifact_ref(snapshot), artifact_ref(changed_snapshot), policy_ref(final.policies[0]),
                            config, artifact_id="qa-stale-plan", created_at=plan.created_at),
        ("TARGET_CHANGED",),
    ))

    # Changing graph or policy cannot reuse the old PRE_APPLY/TARGET reports.
    changed_graph = graph.model_dump(mode="json")
    changed_graph["revision"] += 1
    changed_graph["payload"]["identity_notes"] += " QA drift"
    changed_graph = seal_artifact(changed_graph)
    graph_data = final.model_dump(mode="json")
    graph_data["artifacts"].append(changed_graph)
    graph_bundle = validate_bundle(graph_data, asset_root=executed_path.parent)
    negatives.append(expect_rejection(
        "changed graph with old precheck",
        lambda: create_plan(graph_bundle, artifact_ref(changed_graph), artifact_ref(pre), artifact_ref(target),
                            artifact_ref(snapshot), artifact_ref(snapshot), policy_ref(final.policies[0]), config,
                            artifact_id="qa-graph-drift-plan", created_at=plan.created_at),
        ("VERSION_CONFLICT",),
    ))
    changed_policy = final.policies[0].model_dump(mode="json")
    changed_policy["revision"] += 1
    changed_policy["source_notes"] = list(changed_policy["source_notes"]) + ["QA policy drift"]
    changed_policy = seal_policy(changed_policy)
    policy_data = final.model_dump(mode="json")
    policy_data["policies"].append(changed_policy)
    policy_bundle = validate_bundle(policy_data, asset_root=executed_path.parent)
    negatives.append(expect_rejection(
        "changed policy with old precheck",
        lambda: create_plan(policy_bundle, artifact_ref(graph), artifact_ref(pre), artifact_ref(target),
                            artifact_ref(snapshot), artifact_ref(snapshot), policy_ref(changed_policy), config,
                            artifact_id="qa-policy-drift-plan", created_at=plan.created_at),
        ("VERSION_CONFLICT",),
    ))

    # Source bytes/digest, invalid candidate references, and out-of-bounds boxes fail independently.
    map_source = next(item for item in mapping.artifacts if item.kind == "SourceBundle")
    map_evidence = next(item for item in mapping.artifacts if item.kind == "EvidenceBundle")
    map_graph = next(item for item in mapping.artifacts if item.kind == "QuestionGraph")
    bad_source = map_source.model_dump(mode="json")
    bad_source["payload"]["assets"][0]["sha256"] = "0" * 64
    bad_source = seal_artifact(bad_source)
    negatives.append(expect_rejection(
        "wrong source asset digest",
        lambda: validate_bundle(minimal_bundle(mapping, [bad_source]), asset_root=mapping_path.parent),
        ("RESOURCE_HASH",),
    ))
    bad_candidate = map_graph.model_dump(mode="json")
    bad_candidate["payload"]["answer_relations"][0]["candidate_fragment_ids"] = ["qa-missing-candidate"]
    bad_candidate = seal_artifact(bad_candidate)
    negatives.append(expect_rejection(
        "unknown answer candidate fragment",
        lambda: validate_bundle(minimal_bundle(mapping, [map_source.model_dump(mode="json"),
                                                          map_evidence.model_dump(mode="json"), bad_candidate]),
                                asset_root=mapping_path.parent),
        ("MISSING_REFERENCE",),
    ))
    bad_bounds = map_evidence.model_dump(mode="json")
    region = bad_bounds["payload"]["regions"][0]
    region["box"]["bbox"][2] = float(region["box"]["image"]["width"]) + 1.0
    negatives.append(expect_rejection(
        "out-of-bounds source box",
        lambda: seal_artifact(bad_bounds),
    ))

    # C01 permits exact duplicate geometry when IDs differ; the Q1 high-level guard must close it.
    duplicate = map_evidence.model_dump(mode="json")
    copied = copy.deepcopy(duplicate["payload"]["regions"][0])
    copied["region_id"] = "qa-duplicate-region"
    duplicate["payload"]["regions"].append(copied)
    duplicate = seal_artifact(duplicate)
    duplicate_bundle = validate_bundle(minimal_bundle(mapping, [map_source.model_dump(mode="json"), duplicate]),
                                       asset_root=mapping_path.parent)
    duplicate_evidence = next(item for item in duplicate_bundle.artifacts if item.kind == "EvidenceBundle")
    found = duplicate_geometry(duplicate_evidence.payload.regions)
    require(found, "duplicate-geometry negative control was not detected by the Q1 high-level guard")
    negatives.append({"label": "distinct IDs with duplicate geometry",
                      "generic_contract_accepted": True,
                      "q1_high_level_guard_rejected": True,
                      "duplicates": found})

    result = {
        "schema": "q1-a-hold-independent-acceptance/0.1",
        "accepted": True,
        "technical_scope": "negative gate closure only",
        "business_acceptance": False,
        "positive_simulation_complete": False,
        "a_commit": A_COMMIT,
        "a_source_members_verified": pinned_count,
        "mapping_sha256": args.expected_mapping_sha256.lower(),
        "mapping_manifest_sha256": sha256(args.mapping_manifest.resolve()),
        "mapping_manifest_members_verified": mapping_manifest_count,
        "portable_mapping_text_members_checked": portable_text_count,
        "stage_bundles_validated": [path.name for path in stage_paths],
        "stage_chain_append_only": True,
        "executed_sha256": sha256(executed_path),
        "question_id": QID,
        "pre_decision": pre.payload.decision,
        "target_decision": target.payload.decision,
        "plan_readiness": plan.payload.readiness,
        "receipt_execution_mode": receipt.payload.execution_mode,
        "write_disposition": receipt.payload.write_disposition,
        "action_log_empty": action_log == [],
        "target_state_unchanged": before == after,
        "negative_tests": negatives,
        "capability_boundary": [
            "OBSERVED source/graph plus SYNTHETIC diagnostic snapshot is valid only for this fail-closed diagnostic chain.",
            "No A formal PRE_APPLY, mapping acceptance, platform authorization, positive execution, content verification, or business PASS is established.",
            "Exact duplicate geometry is a Q1 high-level rejection, not a generic C01 guarantee.",
        ],
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditFailure as error:
        print(json.dumps({"accepted": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from error
