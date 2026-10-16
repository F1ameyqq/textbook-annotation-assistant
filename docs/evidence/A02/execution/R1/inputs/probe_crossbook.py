"""Independent A02 counterexample: a foreign UNKNOWN poisons another book's pause.

Run only against the frozen source tree. All assets and outputs are SYNTHETIC;
there are no dispatched actions, browser, network, model or platform operations.
Exit 0 means the asserted defect was reproduced, not that A02 was accepted.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import copy
import json
from pathlib import Path
import shutil

FROZEN = Path("D:/1800/.local/stages/A02-review/frozen-5c928572")
SOURCE = FROZEN / "src"
COMMIT = "5c9285720c8628c5198bedeadfc9f6bc7826a914"
DEFAULT_OUTPUT = Path("D:/1800/docs/evidence/A02/review/formal/counterexamples/crossbook")
TIME = "2026-10-16T00:00:00Z"
OTHER_BOOK = "other-book"
sys.path.insert(0, str(SOURCE))

import annotation.contracts as contracts_module
import annotation.delivery.mock as mock_module
import annotation.delivery.planner as planner_module
import annotation.quality.targetcheck as target_module
from annotation.contracts import (
    ContractError, artifact_ref, assert_plan_ready, load_bundle, policy_ref,
    seal_artifact, validate_bundle, write_bundle,
)
from annotation.delivery.mock import MockSession
from annotation.delivery.planner import create_plan
from annotation.quality.targetcheck import SimulationConfig, check_target


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def get(bundle, kind):
    return next(a for a in bundle.artifacts if a.kind == kind and a.book_id == OTHER_BOOK)


def prepare(case, tag, output):
    """Use public sealing APIs to rebind one complete fixture to another book."""
    fixture = FROZEN / "tests/fixtures/a02" / case
    data = load_bundle(fixture / "input.json").model_dump(mode="json")
    changed = {}

    def update_refs(value):
        if isinstance(value, list):
            return [update_refs(item) for item in value]
        if isinstance(value, dict):
            if set(value) == {"artifact_id", "revision", "kind", "content_hash"}:
                return copy.deepcopy(changed.get((value["artifact_id"], value["revision"]), value))
            return {key: update_refs(item) for key, item in value.items()}
        return value

    for index, item in enumerate(data["artifacts"]):
        key = (item["artifact_id"], item["revision"])
        rebound = update_refs(item)
        rebound["book_id"] = OTHER_BOOK
        rebound = seal_artifact(rebound)
        data["artifacts"][index] = rebound
        changed[key] = artifact_ref(rebound)

    foreign = load_bundle(FROZEN / "tests/fixtures/contracts/unknown/input.json").model_dump(mode="json")
    data["artifacts"].extend(foreign["artifacts"])
    data["policies"].extend(foreign["policies"])
    for evidence in foreign["evidence"]:
        prior = next((e for e in data["evidence"] if e["evidence_id"] == evidence["evidence_id"]), None)
        if prior is None:
            data["evidence"].append(evidence)
        else:
            assert prior == evidence, "shared evidence must be byte-identical in the two legal inputs"

    bundle = validate_bundle(data, asset_root=output)
    write_bundle(bundle, output / (tag + "-input.json"))
    graph, snapshot, precheck = (get(bundle, kind) for kind in ("QuestionGraph", "PlatformSnapshot", "CheckReport"))
    config_data = json.loads((fixture / "config.json").read_text(encoding="utf-8"))
    config_data["book_id"] = OTHER_BOOK
    config_data["allowed_operations"] = tuple(config_data["allowed_operations"])
    config = SimulationConfig(**config_data)
    write_json(output / (tag + "-config.json"), config_data)
    policy = policy_ref(bundle.policies[0])
    bundle = check_target(
        bundle, artifact_ref(graph), artifact_ref(snapshot), artifact_ref(snapshot), policy,
        config, artifact_id=tag + "-target", created_at=TIME,
    )
    write_bundle(bundle, output / (tag + "-checked.json"))
    bundle = create_plan(
        bundle, artifact_ref(graph), artifact_ref(precheck), artifact_ref(bundle.artifacts[-1]),
        artifact_ref(snapshot), artifact_ref(snapshot), policy, config,
        artifact_id=tag + "-plan", created_at=TIME,
    )
    write_bundle(bundle, output / (tag + "-planned.json"))
    return bundle, bundle.artifacts[-1], snapshot, config


def run(output):
    imports = {}
    for module in (contracts_module, mock_module, planner_module, target_module):
        location = Path(module.__file__).resolve()
        location.relative_to(SOURCE.resolve())
        imports[module.__name__] = str(location)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(FROZEN / "tests/fixtures/contracts/unknown/assets", output / "assets")
    blocked, blocked_plan, _, blocked_config = prepare("exceptions", "blocked", output)
    ready, ready_plan, ready_snapshot, ready_config = prepare("normal", "fresh-ready", output)
    assert blocked_plan.payload.readiness == "BLOCKED"
    assert ready_plan.payload.readiness == "READY" and len(ready_plan.payload.actions) == 3
    assert_plan_ready(ready, artifact_ref(ready_plan), artifact_ref(ready_snapshot))

    session = MockSession()
    session.register_target(ready, artifact_ref(ready_snapshot), asset_root=output)
    before = session.read_target(OTHER_BOOK)
    before_paused = session.is_paused(OTHER_BOOK)
    write_json(output / "before-target.json", before)
    write_json(output / "before-log.json", session.action_log)
    write_json(output / "before-history.json", session.receipt_history(OTHER_BOOK))
    result = session.execute(
        blocked, artifact_ref(blocked_plan), blocked_config, asset_root=output,
        receipt_id="diagnostic-other-receipt", created_at=TIME,
    )
    validate_bundle(result, asset_root=output)
    write_bundle(result, output / "blocked-receipt.json")
    receipt = result.artifacts[-1]
    own_unknown = [
        a.artifact_id for a in result.artifacts
        if a.kind == "ExecutionReceipt" and a.book_id == OTHER_BOOK
        and any(r.outcome == "UNKNOWN" for r in a.payload.results)
    ]
    after_diagnostic = session.read_target(OTHER_BOOK)
    after_paused = session.is_paused(OTHER_BOOK)
    write_json(output / "after-diagnostic-target.json", after_diagnostic)
    write_json(output / "after-diagnostic-log.json", session.action_log)
    write_json(output / "after-diagnostic-history.json", session.receipt_history(OTHER_BOOK))

    error = None
    try:
        session.execute(
            ready, artifact_ref(ready_plan), ready_config, asset_root=output,
            receipt_id="ready-other-receipt", created_at=TIME,
        )
    except ContractError as caught:
        error = {"type": type(caught).__name__, "issues": caught.issues, "message": str(caught)}
    after_ready = session.read_target(OTHER_BOOK)
    write_json(output / "after-ready-target.json", after_ready)
    write_json(output / "after-ready-log.json", session.action_log)
    write_json(output / "after-ready-history.json", session.receipt_history(OTHER_BOOK))
    write_json(output / "ready-error.json", error)

    observations = {
        "provenance": "SYNTHETIC", "execution_mode": "SIMULATED", "frozen_commit": COMMIT,
        "python": sys.executable, "imports": imports,
        "initial_pause": before_paused, "blocked_readiness": blocked_plan.payload.readiness,
        "diagnostic_execution_mode": receipt.payload.execution_mode,
        "diagnostic_results": [r.model_dump(mode="json") for r in receipt.payload.results],
        "own_unknown_receipts": own_unknown, "pause_after_diagnostic": after_paused,
        "fresh_readiness": ready_plan.payload.readiness, "fresh_action_count": len(ready_plan.payload.actions),
        "fresh_public_gate_passed": True, "fresh_error": error,
        "target_unchanged": before == after_diagnostic == after_ready,
        "action_log_empty": session.action_log == (),
        "platform_actions": 0, "model_calls": 0,
        "finding": "foreign-book UNKNOWN in stored full bundle incorrectly pauses other-book",
        "source_location": "src/annotation/delivery/mock/__init__.py:47-50",
    }
    write_json(output / "observations.json", observations)
    # Each persisted exchange is independently reloaded with resource verification.
    for path in sorted(output.glob("*-input.json")) + sorted(output.glob("*-checked.json")) + sorted(output.glob("*-planned.json")) + [output / "blocked-receipt.json"]:
        load_bundle(path)
    assert before_paused is False
    assert receipt.payload.execution_mode == "NOT_EXECUTED" and not receipt.payload.results
    assert own_unknown == [] and after_paused is True
    assert error is not None and any(i["code"] == "BOOK_WRITE_PAUSED" for i in error["issues"])
    assert observations["target_unchanged"] and observations["action_log_empty"]
    print(json.dumps(observations, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    run(parser.parse_args().output)
