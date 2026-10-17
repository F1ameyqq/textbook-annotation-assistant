"""Explicitly convert a fresh synthetic fixture and build a new A03 plan.

Historical receipts/intents are never converted. Every output path is new. The
existing A02 fixture is a read-only input; its bytes are hashed before and after.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import sys


def write_new(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2,
                  allow_nan=False)
        stream.write("\n")


def prepare(root, output, fixture="normal", book=None, scope=None):
    from annotation.contracts import (
        artifact_ref, convert_synthetic_fixture, load_recovery_bundle, policy_ref,
        write_bundle,
    )
    from annotation.delivery.planner import create_plan
    from annotation.quality.targetcheck import SimulationConfig, check_target

    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError("fixture output must be new: " + str(output))
    source_root = root / "tests" / "fixtures" / "a02" / fixture
    source = source_root / "input.json"
    before = {p.relative_to(source_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in source_root.rglob("*") if p.is_file()}
    digest = before["input.json"]
    if book is not None or scope is not None:
        # Create a genuinely new, unexecuted old-version fixture, then use the
        # explicit converter. No receipt, UNKNOWN or intent is ever relabelled.
        spec = importlib.util.spec_from_file_location("a03_p2_old_fixture_helpers",
                                                    root / "examples/a02/R1/scenarios.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        raw = output.parent / (output.name + "-unexecuted-legacy-input")
        raw.mkdir(parents=True, exist_ok=False)
        original_config = json.loads((source_root / "config.json").read_text(encoding="utf-8"))
        book = book or original_config["book_id"]
        new_bundle, new_config = helper.own_input(root, raw, book, "p2-fresh", case=fixture,
                                                  **({"scope": scope} if scope else {}))
        source = raw / "input.json"
        write_bundle(new_bundle, source)
        from dataclasses import asdict
        write_new(raw / "config.json", asdict(new_config))
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
    converted = convert_synthetic_fixture(
        source, output, conversion_id="a03-p2-" + fixture,
        expected_input_sha256=digest,
    )
    bundle_path = Path(converted["bundle_path"])
    if not bundle_path.is_absolute():
        bundle_path = output / bundle_path
    bundle = load_recovery_bundle(bundle_path, asset_root=output)
    config_data = json.loads((source.parent / "config.json").read_text(encoding="utf-8"))
    config_data["allowed_operations"] = tuple(config_data["allowed_operations"])
    config = SimulationConfig(**config_data)
    graph = next(a for a in bundle.artifacts if a.kind == "QuestionGraph")
    snapshot = next(a for a in bundle.artifacts if a.kind == "PlatformSnapshot")
    pre = next(a for a in bundle.artifacts if a.kind == "CheckReport" and a.payload.stage == "PRE_APPLY")
    # The actual fresh target observation bridge is exercised by runtime prepare;
    # construction retains the one exact input snapshot for both check stages.
    output_bundle = check_target(
        bundle, artifact_ref(graph), artifact_ref(snapshot), artifact_ref(snapshot),
        policy_ref(bundle.policies[0]), config, artifact_id="p2-targetcheck",
        created_at="2026-10-17T00:00:00Z",
    )
    target = output_bundle.artifacts[-1]
    output_bundle = create_plan(
        output_bundle, artifact_ref(graph), artifact_ref(pre), artifact_ref(target),
        artifact_ref(snapshot), artifact_ref(snapshot), policy_ref(bundle.policies[0]),
        config, artifact_id="p2-plan", created_at="2026-10-17T00:00:00Z",
    )
    plan = output_bundle.artifacts[-1]
    planned = output / "planned.json"
    write_bundle(output_bundle, planned)
    config_path = output / "config.json"
    write_new(config_path, config_data)
    status_source = source_root / "scope-statuses.json"
    if status_source.exists():
        shutil.copyfile(str(status_source), str(output / status_source.name))
    after = {p.relative_to(source_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in source_root.rglob("*") if p.is_file()}
    if before != after:
        raise AssertionError("read-only legacy source changed")
    imports = {}
    for name in ("annotation.contracts", "annotation.delivery.planner",
                 "annotation.quality.targetcheck"):
        module = importlib.import_module(name)
        imports[name] = str(Path(module.__file__).resolve())
        if root not in Path(module.__file__).resolve().parents:
            raise AssertionError("module imported from outside exact checkout: " + name)
    result = {
        "ok": True, "provenance": "SYNTHETIC", "execution_mode": "SIMULATED",
        "fixture": fixture, "bundle_path": str(planned), "asset_root": str(output),
        "config_path": str(config_path), "source_ref": artifact_ref(next(
            a for a in output_bundle.artifacts if a.kind == "SourceBundle")),
        "snapshot_ref": artifact_ref(snapshot), "plan_ref": artifact_ref(plan),
        "action_ids": [a.action_id for a in plan.payload.actions],
        "source_sha256_before": before, "source_sha256_after": after,
        "python": sys.version, "python_executable": sys.executable,
        "sqlite": sqlite3.sqlite_version, "imports": imports,
    }
    write_new(output / "prepared-input.json", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", default="normal")
    parser.add_argument("--book")
    parser.add_argument("--scope")
    args = parser.parse_args()
    prepare(args.root, args.output, args.fixture, args.book, args.scope)
