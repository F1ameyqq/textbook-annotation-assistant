"""Archive/verify A03 preparation documents; never import or execute business code.

Run from D:/1800 with: python -B docs/evidence/A03/review/preparation/verify_preparation.py
Recheck without writes: append --verify-only.
The first run creates evidence exclusively in this script's preparation directory.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
REPORT = ROOT / "docs/tasks/A03-review-preparation.md"
WORKFLOW = "a354f95f1d0b40a8f0847b57fa3978cac999e7a2"
BASE = "ec1b4defbfa3ec0f181d291106fb53313983e493"
MANIFEST = HERE / "sha256-manifest.json"
COMMANDS = []
READS = {
    WORKFLOW: [
        "AGENTS.md", "docs/coordination.md", "docs/architecture.md",
        "docs/contracts-v1.md", "docs/tasks/A03-runtime-recovery.md",
        "docs/tasks/A03-independent-review.md",
        "docs/tasks/A03-contract-extension-preparation.md",
        "docs/tasks/S01-eligibility-preparation.md",
        "docs/tasks/A02-coordinator-acceptance.md",
    ],
    BASE: [
        "src/annotation/delivery/mock/__init__.py",
        "src/annotation/delivery/planner/__init__.py",
        "src/annotation/quality/targetcheck/__init__.py",
    ],
}
INITIAL_OBSERVATIONS = {
    "head": WORKFLOW,
    "branch": "codex/local-login-config",
    "status_short": [" M docs/coordination-state.json", "?? mermaid-diagram.png"],
    "unrelated_file_sha256_at_start": {
        "docs/coordination-state.json": "bedd764485bc5a0b0e97d8640b8c7adf8fc9925923181c2eaff2b53dd0f7a3fc",
        "mermaid-diagram.png": "960145a6e79769e65d0d6a1437c916d010f67d4f1890f082a9f7eb6150f3d31d",
    },
    "preparation_report_and_directory_existed": False,
    "later_observed_drift": ["docs/coordination.md"],
    "observation_only_not_owned_or_restored": True,
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def git(*args, allowed=(0,)):
    argv = ["git", *args]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    COMMANDS.append({"argv": argv, "cwd": str(ROOT), "timeout_seconds": 30,
                     "returncode": result.returncode})
    if result.returncode not in allowed:
        raise RuntimeError(f"Git failed ({result.returncode}): {args}")
    return result.stdout


def write_new_json(path, data):
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(raw)


def source_entries():
    entries = []
    for commit, paths in READS.items():
        for path in paths:
            raw = git("show", f"{commit}:{path}")
            blob = git("rev-parse", f"{commit}:{path}").decode().strip()
            entries.append({"commit": commit, "path": path, "git_blob": blob,
                            "bytes": len(raw), "sha256": digest(raw),
                            "access": "STATIC_GIT_BYTES_ONLY"})
    return entries


def verify_only():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = set()
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not (path == REPORT or path.is_relative_to(HERE)):
            raise RuntimeError("manifest path outside preparation scope")
        raw = path.read_bytes()
        assert len(raw) == item["bytes"], item["path"]
        assert digest(raw) == item["sha256"], item["path"]
        expected.add(item["path"])
    actual = {relative(p) for p in HERE.rglob("*") if p.is_file() and p != MANIFEST}
    actual.add(relative(REPORT))
    assert actual == expected, {"unexpected": sorted(actual - expected),
                                "missing": sorted(expected - actual)}
    readset = json.loads((HERE / "readset.json").read_text(encoding="utf-8"))
    assert source_entries() == readset["entries"], "frozen readset changed"
    checks = json.loads((HERE / "preparation-checks.json").read_text(encoding="utf-8"))
    assert checks["status"] == "WAITING_FOR_FROZEN_P1"
    assert all(x["result"] == "NOT_RUN" for x in checks["p1_design_checks"])
    print(json.dumps({"result": "PREPARATION_ARCHIVE_VERIFIED", "files": len(expected),
                      "frozen_readset_entries": len(readset["entries"]),
                      "p1_design_checks": "NOT_RUN", "p2": "NOT_RUN"}, ensure_ascii=False))


def create():
    for name in ("readset.json", "scope-declaration.json", "preparation-checks.json",
                 "checks.log", "sha256-manifest.json"):
        if (HERE / name).exists():
            raise RuntimeError(f"existing evidence preserved: {name}; use --verify-only")
    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    entries = source_entries()
    assert git("rev-parse", WORKFLOW).decode().strip() == WORKFLOW
    assert git("rev-parse", BASE).decode().strip() == BASE
    git("merge-base", "--is-ancestor", BASE, WORKFLOW)
    head_now = git("rev-parse", "HEAD").decode().strip()
    status_now = git("status", "--short", "--untracked-files=normal").decode("utf-8", "replace").splitlines()
    write_new_json(HERE / "readset.json", {
        "format_version": "a03-review-preparation-readset-1",
        "captured_at": now, "timezone": "Asia/Shanghai", "workflow_commit": WORKFLOW,
        "code_baseline": BASE, "p1_review_commit": None,
        "authority": "formal dispatch and frozen workflow Git bytes",
        "candidate_documents_are_historical_background": True,
        "entries": entries,
    })
    write_new_json(HERE / "scope-declaration.json", {
        "format_version": "a03-review-preparation-scope-1", "captured_at": now,
        "status": "WAITING_FOR_FROZEN_P1",
        "owned_write_paths": [relative(REPORT), relative(HERE) + "/"],
        "external_actions": {
            "browser": 0, "network": 0, "platform_reads": 0, "platform_writes": 0,
            "credentials_or_profile_access": 0, "ocr": 0, "model_service_api_calls": 0,
            "paid_calls": 0, "model_service_cost": 0, "book_submissions": 0,
            "new_chats": 0, "executor_or_b_messages": 0,
            "recovery_or_simulated_target_runs": 0,
        },
        "quality_and_real_model_cost_measurements": "NOT_RUN",
        "processes": {
            "background_or_service_launches": 0, "recovery_test_processes": 0,
            "other_processes_terminated": 0, "remaining_owned_background_os_processes": 0,
            "local_tools": "synchronous Git/PowerShell/document-only Python; completion confirmed by tool exit codes",
            "subprocess_policy": "subprocess.run with bounded timeout; no detached launch/Popen",
        },
        "static_text_subagent": {"count": 1, "name": "static_preparation_check",
                                 "status": "COMPLETED", "writes": 0,
                                 "business_code_execution": 0, "external_model_api_calls": 0},
        "p1_conclusion": None, "p2_authorized": False, "i01_released": False,
        "b_interface_confirmation": "NOT_RECEIVED", "git_commit_or_integration_by_reviewer": False,
    })
    report_text = REPORT.read_text(encoding="utf-8")
    link_results = []
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", report_text):
        if "://" in target or target.startswith("#"):
            raise RuntimeError("unexpected non-local link in preparation report")
        path = (REPORT.parent / target.split("#", 1)[0]).resolve()
        assert path.is_relative_to(ROOT), target
        # These two evidence files are written later in this same create operation.
        pending = path in (HERE / "preparation-checks.json", HERE / "checks.log", MANIFEST)
        assert path.is_file() or pending, target
        link_results.append({"label": label, "target": target, "exists_or_owned_pending": True})
    owned_before_outputs = [REPORT, Path(__file__).resolve(), HERE / "readset.json", HERE / "scope-declaration.json"]
    whitespace = []
    for path in owned_before_outputs:
        text = path.read_text(encoding="utf-8")
        bad = [i for i, line in enumerate(text.splitlines(), 1) if line.endswith((" ", "\t"))]
        assert not bad, (relative(path), bad)
        whitespace.append({"path": relative(path), "trailing_whitespace_lines": bad})
    json_checks = []
    for path in (HERE / "readset.json", HERE / "scope-declaration.json"):
        json.loads(path.read_text(encoding="utf-8"))
        json_checks.append({"path": relative(path), "result": "PARSED"})
    unrelated_after = {}
    for path, initial_digest in INITIAL_OBSERVATIONS["unrelated_file_sha256_at_start"].items():
        actual_digest = digest((ROOT / path).read_bytes())
        unrelated_after[path] = {"sha256_at_capture": actual_digest,
                                 "equals_start_observation": actual_digest == initial_digest,
                                 "owned_write": False, "not_restored": True}
    checks = {
        "format_version": "a03-review-preparation-checks-1", "captured_at": now,
        "status": "WAITING_FOR_FROZEN_P1", "checks_are_document_preparation_only": True,
        "actual_checks": {
            "workflow_and_baseline_objects": "FOUND",
            "baseline_is_ancestor_of_workflow": True,
            "frozen_static_readset_entries": len(entries),
            "local_links": link_results, "trailing_whitespace": whitespace,
            "json_parsing": json_checks,
            "business_modules_imported_or_executed": False,
        },
        "p1_design_checks": [{"id": f"P1-{i:02d}", "result": "NOT_RUN",
                               "reason": "WAITING_FOR_FROZEN_P1"} for i in range(1, 8)],
        "d_decisions": [{"id": f"D{i:02d}", "result": "NOT_RUN",
                          "reason": "exact Schema/API/decisions await frozen delivery"} for i in range(1, 9)],
        "a02_interface_groups": [{"id": f"G{i}", "static_inventory": "RECORDED",
                                   "p1_adapter_review": "NOT_RUN"} for i in range(1, 5)],
        "other_not_run": ["frozen P1 export", "P1 JSON/Schema/API and counterexamples",
                          "all P2 R01-R18 and V01-V10", "A02/C01 regression rerun",
                          "full historical evidence byte audit", "platform/quality/cost measurement"],
        "workspace_observations": {"start": INITIAL_OBSERVATIONS, "head_at_capture": head_now,
                                   "status_short_at_capture": status_now,
                                   "unrelated_file_hash_observations": unrelated_after,
                                   "external_drift_does_not_change_frozen_authority": True,
                                   "no_staging_commits_branches_resets_or_cleanup_by_this_script": True},
        "commands": COMMANDS,
    }
    write_new_json(HERE / "preparation-checks.json", checks)
    log_lines = [f"captured_at={now}", "scope=DOCUMENT_PREPARATION_ONLY",
                 "status=WAITING_FOR_FROZEN_P1", "P1-01..P1-07=NOT_RUN", "D01..D08=NOT_RUN",
                 "P2=NOT_RUN", f"frozen_readset_entries={len(entries)}",
                 f"local_links_checked={len(link_results)}", "new_business_code_imports=0"]
    log_lines += [json.dumps(c, ensure_ascii=False) for c in COMMANDS]
    with (HERE / "checks.log").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(log_lines) + "\n")
    owned = sorted([REPORT, *[p for p in HERE.rglob("*") if p.is_file() and p != MANIFEST]], key=relative)
    for path in owned:
        assert path == REPORT or path.is_relative_to(HERE), path
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        assert all(not line.endswith((" ", "\t")) for line in path.read_text(encoding="utf-8").splitlines())
    write_new_json(MANIFEST, {
        "format_version": "a03-review-preparation-sha256-1", "captured_at": now,
        "scope": "preparation archive only; no P1 or functionality acceptance",
        "algorithm": "SHA256", "self_excluded": relative(MANIFEST), "ignored_owned_files": [],
        "files": [{"path": relative(p), "bytes": p.stat().st_size,
                   "sha256": digest(p.read_bytes())} for p in owned],
    })
    verify_only()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        verify_only()
    else:
        create()
