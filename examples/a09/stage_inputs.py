"""Own raw input copies only; does not invoke A08 or any B program."""
import argparse
from pathlib import Path

from audit import git

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = "0a9c634d160ac7b39f68a1fb3555f409dd408f49"


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("existing input differs: " + str(path))
    else:
        with path.open("xb") as handle:
            handle.write(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    for source, name in (("docs/tasks/A09-inputs.json", "input-registry.json"),
        ("docs/reviews/q4-first-lesson/proposal.json", "proposal.json"),
        ("docs/approvals/A09-Q4-offline-business-approval.json", "approval.json"),
        ("docs/approvals/A07-Q1-offline-business-approval.json", "q1-approval.json")):
        put(args.destination / name, git(ROOT, "show", WORKFLOW + ":" + source))
    put(args.destination / "stage.zip", args.stage.read_bytes())


if __name__ == "__main__":
    main()
