"""180s trial / 240s release bound; original Popen handle owns termination."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from audit import git, process_creation, utc, raw_manifest

ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-dir", type=Path, required=True)
    args = parser.parse_args()
    assert git(ROOT, "rev-parse", "HEAD").decode().strip() == args.expected_head
    output, budget = args.output.resolve(), args.budget_dir.resolve()
    starts = sorted(budget.glob("attempt-*-start.json"))
    finishes = sorted(budget.glob("attempt-*-finish.json"))
    if len(starts) != len(finishes) or len(starts) >= 2:
        raise ValueError("unreleased attempt or two attempts already consumed")
    previous = [json.loads(p.read_text(encoding="utf-8")) for p in finishes]
    if any(p["success"] for p in previous):
        raise ValueError("success already consumed; no rerun allowed")
    if any(json.loads(p.read_text(encoding="utf-8"))["frozen_head"] == args.expected_head for p in starts):
        raise ValueError("one normal trial per frozen candidate")
    output.mkdir(parents=True, exist_ok=False)
    # Freeze exact raw Git bytes for all project Python imports and this driver.
    prefixes = ["src/", "examples/a09/", "config/policies/a09-q4-offline-v1.json", "tests/test_a09_",
                "docs/approvals/A09-Q4-offline-business-approval.json", "docs/reviews/q4-first-lesson/proposal.json", "docs/tasks/A09-inputs.json"]
    members = raw_manifest(ROOT, args.expected_head, prefixes)
    for m in members:
        import hashlib
        if hashlib.sha256((ROOT / m["path"]).read_bytes()).hexdigest() != m["sha256"]:
            raise ValueError("working bytes differ from frozen Git: " + m["path"])
    save(output / "runtime-members.json", members)
    number = len(starts) + 1
    supervisor = {"pid": os.getpid(), "kernel_creation_time": process_creation(os.getpid()), "started_at": utc()}
    start = {"attempt": number, "frozen_head": args.expected_head, "normal_trial_limit": 180, "release_limit": 240, "supervisor": supervisor}
    save(budget / ("attempt-" + str(number) + "-start.json"), start)
    command = [sys.executable, "-B", str(ROOT / "examples/a09/run_once.py"), "--expected-head", args.expected_head,
               "--inputs", str(args.inputs.resolve()), "--output", str(output / "trial")]
    started = time.monotonic()
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=dict(os.environ, GIT_NO_LAZY_FETCH="1", PYTHONDONTWRITEBYTECODE="1"), stdout=stdout, stderr=stderr)
        creation = process_creation(process.pid)
        save(output / "process-start.json", dict(start, child_pid=process.pid, child_kernel_creation_time=creation, command=command))
        timed_out = False
        try:
            exit_code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Popen retains the original kernel process handle: no PID-reuse kill.
            process.terminate()
            exit_code = process.wait(timeout=max(1, 240 - (time.monotonic() - started)))
    elapsed = time.monotonic() - started
    ended_at = utc()
    seen_creation = process_creation(process.pid)
    released = process.poll() is not None and (seen_creation is None or seen_creation != creation)
    # A waited Windows process object may remain queryable until its handle closes.
    # wait() returned from the original handle, which conclusively proves exit.
    release = {"supervisor": supervisor, "child_pid": process.pid, "child_kernel_creation_time": creation,
        "child_ended_at": ended_at, "exit_code": exit_code, "timed_out": timed_out, "elapsed_seconds": elapsed,
        "waited_original_handle": True, "child_released": process.poll() is not None,
        "pid_requery_creation": seen_creation, "pid_reuse_or_absent": released, "background_services": 0,
        "within_release_bound": elapsed <= 240, "frozen_head": args.expected_head,
        "success": exit_code == 0 and not timed_out and (output / "trial/summary.json").exists()}
    save(output / "release.json", release)
    save(budget / ("attempt-" + str(number) + "-finish.json"), release)
    print(json.dumps(release, ensure_ascii=False), flush=True)
    return 0 if release["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
