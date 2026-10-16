"""Reproduce author R1 commands from the exact, verified source export."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

OUT=Path(__file__).resolve().parent
BOOT=json.loads((OUT/"bootstrap.json").read_text(encoding="utf-8"))
SNAPSHOT=Path(BOOT["snapshot"])
WORK=Path(BOOT["temporary_root"])

def main():
    logs=OUT/"reproduction"
    logs.mkdir(exist_ok=False)
    temp=WORK/"author-temp"
    temp.mkdir(exist_ok=False)
    env=dict(os.environ,PYTHONPATH=str(SNAPSHOT/"src"),PYTHONDONTWRITEBYTECODE="1",TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
    cases=[
        ("01-import-paths",["-B","-c","import json,annotation.contracts as c,annotation.geometry as g,annotation.source.static.importer as s,annotation.source.static.consistency as k; print(json.dumps({m.__name__:m.__file__ for m in (c,g,s,k)}))"]),
        ("02-a01-tests",["-B","-m","unittest","discover","-s","tests","-p","test_a01_*.py","-v"]),
        ("03-c01-tests",["-B","-m","unittest","discover","-s","tests","-p","test_contracts*.py"]),
        ("04-author-replay",["-B","examples/a01/R1/probe.py",str(WORK/"author R1 replay")]),
        ("05-old-old-book",["-B","examples/a01/consume.py","examples/a01/bundles/46006966/exchange.json","--book-id","46006966"]),
        ("06-old-new-book",["-B","examples/a01/consume.py","examples/a01/bundles/46007447/exchange.json","--book-id","46007447"]),
        ("07-r1-old-book",["-B","examples/a01/consume.py","examples/a01/R1/bundles/46006966/exchange.json","--book-id","46006966"]),
        ("08-r1-new-book",["-B","examples/a01/consume.py","examples/a01/R1/bundles/46007447/exchange.json","--book-id","46007447"]),
        ("09-build",["-B","examples/a01/build.py",str(WORK/"author new source bundles")]),
        ("10-validate-delivery",["-B","examples/a01/R1/validate_delivery.py",str(WORK/"author validate delivery")]),
        ("11-verify",["-B","examples/a01/verify.py",str(WORK/"author verify evidence")]),
    ]
    records=[]
    for name,args in cases:
        start=time.monotonic()
        proc=subprocess.run([sys.executable]+args,cwd=SNAPSHOT,env=env,capture_output=True)
        (logs/(name+".stdout.txt")).write_bytes(proc.stdout)
        (logs/(name+".stderr.txt")).write_bytes(proc.stderr)
        records.append({"name":name,"command":[sys.executable]+args,"cwd":str(SNAPSHOT),
                        "environment_overrides":{k:env[k] for k in ("PYTHONPATH","PYTHONDONTWRITEBYTECODE","TMP","TEMP","TMPDIR")},
                        "exit_code":proc.returncode,"seconds":round(time.monotonic()-start,3),"stdout":name+".stdout.txt","stderr":name+".stderr.txt"})
        print(name+": "+str(proc.returncode),flush=True)
    (logs/"commands.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    raise SystemExit(any(r["exit_code"] for r in records))

if __name__ == "__main__":main()
