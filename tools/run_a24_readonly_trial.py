"""Run the packaged A24 offline reader without mixing A and B Python packages.

Arguments are passed unchanged to the bundled CLI. No browser or website is used.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "handoffs/b/a24/a24-readonly-trial-runtime-20261022.zip"
PACKAGE_SHA256 = "8921ec742e5830ce9184dabfde2d563e00c54314f06ee815241e7df77a2e2d6b"


def main():
    arguments = sys.argv[1:]
    if "--sample-46007447" in arguments:
        arguments.remove("--sample-46007447")
        names = ("--source-type", "--expected-sha256", "--expected-bytes")
        if any(name in arguments for name in names):
            raise ValueError("SAMPLE_PRESET_ARGUMENT_CONFLICT")
        arguments += [
            "--source-type", "HISTORICAL_EXPORT",
            "--expected-sha256", "02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c",
            "--expected-bytes", "11625",
        ]
    raw = PACKAGE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PACKAGE_SHA256:
        raise ValueError("READONLY_RUNTIME_PACKAGE_HASH")
    work = ROOT / "data/runs"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="a24-readonly-", dir=work) as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(PACKAGE) as package:
            names = set()
            for member in package.infolist():
                name = PurePosixPath(member.filename)
                if (name.is_absolute() or ".." in name.parts or
                        "\\" in member.filename or ":" in member.filename or
                        (member.external_attr >> 16) & 0o170000 == 0o120000 or
                        member.filename in names):
                    raise ValueError("READONLY_RUNTIME_PACKAGE_PATH")
                names.add(member.filename)
            package.extractall(extracted)
        manifest = json.loads((extracted / "runtime.json").read_bytes())
        for member in manifest["members"]:
            value = (extracted / member["path"]).read_bytes()
            if (len(value) != member["bytes"] or
                    hashlib.sha256(value).hexdigest() != member["sha256"]):
                raise ValueError("READONLY_RUNTIME_MEMBER_HASH")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(extracted / "src")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [sys.executable, str(extracted / manifest["entrypoint"]), *arguments]
        return subprocess.run(command, env=env, cwd=Path.cwd()).returncode


if __name__ == "__main__":
    raise SystemExit(main())
