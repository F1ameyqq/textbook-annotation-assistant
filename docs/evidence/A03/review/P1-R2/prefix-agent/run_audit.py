"""Bounded synchronous runner preserving exact argv/cwd/return/stdout/stderr."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path("D:/1800/.local/stages/A03-review-P1-R2/940a5de33a24b1a3a9ded6e69ade1dd0609ed83a/examples/a03/P1-R2/data")
ARGV = [sys.executable, "-B", str(HERE / "audit_prefix.py"), "--root", str(ROOT), "--output", str(HERE / "independent-results.json")]
p = subprocess.run(ARGV, cwd="D:/1800", capture_output=True, text=True, timeout=60)
entry = {"argv": ARGV, "cwd": "D:/1800", "exit_code": p.returncode,
    "stdout": p.stdout, "stderr": p.stderr,
    "script_sha256": hashlib.sha256((HERE/"audit_prefix.py").read_bytes()).hexdigest(),
    "completed_synchronous_child": True, "background_children_started": 0,
    "recovery_or_platform_execution": "NOT_EXECUTED"}
(HERE / "command-run.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(p.stdout, end="")
if p.stderr:
    print(p.stderr, file=sys.stderr, end="")
raise SystemExit(p.returncode)
