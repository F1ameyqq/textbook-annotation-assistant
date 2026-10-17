"""Capture the outer synchronous reviewer invocation and preserve runner bytes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
target = root / "collector-run01"
target.mkdir(exist_ok=False)
for name in ("run_review.py", "probe.py", "collect.py"):
    (target/name).write_bytes((root/name).read_bytes())
argv = [sys.executable, "-I", str(root/"run_review.py")]
started = time.time()
process = subprocess.Popen(argv, cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()
(target/"stdout.bin").write_bytes(stdout)
(target/"stderr.bin").write_bytes(stderr)
record = dict(argv=argv, cwd=str(root), pid=process.pid, collector_pid=__import__("os").getpid(), started_unix=started,
              finished_unix=time.time(), exit_code=process.returncode, synchronous_return=True,
              stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest(),
              runner_sha256=hashlib.sha256((target/"run_review.py").read_bytes()).hexdigest(),
              probe_sha256=hashlib.sha256((target/"probe.py").read_bytes()).hexdigest())
(target/"command.json").write_bytes((json.dumps(record,indent=2,sort_keys=True)+"\n").encode())
print(stdout.decode("utf-8",errors="replace"),end="")
print(stderr.decode("utf-8",errors="replace"),end="",file=sys.stderr)
print(json.dumps(record))
raise SystemExit(process.returncode)
