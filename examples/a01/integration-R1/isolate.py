"""Author-side exact integration snapshots; all Git commands use the task tree."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAIN = "4946b8ab307f88bdc25c14ace5ead774e3119fc5"
A01 = "180bb1e86fb2a7eb1546be85af70f466f069daf5"
spec = importlib.util.spec_from_file_location("integration_fixed_git",ROOT/"examples/a01/R3/build_references.py")
git_source = importlib.util.module_from_spec(spec); spec.loader.exec_module(git_source)


def git(*arguments,input=None):
    return subprocess.run(["git",*map(str,arguments)],cwd=ROOT,input=input,capture_output=True,check=True).stdout


def integration_commit(patch):
    tree = git("merge-tree","--write-tree",MAIN,patch).decode().strip()
    assert len(tree) == 40 and all(c in "0123456789abcdef" for c in tree),tree
    message = ("Temporary A01 integration validation only\n\nmain="+MAIN+"\nA01="+A01+"\npatch="+patch+"\n").encode()
    commit = git("commit-tree",tree,"-p",MAIN,"-p",patch,input=message).decode().strip()
    return dict(main_parent=MAIN,A01_base=A01,patch_parent=patch,tree=tree,temporary_commit=commit,
                note="Synthetic local object only; no branch/main update or product integration acceptance")


def checkout(commit,path):
    path = Path(path).resolve()
    if path.exists():
        raise ValueError("snapshot path must be new")
    proc = subprocess.run(["git","worktree","add","--detach",str(path),commit],cwd=ROOT,capture_output=True,text=True,check=True)
    return dict(argv=proc.args,cwd=str(ROOT),exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr)


def raw_export(commit,path):
    path = Path(path).resolve(); path.mkdir(parents=True,exist_ok=False)
    rows,blobs = git_source.git_files(commit)
    for row in rows:
        output = path/row["path"]
        output.resolve().relative_to(path)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(blobs[row["oid"]])
    assert not (path/".git").exists()
    return rows


def run(tree,arguments,temporary):
    temporary = Path(temporary); temporary.mkdir(parents=True,exist_ok=True)
    env = dict(os.environ,PYTHONPATH=str(Path(tree)/"src"),PYTHONDONTWRITEBYTECODE="1",
               TMP=str(temporary),TEMP=str(temporary),TMPDIR=str(temporary))
    proc = subprocess.run(arguments,cwd=tree,env=env,capture_output=True,text=True)
    return dict(argv=arguments,cwd=str(tree),exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr)
