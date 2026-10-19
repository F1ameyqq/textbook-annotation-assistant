"""Read-only archive binding inspection; does not import or execute A/B products."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[4]
B_COMMIT = "a76e5a925fec76f20818dfdefa4145aa132ec8a8"
A_COMMIT = "e37606d74d7e538052c563d02df11c6c961b742f"
EVAL_PATH = "evaluation/book-46007447-a07-q1-b-adoption.json"
os.environ["GIT_NO_LAZY_FETCH"] = "1"


def git(*args):
    return subprocess.check_output(
        ["git", "-c", "core.longpaths=true", *args], cwd=ROOT,
        stderr=subprocess.DEVNULL,
    )


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    raw = git("show", B_COMMIT + ":" + EVAL_PATH)
    evaluation = json.loads(raw)
    package = evaluation["evidence_package"]
    zipped = git("show", B_COMMIT + ":" + package["path"])
    assert sha(zipped) == package["sha256"]
    assert len(zipped) == package["bytes"]
    archive = zipfile.ZipFile(io.BytesIO(zipped))
    names = archive.namelist()
    assert len(names) == len(set(names))
    for name in names:
        path = PurePosixPath(name)
        assert not path.is_absolute() and ".." not in path.parts
        assert "\\" not in name and ":" not in name
    manifest_raw = archive.read("manifest.json")
    assert sha(manifest_raw) == package["manifest_sha256"]
    manifest = json.loads(manifest_raw)
    rows = manifest["files"]
    assert len(rows) == package["members_excluding_manifest"]
    assert len({row["path"] for row in rows}) == len(rows)
    assert {row["path"] for row in rows} | {"manifest.json"} == set(names)
    for row in rows:
        content = archive.read(row["path"])
        assert len(content) == row["bytes"] and sha(content) == row["sha256"]
    tree = {}
    for line in git("ls-tree", "-r", "-z", A_COMMIT).split(b"\0"):
        if not line:
            continue
        meta, path = line.split(b"\t", 1)
        tree[path.decode()] = meta.split()[2].decode()
    fixed_count = 0
    for name in names:
        if not name.startswith("a07-fixed/"):
            continue
        content = archive.read(name)
        oid = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        assert tree[name[len("a07-fixed/"):]] == oid
        fixed_count += 1
    for record in evaluation["records"].values():
        assert sha(archive.read(record["path_in_package"])) == record["sha256"]
    assert evaluation["a_commit"] == A_COMMIT
    assert all(evaluation["accepted_items"].values())
    assert evaluation["open_field_differences"] == []
    assert evaluation["scope"]["roles"] == ["Q", "W", "W", "W", "W", "A"]
    for run in evaluation["archive_runs"]:
        base = "a07-fixed/docs/evidence/A07/F01/" + run["run"] + "/"
        matches = [name for name in names if name.startswith(base)
                   and sha(archive.read(name)) == run["readback_sha256"]]
        assert len(matches) >= 1
        # Receipt references are checked against archived C01 objects, never regenerated.
        receipts = []
        for name in names:
            if name.startswith(base) and name.endswith(".json"):
                obj = json.loads(archive.read(name))
                if isinstance(obj, dict) and obj.get("artifact_id") == run["receipt"]["artifact_id"]:
                    receipts.append(obj)
        assert receipts
        assert any(all(obj.get(k) == v for k, v in run["receipt"].items()) for obj in receipts)
    result = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "b_commit": B_COMMIT, "a_commit": A_COMMIT,
        "evaluation_path": EVAL_PATH, "evaluation_sha256": sha(raw),
        "zip_path": package["path"], "zip_sha256": sha(zipped),
        "zip_bytes": len(zipped), "manifest_sha256": sha(manifest_raw),
        "verified_manifest_members": len(rows),
        "a_fixed_members_matching_published_git_blobs": fixed_count,
        "bound_b_record_files": len(evaluation["records"]),
        "archived_receipt_and_readback_bindings": len(evaluation["archive_runs"]),
        "result": "PASS_STATIC_RECEPTION_AND_FIXED_Q1_ADOPTION_BINDING",
        "accepted_items": evaluation["accepted_items"],
        "scope": "Fixed Q1 offline technical terms only; not B internal acceptance or a new business run",
        "b_checker_scripts_executed": 0, "new_business_runs": 0,
        "product_tests_run": 0, "platform_actions": 0,
    }
    out = Path(__file__).with_name("adoption-archive-check.json")
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
