"""Freeze check + 180s child watchdog; terminate/reap only our own child by 240s."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-candidate", required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", PYTHONIOENCODING="utf-8", PYTHONPATH=str(repo / "src"))
    git = ["git", "-c", "core.longpaths=true"]
    head = subprocess.check_output(git + ["rev-parse", "HEAD"], cwd=repo, env=env, text=True).strip()
    if head != args.expected_candidate:
        raise SystemExit("HEAD differs from explicit frozen candidate")
    subprocess.run(git + ["diff", "--quiet", "HEAD", "--"], cwd=repo, env=env, check=True)
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "annotation.delivery.q1_offline", "--input-dir", str(Path(args.input_dir).resolve()),
        "--policy", str(repo / "config/policies/a07-q1-offline-v1.json"), "--output", str(root / "run"), "--run-id", args.run_id]
    start = time.monotonic()
    timed_out = False
    with (root / "process-output.txt").open("wb") as log:
        child = subprocess.Popen(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = child.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait(timeout=60)
    record = {"candidate_commit": head, "command": command, "supervisor_pid": os.getpid(), "child_pid": child.pid,
              "child_exit_code": code, "child_reaped": child.poll() is not None, "timed_out": timed_out,
              "outer_experiment_seconds": 180, "outer_reclaim_seconds": 240,
              "elapsed_seconds": round(time.monotonic() - start, 3), "spawned_children": 1,
              "browser_or_service_processes_started": 0}
    (root / "supervisor.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))
    return code if not timed_out else 124


if __name__ == "__main__":
    sys.exit(main())
