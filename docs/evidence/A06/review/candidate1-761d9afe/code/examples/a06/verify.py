"""Author evidence driver: four real public-consumer children, fixed finite API checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from make_variants import make_variants


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("variant_directory", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    variants = make_variants(args.package, args.variant_directory)
    for recipe in args.variant_directory.glob("*-recipe.json"):
        shutil.copyfile(recipe, out / recipe.name)
    env = dict(os.environ, PYTHONPATH=str(root / "src"), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", GIT_NO_LAZY_FETCH="1")
    foreign_cwd = args.variant_directory.resolve() / "foreign-cwd"
    foreign_cwd.mkdir()
    records = []

    def child(name, argv, cwd):
        started = time.time()
        result = subprocess.run(argv, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        (out / (name + ".stdout.txt")).write_bytes(result.stdout)
        (out / (name + ".stderr.txt")).write_bytes(result.stderr)
        record = {"name": name, "argv": argv, "cwd": str(cwd), "exit_code": result.returncode,
                  "started_unix": started, "finished_unix": time.time(), "process_reaped": True,
                  "environment_overrides": {key: env[key] for key in ("PYTHONPATH", "PYTHONIOENCODING", "PYTHONDONTWRITEBYTECODE", "GIT_NO_LAZY_FETCH")},
                  "stdout_file": name + ".stdout.txt", "stderr_file": name + ".stderr.txt"}
        records.append(record)
        dump(out / (name + ".process.json"), record)
        return result

    metadata = child("imports", [sys.executable, "-c", "import sys,json,hashlib,pathlib,PIL,pydantic; import annotation.source.b_handoff as b; import annotation.contracts as c; mods=[b,c]; print(json.dumps({'python':sys.version,'executable':sys.executable,'Pillow':PIL.__version__,'pydantic':pydantic.__version__,'schema_version':c.SCHEMA_VERSION,'schema_title':c.schema().get('title'),'public_entries':[n for n in ['load_bundle','validate_bundle','schema','ContractError'] if hasattr(c,n)],'modules':[{'file':m.__file__,'sha256':hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest()} for m in mods]}))"], foreign_cwd)
    cases = [{"case": "original", "path": str(args.package.resolve()),
              "sha256": "b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d",
              "manifest_sha256": "3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f"}] + variants
    outcomes = []
    for case in cases:
        result = child(case["case"], [sys.executable, str(root / "examples/a06/consume.py"), case["path"],
                       "--sha256", case["sha256"], "--manifest-sha256", case["manifest_sha256"]], foreign_cwd)
        try:
            receipt = json.loads(result.stdout.decode("utf-8"))
            if case["case"] == "original":
                matched = (result.returncode == 0 and receipt["decision"] == "HOLD" and
                           receipt["business_acceptance"] is False and receipt["c01_execution_eligible"] is False and
                           list(receipt["counts"][k] for k in ("question_candidates", "answer_candidates", "current_check_issues")) == [34, 66, 127] and
                           receipt["history_gap"]["statuses"] == ["UNRESOLVED_HISTORY_REFERENCE", "UNCONFIRMED_REQUIREDNESS"])
            else:
                matched = result.returncode == 2 and receipt["error"]["code"] == case["expected_code"] and receipt["error"]["layer"] == case["expected_layer"]
            outcomes.append({"case": case["case"], "expected_matched": matched, "exit_code": result.returncode,
                             "decision": receipt["decision"], "error": receipt.get("error"),
                             "input_sha256": case["sha256"]})
        except (ValueError, KeyError):
            outcomes.append({"case": case["case"], "expected_matched": False, "exit_code": result.returncode})
    version_code = """import json
from annotation.source.b_handoff import version_policy,HandoffError
rows=[]
for kind,prefix in [('QuestionGraphTrial','b-graph-trial/'),('CheckReportTrial','b-check-trial/')]:
 for v,location,bound in [('0.4','CURRENT',False),('0.4','ARCHIVE',True),('0.5','CURRENT',False),('0.5','ARCHIVE',True),('0.6','CURRENT',False),('0.7','CURRENT',False),('9.9','CURRENT',False)]:
  try: observed=version_policy(prefix+v,kind=kind,location=location,bound_archive=bound)
  except HandoffError as e: observed=e.code
  rows.append(dict(kind=kind,version=v,location=location,observed=observed))
print(json.dumps(rows))
"""
    matrix = child("versions", [sys.executable, "-c", version_code], foreign_cwd)
    for fixture in ("normal", "exception", "unknown"):
        result = child("c01-" + fixture, [sys.executable, str(root / "examples/contracts/consume.py"), str(root / "tests/fixtures/contracts" / fixture)], foreign_cwd)
        outcomes.append({"case": "c01-" + fixture, "expected_matched": result.returncode == 0, "exit_code": result.returncode})
    tests = child("version-tests", [sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-p", "test_a06*.py", "-v"], foreign_cwd)
    summary = {"status": "REVIEW", "author_only": True, "outcomes": outcomes,
               "all_expectations_met": all(v["expected_matched"] for v in outcomes) and all(r.returncode == 0 for r in (metadata, matrix, tests)),
               "children_reaped": len(records), "background_processes_started": 0,
               "original_unchanged": hashlib.sha256(args.package.read_bytes()).hexdigest() == cases[0]["sha256"]}
    dump(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["all_expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
