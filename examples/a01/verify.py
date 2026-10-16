"""Produce new, sanitized A01 execution evidence. Offline verification only."""
import argparse
import copy
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import PIL
import pydantic

from annotation.contracts import ContractError, load_bundle, validate_bundle
from annotation.source.static import load_static_bundle

ROOT = Path(__file__).resolve().parents[2]


def emit(folder,name,data):
    with (folder/name).open("x",encoding="utf-8",newline="\n") as handle:
        handle.write(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n")


class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.events = []

    def addSuccess(self,test):
        super().addSuccess(test)
        self.events.append(dict(test=test.id(),result="PASS"))

    def addSkip(self,test,reason):
        super().addSkip(test,reason)
        self.events.append(dict(test=test.id(),result="NOT_EXECUTED",reason=reason))


def run_tests(pattern):
    suite = unittest.defaultTestLoader.discover(str(ROOT/"tests"),pattern=pattern)
    result = unittest.TextTestRunner(stream=io.StringIO(),resultclass=Result).run(suite)
    summary = dict(pattern=pattern,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                   skipped=len(result.skipped),successful=result.wasSuccessful(),tests=result.events)
    if not result.wasSuccessful():
        raise RuntimeError("verification failed: "+str(summary))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists():
        parser.error("evidence destination exists; preserve prior evidence")
    tests = [run_tests("test_a01_*.py"),run_tests("test_contracts*.py")]
    relocation,resources,inputs,negatives = [],[],[],[]
    with tempfile.TemporaryDirectory(prefix="a01 portable evidence ") as work:
        work = Path(work)
        cwd = work/"different cwd"
        cwd.mkdir()
        for book in ("46006966","46007447"):
            source = ROOT/"examples/a01/bundles"/book
            path = source/"exchange.json"
            bundle = load_static_bundle(path,expected_book_id=book)
            data = bundle.model_dump(mode="json")
            copied = work/("copied archive "+book)
            shutil.copytree(source,copied)
            run = subprocess.run([sys.executable,str(ROOT/"examples/a01/consume.py"),str(copied/"exchange.json"),"--book-id",book],
                                 cwd=cwd,env=dict(os.environ,PYTHONPATH=str(ROOT/"src")),capture_output=True,text=True,check=False)
            if run.returncode:
                raise RuntimeError("relocated consumer failed: "+run.stderr)
            relocation.append(dict(book_id=book,directory_has_spaces=True,different_cwd=True,
                                   command="python <repo>/examples/a01/consume.py '<copied archive>/exchange.json' --book-id "+book,
                                   exit_code=run.returncode,result=json.loads(run.stdout)))
            resources.append(dict(book_id=book,files=[dict(path=p.relative_to(source).as_posix(),bytes=p.stat().st_size,
                                                           sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                                      for p in sorted(source.rglob("*")) if p.is_file()]))
            inputs.append(json.loads((source/"input-integrity.json").read_text(encoding="utf-8")))
            empty = copy.deepcopy(data)
            empty["artifacts"][0]["payload"]["scope_manifest"] = []
            try:
                validate_bundle(empty)
            except ContractError as error:
                negatives.append(dict(case="unknown independent denominator cannot be encoded as empty scope",book_id=book,
                                      mutation=dict(path="$.artifacts[0].payload.scope_manifest",value=[]),issues=error.issues))
            else:
                raise RuntimeError("C01 scope assumption changed; revisit S01")
            assert load_bundle(path,verify_assets=True) == bundle
    target.mkdir(parents=True,exist_ok=False)
    emit(target,"verification.json",dict(task="A01",status="REVIEW",observed_at=datetime.now(timezone.utc).isoformat(),
                                         environment=dict(python=platform.python_version(),python_implementation=platform.python_implementation(),
                                                          os=platform.system(),pydantic=pydantic.__version__,Pillow=PIL.__version__),
                                         commands=["python -m unittest discover -s tests -p 'test_a01_*.py' -v",
                                                   "python -m unittest discover -s tests -p 'test_contracts*.py'"],
                                         tests=tests,network_calls=0,browser_calls=0,model_calls=0,model_cost=0,
                                         real_platform_acceptance="NOT_EXECUTED",independent_A01_acceptance="PENDING"))
    emit(target,"relocation.json",relocation)
    emit(target,"resources.json",resources)
    emit(target,"input-integrity.json",inputs)
    emit(target,"negative-cases.json",negatives)
    emit(target,"evidence-manifest.json",dict(files=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                                    for p in sorted(target.glob("*.json"))]))
    print(json.dumps(dict(status="REVIEW",tests=[{k:v for k,v in r.items() if k != "tests"} for r in tests],
                          relocated_books=len(relocation),model_calls=0,model_cost=0)))


if __name__ == "__main__":
    main()
