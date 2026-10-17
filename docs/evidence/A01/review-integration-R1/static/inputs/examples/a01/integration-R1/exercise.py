"""Reproduce the exact bounded integration in default checkout and raw export."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from isolate import ROOT,A01,checkout,git,git_source,integration_commit,raw_export,run


def write(path,data):
    with Path(path).open("x",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(data,ensure_ascii=False,indent=2)+"\n")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot(tree,rows,blobs):
    records=[]
    for item in rows:
        disk=(tree/item["path"]).read_bytes(); original=blobs[item["oid"]]
        representation="GIT_BLOB" if disk==original else "EXACT_LF_TO_CRLF" if disk==original.replace(b"\n",b"\r\n") else "OTHER"
        records.append(dict(path=item["path"],git_blob_oid=item["oid"],git_sha256=sha(original),
                            disk_sha256=sha(disk),representation=representation))
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch",required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    identity=integration_commit(args.patch)
    work=Path(tempfile.mkdtemp(prefix="a01-i1-after-"))
    normal,raw,frozen=work/"c",work/"r",work/"f"
    creation=checkout(identity["temporary_commit"],normal)
    rows,blobs=git_source.git_files(identity["temporary_commit"])
    raw_export(identity["temporary_commit"],raw)
    before={"checkout":snapshot(normal,rows,blobs),"raw":snapshot(raw,rows,blobs)}
    assert all(r["representation"]=="GIT_BLOB" for r in before["raw"])
    write(out/"snapshots.json",dict(identity=identity,checkout=creation,has_git_raw=False,
                                    checkout_index_status=git("-C",normal,"status","--porcelain=v1").decode(),files=before))
    commands=[]
    def invoke(label,tree,arguments,expected):
        row=run(tree,[sys.executable,"-B",*map(str,arguments)],work/"temp")
        row.update(label=label,expected_exit_code=expected,matched=row["exit_code"]==expected)
        commands.append(row); write(out/(label+"-command.json"),row)
        print(json.dumps(dict(label=label,exit_code=row["exit_code"],expected=expected)),flush=True)
        if not row["matched"]:
            raise RuntimeError(label+" failed its expected exit condition")
    invoke("checkout",normal,[normal/"examples/a01/integration-R1/verify.py",out/"checkout"],0)
    invoke("raw",raw,[raw/"examples/a01/integration-R1/verify.py",out/"raw"],0)
    after={"checkout":snapshot(normal,rows,blobs),"raw":snapshot(raw,rows,blobs)}
    assert before==after,"integrated snapshot changed during conventional regression"
    assert not git("-C",normal,"status","--porcelain=v1").strip()
    write(out/"post-regression.json",dict(all_snapshot_disk_bytes_unchanged=True,files=after))
    # Negative controls modify only the new raw snapshot, restoring each exact
    # Git original afterwards; no expected manifest is rewritten or regenerated.
    for label,relative,damage in (
        ("damaged-source","src/annotation/source/static/importer.py",lambda b:b'raise RuntimeError("integration negative control")\n'+b),
        ("damaged-fixed-input","tests/fixtures/a01/integration-R1/reference.json",lambda b:b.replace(b'9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795',b'0ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795')),
    ):
        path=raw/relative; original=path.read_bytes(); modified=damage(original)
        path.write_bytes(modified)
        write(out/(label+"-input.json"),dict(path=relative,before_sha256=sha(original),after_sha256=sha(modified)))
        invoke(label,raw,[raw/"examples/a01/integration-R1/verify.py",out/label,"--focused"],1)
        path.write_bytes(original)
    # The unchanged old R3 gate is run only against the original frozen A01
    # release; it must continue to reject real source or resource changes.
    frozen_rows=raw_export(A01,frozen)
    invoke("frozen-release-original",frozen,[frozen/"examples/a01/R3/verify.py",out/"frozen-original","--preservation-only"],0)
    for label,relative in (
        ("frozen-source-damage","src/annotation/source/static/importer.py"),
        ("frozen-binary-damage","examples/a01/bundles/46007447/assets/4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9.jpg"),
    ):
        path=frozen/relative; original=path.read_bytes(); changed=original+b"damage"
        path.write_bytes(changed)
        write(out/(label+"-input.json"),dict(path=relative,before_sha256=sha(original),after_sha256=sha(changed)))
        invoke(label,frozen,[frozen/"examples/a01/R3/verify.py",out/label,"--preservation-only"],1)
        path.write_bytes(original)
    git("worktree","remove",normal)
    write(out/"results.json",dict(task="A01-integration-R1",status="REVIEW",identity=identity,
                                  temporary_root=str(work),snapshot_files=len(rows),original_release_files=len(frozen_rows),
                                  commands=commands,all_expected_exit_codes=True,normal_worktree_removed=True,
                                  no_main_update=True,network_browser_platform_model_calls=0,sessions_to_release=0))


if __name__=="__main__":
    main()
