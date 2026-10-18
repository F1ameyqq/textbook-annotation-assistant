"""Read fixed Git objects for A07-F01 delivery integrity; never run the product."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


WORKFLOW = "ca1fb902c2228579cd2d0c84d81fc72cd0643796"
REPO = Path(__file__).resolve().parents[4]
PRODUCT_EDITS = {
    "src/annotation/source/b_q1/reader.py",
    "src/annotation/quality/q1_offline.py",
}
PRODUCT_ADDITIONS = {
    "tests/test_a07_role_delta.py",
    "examples/a07/role_delta_check.py",
}
PRE_FREEZE_EVIDENCE = {
    'docs/evidence/A07/F01/execution/authorizations/A07-F01-role-correction-approval.json',
    'docs/evidence/A07/F01/execution/authorizations/A07-Q1-offline-business-approval.json',
    'docs/evidence/A07/F01/execution/authorizations/binding.json',
    'docs/evidence/A07/F01/execution/pre-freeze/role-gate-calls.json',
    'docs/evidence/A07/F01/execution/pre-freeze/role-gate-output.txt',
    'docs/evidence/A07/F01/execution/pre-freeze/role-gate-process.json',
    'docs/evidence/A07/F01/execution/pre-freeze/scope-check.json',
}
ENV = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1")


class IntegrityError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise IntegrityError(message)


def git(*args):
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-c", "core.longpaths=true", *args],
        cwd=REPO, env=ENV, stderr=subprocess.PIPE, timeout=60,
    )


def resolve(value):
    require(bool(re.fullmatch(r"[0-9a-fA-F]{40}", value)), "full 40-character commit ID required")
    actual = git("rev-parse", "--verify", value + "^{commit}").decode("ascii").strip()
    require(actual == value.lower(), "commit must resolve to the exact supplied object")
    return actual


def tree(commit):
    result = {}
    for entry in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if entry:
            header, path = entry.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split()
            result[path.decode("utf-8")] = {"mode": mode, "type": kind, "oid": oid}
    return result


def diff(old, new):
    return [
        {"path": path, "status": "A" if path not in old else "D" if path not in new else "M",
         "before": old.get(path), "after": new.get(path)}
        for path in sorted(set(old) | set(new)) if old.get(path) != new.get(path)
    ]


def file_record(path, entries, cache):
    require(path in entries, "manifest or evidence path missing from delivery: " + path)
    entry = entries[path]
    require(entry["type"] == "blob" and entry["mode"] in ("100644", "100755"),
            "expected regular Git blob: " + path)
    oid = entry["oid"]
    if oid not in cache:
        cache[oid] = git("cat-file", "blob", oid)
    raw = cache[oid]
    return {"path": path, "blob_oid": oid, "mode": entry["mode"], "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}, raw


def members(document):
    if isinstance(document, list):
        rows = document
    elif isinstance(document, dict):
        rows = document.get("members", document.get("files"))
    else:
        rows = None
    require(isinstance(rows, list) and bool(rows), "manifest needs a nonempty members/files array")
    require(all(isinstance(row, dict) for row in rows), "manifest members must be objects")
    return rows


def manifest_path(explicit, added, prefix, entries, cache):
    if explicit:
        require(explicit in added and explicit.startswith(prefix),
                "explicit manifest must be newly added under this role's F01 evidence directory")
        return explicit
    found = []
    for path in sorted(added):
        if path.startswith(prefix) and path.endswith(".json") and "manifest" in PurePosixPath(path).name.lower():
            _record, raw = file_record(path, entries, cache)
            try:
                members(json.loads(raw))
            except (ValueError, TypeError):
                continue
            found.append(path)
    require(len(found) == 1, "expected one raw-member manifest; use --manifest if ambiguous: " + repr(found))
    return found[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--delivery", required=True)
    parser.add_argument("--role", required=True, choices=("execution", "review"))
    parser.add_argument("--output", required=True, help="new JSON report path; never overwritten")
    parser.add_argument("--manifest", help="optional repository-relative manifest path at delivery")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    require(not output.exists(), "output already exists; refusing to overwrite")
    report = {
        "scope": "A07-F01 fixed-commit raw Git delivery integrity only",
        "workflow": WORKFLOW, "candidate": args.candidate, "delivery": args.delivery, "role": args.role,
        "result": "INTEGRITY_CHECK_FAILED", "product_verdict": "NOT_EVALUATED",
        "business_runs": 0, "product_imports": 0, "tests_run": 0, "network_calls": 0,
        "basis": "Git tree mode/type/blob identity preserves old raw bytes; cat-file reads declared new members",
        "errors": [],
    }
    try:
        workflow = resolve(WORKFLOW)
        candidate, delivery = resolve(args.candidate), resolve(args.delivery)
        report.update(candidate=candidate, delivery=delivery)
        old, product, final = tree(workflow), tree(candidate), tree(delivery)
        candidate_diff, delivery_diff = diff(old, product), diff(product, final)
        report["candidate_diff"], report["delivery_diff"] = candidate_diff, delivery_diff
        candidate_violations = [row for row in candidate_diff if not (
            row["status"] == "M" and row["path"] in PRODUCT_EDITS and
            row["after"]["mode"] == row["before"]["mode"] and
            row["after"]["type"] == row["before"]["type"] == "blob"
            or row["status"] == "A" and row["path"] in (PRODUCT_ADDITIONS | PRE_FREEZE_EVIDENCE) and
            row["after"]["type"] == "blob" and row["after"]["mode"] in ("100644", "100755")
        )]
        prefix = "docs/evidence/A07/F01/" + args.role + "/"
        report_path = "docs/tasks/A07-F01-" + args.role + "-report.md"
        delivery_violations = [row for row in delivery_diff if not (
            row["status"] == "A" and (row["path"] == report_path or row["path"].startswith(prefix)) and
            row["after"]["type"] == "blob" and row["after"]["mode"] in ("100644", "100755")
        )]
        preserved_old = [path for path in old if path not in PRODUCT_EDITS and product.get(path) == old[path]]
        broken_old = [path for path in old if path not in PRODUCT_EDITS and product.get(path) != old[path]]
        preserved_candidate = [path for path in product if final.get(path) == product[path]]
        report.update(
            candidate_scope_violations=candidate_violations, delivery_scope_violations=delivery_violations,
            old_paths_required_unchanged=len(set(old) - PRODUCT_EDITS),
            old_paths_preserved=len(preserved_old), old_path_violations=sorted(broken_old),
            candidate_paths_required_unchanged=len(product), candidate_paths_preserved=len(preserved_candidate),
            changed_product_paths=sorted(row["path"] for row in candidate_diff if row["status"] == "M"),
            unchanged_allowed_product_paths=sorted(PRODUCT_EDITS - {row["path"] for row in candidate_diff}),
        )
        require(not candidate_violations and not broken_old, "candidate exceeds the F01 product whitelist")
        require(not delivery_violations and len(preserved_candidate) == len(product),
                "delivery must only add this role's F01 report/evidence and preserve every candidate path")
        added = {row["path"] for row in delivery_diff}
        require(report_path in added, "missing newly added role report: " + report_path)
        cache = {}
        report["report_file"], _raw = file_record(report_path, final, cache)
        selected_manifest = manifest_path(args.manifest, added, prefix, final, cache)
        report["manifest_file"], raw = file_record(selected_manifest, final, cache)
        document = json.loads(raw)
        if isinstance(document, dict) and "self_excluded_path" in document:
            require(document["self_excluded_path"] == selected_manifest, "manifest self-exclusion path differs")
        checked, seen = [], set()
        for member in members(document):
            path = member.get("path")
            require(isinstance(path, str) and path and "\\" not in path and
                    not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts,
                    "manifest member path must be repository-relative POSIX text")
            require(path not in seen, "duplicate manifest member: " + path)
            seen.add(path)
            record, _raw = file_record(path, final, cache)
            expected_size = member.get("bytes", member.get("size"))
            require(type(expected_size) is int and expected_size == record["bytes"], "member bytes differ: " + path)
            require(member.get("sha256") == record["sha256"], "member SHA256 differs: " + path)
            for key in ("blob_oid", "oid"):
                if key in member:
                    require(member[key] == record["blob_oid"], "member " + key + " differs: " + path)
            checked.append(record)
        report["manifest_members_checked"] = checked
        report["manifest_member_count"] = len(checked)
        report["manifest_member_bytes"] = sum(row["bytes"] for row in checked)
        report["delivery_paths_not_in_manifest"] = sorted(added - {selected_manifest} - seen)
        report["manifest_additional_paths"] = sorted(seen - added)
        report["candidate_diff_paths_not_in_manifest"] = sorted({row["path"] for row in candidate_diff} - seen)
        require(not report["delivery_paths_not_in_manifest"], "manifest does not cover all new delivery paths except itself")
        observations = []
        for path in sorted(added):
            if path.startswith(prefix) and PurePosixPath(path).name in ("summary.json", "supervisor.json"):
                record, raw = file_record(path, final, cache)
                observations.append({"file": record, "reported_content": json.loads(raw)})
        report["fixed_summary_supervisor"] = observations
        report["observation_note"] = "Stored JSON only; product outcomes, attempt counts and process claims are not independently adjudicated here."
        report["result"] = "INTEGRITY_ONLY_COMPLETE"
    except (IntegrityError, ValueError, OSError, subprocess.SubprocessError) as exc:
        report["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"result": report["result"], "product_verdict": "NOT_EVALUATED",
                      "output": str(output), "errors": report["errors"]}, ensure_ascii=False))
    return 0 if report["result"] == "INTEGRITY_ONLY_COMPLETE" else 2


if __name__ == "__main__":
    sys.exit(main())
