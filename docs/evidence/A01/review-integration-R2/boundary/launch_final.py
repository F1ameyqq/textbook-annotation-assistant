"""Capture the read-only final boundary audit's real code, argv, bytes and exit."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

out = Path(__file__).resolve().parent
script = out / "audit.py"
frozen = script.read_bytes()
with (out / "audit.executed.py").open("xb") as handle:
    handle.write(frozen)
argv = [sys.executable, "-B", str(script), "--phase", "final"]
process = subprocess.run(argv, cwd=r"D:\1800", capture_output=True)
with (out / "stdout.log").open("xb") as handle:
    handle.write(process.stdout)
with (out / "stderr.log").open("xb") as handle:
    handle.write(process.stderr)
record = dict(argv=argv, cwd=r"D:\1800", exit_code=process.returncode,
              audit_sha256_before=hashlib.sha256(frozen).hexdigest(),
              audit_sha256_after=hashlib.sha256(script.read_bytes()).hexdigest(),
              executed_source_copy="audit.executed.py", stdout="stdout.log", stderr="stderr.log",
              functional_tests_run=0, own_running_processes_or_sessions=0)
with (out / "command.json").open("x", encoding="utf-8", newline="\n") as handle:
    handle.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(record))
if process.returncode:
    print(process.stderr.decode("utf-8", "replace"))
raise SystemExit(process.returncode)
