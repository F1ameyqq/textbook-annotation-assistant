"""Create portable A02 synthetic INPUTS, never plans/receipts/expected outputs.

Uses the accepted C01 fixture only as a source of clearly fabricated regions/assets.
Existing files are verified byte-for-byte; no overwrite/cleanup/replay is performed.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from annotation.contracts import (
    artifact_ref, load_bundle, policy_ref, seal_artifact, seal_policy, validate_bundle, write_bundle,
)
from annotation.quality.targetcheck import SimulationConfig, coverage_for, make_artifact

ROOT = Path(__file__).resolve().parents[2]
TIME = "2026-10-16T00:00:00Z"


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("existing immutable fixture differs: " + str(path))
    else:
        with path.open("xb") as handle:
            handle.write(raw)


def build(destination, case="normal"):
    origin = ROOT / "tests/fixtures/contracts" / ("choice-assumption" if case == "choice" else "normal")
    base = load_bundle(origin / "input.json")
    data = base.model_dump(mode="json")
    for asset in (origin / "assets").iterdir():
        if asset.is_file():
            put(destination / "assets" / asset.name, asset.read_bytes())
    policy = seal_policy(dict(data["policies"][0], policy_id="synthetic-a02-policy",
                             confirmation_status="SYNTHETIC_ASSUMPTION", applicability="SYNTHETIC_ONLY",
                             option_grouping="SEPARATE", frame_save_status="SYNTHETIC", ocr_status="SYNTHETIC",
                             source_notes=["SYNTHETIC A02 simulation assumption; no A/B or platform confirmation.",
                                           "SEPARATE options are supported only by this offline simulator."]))
    artifacts = []

    def convert(item, identity, payload, dependencies=()):
        result = seal_artifact(dict(item, artifact_id=identity, revision=1, run_id="a02-fixture-run",
                                    input_refs=[artifact_ref(a) for a in dependencies], payload=payload,
                                    producer={"module": "a02-synthetic-input", "implementation_version": "a02-fixtures-1",
                                              "config_version": case, "policy_versions": [policy_ref(policy)],
                                              "model_version": None, "prompt_version": None, "evidence_mode": "SYNTHETIC"}))
        artifacts.append(result)
        return result

    source_data = next(a for a in data["artifacts"] if a["kind"] == "SourceBundle")
    source_payload = source_data["payload"]
    if case == "exceptions":
        source_payload["scope_manifest"].append("question-missing")
    source = convert(source_data, "a02-source", source_payload)
    evidence_data = next(a for a in data["artifacts"] if a["kind"] == "EvidenceBundle")
    evidence = convert(evidence_data, "a02-evidence", dict(evidence_data["payload"], source=artifact_ref(source)), [source])
    graph_data = next(a for a in data["artifacts"] if a["kind"] == "QuestionGraph" and a["revision"] == 1)
    graph_payload = graph_data["payload"]
    graph_payload.update(source=artifact_ref(source), evidence=artifact_ref(evidence),
                         identity_notes="SYNTHETIC stable entity IDs; two directories repeat printed 1. Shared/cross-page regions are manually authored.")
    for q in graph_payload["questions"]:
        q["parent_question_id"] = None
        if q["question_type"] == "combination":
            q["question_type"] = "free_response"
        if q["question_id"] == "question-alpha":
            q["external_refs"]["printed_number"] = "1"
    graph = convert(graph_data, "a02-graph", graph_payload, [source, evidence])
    snapshot_data = next(a for a in data["artifacts"] if a["kind"] == "PlatformSnapshot")
    snapshot_payload = snapshot_data["payload"]
    snapshot_payload["directories"] = ["platform-unit-a", "platform-unit-b"]
    snapshot_payload["platform_version"] = "a02-synthetic-platform-1"
    for cap in snapshot_payload["capabilities"]:
        cap["platform_version"] = "a02-synthetic-platform-1"
    snapshot = convert(snapshot_data, "a02-snapshot", snapshot_payload)
    config = SimulationConfig(book_id=graph["book_id"], target_id=snapshot_payload["target_id"], scope_id=graph["scope_id"],
                              directory_map={"directory-a": "platform-unit-a", "directory-b": "platform-unit-b"})
    bundle = validate_bundle({"format_version": "c01-exchange-1", "policies": [policy],
                              "evidence": data["evidence"], "artifacts": artifacts}, asset_root=destination)
    model_graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    coverage, _ = coverage_for(bundle, model_graph)
    problems = []
    if case == "exceptions":
        problems.append({"issue_id": "issue-a02-missing-input", "code": "UNASSIGNED_CONTENT", "scope_type": "question",
                         "scope_id": "question-missing", "evidence_refs": ["proof-checks"], "severity": "blocking",
                         "blocks": ["PLAN", "APPLY", "COMPLETE"],
                         "suggested_strategy": {"strategy_id": "HUMAN_REVIEW", "max_attempts": 0, "max_cost": 0.0},
                         "reason": "SYNTHETIC independent inventory contains a question missing from graph"})
    pre = make_artifact("CheckReport", "a02-precheck-stub", model_graph,
                        {"stage": "PRE_APPLY", "subject": artifact_ref(graph), "graph": artifact_ref(graph),
                         "policy": policy_ref(policy), "snapshot": None, "receipt": None, "coverage": coverage,
                         "checks": [{"check_id": name, "outcome": "FAIL" if problems and name == "coverage" else "PASS",
                                     "evidence_refs": ["proof-checks"], "reason": "SYNTHETIC CONTRACT STUB; not algorithm quality evidence"}
                                    for name in ("source_integrity", "structure", "answer_matching", "coverage", "policy")],
                         "issues": problems, "decision": "EXCEPTION" if problems else "PASS",
                         "reason": "SYNTHETIC PRE_APPLY stub; B implementation not invoked or evaluated"},
                        [model_graph], "a02-fixtures-1", "a02-precheck-stub", TIME)
    bundle = validate_bundle(dict(bundle.model_dump(mode="json"), artifacts=artifacts + [pre]), asset_root=destination)
    output = destination / "input.json"
    if output.exists():
        if load_bundle(output) != bundle:
            raise ValueError("existing immutable input differs")
    else:
        write_bundle(bundle, output)
    put(destination / "config.json", (json.dumps(asdict(config), sort_keys=True, indent=2) + "\n").encode("utf-8"))
    statuses = ({"question-alpha": "EXCEPTION", "question-beta": "SKIPPED", "question-missing": "EXCEPTION"}
                if case == "exceptions" else {})
    put(destination / "scope-statuses.json", (json.dumps({"provenance": "SYNTHETIC", "statuses": statuses}, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["normal", "choice", "exceptions"], default="normal")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(build(args.output or ROOT / "tests/fixtures/a02" / args.case, args.case))
