"""Independent A02 probes for EXCLUDED coverage and evidence provenance labels.

This script imports only public APIs from the fixed Git-blob export.  It never
imports the mock executor, opens a browser, calls a model, or writes a platform.
The runner must supply a new output directory; evidence is never overwritten.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys


FROZEN_COMMIT = "5c9285720c8628c5198bedeadfc9f6bc7826a914"
FROZEN_ROOT = Path("D:/1800/.local/stages/A02-review/frozen-5c928572")
FROZEN_SRC = FROZEN_ROOT / "src"
ORIGIN = FROZEN_ROOT / "tests/fixtures/a02/normal"
TIME = "2026-10-16T00:00:00Z"
HEADER_REGION = "region-review-excluded-header"
HEADER_CLUE = "clue-review-excluded-header"


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def ref_key(reference):
    return tuple(reference[name] for name in ("artifact_id", "revision", "kind", "content_hash"))


def reseal_dependencies(data, case, artifact_ref, seal_artifact, seal_policy):
    """Create new revisions and rebind every exact artifact dependency publicly."""
    result = deepcopy(data)
    pending = list(result["artifacts"])
    sealed = []
    replacements = {}

    def rebind(value):
        if isinstance(value, dict):
            if set(value) == {"artifact_id", "revision", "kind", "content_hash"}:
                return deepcopy(replacements.get(ref_key(value), value))
            return {key: rebind(child) for key, child in value.items()}
        if isinstance(value, list):
            return [rebind(child) for child in value]
        return value

    while pending:
        progressed = False
        for old in list(pending):
            if any(ref_key(ref) not in replacements for ref in old["input_refs"]):
                continue
            new = rebind(old)
            new["revision"] += 1
            new["run_id"] = "review-coverage-labels-" + case
            new["created_at"] = TIME
            new["producer"]["config_version"] = "review-coverage-labels-" + case
            new = seal_artifact(new)
            replacements[ref_key(artifact_ref(old))] = artifact_ref(new)
            sealed.append(new)
            pending.remove(old)
            progressed = True
        if not progressed:
            raise ValueError("probe input has an unresolved or cyclic dependency")
    result["artifacts"] = sealed
    result["policies"] = [seal_policy(policy) for policy in result["policies"]]
    return result


def artifact(data, kind, stage=None):
    matches = [item for item in data["artifacts"] if item["kind"] == kind and
               (stage is None or item["payload"].get("stage") == stage)]
    if len(matches) != 1:
        raise ValueError("probe requires one {} {}".format(kind, stage or ""))
    return matches[0]


def build_excluded_header(data):
    evidence = artifact(data, "EvidenceBundle")
    pre = artifact(data, "CheckReport", "PRE_APPLY")
    region = deepcopy(evidence["payload"]["regions"][0])
    region.update(region_id=HEADER_REGION, content_type="text",
                  text="SYNTHETIC page header: Unit A", source="SYNTHETIC",
                  printed_number_candidates=[], certainty="CONFIRMED")
    region["box"]["bbox"] = [5.0, 0.0, 65.0, 4.0]
    evidence["payload"]["regions"].append(region)
    # C01 requires EXCLUDED.region_ids=[]; the exact original-image box joins
    # this independent non-question exclusion to the header region semantically.
    clue = {"clue_id": HEADER_CLUE, "box": deepcopy(region["box"]),
            "source": "SYNTHETIC", "disposition": "EXCLUDED", "region_ids": [],
            "reason": "SYNTHETIC independent inventory: this page header is non-question content, explicitly excluded; scope questions are unchanged.",
            "evidence_refs": list(region["evidence_refs"])}
    evidence["payload"]["coverage_clues"].append(clue)
    pre["payload"]["coverage"]["clue_ids"].append(HEADER_CLUE)
    pre["payload"]["reason"] = (
        "SYNTHETIC PRE_APPLY CONTRACT STUB; includes an explicit non-question header exclusion; not algorithm quality evidence.")
    if pre["payload"]["decision"] != "PASS" or pre["payload"]["coverage"]["unassigned_region_ids"]:
        raise ValueError("excluded-header probe requires an otherwise passing PRE_APPLY")
    return {"added_region_id": HEADER_REGION, "added_clue_id": HEADER_CLUE,
            "exclusion_box": deepcopy(region["box"]), "exclusion_region_ids": [],
            "required_behavior": "An explicit non-question EXCLUDED header must not become unassigned question content."}


def build_observed_evidence_label(data):
    snapshot = artifact(data, "PlatformSnapshot")
    evidence_id = snapshot["payload"]["evidence_refs"][0]
    record = next(item for item in data["evidence"] if item["evidence_id"] == evidence_id)
    original_mode = record["mode"]
    record["mode"] = "OBSERVED"
    return {"changed_evidence_id": evidence_id, "original_mode": original_mode,
            "injected_mode": "OBSERVED",
            "construction_note": "The bytes remain fabricated SYNTHETIC fixture material. OBSERVED is a deliberate fault-injected label, not a claim of platform observation.",
            "required_behavior": "A02's all-inputs/all-evidence SYNTHETIC restriction must reject an actively referenced OBSERVED registry label."}


def run_case(case, destination, api):
    (artifact_ref, load_bundle, policy_ref, seal_artifact, seal_policy,
     validate_bundle, write_bundle, SimulationConfig, check_target, create_plan) = api
    destination.mkdir()
    shutil.copytree(ORIGIN / "assets", destination / "assets")
    shutil.copyfile(ORIGIN / "config.json", destination / "config.json")
    base = load_bundle(ORIGIN / "input.json")
    data = base.model_dump(mode="json")
    original_scope = deepcopy(artifact(data, "SourceBundle")["payload"]["scope_manifest"])
    mutation = (build_excluded_header(data) if case == "excluded-header"
                else build_observed_evidence_label(data))
    data = reseal_dependencies(data, case, artifact_ref, seal_artifact, seal_policy)
    bundle = validate_bundle(data, asset_root=destination)
    write_bundle(bundle, destination / "input.json")
    bundle = load_bundle(destination / "input.json")

    graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    source = next(a for a in bundle.artifacts if a.kind == "SourceBundle")
    snapshot = next(a for a in bundle.artifacts if a.kind == "PlatformSnapshot")
    pre = next(a for a in bundle.artifacts if a.kind == "CheckReport" and a.payload.stage == "PRE_APPLY")
    policy = bundle.policies[0]
    config_data = json.loads((destination / "config.json").read_text(encoding="utf-8"))
    config_data["allowed_operations"] = tuple(config_data["allowed_operations"])
    config = SimulationConfig(**config_data)
    if pre.payload.decision != "PASS" or source.payload.scope_manifest != original_scope:
        raise ValueError("probe violated its legal PASS/scope invariant")
    if case == "excluded-header" and any(
            HEADER_REGION in fragment.region_ids for fragment in graph.payload.fragments):
        raise ValueError("header accidentally entered the question/answer closure")

    input_before = bundle.model_dump(mode="json")
    snapshot_before = snapshot.model_dump(mode="json")
    actual = {"case": case, "frozen_commit": FROZEN_COMMIT,
              "provenance": "SYNTHETIC independent fault-injection probe",
              "mode": "PLANNING_ONLY; no executor imported or invoked",
              "mutation": mutation, "input_public_validation": "PASS including resource bytes",
              "pre_apply_decision": pre.payload.decision,
              "pre_apply_coverage": pre.payload.coverage.model_dump(mode="json"),
              "scope_manifest": list(source.payload.scope_manifest),
              "graph_question_ids": [q.question_id for q in graph.payload.questions],
              "registry_modes": {e.evidence_id: e.mode for e in bundle.evidence},
              "platform_actions": 0, "browser_actions": 0, "model_calls": 0,
              "snapshot_before": snapshot_before}
    try:
        checked = check_target(bundle, artifact_ref(graph), artifact_ref(snapshot), artifact_ref(snapshot),
                               policy_ref(policy), config,
                               artifact_id="review-target-" + case, created_at=TIME)
        target = checked.artifacts[-1]
        write_bundle(checked, destination / "targetchecked.json")
        actual["target_decision"] = target.payload.decision
        actual["target_coverage"] = target.payload.coverage.model_dump(mode="json")
        actual["target_checks"] = [c.model_dump(mode="json") for c in target.payload.checks]
        actual["target_issues"] = [i.model_dump(mode="json") for i in target.payload.issues]
        planned = create_plan(checked, artifact_ref(graph), artifact_ref(pre), artifact_ref(target),
                              artifact_ref(snapshot), artifact_ref(snapshot), policy_ref(policy), config,
                              artifact_id="review-plan-" + case, created_at=TIME)
        write_bundle(planned, destination / "planned.json")
        planned = load_bundle(destination / "planned.json")
        plan = next(a for a in planned.artifacts if a.kind == "ApplyPlan")
        after_snapshot = next(a for a in planned.artifacts if a.kind == "PlatformSnapshot")
        actual.update(planning_result="RETURNED_VALID_PLAN", plan_readiness=plan.payload.readiness,
                      action_count=len(plan.payload.actions), plan_ref=artifact_ref(plan),
                      blocked_issue_ids=list(plan.payload.blocked_issue_ids),
                      snapshot_after=after_snapshot.model_dump(mode="json"),
                      snapshot_unchanged=after_snapshot.model_dump(mode="json") == snapshot_before,
                      input_unchanged=bundle.model_dump(mode="json") == input_before)
        if case == "excluded-header":
            observed = (target.payload.decision != "PASS" and
                        HEADER_REGION in target.payload.coverage.unassigned_region_ids)
        else:
            observed = target.payload.decision == "PASS" and plan.payload.readiness == "READY"
        actual["candidate_counterexample_observed"] = observed
    except Exception as error:
        actual.update(planning_result="REJECTED_OR_PROBE_ERROR",
                      error_type=type(error).__name__, error=str(error),
                      contract_issues=getattr(error, "issues", None),
                      input_unchanged=bundle.model_dump(mode="json") == input_before)
        write_json(destination / "actual.json", actual)
        raise
    write_json(destination / "actual.json", actual)
    return {key: actual[key] for key in ("case", "target_decision", "plan_readiness",
                                        "action_count", "candidate_counterexample_observed",
                                        "snapshot_unchanged", "input_unchanged")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "counterexamples/coverage-labels")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("output must be a new directory: " + str(args.output))
    if not (FROZEN_SRC / "annotation/contracts/__init__.py").is_file():
        raise FileNotFoundError("fixed frozen source export is missing: " + str(FROZEN_SRC))
    sys.path.insert(0, str(FROZEN_SRC))
    import annotation.contracts as contracts
    import annotation.delivery.planner as planner
    import annotation.quality.targetcheck as targetcheck
    for module in (contracts, planner, targetcheck):
        Path(module.__file__).resolve().relative_to(FROZEN_SRC.resolve())
    api = (contracts.artifact_ref, contracts.load_bundle, contracts.policy_ref,
           contracts.seal_artifact, contracts.seal_policy, contracts.validate_bundle,
           contracts.write_bundle, targetcheck.SimulationConfig, targetcheck.check_target,
           planner.create_plan)
    args.output.mkdir(parents=True)
    results = [run_case(case, args.output / case, api)
               for case in ("excluded-header", "observed-evidence-label")]
    code_paths = ("src/annotation/contracts/validation.py", "src/annotation/contracts/models.py",
                  "src/annotation/quality/targetcheck/__init__.py", "src/annotation/delivery/planner/__init__.py")
    summary = {"frozen_commit": FROZEN_COMMIT, "frozen_root": str(FROZEN_ROOT),
               "python": sys.version, "executable": sys.executable,
               "source_sha256": {path: hashlib.sha256((FROZEN_ROOT / path).read_bytes()).hexdigest()
                                 for path in code_paths},
               "platform_actions": 0, "browser_actions": 0, "model_calls": 0, "cases": results}
    write_json(args.output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
