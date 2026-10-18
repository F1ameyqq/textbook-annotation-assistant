"""Record the synchronous D01 runner's own exit independently of its ledger."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("runner_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    assert not args.receipt.exists(), "preserve the previous collector receipt"
    args.receipt.mkdir(parents=True)
    runner_args = args.runner_args[1:] if args.runner_args[:1] == ["--"] else args.runner_args
    argv = [sys.executable, "-I", str(Path(__file__).with_name("run.py")), *runner_args]
    start = time.time()
    with (args.receipt / "stdout.txt").open("wb") as out, (args.receipt / "stderr.txt").open("wb") as err:
        child = subprocess.Popen(argv, cwd=str(Path.cwd()), stdout=out, stderr=err)
        code = child.wait()
    record = {"argv": argv, "cwd": str(Path.cwd()), "pid": child.pid,
              "started_unix": start, "finished_unix": time.time(), "exit_code": code,
              "synchronous_return": True, "background_children_started": 0}
    for name in ("stdout.txt", "stderr.txt"):
        record[name + "_sha256"] = hashlib.sha256((args.receipt / name).read_bytes()).hexdigest()
    (args.receipt / "command.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2), flush=True)
    print((args.receipt / "stdout.txt").read_text(encoding="utf-8"), flush=True)
    if code:
        print((args.receipt / "stderr.txt").read_text(encoding="utf-8"), file=sys.stderr, flush=True)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
