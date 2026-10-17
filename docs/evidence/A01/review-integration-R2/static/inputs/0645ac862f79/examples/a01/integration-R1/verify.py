"""Conventional integrated regression, not the historical R3 release-byte gate."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--focused",action="store_true",help="negative controls: A01 regression only; not a full result")
    args=parser.parse_args()
    out=args.destination.resolve(); out.mkdir(parents=True,exist_ok=False)
    commands=[]
    with tempfile.TemporaryDirectory(prefix="a01-i1-run-") as folder:
        folder=Path(folder)
        env=dict(os.environ,PYTHONPATH=str(ROOT/"src"),PYTHONDONTWRITEBYTECODE="1",
                 TMP=str(folder),TEMP=str(folder),TMPDIR=str(folder))
        def run(label,arguments,cwd=ROOT):
            proc=subprocess.run([sys.executable,"-B",*map(str,arguments)],cwd=cwd,env=env,capture_output=True,text=True)
            commands.append(dict(label=label,argv=proc.args,cwd=str(cwd),exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr))
            return proc.returncode==0
        all_ok=run("A01 conventional regression",["-m","unittest","discover","-s","tests","-p","test_a01*.py","-v"])
        if not args.focused:
            for label,where,pattern in (("C01","tests","test_contracts*.py"),("A02","tests","test_a02*.py"),("login offline","tools","test_usense_login.py")):
                all_ok=run(label,["-m","unittest","discover","-s",where,"-p",pattern,"-v"]) and all_ok
            all_ok=run("fixed R3 URL cases",[ROOT/"examples/a01/R3/probe.py",out/"URL-replay"]) and all_ok
            cwd=folder/"different cwd"; cwd.mkdir()
            for version in ("legacy","R3"):
                base=ROOT/("examples/a01/bundles" if version=="legacy" else "examples/a01/R3/bundles")
                for book in ("46006966","46007447"):
                    all_ok=run(version+" "+book,[ROOT/"examples/a01/consume.py",base/book/"exchange.json","--book-id",book]) and all_ok
                    if version=="R3":
                        copied=folder/("copied book "+book); shutil.copytree(base/book,copied)
                        all_ok=run("relocated "+book,[ROOT/"examples/a01/consume.py",copied/"exchange.json","--book-id",book],cwd) and all_ok
    modules={}
    sys.path.insert(0,str(ROOT/"src"))
    for relative in ("src/annotation/source/static/importer.py","src/annotation/source/static/consistency.py","src/annotation/geometry/__init__.py","src/annotation/contracts/models.py","tests/test_a01_rework_r3.py"):
        path=ROOT/relative
        modules[relative]=dict(path=str(path),disk_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    result=dict(task="A01-integration-R1",status="REVIEW",scope="focused A01 negative control" if args.focused else "conventional integrated regression",
                cwd=str(ROOT),command=sys.argv,commands=commands,passed=all_ok,source_files=modules,
                historical_R3_verify_scope="Only its unchanged bound frozen release; this entry does not claim to satisfy that release identity.",
                network_browser_platform_model_calls=0,sessions_to_release=0)
    with (out/"results.json").open("x",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(passed=all_ok,commands=len(commands),status="REVIEW")))
    return 0 if all_ok else 1


if __name__=="__main__":
    raise SystemExit(main())
