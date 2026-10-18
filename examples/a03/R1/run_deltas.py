"""One bounded sequential L package; stop on its first failure."""
import importlib.util
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('m_driver', ROOT/'examples/a03/T3-closure/run.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def main():
    output=ROOT/'docs/evidence/A03/R1/execution/deltas-correction'
    output.mkdir(parents=True, exist_ok=False)
    mroot=ROOT/'docs/evidence/A03/R1/execution/candidate-1/business'
    view=mroot/'runtime-view'
    env=dict(os.environ, PYTHONPATH=str(view/'src'), PYTHONDONTWRITEBYTECODE='1')
    phases=['legacy','L1','B','L3-execute','L3-recover','L3-second']
    m.write(output/'preregistered.json', dict(phases=phases, product_candidate='6097a06de937fee8876feccedf46920510850b83',
        new_native_targets_upper=2, native_dispatch_upper=3, legacy_dispatch_upper=2,
        reuse='completed owned M2-sufficient; no replay', child_seconds=180, parent_seconds=240))
    rows=[]
    try:
        for phase in phases:
            result=m.run_child(output/'processes'/phase,
                [sys.executable,'-X','utf8','-B',str(ROOT/'examples/a03/R1/deltas.py'),'--phase',phase,
                 '--mroot',str(mroot),'--output',str(output/phase)],cwd=ROOT,env=env,timeout=180)
            rows.append(dict(phase=phase, process=result))
            if result['exit_code']!=0 or result['timeout']:
                raise RuntimeError('first L delta failure: '+phase)
    finally:
        m.write(output/'matrix.json',dict(actual=rows, not_run=phases[len(rows):]))


if __name__=='__main__': main()
