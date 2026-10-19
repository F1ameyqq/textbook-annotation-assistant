"""One bounded six-case delta with an owned Popen handle and fail-fast evidence."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent


def write(path, data):
    with path.open("xb") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def worker(destination):
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "tests"))
    os.environ["A11_DELTA_CASE_ROOT"] = str(destination / "cases")
    catalog = json.loads((HERE / "case-catalog.json").read_bytes())
    statuses = {case["id"]: "NOT_RUN" for case in catalog["cases"]}
    def progress():
        # Unique progress snapshots retain first unexpected failure and remaining NOT_RUN.
        n = len(list(destination.glob("progress-*.json"))) + 1
        write(destination / ("progress-%02d.json" % n), statuses)
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            statuses[test.id()] = "RUNNING"
            progress()
            super().startTest(test)
        def addSuccess(self, test):
            statuses[test.id()] = "PASS"
            progress()
            super().addSuccess(test)
        def addFailure(self, test, error):
            statuses[test.id()] = "FAIL"
            progress()
            super().addFailure(test, error)
        def addError(self, test, error):
            statuses[test.id()] = "ERROR"
            progress()
            super().addError(test, error)
    suite = unittest.TestSuite()
    for identity in statuses:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(identity))
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (destination / "suite.log").open("x", encoding="utf-8", newline="\n") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, failfast=True, resultclass=Result).run(suite)
    record = {"status": "PASS" if result.wasSuccessful() else "FAIL", "case_results": statuses,
              "started_at": started, "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "pid": os.getpid(), "new_plan_calls": 0, "new_intent_calls": 0, "new_apply_calls": 0,
              "new_send_calls": 0, "platform_calls": 0, "independent_acceptance": "PENDING"}
    write(destination / "result.json", record)
    print(json.dumps(record, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


def main():
    if sys.argv[1] == "worker":
        return worker(Path(sys.argv[2]))
    destination = Path(sys.argv[1]).resolve()
    destination.relative_to(HERE)
    destination.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
               PYTHONPATH=str(ROOT / "src"))
    head = subprocess.check_output(["git", "-c", "core.longpaths=true", "rev-parse", "HEAD"], cwd=ROOT, env=env, text=True).strip()
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "worker", str(destination)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    write(destination / "process-created.json", {"pid": process.pid, "supervisor_pid": os.getpid(),
          "product_commit": head, "timeout_seconds": 180, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "handle_owner": "this supervisor retains original Popen until communicate/wait completes"})
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    write(destination / "process-release.json", {"pid": process.pid, "returncode": process.returncode,
          "timed_out": timed_out, "original_popen_wait_completed": process.poll() is not None,
          "stdout_pipe_closed": process.stdout.closed, "stderr_pipe_closed": process.stderr.closed,
          "owned_process_only": True, "released_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (destination / "worker-stdout.log").write_bytes(stdout)
    (destination / "worker-stderr.log").write_bytes(stderr)
    if timed_out:
        last = sorted(destination.glob("progress-*.json"))
        statuses = json.loads(last[-1].read_bytes()) if last else {c["id"]: "NOT_RUN" for c in json.loads((HERE/"case-catalog.json").read_bytes())["cases"]}
        statuses = {k: "TIMEOUT" if v == "RUNNING" else v for k, v in statuses.items()}
        write(destination / "timeout-result.json", {"status": "TIMEOUT", "case_results": statuses})
    print(stdout.decode("utf-8", errors="replace"))
    if stderr:
        print(stderr.decode("utf-8", errors="replace"), file=sys.stderr)
    return 1 if timed_out else process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
