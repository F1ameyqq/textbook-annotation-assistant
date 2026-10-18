"""Compare disk bytes to fixed Git-derived hashes; never normalize the input."""
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_manifest(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def audit(root,manifest):
    root = Path(root).resolve()
    records,errors,seen = [],[],set()
    for entry in manifest["files"]:
        relative = entry["path"]
        if (relative in seen or PurePosixPath(relative).is_absolute() or PureWindowsPath(relative).drive
                or "\\" in relative or any(p in ("",".","..") for p in relative.split("/"))):
            errors.append(dict(code="REFERENCE_PATH",path=relative))
            continue
        seen.add(relative)
        path = root/relative
        try:
            path.resolve().relative_to(root)
        except ValueError:
            errors.append(dict(code="PATH_ESCAPE",path=relative))
            continue
        if not path.is_file():
            errors.append(dict(code="FILE_MISSING",path=relative))
            continue
        data = path.read_bytes()
        actual = sha(data)
        candidates = entry["representations"]
        matched = next((r for r in candidates if r["sha256"] == actual and r["bytes"] == len(data)),None)
        row = dict(path=relative,git_blob_oid=entry["git_blob_oid"],git_original_sha256=entry["git_sha256"],
                   actual_disk_sha256=actual,actual_bytes=len(data),representation=matched["kind"] if matched else "UNRECOGNIZED",
                   accepted=matched is not None)
        records.append(row)
        if matched is None:
            errors.append(dict(code="CONTENT_MISMATCH",path=relative,actual_sha256=actual,
                               accepted_sha256=[r["sha256"] for r in candidates]))
    return dict(reference_commit=manifest["reference_commit"],checked=len(records),records=records,errors=errors,passed=not errors)


def disk_changes(before,after):
    initial = {r["path"]:r["actual_disk_sha256"] for r in before["records"]}
    final = {r["path"]:r["actual_disk_sha256"] for r in after["records"]}
    return [dict(code="DISK_CHANGED_DURING_RUN",path=p,before_sha256=initial.get(p),after_sha256=final.get(p))
            for p in sorted(set(initial)|set(final)) if initial.get(p) != final.get(p)]
