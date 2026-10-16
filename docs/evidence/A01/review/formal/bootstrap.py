"""Export and verify the exact A01 delivery; offline, no source-worktree writes."""
import hashlib
import io
import json
import subprocess
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
FORMAL = Path(__file__).resolve().parent
COMMIT = "a8d5e96d128e10d341de935d4856682e50df79d9"
BASE = "39341c98d73c354d639f3beeb55429f55d0e9be5"
STAGE = ROOT / ".local/stages/A01-review" / COMMIT


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    snapshot = STAGE / "snapshot-verified"
    snapshot.mkdir(parents=True, exist_ok=False)
    # A first archive used this host's autocrlf conversion. Keep that failed
    # attempt in place and export a fresh directory with conversion disabled.
    archive = (STAGE / "delivery-raw.zip").read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_handle:
        for info in zip_handle.infolist():
            path = (snapshot / info.filename).resolve()
            path.relative_to(snapshot.resolve())
        zip_handle.extractall(snapshot)
    changed = git("diff", "--name-only", "-z", BASE, COMMIT).decode("utf-8").split("\0")
    changed = [p for p in changed if p]
    input_data = json.loads((ROOT / "docs/evidence/A01/review/input-inventory-before.json").read_text(encoding="utf-8"))
    paths = sorted(set(changed + [x["path"] for x in input_data["records"]] + [
        "AGENTS.md", "docs/architecture.md", "docs/contracts-v1.md", "docs/coordination.md",
        "docs/tasks/A01-independent-review.md", "docs/tasks/A01-source-geometry.md",
        "src/annotation/contracts/__init__.py", "src/annotation/contracts/models.py",
        "src/annotation/contracts/validation.py", "src/annotation/contracts/integrity.py",
    ]))
    verified = []
    restored = []
    for tree_entry in git("ls-tree", "-r", "-z", COMMIT).split(b"\0"):
        if not tree_entry:
            continue
        metadata, raw_path = tree_entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        relative = raw_path.decode("utf-8")
        if kind != b"blob" or mode == b"120000":
            raise RuntimeError("unsupported export entry: " + relative)
        exported = (snapshot / relative).read_bytes()
        computed_oid = hashlib.sha1(b"blob " + str(len(exported)).encode() + b"\0" + exported).hexdigest()
        if computed_oid != oid.decode():
            exported = git("cat-file", "blob", oid.decode())
            (snapshot / relative).write_bytes(exported)
            restored.append(relative)
            computed_oid = hashlib.sha1(b"blob " + str(len(exported)).encode() + b"\0" + exported).hexdigest()
            if computed_oid != oid.decode():
                raise RuntimeError("Git blob mismatch: " + relative)
        verified.append({"path": relative, "bytes": len(exported), "sha256": sha(exported),
                         "git_blob_oid": oid.decode(), "review_focus": relative in paths})
    prep_manifest = json.loads((ROOT / "docs/evidence/A01/review/sha256-manifest.json").read_text(encoding="utf-8"))
    preparation = []
    for entry in prep_manifest["records"]:
        current = sha((ROOT / entry["path"]).read_bytes())
        preparation.append({"path": entry["path"], "expected": entry["sha256"], "actual": current,
                            "matches": current == entry["sha256"]})
    report = snapshot / "docs/tasks/A01-execution-report.md"
    expected_report_sha = "df8b5c0123cdb9f75146c345ae2301a83dfad0efdf93fd6db5f0672f0a260ae2"
    if sha(report.read_bytes()) != expected_report_sha or not all(x["matches"] for x in preparation):
        raise RuntimeError("report or preparation integrity mismatch")
    prefixes = ("src/annotation/source/static/", "src/annotation/geometry/", "tests/test_a01_",
                "tests/fixtures/a01/", "examples/a01/", "docs/evidence/A01/execution/")
    allowed = {"docs/a01-source-geometry.md", "docs/tasks/A01-execution-report.md"}
    result = {"observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
              "target_commit": COMMIT, "base_commit": BASE, "workflow_commit": BASE,
              "snapshot": str(snapshot), "archive_sha256": sha(archive), "archive_bytes": len(archive),
              "export_attribute_corrections": restored,
              "preparation_errors": [{"stage":"initial archive", "exit_code":1,
                                      "cause":"host autocrlf changed examples/a01/.gitattributes LF into CRLF"},
                                     {"stage":"autocrlf=false archive", "exit_code":1,
                                      "cause":"text=auto attributes changed data/derived/analysis/route_c_dump.txt bytes"}],
              "export_method":"archive scaffold; restore every mismatching file from exact Git blob; verify every tree blob OID",
              "changed_files": changed, "out_of_scope": [p for p in changed if p not in allowed and not p.startswith(prefixes)],
              "exported_files_verified": verified, "execution_report_sha256": sha(report.read_bytes()),
              "preparation_preserved": preparation,
              "accepted_C01_ancestor": subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
                                                       "4e42668ab28eda37a37285285d2f6c595d3bba12", COMMIT]).returncode == 0}
    with (FORMAL / "bootstrap.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2); handle.write("\n")
    print(json.dumps({"snapshot": str(snapshot), "changed_files": len(changed), "verified_files":len(verified),
                      "out_of_scope":result["out_of_scope"],"report_sha256":result["execution_report_sha256"]}))


if __name__ == "__main__":
    main()
