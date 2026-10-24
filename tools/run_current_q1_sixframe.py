"""Replay the fixed current-Q1 content against the existing A07 offline consumer.

Only a local visual-transcription file and a new output directory are needed.
The A07 source is extracted from the pinned repository archive, never from an
arbitrary Python package on the machine. No browser or platform is accessed.
"""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_current_q1_sixframe.py"
BUILDER_SHA256 = "8dc1383cc0e6f5f348d71c058a6e492e5587b2097a7593a8c7518681db8ecb79"
ARCHIVE = ROOT / "handoffs/b/46007447/B-46007447-Q1-A07-adoption-2026-10-19.zip"
PINS = {
    ARCHIVE: "41ebfa94ea9d880d375f8428d054f8da857e7a5587b52d2734ef8a47d6287dbe",
    ROOT / "handoffs/b/46007447/B-46007447-Q16-offline-HOLD-2026-10-17.zip":
        "b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d",
    ROOT / "handoffs/b/46007447/B-46007447-Q1-source-candidate-v1-HOLD-2026-10-18.zip":
        "3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac",
    ROOT / "handoffs/b/46007447/single-question-q1/historical-evidence-revision1.json":
        "a763af50c0515f863eeb6dbaf533f4215535591096dd06b81632cec4acbb4493",
}
CURRENT_Q1_SHA256 = "2384a8386e8946b5842dfa5d9ce099857e7795f9397335bd6434da1f2f4aab1f"


def verify(path, expected):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
        raise ValueError("Q1_INPUT_HASH_MISMATCH: " + Path(path).name)


def extract_source(destination):
    """Extract only the already hashed A07 Python source, with no ZIP paths trusted."""
    prefix = "a07-fixed/src/"
    with zipfile.ZipFile(ARCHIVE) as package:
        members = []
        names = set()
        for member in package.infolist():
            if not member.filename.startswith(prefix) or member.is_dir():
                continue
            name = PurePosixPath(member.filename)
            if (name.is_absolute() or ".." in name.parts or
                    "\\" in member.filename or ":" in member.filename or
                    (member.external_attr >> 16) & 0o170000 == 0o120000 or
                    member.filename in names):
                raise ValueError("Q1_RUNTIME_ARCHIVE_PATH")
            names.add(member.filename)
            members.append(member)
        if not members:
            raise ValueError("Q1_RUNTIME_SOURCE_MISSING")
        for member in members:
            output = destination.joinpath(*PurePosixPath(member.filename).parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(package.read(member))
    return destination / "a07-fixed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-q1", required=True,
                        help="fixed v3 local visual transcription; not a server record")
    parser.add_argument("--output", required=True, help="a directory that does not exist")
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError("Q1_OUTPUT_EXISTS: use a new directory")
    verify(args.current_q1, CURRENT_Q1_SHA256)
    verify(BUILDER, BUILDER_SHA256)
    for path, expected in PINS.items():
        verify(path, expected)
    work = ROOT / "data/runs"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="q1-a07-source-", dir=work) as temporary:
        runtime = extract_source(Path(temporary))
        base, candidate, history = list(PINS)[1:]
        command = [
            sys.executable, str(BUILDER), "--python", sys.executable,
            "--runtime-root", str(runtime), "--a07-archive", str(ARCHIVE),
            "--base-zip", str(base), "--candidate-zip", str(candidate),
            "--history", str(history), "--current-q1", str(Path(args.current_q1).resolve()),
            "--output", str(output),
        ]
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(command, env=env, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
