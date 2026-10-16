"""Reproduce only frozen author P1 static design checks and manifest hashes."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("D:/1800")
COMMIT = "2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9"
STAGE = ROOT / ".local/stages/A03-review-P1" / COMMIT
OUT = ROOT / "docs/evidence/A03/review/P1/author-reproduction"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(STAGE / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    commands = []
    for name, relative in (
        ("check-design", "examples/a03/P1/check_design.py"),
        ("check-api-design", "docs/evidence/A03/execution/P1/check_api_design.py"),
    ):
        argv = [sys.executable, "-B", str(STAGE / relative)]
        result = subprocess.run(argv, cwd=STAGE, env=env, capture_output=True, timeout=60)
        for stream, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
            with (OUT / f"{name}.{stream}.log").open("xb") as h:
                h.write(raw)
        parsed = json.loads(result.stdout) if result.returncode == 0 else None
        commands.append({"argv": argv, "cwd": str(STAGE), "timeout_seconds": 60,
            "PYTHONPATH": env["PYTHONPATH"], "returncode": result.returncode,
            "script_sha256": hashlib.sha256((STAGE / relative).read_bytes()).hexdigest(),
            "script_resolved_path": str((STAGE / relative).resolve()),
            "business_imports_or_functionality": "NOT_EXECUTED", "parsed_result": parsed})
    manifest_path = "docs/evidence/A03/execution/P1/sha256-manifest.json"
    manifest = json.loads((STAGE / manifest_path).read_bytes())
    for item in manifest["files"]:
        path = (STAGE / item["path"]).resolve()
        assert path.is_relative_to(STAGE)
        raw = path.read_bytes()
        assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], item["path"]
    result = {"commit": COMMIT, "python": sys.version, "executable": sys.executable,
        "commands": commands, "execution_manifest_entries_verified": len(manifest["files"]),
        "execution_manifest_metadata": {k: v for k, v in manifest.items() if k != "files"},
        "all_commands_exited": True, "remaining_owned_background_processes": 0,
        "runtime_functionality_executed": False}
    with (OUT / "results.json").open("x", encoding="utf-8", newline="\n") as h:
        json.dump(result, h, ensure_ascii=False, indent=2)
        h.write("\n")
    print(json.dumps({"manifest_entries_verified": len(manifest["files"]),
        "command_exit_codes": [c["returncode"] for c in commands],
        "static_cases": commands[0]["parsed_result"].get("case_count") if commands[0]["parsed_result"] else None,
        "business_functionality_executed": False}))

if __name__ == "__main__":
    main()
