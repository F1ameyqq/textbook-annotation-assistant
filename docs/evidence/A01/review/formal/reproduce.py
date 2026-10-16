"""Reproduce author commands using only the verified frozen export."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / "reproduction"
STAGE = ROOT / ".local/stages/A01-review/a8d5e96d128e10d341de935d4856682e50df79d9"
SNAPSHOT = STAGE / "snapshot-verified"


def main():
    OUT.mkdir(exist_ok=False)
    temp = STAGE / "author-command-temp"
    temp.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONPATH=str(SNAPSHOT / "src"), PYTHONDONTWRITEBYTECODE="1",
               TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp))
    tasks = [
        ("01-import-paths", ["-B", "-c", "import json,annotation.contracts as c,annotation.geometry as g,annotation.source.static as s; print(json.dumps({'contracts':c.__file__,'geometry':g.__file__,'source':s.__file__}))"]),
        ("02-a01-tests", ["-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_a01_*.py", "-v"]),
        ("03-c01-tests", ["-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_contracts*.py"]),
        ("04-old-consumer", ["-B", "examples/a01/consume.py", "examples/a01/bundles/46006966/exchange.json", "--book-id", "46006966"]),
        ("05-new-consumer", ["-B", "examples/a01/consume.py", "examples/a01/bundles/46007447/exchange.json", "--book-id", "46007447"]),
        ("06-build", ["-B", "examples/a01/build.py", str(STAGE / "independent built bundles")]),
        ("07-verify", ["-B", "examples/a01/verify.py", str(STAGE / "independent author evidence")]),
    ]
    records = []
    for name, arguments in tasks:
        start = time.monotonic()
        proc = subprocess.run([sys.executable] + arguments, cwd=SNAPSHOT, env=env, capture_output=True)
        (OUT / (name + ".stdout.txt")).write_bytes(proc.stdout)
        (OUT / (name + ".stderr.txt")).write_bytes(proc.stderr)
        records.append({"name":name,"command":[sys.executable] + arguments,"cwd":str(SNAPSHOT),
                        "environment_overrides":{k:env[k] for k in ("PYTHONPATH","PYTHONDONTWRITEBYTECODE","TMP","TEMP","TMPDIR")},
                        "exit_code":proc.returncode,"seconds":round(time.monotonic()-start,3),
                        "stdout":name+".stdout.txt","stderr":name+".stderr.txt"})
        print(name + ": exit=" + str(proc.returncode), flush=True)
    (OUT / "commands.json").write_text(json.dumps(records, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    raise SystemExit(any(r["exit_code"] != 0 for r in records))


if __name__ == "__main__":
    main()
