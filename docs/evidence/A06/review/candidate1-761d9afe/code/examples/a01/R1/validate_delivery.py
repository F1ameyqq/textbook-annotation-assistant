"""Record actual consumer commands, relocation and preservation; new evidence only."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    args = parser.parse_args()
    target = args.destination.resolve()
    target.mkdir(parents=True,exist_ok=False)
    env = dict(os.environ,PYTHONPATH=str(ROOT/"src"),PYTHONDONTWRITEBYTECODE="1")
    commands = []
    def consume(path,book,cwd,scope):
        command = [sys.executable,"-B",str(ROOT/"examples/a01/consume.py"),str(path),"--book-id",book]
        result = subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True)
        row = dict(command=command,cwd=str(cwd),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,scope=scope)
        commands.append(row)
        if result.returncode:
            raise RuntimeError(row)
        return json.loads(result.stdout)
    for version in ("legacy","R1"):
        base = ROOT/("examples/a01/bundles" if version == "legacy" else "examples/a01/R1/bundles")
        for book in ("46006966","46007447"):
            consume(base/book/"exchange.json",book,ROOT,version+" fixed package")
    with tempfile.TemporaryDirectory(prefix="a01 R1 relocated ") as folder:
        folder = Path(folder)
        cwd = folder/"different cwd"
        cwd.mkdir()
        for book in ("46006966","46007447"):
            copied = folder/("copied R1 archive "+book)
            shutil.copytree(ROOT/"examples/a01/R1/bundles"/book,copied)
            consume(copied/"exchange.json",book,cwd,"R1 package copied to space path and different cwd")
    baseline = json.loads((ROOT/"docs/evidence/A01/execution/R1/baseline.json").read_text(encoding="utf-8"))
    preserved = [dict(row,current_sha256=sha(ROOT/row["path"])) for row in baseline["preserved_files"]]
    original_inputs = {}
    for book in ("46006966","46007447"):
        integrity = json.loads((ROOT/"examples/a01/bundles"/book/"input-integrity.json").read_text(encoding="utf-8"))
        for row in integrity["inputs"]:
            original_inputs[row["archive_path"]] = dict(row,current_sha256=sha(ROOT/row["archive_path"]))
    unchanged = all(row["sha256"] == row["current_sha256"] for row in preserved)
    original_unchanged = all(row["before_sha256"] == row["after_sha256"] == row["current_sha256"] for row in original_inputs.values())
    require = unchanged and original_unchanged
    modules = {module.__name__:dict(path=module.__file__,sha256=sha(Path(module.__file__)))
               for module in (contracts,geometry,importer,consistency)}
    result = dict(task="A01-R1",status="REVIEW",command=sys.argv,cwd=str(Path.cwd()),modules=modules,
                  consumers=commands,preserved_prior_outputs=preserved,prior_output_bytes_unchanged=unchanged,
                  original_inputs=list(original_inputs.values()),original_input_bytes_unchanged=original_unchanged,
                  no_browser_session_opened=True,sessions_to_release=0,network_browser_platform_model_calls=0)
    (target/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert require,"prior output or original input byte mismatch"
    print(json.dumps(dict(consumer_commands=len(commands),all_exit_zero=True,preserved_prior_files=len(preserved),
                          original_input_files=len(original_inputs),all_bytes_unchanged=require,status="REVIEW")))


if __name__ == "__main__":
    main()
