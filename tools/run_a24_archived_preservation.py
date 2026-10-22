"""Preserve the fixed 46007447 archived target and historical export offline.

The three inputs are separate evidence sets. This command never infers a full
current question inventory or permits a platform write.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "handoffs/b/a24/a24-archived-preservation-runtime-v2-20261022.zip"
RUNTIME_SHA256 = "65df4a0a206b1992465d30b7cf0d3ab1340ada73d08e06c78e7c1625deb44758"
STATE_SHA256 = "640aaabe023c1e96e24ac3b1b002c8b9e7c045ed7b075a8777377a8ae9ba5775"
HISTORICAL_SHA256 = "02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c"
DOM_SHA256 = "ddf4251950bc3ef076416e3a677a18d378890dd251a94d33f062a431d838a770"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="fixed parsed current-state.json archive")
    parser.add_argument("--historical", required=True, help="fixed historical 19-record JSONL")
    parser.add_argument("--current-dom", required=True, help="fixed v6 tree DOM attributes JSON")
    parser.add_argument("--out", required=True, help="new or empty directory for private outputs")
    args = parser.parse_args(argv)
    if hashlib.sha256(RUNTIME.read_bytes()).hexdigest() != RUNTIME_SHA256:
        raise ValueError("ARCHIVED_RUNTIME_HASH")
    work = ROOT / "data/runs"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="a24-archived-", dir=work) as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(RUNTIME) as package:
            names = set()
            for member in package.infolist():
                name = PurePosixPath(member.filename)
                if (name.is_absolute() or ".." in name.parts or
                        "\\" in member.filename or ":" in member.filename or
                        (member.external_attr >> 16) & 0o170000 == 0o120000 or
                        member.filename in names):
                    raise ValueError("ARCHIVED_RUNTIME_PATH")
                names.add(member.filename)
            package.extractall(extracted)
        manifest = json.loads((extracted / "runtime.json").read_bytes())
        for member in manifest["members"]:
            raw = (extracted / member["path"]).read_bytes()
            if len(raw) != member["bytes"] or hashlib.sha256(raw).hexdigest() != member["sha256"]:
                raise ValueError("ARCHIVED_RUNTIME_MEMBER_HASH")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(extracted / "src")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run([
            sys.executable, str(extracted / manifest["entrypoint"]),
            "--input", args.state, "--expected-sha256", STATE_SHA256,
            "--expected-bytes", "232913", "--historical", args.historical,
            "--historical-sha256", HISTORICAL_SHA256, "--historical-bytes", "11625",
            "--current-dom", args.current_dom, "--current-dom-sha256", DOM_SHA256,
            "--current-dom-bytes", "340", "--out", args.out,
        ], env=env, cwd=Path.cwd()).returncode


if __name__ == "__main__":
    raise SystemExit(main())
