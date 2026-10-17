"""Read-only D01 SHA closure check; no installation, Git, or source injection."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.absolute().resolve()
    manifest = root / "docs/evidence/D01/execution/SHA256SUMS.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    failures = []
    for entry in data["files"]:
        path = root / entry["path"]
        if not path.is_file():
            failures.append(entry["path"] + ": missing")
            continue
        raw = path.read_bytes()
        if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            failures.append(entry["path"] + ": byte mismatch")
    expected = {entry["path"] for entry in data["files"]}
    actual = {"pyproject.toml", "docs/tasks/D01-execution-report.md"}
    for prefix in ("examples/d01", "docs/evidence/D01/execution"):
        actual.update(p.relative_to(root).as_posix() for p in (root / prefix).rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts)
    actual -= set(data["excluded_self"])
    if expected != actual:
        failures.append("closure mismatch: " + repr(sorted(expected ^ actual)))
    print(json.dumps({"files": len(data["files"]), "failures": failures,
                      "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}, indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
