"""Export exact Git bytes for the authorized P1 static review, without checkout."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("D:/1800")
COMMIT = "2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9"
DESIGN = "6ac0256f05169570605fcb921a773ff2ae0f4aef"
WORKFLOW = "a354f95f1d0b40a8f0847b57fa3978cac999e7a2"
STAGE = ROOT / ".local/stages/A03-review-P1" / COMMIT
OUT = ROOT / "docs/evidence/A03/review/P1"
EXPECTED = {
    "docs/tasks/A03-P1-execution-report.md": "56f873291d0a60b376327b62eb12d032dc0c671cc55d90ce5582fe74d1724627",
    "docs/evidence/A03/execution/P1/sha256-manifest.json": "4988c1ce490ef62d0c1a019ac8f746166eb4dc0b595c3b29036bde38a6315950",
    "docs/a03-recovery-contract-v1-proposal.md": "fd1ddbf1d4252df50d7273ccd939e529129755847b3973a1b22938eb9d03e07f",
}

def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, timeout=60)
    if p.returncode:
        raise RuntimeError((args, p.returncode, p.stderr.decode("utf-8", "replace")))
    return p.stdout

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as h:
        json.dump(value, h, ensure_ascii=False, indent=2)
        h.write("\n")

def main():
    assert git("rev-parse", COMMIT).decode().strip() == COMMIT
    git("merge-base", "--is-ancestor", DESIGN, COMMIT)
    git("merge-base", "--is-ancestor", WORKFLOW, COMMIT)
    assert git("rev-parse", "--show-object-format").strip() == b"sha1"
    tree = {}
    for row in git("ls-tree", "-rz", COMMIT).split(b"\0"):
        if not row:
            continue
        header, name = row.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        assert kind == "blob" and mode in ("100644", "100755"), (mode, kind, name)
        tree[name.decode("utf-8")] = oid
    # git archive can transform an exported text file; only raw blobs are authoritative.
    # Resume only this review's verified partial export without replacing any file.
    STAGE.mkdir(parents=True, exist_ok=True)
    assert {p.relative_to(STAGE).as_posix() for p in STAGE.rglob("*") if p.is_file()} <= set(tree)
    batch = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT,
        input=("\n".join(tree.values()) + "\n").encode(), capture_output=True, timeout=60)
    assert batch.returncode == 0, batch.stderr.decode("utf-8", "replace")
    position = 0
    files = []
    resumed = 0
    for name, expected_oid in tree.items():
        end = batch.stdout.index(b"\n", position)
        oid, kind, size = batch.stdout[position:end].decode().split()
        assert oid == expected_oid and kind == "blob", name
        position = end + 1
        raw = batch.stdout[position:position + int(size)]
        position += int(size)
        assert batch.stdout[position:position + 1] == b"\n", name
        position += 1
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == oid, name
        destination = (STAGE / name).resolve()
        assert destination.is_relative_to(STAGE.resolve()), name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == raw, name
            resumed += 1
        else:
            with destination.open("xb") as h:
                h.write(raw)
        files.append({"path": name, "bytes": len(raw), "sha256": sha(raw), "git_blob": oid})
    assert position == len(batch.stdout)
    assert {x["path"] for x in files} == set(tree)
    for path, digest in EXPECTED.items():
        assert sha((STAGE / path).read_bytes()) == digest, path
    handoff = ROOT / "docs/tasks/A03-P1-review-handoff.md"
    raw = handoff.read_bytes()
    assert sha(raw) == "cfe84c0b12ded7e957c4b30e0cdcb12108d30ab7c6544f16b25d13da05171ed6"
    (OUT / "inputs").mkdir(parents=True)
    with (OUT / "inputs/A03-P1-review-handoff.md").open("xb") as h:
        h.write(raw)
    changes = git("diff", "--name-status", WORKFLOW, COMMIT).decode().splitlines()
    assert len(changes) == 149 and all(line.startswith("A\t") for line in changes)
    allowed = ("examples/a03/P1/", "docs/evidence/A03/execution/P1/")
    assert all(line[2:].startswith(allowed) or line[2:] in (
        "docs/a03-recovery-contract-v1-proposal.md", "docs/tasks/A03-P1-execution-report.md") for line in changes)
    old_changes = git("diff", "--diff-filter=DMRTUXB", "--name-only", WORKFLOW, COMMIT).decode().splitlines()
    assert not old_changes, old_changes
    manifest = json.loads((STAGE / "docs/evidence/A03/execution/P1/sha256-manifest.json").read_bytes())
    write(OUT / "export-manifest.json", {"commit": COMMIT, "design_commit": DESIGN,
        "workflow_commit": WORKFLOW, "stage": str(STAGE), "all_raw_git_blobs_verified": True,
        "files": files})
    write(OUT / "freeze-checks.json", {"commit": COMMIT, "file_count": len(files),
        "export_method": "git cat-file --batch", "resumed_verified_files": resumed,
        "new_allowed_paths": len(changes), "old_modified_or_deleted_paths": old_changes,
        "expected_sha256_verified": EXPECTED, "handoff_sha256": sha(raw),
        "execution_manifest_structure_keys": sorted(manifest), "raw_git_bytes_not_checkout": True,
        "business_code_executed": False})
    print(json.dumps({"result": "FROZEN_GIT_EXPORT_VERIFIED", "files": len(files),
                      "new_files": len(changes), "stage": str(STAGE)}))

if __name__ == "__main__":
    main()
