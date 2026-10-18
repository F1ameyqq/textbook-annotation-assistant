"""Recheck existing L1 using the independent M2 state and frozen legacy input.

No legacy execute, new target, L2 attempt, or extra dispatch is performed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
REVIEW=ROOT/'docs/evidence/A03/R1/review'
MROOT=REVIEW/'business'
spec=importlib.util.spec_from_file_location('fixed_deltas',ROOT/'examples/a03/R1/deltas.py')
d=importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
sys.path.insert(0,str(MROOT/'runtime-view/examples/a03/T1-capture'))

def main():
    assert not (REVIEW/'L1').exists() and not (REVIEW/'legacy').exists()
    assert json.loads((MROOT/'matrix.json').read_bytes())['not_run']==[]
    provenance=[]
    for ordinal in (1,2):
        src=ROOT/'docs/evidence/A03/R1/execution/deltas-correction/legacy'/('history-'+str(ordinal))
        dst=REVIEW/'legacy'/src.name
        shutil.copytree(src,dst)
        for f in sorted(src.rglob('*')):
            if f.is_file():
                raw=f.read_bytes();assert raw==(dst/f.relative_to(src)).read_bytes()
                provenance.append(dict(path=str(f.relative_to(ROOT)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    (REVIEW/'L1').mkdir()
    d.write(REVIEW/'L1/preregistered.json',dict(product='6097a06de937fee8876feccedf46920510850b83',
        source_delivery='54e86adfaf144093a688b62fe0dad5190ceb2fa6',history_inputs=provenance,
        continuing_state=str(MROOT/'cases/M2-sufficient'),new_targets=0,extra_dispatch=0,
        reconcile_upper=1,max_attempts=1,child_seconds=180,parent_seconds=240))
    d.ledger(argparse.Namespace(mroot=MROOT,output=REVIEW/'L1'))
    d.write(REVIEW/'L1/imports.json',d.imports())
    print('INDEPENDENT_L1_ENDED; no dispatch/new target/legacy generation')

if __name__=='__main__':main()
