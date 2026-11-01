"""Verify, rebuild, and test the public A24 offline replay package.

This utility never performs browser/platform requests. Rebuild and test outputs
must point at paths that do not already exist.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from unittest.mock import patch


PACKAGE = Path(__file__).resolve().parent
BASELINE = PACKAGE / "baseline"
OVERLAYS = PACKAGE / "overlays"
MANIFESTS = PACKAGE / "manifests"
EXPECTED_SUITES = (
    ("controlled_capture", "tests/a24_controlled_capture/test_integration.py", 7),
    ("minimum_gate", "tests/a24_first_save_current_body/test_minimum_gate.py", 10),
    ("book_snapshot", "tests/a24_book_snapshot_fix/test_book_snapshot.py", 4),
)
WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                    *(f"lpt{i}" for i in range(1, 10))}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_bytes())


def safe_relative(value: str) -> Path:
    if "\\" in value or ":" in value:
        raise ValueError("unsafe manifest path")
    raw_parts = value.split("/")
    if not raw_parts or any(part in ("", ".", "..") for part in raw_parts):
        raise ValueError("unsafe manifest path")
    if any(part.endswith((".", " ")) or part.split(".", 1)[0].casefold() in WINDOWS_RESERVED
           for part in raw_parts):
        raise ValueError("Windows-unsafe manifest path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts:
        raise ValueError("unsafe manifest path")
    return Path(*pure.parts)


def require_casefold_unique(values, label: str) -> None:
    keys = [value.casefold() for value in values]
    if len(keys) != len(set(keys)):
        raise ValueError(f"casefold-duplicate {label} path")


def listed_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def verify_file(path: Path, item: dict) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or non-regular file: {item['path']}")
    if path.stat().st_size != item["bytes"]:
        raise ValueError(f"byte mismatch: {item['path']}")
    if sha256_file(path) != item["sha256"]:
        raise ValueError(f"hash mismatch: {item['path']}")


def verify_package() -> dict:
    original_path = MANIFESTS / "baseline-original-manifest.json"
    original = load_json(original_path)
    members = original["members"]
    if original.get("schema") != "A24BSelectivePublication/v1":
        raise ValueError("unexpected baseline manifest schema")
    if original.get("member_count") != 522 or len(members) != 522:
        raise ValueError("baseline member count is not 522")
    member_paths = [item["path"] for item in members]
    if len(set(member_paths)) != 522:
        raise ValueError("duplicate baseline member path")
    require_casefold_unique(member_paths, "baseline")
    if listed_files(BASELINE) != set(member_paths):
        raise ValueError("baseline tree differs from the original manifest")
    for item in members:
        verify_file(BASELINE / safe_relative(item["path"]), item)

    overlay_manifest = load_json(MANIFESTS / "overlay-manifest.json")
    overlays = overlay_manifest["members"]
    if len(overlays) != 3 or len({item["path"] for item in overlays}) != 3:
        raise ValueError("overlay count is not three")
    require_casefold_unique([item["path"] for item in overlays], "overlay")
    if listed_files(OVERLAYS) != {item["path"] for item in overlays}:
        raise ValueError("overlay tree differs from overlay manifest")
    for item in overlays:
        verify_file(OVERLAYS / safe_relative(item["path"]), item)

    effective = load_json(MANIFESTS / "effective-manifest.json")
    if effective.get("member_count") != 523 or len(effective["members"]) != 523:
        raise ValueError("effective member count is not 523")
    effective_paths = {item["path"] for item in effective["members"]}
    require_casefold_unique([item["path"] for item in effective["members"]], "effective")
    expected_paths = set(member_paths) | {item["path"] for item in overlays}
    if effective_paths != expected_paths:
        raise ValueError("effective path set is not baseline plus overlays")
    by_overlay = {item["path"]: item for item in overlays}
    by_baseline = {item["path"]: item for item in members}
    for item in effective["members"]:
        source_item = by_overlay.get(item["path"], by_baseline.get(item["path"]))
        if source_item is None or item["bytes"] != source_item["bytes"] or item["sha256"] != source_item["sha256"]:
            raise ValueError(f"effective binding mismatch: {item['path']}")

    root_path = PACKAGE / "root-manifest.json"
    if not root_path.is_file():
        raise ValueError("required root manifest is missing")
    root = load_json(root_path)
    root_paths = {item["path"] for item in root["members"]}
    require_casefold_unique([item["path"] for item in root["members"]], "root")
    actual = listed_files(PACKAGE) - {"root-manifest.json"}
    if root_paths != actual or root.get("member_count") != len(actual):
        raise ValueError("root manifest membership mismatch")
    for item in root["members"]:
        verify_file(PACKAGE / safe_relative(item["path"]), item)

    return {
        "schema": "A24OfflineReplayVerification/v1",
        "baseline_members": 522,
        "overlay_members": 3,
        "effective_members": 523,
        "root_manifest_checked": True,
        "status": "PASS",
    }


def exclusive_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer, length=1024 * 1024)


def rebuild(target: Path) -> dict:
    verify_package()
    if target.exists():
        raise FileExistsError("rebuild target already exists")
    target.mkdir(parents=True)
    overlay_paths = {item["path"] for item in load_json(MANIFESTS / "overlay-manifest.json")["members"]}
    effective = load_json(MANIFESTS / "effective-manifest.json")
    for item in effective["members"]:
        relative = safe_relative(item["path"])
        source = (OVERLAYS if item["path"] in overlay_paths else BASELINE) / relative
        destination = target / relative
        exclusive_copy(source, destination)
        verify_file(destination, item)
    return {"schema": "A24OfflineReplayRebuild/v1", "target": str(target),
            "members": len(effective["members"]), "status": "PASS"}


def verify_effective_tree(tree: Path) -> dict:
    effective = load_json(MANIFESTS / "effective-manifest.json")
    expected = {item["path"] for item in effective["members"]}
    actual = listed_files(tree) if tree.is_dir() else set()
    require_casefold_unique(actual, "test tree")
    if actual != expected:
        raise ValueError("test tree file set differs from effective manifest")
    for item in effective["members"]:
        verify_file(tree / safe_relative(item["path"]), item)
    return {"members": len(effective["members"]), "status": "PASS"}


def forbidden(*args, **kwargs):
    raise AssertionError("A24_OFFLINE_REPLAY_REAL_IO_FORBIDDEN")


def load_test_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_tests(tree: Path, report_dir: Path, temp_dir: Path) -> dict:
    package_verification = verify_package()
    tree_verification = verify_effective_tree(tree)
    if report_dir.exists() or temp_dir.exists():
        raise FileExistsError("test report/temp directory already exists")
    os.environ["TEMP"] = str(temp_dir)
    os.environ["TMP"] = str(temp_dir)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(tree / "src"))
    sys.path.insert(0, str(tree / "tests/a24_first_save_wire_r1"))
    from noio_loop import MemoryPolicy
    import pydantic
    import PIL

    asyncio.set_event_loop_policy(MemoryPolicy())
    report_dir.mkdir(parents=True)
    temp_dir.mkdir(parents=True)
    started = time.monotonic()
    suite_results = []
    with patch.object(socket, "create_connection", forbidden), \
         patch.object(socket.socket, "connect", forbidden), \
         patch.object(subprocess, "Popen", forbidden), \
         patch.object(urllib.request, "urlopen", forbidden):
        for index, (suite_name, relative, expected) in enumerate(EXPECTED_SUITES):
            module = load_test_module(tree / safe_relative(relative), f"a24_offline_{index}_{suite_name}")
            suite = unittest.defaultTestLoader.loadTestsFromModule(module)
            result = unittest.TestResult()
            suite.run(result)
            failures = [{"test_id": test.id(), "traceback": traceback_text}
                        for test, traceback_text in result.failures]
            errors = [{"test_id": test.id(), "traceback": traceback_text}
                      for test, traceback_text in result.errors]
            record = {"suite": suite_name, "expected": expected, "tests": result.testsRun,
                      "failure_count": len(failures), "error_count": len(errors),
                      "failures": failures, "errors": errors,
                      "passed": result.wasSuccessful() and result.testsRun == expected}
            suite_results.append(record)
            if not record["passed"]:
                break
    total = sum(item["tests"] for item in suite_results)
    receipt = {
        "schema": "A24OfflineReplayTestReceipt/v1",
        "mode": "SYNTHETIC_MEMORY_POLICY_ONLY",
        "tree": str(tree),
        "package_verification": package_verification,
        "tree_verification": tree_verification,
        "suites": suite_results,
        "tests": total,
        "expected_tests": 21,
        "passed": len(suite_results) == 3 and total == 21 and all(item["passed"] for item in suite_results),
        "guard_scope": ["asyncio MemoryPolicy", "socket.create_connection", "socket.socket.connect",
                        "subprocess.Popen", "urllib.request.urlopen"],
        "observed_guarded_entrypoint_calls": 0,
        "guard_limit": "Not an OS filesystem sandbox and not a proof that every possible I/O API is blocked",
        "pydantic_version": pydantic.__version__,
        "pillow_version": PIL.__version__,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }
    report = report_dir / "test-receipt.json"
    with report.open("xb") as handle:
        handle.write((json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if not receipt["passed"]:
        raise AssertionError("offline replay tests failed")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify")
    rebuild_parser = commands.add_parser("rebuild")
    rebuild_parser.add_argument("--target", type=Path, required=True)
    test_parser = commands.add_parser("test")
    test_parser.add_argument("--tree", type=Path, required=True)
    test_parser.add_argument("--report-dir", type=Path, required=True)
    test_parser.add_argument("--temp-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "verify":
        result = verify_package()
    elif args.command == "rebuild":
        result = rebuild(args.target.resolve())
    else:
        result = run_tests(args.tree.resolve(), args.report_dir.resolve(), args.temp_dir.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
