"""Run an existing Usense entry under the unchanged frozen Windows Job holder.

No default business action, retry, authorization, profile or input selection.
Supply the current explicit input arguments after --. Use --help for usage.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
# In a release the child cwd is app/, but outputs must stay outside its parent
# package as well. Source-checkout invocations keep the repository boundary.
PACKAGE_ROOT = ROOT.parent if ROOT.name.casefold() == "app" else ROOT
HOLDER_SHA = "90babd87d0ec8e7bcda00f4ff0d2aa3f148ac26b84884735c4301c2a12a74e57"
ENTRIES = {"batch": "run_usense_reviewed_batch.py", "recovery": "run_usense_postsave_readback.py", "live": "run_usense_live.py"}


def run(tool, args, record_prefix, seconds):
    if seconds <= 0:
        raise ValueError("POSITIVE_TIMEOUT_REQUIRED")
    prefix = Path(record_prefix)
    resolved = prefix.resolve()
    boundary = PACKAGE_ROOT.resolve()
    # samefile also catches Windows directory aliases whose spelling differs
    # after resolution (for example extended-length drive paths).
    if not prefix.is_absolute() or any(
        p == boundary or (p.exists() and p.samefile(boundary))
        for p in (resolved, *resolved.parents)
    ):
        raise ValueError("ABSOLUTE_OUTPUT_OUTSIDE_PACKAGE_REQUIRED")
    for suffix in (".stdout", ".stderr", ".process.json"):
        if prefix.with_suffix(suffix).exists():
            raise FileExistsError("OWNED_OUTPUT_EXISTS_NO_RETRY:" + str(prefix.with_suffix(suffix)))
    holder_path = ROOT / "tools/owned_process.py"
    if hashlib.sha256(holder_path.read_bytes()).hexdigest() != HOLDER_SHA:
        raise ValueError("FROZEN_HOLDER_CHANGED")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("a29_frozen_owned_process", holder_path)
    holder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(holder)
    command = [sys.executable, "-I", "-B", str(ROOT / "tools" / ENTRIES[tool]), *args]
    result = holder.run(command, ROOT, prefix, seconds)
    passed = result.get("exit_code") == 0 and result.get("owned_os_release_confirmed") is True and not result.get("timeout")
    print(json.dumps({"status": "CHILD_EXIT_ZERO_AND_OWNED_OS_RELEASED" if passed else "STOPPED_NO_RETRY",
                      "process_record": str(prefix.with_suffix(".process.json")),
                      "child_exit_code": result.get("exit_code"), "owned_os_release_confirmed": result.get("owned_os_release_confirmed"),
                      "business_acceptance": "NOT_INFERRED_FROM_HOLDER"}))
    return 0 if passed else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record-prefix", required=True)
    p.add_argument("--seconds", type=int, required=True)
    p.add_argument("tool", choices=ENTRIES)
    p.add_argument("args", nargs=argparse.REMAINDER)
    a = p.parse_args()
    args = a.args[1:] if a.args[:1] == ["--"] else a.args
    if not args:
        p.error("explicit original-tool arguments required; no default production inputs")
    return run(a.tool, args, a.record_prefix, a.seconds)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "STOPPED_NO_RETRY", "error_type": type(exc).__name__, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
