"""Run only the frozen new A11 suite once, fail fast, retaining every owned artifact."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))


def main():
    destination = Path(sys.argv[1]).resolve()
    destination.relative_to(ROOT / "docs" / "evidence" / "A11" / "execution")
    destination.mkdir(parents=True, exist_ok=False)
    os.environ["A11_CASE_ROOT"] = str(destination / "runtime")
    os.environ["A11_PROCESS_LOG"] = str(destination / "process-events.jsonl")
    os.environ["PYTHONPATH"] = str(ROOT / "src")
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    catalog = json.loads((ROOT / "docs/evidence/A11/execution/suite-catalog.json").read_text(encoding="utf-8"))
    suite = unittest.TestSuite()
    for identity in catalog["case_ids"]:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(identity))
    result_path = destination / "result.json"
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    head = subprocess.check_output(["git", "-c", "core.longpaths=true", "rev-parse", "HEAD"], cwd=ROOT,
        env=dict(os.environ, GIT_NO_LAZY_FETCH="1"), text=True).strip()
    cases = {identity: "NOT_RUN" for identity in catalog["case_ids"]}
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            cases[test.id()] = "RUNNING"
            super().startTest(test)
        def addSuccess(self, test):
            cases[test.id()] = "PASS"
            super().addSuccess(test)
        def addFailure(self, test, error):
            cases[test.id()] = "FAIL"
            super().addFailure(test, error)
        def addError(self, test, error):
            cases[test.id()] = "ERROR"
            super().addError(test, error)
    with (destination / "suite.log").open("x", encoding="utf-8") as log:
        runner = unittest.TextTestRunner(stream=log, verbosity=2, failfast=True, resultclass=Result)
        result = runner.run(suite)
    summary = {"status": "PASS" if result.wasSuccessful() else "FAIL", "candidate_commit": head,
        "started_at": started, "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "suite_attempt": destination.name, "case_results": cases, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "platform_calls": 0,
        "independent_acceptance": "PENDING", "submission_status": "NOT_SUBMITTED"}
    result_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__": raise SystemExit(main())
