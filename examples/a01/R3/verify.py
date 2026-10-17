"""Git-free R3 verification against committed fixed Git-blob references."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fixtures import reconstruct
from preservation import audit, disk_changes, read_manifest

ROOT = Path(__file__).resolve().parents[3]


def write(path,data):
    with path.open("x",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(data,ensure_ascii=False,indent=2)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--preservation-only",action="store_true")
    args = parser.parse_args()
    out = args.destination.resolve(); out.mkdir(parents=True,exist_ok=False)
    refs = ROOT/"tests/fixtures/a01/R3"
    code_ref = read_manifest(refs/"code-reference.json")
    initial_code = audit(ROOT,code_ref)
    write(out/"code-begin.json",initial_code)
    if not initial_code["passed"]:
        print(json.dumps(dict(status="REVIEW",passed=False,gate="implementation",errors=initial_code["errors"])))
        return 1
    preserved_ref = read_manifest(refs/"preservation-manifest.json")
    initial = audit(ROOT,preserved_ref)
    write(out/"preservation-begin.json",initial)
    if not initial["passed"]:
        print(json.dumps(dict(status="REVIEW",passed=False,gate="preservation",errors=initial["errors"])))
        return 1
    sys.path.insert(0,str(ROOT/"src"))
    import annotation.contracts as contracts
    import annotation.geometry as geometry
    import annotation.source.static.importer as importer
    import annotation.source.static.consistency as consistency
    temp = ROOT/"examples/a01/R3/tmp"; temp.mkdir(exist_ok=True)
    env = dict(os.environ,PYTHONPATH=str(ROOT/"src"),PYTHONDONTWRITEBYTECODE="1",TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
    commands = []
    def run(label,arguments,cwd=ROOT):
        command = [sys.executable,"-B"]+list(map(str,arguments))
        proc = subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True)
        row = dict(label=label,command=command,cwd=str(cwd),exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr)
        commands.append(row)
        if proc.returncode:
            write(out/"failed-commands.json",commands)
            raise RuntimeError(label+" failed: "+proc.stderr)
    if not args.preservation_only:
        run("A01 suite",["-m","unittest","discover","-s","tests","-p","test_a01_*.py","-v"])
        run("C01 suite",["-m","unittest","discover","-s","tests","-p","test_contracts*.py","-v"])
        run("original 16",[ROOT/"examples/a01/R1/probe.py",out/"R1-replay"])
        with tempfile.TemporaryDirectory(prefix="a01 R3 work ",dir=temp) as work:
            work = Path(work)
            official = work/"R2-fixed"
            reconstruct(ROOT,"R2-official",official)
            run("R2 nine fixed cases",[ROOT/"examples/a01/R2/probe.py",out/"R2-replay","--official-inputs",official])
            run("R3 five URL cases",[ROOT/"examples/a01/R3/probe.py",out/"R3-replay"])
            cwd = work/"different cwd"; cwd.mkdir()
            for version in ("legacy","R1","R2","R3"):
                base = ROOT/("examples/a01/bundles" if version == "legacy" else "examples/a01/"+version+"/bundles")
                for book in ("46006966","46007447"):
                    run(version+" consumer "+book,[ROOT/"examples/a01/consume.py",base/book/"exchange.json","--book-id",book])
                    copied = work/("copied "+version+" "+book)
                    shutil.copytree(base/book,copied)
                    run("relocated "+version+" "+book,[ROOT/"examples/a01/consume.py",copied/"exchange.json","--book-id",book],cwd)
    final = audit(ROOT,preserved_ref); final_code = audit(ROOT,code_ref)
    write(out/"preservation-end.json",final); write(out/"code-end.json",final_code)
    changed = disk_changes(initial,final)+disk_changes(initial_code,final_code)
    result = dict(task="A01-R3",status="REVIEW",command=sys.argv,cwd=str(Path.cwd()),
                  baseline_commit=preserved_ref["reference_commit"],implementation_commit=code_ref["reference_commit"],
                  preserved_reference_sha256=hashlib.sha256((refs/"preservation-manifest.json").read_bytes()).hexdigest(),
                  code_reference_sha256=hashlib.sha256((refs/"code-reference.json").read_bytes()).hexdigest(),
                  preserved_files=len(initial["records"]),disk_changes=changed,commands=commands,
                  passed=final["passed"] and final_code["passed"] and not changed,
                  modules={m.__name__:dict(path=m.__file__,disk_sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest())
                           for m in (contracts,geometry,importer,consistency)},
                  platform_network_browser_model_calls=0,sessions_to_release=0)
    write(out/"results.json",result)
    print(json.dumps(dict(status="REVIEW",passed=result["passed"],commands=len(commands),preserved_files=result["preserved_files"],
                          representations=sorted({r["representation"] for r in initial["records"]}))))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
