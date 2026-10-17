"""Read-only raw Git and recorded-process preflight; never imports the candidate."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(r"D:\1800")
WORK = Path(r"C:\Users\ASUS\.codex\worktrees\a03-runtime-recovery\1800")
BASE = "58d8a64734271d15654bb00b03d760f0f3eccd10"
TARGET = "d9ed692db9ab8e9277f8ffd09e040451e8b8f65f"
EVIDENCE = "docs/evidence/A03/execution/P2-R8-R3-post-hold/"
MANIFEST = EVIDENCE + "manifest.json"
REPORT = "docs/tasks/A03-P2-R8-R3-post-hold-report.md"

def git(*args):
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args], cwd=WORK)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def blobs(paths):
    raw = subprocess.run(["git", "-c", "core.longpaths=true", "cat-file", "--batch"],
        cwd=WORK, input="".join(TARGET + ":" + p + "\n" for p in paths).encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    found, offset = {}, 0
    for path in paths:
        end = raw.index(b"\n", offset)
        header = raw[offset:end].split()
        assert header[1] == b"blob", (path, header)
        size = int(header[2]); offset = end + 1
        data = raw[offset:offset + size]; offset += size + 1
        assert hashlib.sha1(b"blob " + str(size).encode() + b"\0" + data).hexdigest() == header[0].decode()
        found[path] = data
    assert offset == len(raw)
    return found

def tree(ref):
    result = {}
    for line in git("ls-tree", "-rz", "--full-tree", ref).split(b"\0"):
        if line:
            identity, path = line.split(b"\t", 1)
            result[path.decode("utf-8")] = identity.decode()
    return result

assert git("rev-parse", "HEAD").decode().strip() == TARGET
assert not git("status", "--porcelain").strip()
manifest_raw = blobs([MANIFEST])[MANIFEST]
manifest = json.loads(manifest_raw)
entries = manifest["entries"]
paths = [e["path"] for e in entries]
assert len(paths) == len(set(paths)) and MANIFEST not in paths
raw = blobs(paths + [MANIFEST])
for e in entries:
    value = raw[e["path"]]
    assert len(value) == e["bytes"] and digest(value) == e["sha256"], e["path"]
    assert digest((WORK / e["path"]).read_bytes()) == e["sha256"], e["path"]
before, after = tree(BASE), tree(TARGET)
changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
assert changed == set(paths) | {MANIFEST}, changed ^ (set(paths) | {MANIFEST})
shared = {"src/annotation/runtime/storage/native.py",
    "src/annotation/contracts/a03_native/data/profile.json",
    "src/annotation/contracts/a03_native/data/adoption.json"}
assert {p for p in before if before[p] != after.get(p)} == shared
for p in changed - shared:
    assert p.startswith((EVIDENCE, "examples/a03/P2-R8-R3-post-hold/",
        "tests/fixtures/a03/P2-R8-R3-post-hold/", "tests/test_a03_r8_r3_")) or p == REPORT, p
release = json.loads(raw[EVIDENCE + "process-release.json"])
processes = []
for record in release["records"]:
    parent = EVIDENCE + record["path"].rsplit("/", 1)[0] + "/"
    started = json.loads(raw[parent + "started.json"])
    completed = json.loads(raw[parent + "completed.json"])
    prereg = json.loads(raw[parent + "preregistered.json"])
    assert started["pid"] == completed["pid"] == record["pid"]
    assert completed["exit_code"] == record["exit_code"]
    assert "timed_out" in completed or "timeout" in completed
    assert not completed.get("timed_out", completed.get("timeout")) and not completed["alive"]
    assert not record["timeout"] and not record["alive"]
    for stream in ("stdout", "stderr"):
        data = raw[parent + stream + ".txt"]
        if stream + "_sha256" in completed:
            assert digest(data) == completed[stream + "_sha256"]
    processes.append({"path": parent, "pid": record["pid"], "exit_code": record["exit_code"],
        "preregistration_present": bool(prereg), "recorded_exited": True})
assert len(processes) == 34 and release["all_recorded_processes_waited_and_ended"]
result = {"status": "READY_FOR_BOUNDED_INDEPENDENT_REVIEW", "base": BASE, "target": TARGET,
    "manifest_entries": len(entries), "raw_and_disk_hash_mismatches": 0,
    "manifest_sha256": digest(manifest_raw), "report": REPORT, "report_sha256": digest(raw[REPORT]),
    "changed_paths": len(changed), "shared_changes": sorted(shared),
    "old_tree_entries": len(before), "old_entries_preserved": len(before) - len(shared),
    "process_release_sha256": digest(raw[EVIDENCE + "process-release.json"]), "recorded_processes": processes,
    "bounded_outcome_sha256": digest(raw[EVIDENCE + "bounded-outcome.json"]),
    "n7_failure_stderr_sha256": digest(raw[EVIDENCE + "runs/N7/stderr.txt"]),
    "coverage_map_sha256": digest(raw[EVIDENCE + "p2-coverage-map.json"]),
    "product_paths_rerun_after_N7_failure": release["product_paths_rerun_after_N7_failure"],
    "report_utf8_replacement_characters": raw[REPORT].decode("utf-8").count("\ufffd"),
    "scope": "Delivery bytes, allowed diff and recorded release only; no candidate imports, database opens or functional reruns.",
    "functional_acceptance": False, "I01_released": False, "platform_actions": 0, "paid_model_calls": 0}
out = ROOT / "docs/evidence/coordinator/heartbeat-20261018-0242/A03-R8-R3-delivery-preflight.json"
out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
print(json.dumps({k: result[k] for k in ("status", "target", "manifest_entries", "changed_paths", "old_entries_preserved", "report_sha256")}, ensure_ascii=True))
