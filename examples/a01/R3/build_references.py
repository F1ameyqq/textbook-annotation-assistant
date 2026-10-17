"""Author fixed references from explicit Git blobs, not current disk contents.

This authoring tool requires Git. The verification entry does not call it.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "c3aff9598b6705ab4122062615a13ae3774698b2"
MUTABLE = {"src/annotation/source/static/importer.py","src/annotation/source/static/consistency.py","docs/a01-source-geometry.md"}
# Exact files from the frozen independent LF/CRLF diagnosis. This is not a
# suffix rule: all other historical files/binaries have only their Git bytes.
EOL_ALLOWLIST = (
    "data/derived/analysis/route_c_dump.txt","examples/contracts/build_fixtures.py","examples/contracts/consume.py","pyproject.toml",
    "src/annotation/__init__.py","src/annotation/contracts/__init__.py","src/annotation/contracts/__main__.py",
    "src/annotation/contracts/cli.py","src/annotation/contracts/integrity.py","src/annotation/contracts/models.py",
    "src/annotation/contracts/validation.py","tests/test_contracts.py","tests/test_contracts_platform_refs.py",
    "tools/bridge.py","tools/build_release.py","tools/coord_reverse.py","tools/land_data.py","tools/layout_probe.py",
    "tools/page_mapping.py","tools/route_a_layout.py","tools/route_c_ocr.py","tools/test_usense_login.py",
    "tools/usense_login.py","tools/verify_data.py","tools/verify_page_mapping.py",
)


def git_files(commit):
    listing = subprocess.check_output(["git","ls-tree","-rz","--full-tree",commit],cwd=ROOT)
    rows = []
    for record in listing.split(b"\0"):
        if not record:
            continue
        header,path = record.split(b"\t",1)
        mode,kind,oid = header.decode().split()
        if kind != "blob" or mode not in ("100644","100755"):
            raise ValueError("unsupported Git entry: "+path.decode("utf-8"))
        rows.append(dict(path=path.decode("utf-8"),mode=mode,oid=oid))
    ids = list(dict.fromkeys(r["oid"] for r in rows))
    stream = subprocess.check_output(["git","cat-file","--batch"],cwd=ROOT,input=("\n".join(ids)+"\n").encode())
    blobs = {}; offset = 0
    for expected in ids:
        end = stream.index(b"\n",offset)
        oid,kind,size = stream[offset:end].decode().split(); size = int(size)
        raw = stream[end+1:end+1+size]; offset = end+size+2
        assert oid == expected and kind == "blob" and hashlib.sha1(b"blob "+str(size).encode()+b"\0"+raw).hexdigest() == oid
        blobs[oid] = raw
    return rows,blobs


def reference(row,raw,allow_eol=False):
    actual = hashlib.sha256(raw).hexdigest()
    candidates = [dict(kind="GIT_BLOB",sha256=actual,bytes=len(raw))]
    if allow_eol:
        raw.decode("utf-8")
        assert b"\0" not in raw and b"\r" not in raw and b"\n" in raw
        converted = raw.replace(b"\n",b"\r\n")
        candidates.append(dict(kind="FIXED_CRLF_TEXT_REPRESENTATION",sha256=hashlib.sha256(converted).hexdigest(),bytes=len(converted)))
    return dict(path=row["path"],git_blob_oid=row["oid"],git_sha256=actual,representations=candidates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind",choices=("baseline","code"))
    parser.add_argument("--commit")
    args = parser.parse_args()
    commit = BASE if args.kind == "baseline" else args.commit
    if not commit or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        parser.error("code reference requires an explicit 40-character commit")
    rows,blobs = git_files(commit)
    if args.kind == "baseline":
        assert set(EOL_ALLOWLIST) <= {r["path"] for r in rows}
        records = [reference(r,blobs[r["oid"]],r["path"] in EOL_ALLOWLIST) for r in rows if r["path"] not in MUTABLE]
        filename = "preservation-manifest.json"
    else:
        selected = [r for r in rows if r["path"] in MUTABLE or r["path"] == "tests/test_a01_rework_r3.py"
                    or r["path"].startswith(("examples/a01/R3/","tests/fixtures/a01/R3/"))]
        selected = [r for r in selected if not r["path"].endswith("/code-reference.json")]
        eol = {"src/annotation/source/static/importer.py","src/annotation/source/static/consistency.py","tests/test_a01_rework_r3.py"}
        records = [reference(r,blobs[r["oid"]],r["path"] in eol) for r in selected]
        filename = "code-reference.json"
    data = dict(format_version="a01-fixed-git-reference-1",reference_commit=commit,kind=args.kind,
                note="Generated only from the explicit Git blobs; runtime uses these fixed hashes without normalization or regeneration.",files=records)
    target = ROOT/"tests/fixtures/a01/R3"/filename
    with target.open("x",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(kind=args.kind,reference_commit=commit,files=len(records),fixed_EOL_variants=sum(len(r["representations"]) > 1 for r in records))))


if __name__ == "__main__":
    main()
