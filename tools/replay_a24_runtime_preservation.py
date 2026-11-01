"""Replay the fixed runtime-preservation regressions with synthetic data only.

The packaged A source is isolated from the repository's B Python namespace.
No browser, website, API, model or original private input is accessed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "handoffs/b/a24/a24-runtime-preservation-v3-20261022.zip"
PACKAGE_SHA256 = "2f97801dc13bc040b1eefb97b02932c2c7cbfee887297eedf579cd6998c52638"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="new directory; old runs are not overwritten")
    args = parser.parse_args(argv)
    output = Path(args.out).resolve()
    if output.exists():
        raise FileExistsError("RUNTIME_REPLAY_OUTPUT_EXISTS")
    if hashlib.sha256(PACKAGE.read_bytes()).hexdigest() != PACKAGE_SHA256:
        raise ValueError("RUNTIME_REPLAY_PACKAGE_HASH")
    with zipfile.ZipFile(PACKAGE) as package:
        names = set()
        for item in package.infolist():
            path = PurePosixPath(item.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in item.filename or
                    ":" in item.filename or item.filename in names or
                    (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("RUNTIME_REPLAY_PACKAGE_PATH")
            names.add(item.filename)
        manifest = json.loads(package.read("runtime.json"))
        expected = {item["path"] for item in manifest["members"]} | {"runtime.json"}
        if expected != names or len(expected) != len(manifest["members"]) + 1:
            raise ValueError("RUNTIME_REPLAY_MEMBER_SET")
        for item in manifest["members"]:
            raw = package.read(item["path"])
            if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("RUNTIME_REPLAY_MEMBER_HASH")
        output.mkdir(parents=True)
        source = output / "runtime"
        package.extractall(source)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    calls = []
    for suite in manifest["regression_suites"]:
        command = [sys.executable, "-m", "unittest", "discover", "-s", suite["path"], "-v"]
        result = subprocess.run(command, cwd=source, env=environment,
                                capture_output=True, text=True, encoding="utf-8")
        observed = re.search(r"^Ran (\d+) tests? in ", result.stderr, re.MULTILINE)
        count = int(observed.group(1)) if observed else None
        qualified = (result.returncode == 0 and count == suite["expected_tests"] and
                     not re.search(r"^OK \(skipped=", result.stderr, re.MULTILINE))
        calls.append({"suite": suite["path"], "command": command, "exit_code": result.returncode,
                      "expected_tests": suite["expected_tests"], "observed_tests": count,
                      "suite_qualified": qualified, "stdout": result.stdout, "stderr": result.stderr})
        if not qualified:
            break
    passed = len(calls) == len(manifest["regression_suites"]) and all(c["suite_qualified"] for c in calls)
    receipt = {"schema": "A24RuntimePreservationReplay/v1",
               "result": "PASS_SYNTHETIC_RUNTIME_REGRESSIONS" if passed else "FAIL_PRESERVED",
               "package_sha256": PACKAGE_SHA256, "calls": calls,
               "evidence_mode": "SYNTHETIC", "real_platform_format_qualified": False,
               "platform_use_allowed": False, "platform_calls": 0, "model_calls": 0}
    (output / "replay-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8", newline="\n")
    print(json.dumps({"result": receipt["result"], "suite_exit_codes": [c["exit_code"] for c in calls],
                      "receipt": str(output / "replay-receipt.json"), "platform_use_allowed": False}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
