"""Archive/verify P1 static review, preserving all frozen sources and prior evidence."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("D:/1800")
HERE = ROOT / "docs/evidence/A03/review/P1"
REPORT = ROOT / "docs/tasks/A03-P1-review-report.md"
COMMIT = "2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9"
DESIGN = "6ac0256f05169570605fcb921a773ff2ae0f4aef"
WORKFLOW = "a354f95f1d0b40a8f0847b57fa3978cac999e7a2"
STAGE = ROOT / ".local/stages/A03-review-P1" / COMMIT
EXECUTION_TREE = Path("C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800")
MANIFEST = HERE / "sha256-manifest.json"
COMMANDS = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def rel(path):
    return path.relative_to(ROOT).as_posix()

def load(path):
    return json.loads(path.read_bytes())

def write_new(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as h:
        json.dump(data, h, ensure_ascii=False, indent=2)
        h.write("\n")

def git(*args, allowed=(0,)):
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    p = subprocess.run(["git", *args], cwd=ROOT, env=env, capture_output=True, timeout=30)
    COMMANDS.append({"argv": ["git", *args], "cwd": str(ROOT), "timeout_seconds": 30,
                     "returncode": p.returncode, "GIT_OPTIONAL_LOCKS": "0"})
    assert p.returncode in allowed, (args, p.returncode, p.stderr.decode("utf-8", "replace"))
    return p.stdout

def verify_stage():
    export = load(HERE / "export-manifest.json")
    listed = set()
    for item in export["files"]:
        p = STAGE / item["path"]
        raw = p.read_bytes()
        assert len(raw) == item["bytes"] and sha(raw) == item["sha256"], item["path"]
        listed.add(item["path"])
    actual = {p.relative_to(STAGE).as_posix() for p in STAGE.rglob("*") if p.is_file()}
    assert actual == listed, {"unexpected": sorted(actual - listed), "missing": sorted(listed - actual)}
    return len(listed)

def verify_only():
    manifest = load(MANIFEST)
    listed = set()
    for item in manifest["files"]:
        p = ROOT / item["path"]
        assert p == REPORT or p.is_relative_to(HERE), p
        raw = p.read_bytes()
        assert len(raw) == item["bytes"] and sha(raw) == item["sha256"], item["path"]
        listed.add(item["path"])
    actual = {rel(p) for p in HERE.rglob("*") if p.is_file() and p != MANIFEST} | {rel(REPORT)}
    assert listed == actual, {"unexpected": sorted(actual - listed), "missing": sorted(listed - actual)}
    count = verify_stage()
    assert manifest["conclusion"] == "REWORK"
    print(json.dumps({"result": "REVIEW_ARCHIVE_VERIFIED", "conclusion": "REWORK",
        "manifest_files": len(listed), "isolated_git_input_files": count,
        "functional_recovery": "NOT_EXECUTED"}))

def create():
    assert not MANIFEST.exists(), "final manifest already exists; preserve and use --verify-only"
    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    count = verify_stage()
    execution_head = git("-C", str(EXECUTION_TREE), "rev-parse", "HEAD").decode().strip()
    execution_status = git("-C", str(EXECUTION_TREE), "status", "--porcelain=v1", "--untracked-files=all").decode().splitlines()
    assert execution_head == COMMIT and not execution_status, (execution_head, execution_status)
    old_changes = git("diff", "--diff-filter=DMRTUXB", "--name-only", WORKFLOW, COMMIT).decode().splitlines()
    assert not old_changes
    added = git("diff", "--diff-filter=A", "--name-only", WORKFLOW, COMMIT).decode().splitlines()
    assert len(added) == 149
    design_later_changes = git("diff", "--name-only", DESIGN, COMMIT, "--",
        "docs/a03-recovery-contract-v1-proposal.md", "examples/a03/P1").decode().splitlines()
    assert not design_later_changes
    frozen_copy = HERE / "inputs/frozen-P1"
    assert not frozen_copy.exists(), "preserve existing input copy rather than overwrite"
    for path in added:
        p = frozen_copy / path
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("xb") as h:
            h.write((STAGE / path).read_bytes())
        assert p.read_bytes() == (STAGE / path).read_bytes(), path
    readset = []
    for path in ("AGENTS.md", "docs/tasks/A03-independent-review.md", "docs/tasks/A03-runtime-recovery.md",
                 "docs/tasks/A03-review-preparation.md"):
        raw = (ROOT / path).read_bytes()
        readset.append({"path": path, "bytes": len(raw), "sha256": sha(raw)})
    write_new(HERE / "scope-declaration.json", {
        "captured_at": now, "timezone": "Asia/Shanghai", "conclusion": "REWORK",
        "reviewed_commit": COMMIT, "design_commit": DESIGN,
        "allowed_writes": [rel(REPORT), rel(HERE) + "/", str(STAGE)],
        "standard_readset": readset,
        "operations": {"network": 0, "browser": 0, "platform_read_write": 0,
            "credentials_or_profile_access": 0, "ocr": 0, "model_service_api": 0,
            "paid_model_calls": 0, "model_service_cost": 0, "book_submissions": 0,
            "new_chats": 0, "messages_to_executor_or_b": 0, "b_tasks": 0,
            "recovery_functionality_or_target_runs": 0, "p2_started": False,
            "integration_push_commit_or_state_changes": False, "i01_released": False},
        "local_tools": "bounded synchronous Git/PowerShell/Python static inspections only",
        "static_subagents": [{"name": "p1_schema_review", "status": "COMPLETED"},
                             {"name": "p1_api_ledger_review", "status": "COMPLETED"}],
        "background_processes_started": 0, "other_processes_terminated": 0,
        "remaining_owned_background_os_processes": 0,
        "release_evidence": "completed synchronous tool exit codes and completed subagent turns; no OS-wide process scan",
        "execution_process_release": "frozen author declaration and coordinator completed-turn handoff, not independently OS-scanned",
        "real_quality_and_cost": "NOT_RUN", "b_interface_confirmation": "NOT_RECEIVED",
    })
    text = REPORT.read_text(encoding="utf-8")
    assert not any(line.endswith((" ", "\t")) for line in text.splitlines())
    assert "结论：**REWORK**" in text and COMMIT in text
    pending = {HERE / "final-verification.json", MANIFEST}
    links = []
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text):
        p = (REPORT.parent / target.split("#", 1)[0]).resolve()
        assert p.is_relative_to(ROOT) and (p.is_file() or p in pending), target
        links.append({"target": target, "label": label})
    schema = load(HERE / "schema-agent/audit-summary.json")
    assert schema["case_count"] == 42 and schema["all_shape_expectations_match"]
    assert schema["all_referenced_fact_shapes_accepted"]
    author = load(HERE / "author-reproduction/results.json")
    assert all(c["returncode"] == 0 for c in author["commands"])
    assert author["commands"][0]["parsed_result"]["case_count"] == 42
    assert all(c["semantic_actual"] == "NOT_EXECUTED" for c in author["commands"][0]["parsed_result"]["cases"])
    bindings = load(HERE / "independent-bindings.json")
    assert len(bindings["cases"]) == 13 and len(bindings["failures"]) == 40
    write_new(HERE / "final-verification.json", {
        "captured_at": now, "reviewed_commit": COMMIT, "conclusion": "REWORK",
        "all_isolated_raw_git_input_files_unchanged": count,
        "execution_worktree": {"head": execution_head, "porcelain": execution_status,
            "ignored_files": "NOT_INSPECTED; only report/cache declarations retained"},
        "old_git_paths_modified_deleted": old_changes, "old_git_paths_preserved": count - len(added),
        "design_files_unchanged_after_design_commit": not design_later_changes,
        "frozen_p1_input_copies": len(added), "report_local_links": links,
        "author_static_exit_codes": [c["returncode"] for c in author["commands"]],
        "author_cases": 42, "semantic_results": "ALL_NOT_EXECUTED",
        "independent_subset_schema_shapes": "42/42 expected shapes match; not full standards certification",
        "complete_jsonschema_implementation": "NOT_RUN: absent from existing Python39/311/312",
        "independent_formula_cases": len(bindings["cases"]),
        "nested_reference_missing_declaration_occurrences": len(bindings["failures"]),
        "occurrences_are_not_independent_functional_failures": True,
        "confirmed_design_findings": ["A03-P1-API-01", "A03-P1-REF-01"],
        "p2_all_functionality": "NOT_RUN", "commands": COMMANDS,
    })
    command_summary = {"record_kind": "REVIEW_STATIC_COMMAND_EXIT_INDEX",
        "prior_observed_commands": [
            {"argv": ["python", "-B", rel(HERE / "scripts/freeze_delivery.attempt-01.py")],
             "original_invocation_path": rel(HERE / "scripts/freeze_delivery.py"),
             "cwd": str(ROOT), "exit_code": 1, "classification": "review tool export mismatch; preserved log"},
            {"argv": ["python", "-B", rel(HERE / "scripts/freeze_delivery.py")],
             "cwd": str(ROOT), "exit_code": 0},
            {"argv": ["python", "-B", rel(HERE / "scripts/run_static_checks.py")],
             "cwd": str(ROOT), "exit_code": 0},
            {"argv": ["python", "-B", rel(HERE / "scripts/audit_static_bindings.py")],
             "cwd": str(ROOT), "exit_code": 0, "static_findings": 40}],
        "finalization_git_commands": COMMANDS,
        "static_subagent_logs": ["schema-agent/audit-run.log", "schema-agent/exploration-history.log"],
        "business_functionality_executed": False}
    write_new(HERE / "review-command-results.json", command_summary)
    with (HERE / "finalization.log").open("x", encoding="utf-8", newline="\n") as h:
        h.write("captured_at=" + now + "\n")
        h.write("conclusion=REWORK\nstatic_only=true\nfunctional_recovery=NOT_EXECUTED\n")
        h.write(json.dumps({"isolated_files_unchanged": count, "copied_P1_files": len(added),
            "local_links": len(links), "static_author_commands": [0, 0],
            "confirmed_findings": ["A03-P1-API-01", "A03-P1-REF-01"]}, ensure_ascii=False) + "\n")
    files = sorted([REPORT, *[p for p in HERE.rglob("*") if p.is_file() and p != MANIFEST]], key=rel)
    owned = [rel(p) for p in files]
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    ignored = subprocess.run(["git", "check-ignore", "--stdin", "-z"], cwd=ROOT,
        env=env, input=("\0".join(owned) + "\0").encode(), capture_output=True, timeout=30)
    assert ignored.returncode in (0, 1)
    ignored_names = sorted(s.decode() for s in ignored.stdout.split(b"\0") if s)
    for path in files:
        if path.suffix == ".json":
            load(path)
    write_new(MANIFEST, {"format_version": "a03-p1-independent-review-sha256-1",
        "captured_at": now, "reviewed_commit": COMMIT, "design_commit": DESIGN,
        "conclusion": "REWORK", "scope": "P1 static design review only",
        "algorithm": "SHA256", "self_excluded": rel(MANIFEST),
        "excluded_owned_files": [], "git_ignored_but_included": ignored_names,
        "isolated_input_set": {"root": str(STAGE), "index": rel(HERE / "export-manifest.json"),
            "file_count": count, "not_omitted_from_byte_verification": True,
            "portable_frozen_P1_copy": rel(frozen_copy), "portable_files": 149},
        "files": [{"path": rel(p), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in files]})
    verify_only()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    verify_only() if args.verify_only else create()
