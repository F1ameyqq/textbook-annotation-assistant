"""Replay author commands using exact blobs under an ordinary temporary root."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
BOOT=json.loads((OUT/"bootstrap.json").read_text(encoding="utf-8"))
WORK=Path(BOOT["temporary_root"])

def main():
    logs=OUT/"reproduction";logs.mkdir(exist_ok=False)
    source=WORK/"verified author source"
    shutil.copytree(BOOT["snapshot"],source)
    checked=[]
    for item in BOOT["verified_blobs"]:
        actual=hashlib.sha256((source/item["path"]).read_bytes()).hexdigest()
        assert actual==item["sha256"],item["path"]
        checked.append({"path":item["path"],"sha256":actual})
    (logs/"source-copy-verification.json").write_text(json.dumps({"source":str(source),"reason":"author verify.py pins its TMP under ROOT/examples; use a verified ordinary-temp source export without modifying that code","verified_files":checked},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    temp=WORK/"author-temp";temp.mkdir(exist_ok=False)
    env=dict(os.environ,PYTHONPATH=str(source/"src"),PYTHONDONTWRITEBYTECODE="1",TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
    cases=[
        ("01-import-paths",["-B","-c","import json,annotation.contracts as c,annotation.geometry as g,annotation.source.static.importer as i,annotation.source.static.consistency as s; print(json.dumps({m.__name__:m.__file__ for m in (c,g,i,s)}))"]),
        ("02-a01-tests",["-B","-m","unittest","discover","-s","tests","-p","test_a01_*.py","-v"]),
        ("03-c01-tests",["-B","-m","unittest","discover","-s","tests","-p","test_contracts*.py","-v"]),
        ("04-original-16",["-B","examples/a01/R1/probe.py",str(WORK/"author original 16")]),
        ("05-R2-nine",["-B","examples/a01/R2/probe.py",str(WORK/"author R2 nine"),"--official-inputs",str(ROOT/"docs/evidence/A01/review-R1/primary-source-confirmation")]),
    ]
    for version in ("legacy","R1","R2"):
        base="examples/a01/bundles" if version=="legacy" else "examples/a01/"+version+"/bundles"
        for book in ("46006966","46007447"):
            cases.append((version+"-"+book,["-B","examples/a01/consume.py",base+"/"+book+"/exchange.json","--book-id",book]))
    cases.extend([
        ("12-build",["-B","examples/a01/build.py",str(WORK/"author newly built bundles")]),
        ("13-verify",["-B","examples/a01/R2/verify.py",str(WORK/"author R2 verify")]),
    ])
    records=[]
    for name,args in cases:
        start=time.monotonic()
        proc=subprocess.run([sys.executable]+args,cwd=source,env=env,capture_output=True)
        (logs/(name+".stdout.txt")).write_bytes(proc.stdout);(logs/(name+".stderr.txt")).write_bytes(proc.stderr)
        records.append({"name":name,"command":[sys.executable]+args,"cwd":str(source),"exit_code":proc.returncode,"seconds":round(time.monotonic()-start,3),
                        "environment_overrides":{k:env[k] for k in ("PYTHONPATH","PYTHONDONTWRITEBYTECODE","TMP","TEMP","TMPDIR")},"stdout":name+".stdout.txt","stderr":name+".stderr.txt"})
        print(name+": "+str(proc.returncode),flush=True)
    (logs/"commands.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    raise SystemExit(any(r["exit_code"] for r in records))

if __name__=="__main__":main()
