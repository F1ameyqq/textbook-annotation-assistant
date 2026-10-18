"""Author-side evidence: normal checkout, exact Git export, and corruption controls.

Git operations run only in this original task worktree. The exported verifier
uses only its committed references and never invokes Git or the primary tree.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from build_references import git_files

ROOT = Path(__file__).resolve().parents[3]


def write(path,data):
    with path.open("x",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(data,ensure_ascii=False,indent=2)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit",required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    temp = ROOT/"examples/a01/R3/tmp"; temp.mkdir(exist_ok=True)
    export = temp/"g"
    export.mkdir(exist_ok=False)
    rows,blobs = git_files(args.commit)
    exported = []
    for row in rows:
        path = export/row["path"]
        path.resolve().relative_to(export.resolve())
        path.parent.mkdir(parents=True,exist_ok=True)
        raw = blobs[row["oid"]]; path.write_bytes(raw)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == hashlib.sha256(raw).hexdigest()
        exported.append(dict(path=row["path"],git_blob_oid=row["oid"],sha256=actual))
    assert not (export/".git").exists()
    write(out/"export.json",dict(commit=args.commit,destination=str(export),has_git_directory=False,files=exported))
    env = dict(os.environ,PYTHONDONTWRITEBYTECODE="1")
    commands = []
    def run(label,tree,output,expected,preservation_only=False):
        command = [sys.executable,"-B",str(tree/"examples/a01/R3/verify.py"),str(output)]
        if preservation_only:
            command.append("--preservation-only")
        proc = subprocess.run(command,cwd=tree,env=env,capture_output=True,text=True)
        row = dict(label=label,command=command,cwd=str(tree),expected_exit_code=expected,
                   exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr,matched=proc.returncode == expected)
        commands.append(row)
        write(out/(label+"-command.json"),row)
        print(json.dumps(dict(label=label,exit_code=proc.returncode,expected=expected)),flush=True)
        if not row["matched"]:
            raise RuntimeError(label+" did not meet its expected exit condition")
    run("normal-checkout",ROOT,out/"normal",0)
    run("raw-Git-export",export,out/"raw",0)
    with tempfile.TemporaryDirectory(prefix="a01-r3-controls-",dir=temp) as work:
        work = Path(work); work.resolve().relative_to(temp.resolve())
        controls = (
            ("allowed-fixed-CRLF","tests/test_contracts.py",lambda raw:raw.replace(b"\n",b"\r\n"),0,True),
            ("true-text-content-damage","tests/test_contracts.py",lambda raw:raw+b"\n# changed actual content\n",1,False),
            ("mixed-EOL-rejected","tests/test_contracts.py",lambda raw:raw.replace(b"\n",b"\r\n",1),1,False),
            ("historical-EOL-rejected","docs/evidence/A01/execution/final/verification.json",lambda raw:raw.replace(b"\n",b"\r\n"),1,False),
            ("binary-content-damage","examples/a01/bundles/46007447/assets/4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9.jpg",lambda raw:raw+b"damage",1,False),
        )
        for label,relative,mutate,expected,only in controls:
            tree = work/label
            shutil.copytree(export,tree,ignore=shutil.ignore_patterns("tmp","__pycache__"))
            path = tree/relative; before = hashlib.sha256(path.read_bytes()).hexdigest()
            path.write_bytes(mutate(path.read_bytes()))
            write(out/(label+"-input.json"),dict(path=relative,before_sha256=before,after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                                mutation=label,source_commit=args.commit))
            run(label,tree,out/label,expected,only)
    write(out/"results.json",dict(task="A01-R3",status="REVIEW",source_commit=args.commit,commands=commands,
                                  all_matches=True,exported_files=len(exported),platform_network_browser_model_calls=0,sessions_to_release=0))


if __name__ == "__main__":
    main()
