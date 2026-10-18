"""Second/final frozen candidate: original and non-final stage version, once each."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    foreign_cwd = out / "foreign-cwd"
    foreign_cwd.mkdir()
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    env = dict(os.environ, PYTHONPATH=str(root / "src"), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", GIT_NO_LAZY_FETCH="1")
    metadata = {"pid": os.getpid(), "python": sys.version, "executable": sys.executable, "source_root": str(root),
                "files": [{"path": str(root / p), "sha256": hashlib.sha256((root / p).read_bytes()).hexdigest()}
                          for p in ("src/annotation/source/b_handoff/reader.py", "src/annotation/source/b_handoff/__main__.py", "examples/a06/consume.py")]}
    dump(out / "driver-metadata.json", metadata)
    outcomes = []
    cases = [("original", str(args.original.resolve()), recipe["original_sha256"], "3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f"),
             ("unknown-stage-result", recipe["path"], recipe["sha256"], recipe["manifest_sha256"])]
    for name, package, package_sha, manifest_sha in cases:
        argv = [sys.executable, "-B", str(root / "examples/a06/consume.py"), package, "--sha256", package_sha, "--manifest-sha256", manifest_sha]
        started = time.time()
        child = subprocess.Popen(argv, cwd=str(foreign_cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = child.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            child.kill()
            stdout, stderr = child.communicate()
        record = {"argv": argv, "cwd": str(foreign_cwd), "pid": child.pid, "exit_code": child.returncode,
                  "started_unix": started, "finished_unix": time.time(), "process_reaped": child.poll() is not None,
                  "environment_overrides": {key: env[key] for key in ("PYTHONPATH", "PYTHONIOENCODING", "PYTHONDONTWRITEBYTECODE", "GIT_NO_LAZY_FETCH")}}
        (out / (name + ".stdout.txt")).write_bytes(stdout)
        (out / (name + ".stderr.txt")).write_bytes(stderr)
        dump(out / (name + ".process.json"), record)
        try:
            receipt = json.loads(stdout.decode("utf-8"))
            if name == "original":
                checks = [s["result_version_check"] for s in receipt["pipeline"]["stages"]]
                matched = (child.returncode == 0 and receipt["decision"] == "HOLD" and
                           receipt["counts"] == {"question_candidates": 34, "answer_candidates": 66, "current_check_issues": 127} and
                           receipt["business_acceptance"] is False and receipt["c01_execution_eligible"] is False and
                           receipt["history_gap"]["statuses"] == ["UNRESOLVED_HISTORY_REFERENCE", "UNCONFIRMED_REQUIREDNESS"] and
                           receipt["history_gap"]["optional"] is None and len(checks) == 14 and
                           all(c["validated"] and c["context"] == "FIXED_STAGE_DIAGNOSTIC_ONLY" and not c["grants_current_top_level_support"] for c in checks))
                dump(out / "result-version-checks.json", checks)
            else:
                matched = (child.returncode == 2 and receipt["error"]["code"] == recipe["expected_code"] and
                           receipt["error"]["layer"] == recipe["expected_layer"] and receipt["error"]["path"] == recipe["expected_error_path"])
            outcomes.append({"name": name, "exit_code": child.returncode, "expected_matched": matched,
                             "decision": receipt["decision"], "error": receipt.get("error")})
        except (ValueError, KeyError):
            outcomes.append({"name": name, "exit_code": child.returncode, "expected_matched": False})
    summary = {"status": "REVIEW", "candidate_number": 2, "final_candidate": True, "outcomes": outcomes,
               "all_expectations_met": all(row["expected_matched"] for row in outcomes), "children_reaped": 2,
               "background_processes_started": 0, "original_unchanged": hashlib.sha256(args.original.read_bytes()).hexdigest() == recipe["original_sha256"]}
    dump(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["all_expectations_met"] and summary["original_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
