"""Bounded R2 regression, relocation, and preservation with actual command logs."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
import annotation.contracts as contracts
import annotation.geometry as geometry
import annotation.source.static.importer as importer
import annotation.source.static.consistency as consistency


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    args = parser.parse_args()
    out = args.destination.resolve()
    out.mkdir(parents=True,exist_ok=False)
    temp = ROOT/"examples/a01/R2/tmp"
    temp.mkdir(exist_ok=True)
    env = dict(os.environ,PYTHONPATH=str(ROOT/"src"),PYTHONDONTWRITEBYTECODE="1",
               TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
    commands = []
    def run(label,arguments,cwd=ROOT):
        command = [sys.executable,"-B"]+list(map(str,arguments))
        result = subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True)
        row = dict(label=label,command=command,cwd=str(cwd),exit_code=result.returncode,
                   stdout=result.stdout,stderr=result.stderr)
        commands.append(row)
        if result.returncode:
            (out/"failed-commands.json").write_text(json.dumps(commands,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            raise RuntimeError(label+" failed: "+result.stderr)
        return row
    run("A01 suite",["-m","unittest","discover","-s","tests","-p","test_a01_*.py","-v"])
    run("C01 suite",["-m","unittest","discover","-s","tests","-p","test_contracts*.py","-v"])
    run("original 16 R1 cases",[ROOT/"examples/a01/R1/probe.py",out/"R1-replay"])
    consumers = []
    for version in ("legacy","R1","R2"):
        base = ROOT/("examples/a01/bundles" if version == "legacy" else "examples/a01/"+version+"/bundles")
        for book in ("46006966","46007447"):
            consumers.append(run(version+" consumer "+book,[ROOT/"examples/a01/consume.py",base/book/"exchange.json","--book-id",book]))
    with tempfile.TemporaryDirectory(prefix="a01 R2 relocated ",dir=temp) as work:
        work = Path(work)
        cwd = work/"different cwd"
        cwd.mkdir()
        for version in ("legacy","R1","R2"):
            base = ROOT/("examples/a01/bundles" if version == "legacy" else "examples/a01/"+version+"/bundles")
            for book in ("46006966","46007447"):
                copied = work/("copied "+version+" archive "+book)
                shutil.copytree(base/book,copied)
                consumers.append(run("relocated "+version+" "+book,[ROOT/"examples/a01/consume.py",copied/"exchange.json","--book-id",book],cwd))
    baseline = json.loads((ROOT/"docs/evidence/A01/execution/R2/baseline.json").read_text(encoding="utf-8"))
    preserved = [dict(row,current_sha256=digest(ROOT/row["path"])) for row in baseline["preserved_tracked_files"]]
    intact = all(row["sha256"] == row["current_sha256"] for row in preserved)
    original_inputs = {}
    for book in ("46006966","46007447"):
        data = json.loads((ROOT/"examples/a01/bundles"/book/"input-integrity.json").read_text(encoding="utf-8"))
        for row in data["inputs"]:
            original_inputs[row["archive_path"]] = dict(row,current_sha256=digest(ROOT/row["archive_path"]))
    original_intact = all(r["before_sha256"] == r["after_sha256"] == r["current_sha256"] for r in original_inputs.values())
    geometry_intact = digest(ROOT/"src/annotation/geometry/__init__.py") == baseline["geometry_sha256"]
    result = dict(task="A01-R2",status="REVIEW",command=sys.argv,cwd=str(Path.cwd()),commands=commands,
                  consumer_commands=len(consumers),preserved_files=preserved,all_preserved_bytes_unchanged=intact,
                  geometry_bytes_unchanged=geometry_intact,geometry_sha256=baseline["geometry_sha256"],
                  original_inputs=list(original_inputs.values()),original_input_bytes_unchanged=original_intact,
                  modules={m.__name__:dict(path=m.__file__,sha256=digest(m.__file__)) for m in (contracts,geometry,importer,consistency)},
                  network_browser_platform_model_calls=0,sessions_to_release=0)
    (out/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert intact and original_intact and geometry_intact,"preservation mismatch"
    print(json.dumps(dict(commands=len(commands),consumers=len(consumers),all_exit_zero=True,
                          preserved_files=len(preserved),original_inputs=len(original_inputs),geometry_unchanged=True,status="REVIEW")))


if __name__ == "__main__":
    main()
