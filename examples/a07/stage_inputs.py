"""Read-only copies of fixed local originals and raw Git approval; never executes B files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

SOURCE = Path("D:/1800/.local/stages/coordinator")
PATHS = {
    "base.zip": SOURCE / "b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip",
    "candidate.zip": SOURCE / "b-q1-ef6ba4dd/handoffs/b/46007447/B-46007447-Q1-source-candidate-v1-HOLD-2026-10-18.zip",
    "history.json": SOURCE / "b-q1-ef6ba4dd/handoffs/b/46007447/single-question-q1/historical-evidence-revision1.json",
}
WORKFLOW = "b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    dest = Path(args.destination)
    dest.mkdir(parents=True, exist_ok=False)
    files = {name: path.read_bytes() for name, path in PATHS.items()}
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    files["approval.json"] = subprocess.check_output(["git", "-c", "core.longpaths=true", "show",
        WORKFLOW + ":docs/approvals/A07-Q1-offline-business-approval.json"], env=env)
    manifest = {}
    for name, raw in files.items():
        (dest / name).write_bytes(raw)
        manifest[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    (dest / "copy-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
