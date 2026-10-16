"""Offline inventory only. This does not test or accept the A01 implementation."""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
EXECUTION = Path("C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800")
BASE = "39341c98d73c354d639f3beeb55429f55d0e9be5"
C01 = "4e42668ab28eda37a37285285d2f6c595d3bba12"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(cwd, *args):
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    return {"args": list(args), "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def save(name, data):
    # Do not silently refresh an earlier observation or overwrite review evidence.
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def main():
    names = [
        "技术证据/只读样本-46006966/viewer-page-0008.jpg",
        "技术证据/只读样本-46006966/viewer-page-0009.jpg",
        "技术证据/只读样本-46006966/viewer-page-0010.jpg",
        "技术证据/只读样本-46006966/viewer-page-0234.jpg",
        "技术证据/只读样本-46006966/source-images-complete.json",
        "技术证据/只读样本-46006966/directory.json",
        "技术证据/只读样本-46006966/manual-annotations.json",
        "技术证据/只读样本-46006966/paper-questions-original.jsonl",
        "技术证据/只读样本-46006966/reference-review-notes.json",
        "data/derived/manifest.json",
        "data/derived/CORRECTION-page-mapping.md",
        "docs/evidence/A05/review/independent-original-question.jpg",
        "docs/evidence/A05/review/independent-original-answer.jpg",
        "docs/evidence/A05/review/independent-originals.json",
        "docs/evidence/A05/review/independent-source-page14.json",
        "docs/evidence/A05/review/independent-source-page173.json",
        "docs/evidence/A05/review/independent-response-0003.json",
        "docs/evidence/A05/review/independent-book.json",
        "docs/evidence/A05/execution/source-metadata.json",
        "docs/evidence/A05/execution/source-viewer14.jpg",
        "docs/evidence/A05/execution/source-viewer173.jpg",
    ]
    names.extend(p.relative_to(ROOT).as_posix()
                 for p in sorted((ROOT / "data/raw/images").glob("*.jpg")))
    records = []
    for name in names:
        path = ROOT / name
        entry = {"path": name, "exists": path.is_file()}
        if path.is_file():
            data = path.read_bytes()
            entry.update(bytes=len(data), sha256=digest(data))
        records.append(entry)
    state_bytes = (ROOT / "docs/coordination-state.json").read_bytes()
    state = json.loads(state_bytes)
    packages = {}
    for name in ("pydantic", "pytest", "Pillow"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    rule_paths = ["AGENTS.md", "docs/architecture.md", "docs/contracts-v1.md",
                  "docs/coordination.md", "docs/tasks/A01-independent-review.md",
                  "docs/tasks/A01-source-geometry.md",
                  "docs/tasks/A01-A02-A04-preparation.md"]
    observation = {
        "schema_version": 1, "phase": "PREPARATION", "status": "WAITING_EXECUTION",
        "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "time_zone": "Asia/Shanghai", "base_commit": BASE, "workflow_commit": BASE,
        "target_delivery_commit": None,
        "coordinator_head": git(ROOT, "rev-parse", "HEAD"),
        "execution_head": git(EXECUTION, "rev-parse", "HEAD"),
        "execution_worktree_status": git(EXECUTION, "status", "--short"),
        "execution_report_present": (EXECUTION / "docs/tasks/A01-execution-report.md").is_file(),
        "frozen_delivery_received": False,
        "coordination_state_sha256": digest(state_bytes),
        "coordination_state_updated_at": state["updated_at"],
        "A01": state["tasks"]["A01"],
        "accepted_C01_commit": C01,
        "accepted_C01_is_baseline_ancestor": git(ROOT, "merge-base", "--is-ancestor", C01, BASE),
        "rule_files": [{"path": p, "sha256": digest((ROOT / p).read_bytes())} for p in rule_paths],
        "environment": {"python": sys.version, "executable": sys.executable,
                        "platform": platform.platform(), "packages": packages},
        "limits": {"formal_A01_tests_run": False, "image_decode_verified": False,
                   "input_mapping_independently_verified": False,
                   "browser_started": False, "network_used": False,
                   "credentials_read": False, "OCR_or_model_tool_calls": 0,
                   "paid_model_tool_cost": 0, "platform_actions": False,
                   "implementation_modified": False, "coordination_state_modified": False,
                   "integration_performed": False, "A04_dependency_released": False},
    }
    save("preparation-observation.json", observation)
    save("input-inventory-before.json", {
        "schema_version": 1, "phase": "PREPARATION_ONLY", "observed_at": observation["observed_at"],
        "purpose": "Byte baseline for later frozen-commit import and before/after comparison; not a source acceptance result.",
        "records": records,
    })
    print(json.dumps({"status": observation["status"], "input_files": len(records),
                      "missing": [r["path"] for r in records if not r["exists"]],
                      "execution_head": observation["execution_head"]["stdout"],
                      "execution_report_present": observation["execution_report_present"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
