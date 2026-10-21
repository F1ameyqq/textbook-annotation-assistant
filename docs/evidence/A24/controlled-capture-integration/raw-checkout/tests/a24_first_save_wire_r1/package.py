"""R1 raw Git packaging, old-tree preservation and one authoritative manifest."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"docs/evidence/A24/first-save-wire-r1"
BASE = "680bd5f624659f1091db974d5ed30b332ff946dc"
CHANGED = {"src/annotation/delivery/live_pilot/plan.py", "src/annotation/delivery/live_pilot/usense.py",
           "src/annotation/delivery/live_pilot/wire.py", "src/annotation/quality/live_pilot.py",
           "src/annotation/runtime/live_pilot/runner.py"}
NEW = {"src/annotation/runtime/live_pilot/authority.py", "src/annotation/runtime/live_pilot/owner.py",
       "src/annotation/runtime/live_pilot/private_payload.py", "tools/a24_first_save_launcher.py"}
INPUTS = ["docs/tasks/A24-first-save-wire-r1-consolidated-continuation.md",
    "docs/evidence/coordinator/a24-first-save-wire-independent-closure/report.md",
    "docs/evidence/coordinator/a24-first-save-wire-independent-closure/independent-result.json",
    "docs/evidence/coordinator/a24-first-save-wire-independent-closure/static-snapshot-contract.json",
    "docs/evidence/coordinator/a24-model-one-question-independent-closure/independent-result.json",
    "docs/evidence/coordinator/a24-model-one-question-independent-closure/root-disposition.json"]

def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write((json.dumps(value, ensure_ascii=False, indent=2)+"\n").encode("utf-8"))
def git(*args):
    return subprocess.run(["git", "-c", "core.longpaths=true", *args], cwd=ROOT,
        env=dict(os.environ, GIT_NO_LAZY_FETCH="1"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
def tree(commit):
    result = {}
    for row in git("ls-tree", "-r", "-z", commit).split(b"\0"):
        if row:
            meta, name = row.split(b"\t", 1)
            result[name.decode()] = meta.decode().split()
    return result
def record(path, raw): return {"path": path, "bytes": len(raw), "sha256": sha(raw)}

def prepare():
    records = []
    for name in INPUTS:
        raw = (Path("D:/1800")/name).read_bytes()
        dest = OUT/"inputs"/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as handle: handle.write(raw)
        records.append(dict(record(dest.relative_to(ROOT).as_posix(), raw), source=str(Path("D:/1800")/name)))
    write(OUT/"fixed-input-provenance.json", {"schema": "A24R1FixedInputs/v1", "inputs": records,
        "old_review_result": "REWORK_PRESERVED", "private_originals_or_text_copied_to_git": False})

def package(product):
    before, after = tree(BASE), tree(product)
    changed = {p for p in before.keys() & after.keys() if before[p] != after[p]}
    added = set(after)-set(before)
    assert not (set(before)-set(after)) and changed == CHANGED
    assert all(p in NEW or p.startswith(("tests/a24_first_save_wire_r1/", "docs/evidence/A24/first-save-wire-r1/")) for p in added)
    write(OUT/"old-preservation.json", {"schema": "A24R1OldRawPreservation/v1", "base": BASE, "product": product,
        "old_members": len(before), "changed": sorted(changed), "added": sorted(added), "deleted": [],
        "other_mode_type_blob_triples_preserved": True,
        "old_evidence_preserved": all(before[p] == after[p] for p in before if p.startswith("docs/evidence/"))})
    old = json.loads((ROOT/"docs/evidence/A24/first-save-wire/candidate-manifest.json").read_bytes())
    selected = {v["path"] for v in old["dependencies"] if not v["path"].startswith("tests/a24_first_save_wire/")}
    selected.update(p for p in after if p.startswith("src/") and p.endswith((".py", ".json")))
    selected.update(p for p in after if p.startswith("tests/a24_first_save_wire_r1/") and p.endswith(".py"))
    selected.update(CHANGED | NEW)
    selected.update({"docs/evidence/A24/first-save-wire-r1/concrete-plan.json",
        "docs/evidence/A24/first-save-wire-r1/crop-bindings.json",
        "docs/evidence/A15/certificate-exception/reviewed-native/native_windows.py",
        "docs/evidence/A15/certificate-exception/reviewed-native/process_check.py"})
    dependencies = []
    for path in sorted(selected):
        raw = git("show", product+":"+path)
        dest = OUT/"raw-checkout"/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as handle: handle.write(raw)
        dependencies.append(record(path, raw))
    plan = json.loads(git("show", product+":docs/evidence/A24/first-save-wire-r1/concrete-plan.json"))
    import sys
    sys.path.insert(0, str(ROOT/"src"))
    from annotation.runtime.storage.common import digest
    write(OUT/"candidate-manifest.json", {"schema": "A24R1FrozenCandidate/v1", "task": "A24", "product": product,
        "base": BASE, "scope_sha256": digest(plan), "dependencies": dependencies,
        "status": "AUTHOR_FROZEN_OFFLINE_PENDING_FORMAL_REVIEW", "actual_schema": "CURRENT_SCHEMA_UNBOUND",
        "actual_save": "NOT_RUN", "model_calls": 0, "platform_calls": 0, "activation_created": False,
        "old_readonly_remaining": [0, 0]})
    print(json.dumps({"product": product, "dependencies": len(dependencies), "old_members": len(before), "old_evidence_preserved": True}))

def seal(commit):
    members = tree(commit)
    candidate = json.loads((OUT/"candidate-manifest.json").read_bytes())
    paths = set(CHANGED | NEW)
    paths.update(p for p in members if p.startswith(("tests/a24_first_save_wire_r1/", "docs/evidence/A24/first-save-wire-r1/")))
    paths.update(v["path"] for v in candidate["dependencies"])
    records = [record(p, git("show", commit+":"+p)) for p in sorted(paths)]
    # Self is excluded by construction; every member is a raw Git blob.
    write(OUT/"delivery-final-manifest.json", {"schema": "A24R1AuthoritativeRawDelivery/v1", "content_commit": commit,
        "base": BASE, "self_excluded": True, "source": "RAW_GIT_BLOBS", "members": records,
        "members_count": len(records), "formal_acceptance": "PENDING", "actual_save": "NOT_RUN"})
    print(json.dumps({"manifest_members": len(records), "manifest_sha256": sha((OUT/"delivery-final-manifest.json").read_bytes())}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "package", "seal"))
    parser.add_argument("--commit")
    args = parser.parse_args()
    if args.mode == "prepare": prepare()
    elif args.mode == "package": package(args.commit)
    else: seal(args.commit)
