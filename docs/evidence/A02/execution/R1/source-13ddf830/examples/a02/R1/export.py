"""Export the required R1 source/tests/fixtures as exact Git bytes, never a checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from identity import git_identity

PATHS = ["src/annotation", "examples/a02", "examples/contracts", "tests/fixtures/a02", "tests/fixtures/contracts",
         "tests/test_a02.py", "tests/test_a02_r1.py", "tests/test_contracts.py", "tests/test_contracts_platform_refs.py", "pyproject.toml"]


def export(repo, commit, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    assert git_identity(repo)["checkout_commit"] is not None, "explicit repository must be its Git top-level"
    resolved = subprocess.check_output(["git", "rev-parse", "--verify", commit + "^{commit}"], cwd=repo, text=True).strip()
    files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", resolved] + PATHS, cwd=repo, text=True).splitlines()
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for relative in files:
        blob = subprocess.check_output(["git", "show", resolved + ":" + relative], cwd=repo)
        destination = output / relative
        destination.resolve().relative_to(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(blob)
        hashes[relative] = hashlib.sha256(blob).hexdigest()
    with (output / "source-export.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump({"declared_commit": resolved, "identity_repo": str(repo), "method": "raw Git blob export; no .git",
                   "files_sha256": hashes}, handle, indent=2)
        handle.write("\n")
    assert git_identity(output)["checkout_commit"] is None
    print(json.dumps({"declared_commit": resolved, "exported_files": len(files), "checkout_commit": None}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.repo, args.commit, args.output)
