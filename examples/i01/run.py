"""Exclusive frozen I01 run. Existing evidence cannot be overwritten or rerun."""
import argparse
import os
from pathlib import Path
import sys
from support import ROOT, BASE, PRODUCT, WORKFLOW, EVIDENCE, export, git, load, sha, write, run_child


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',required=True)
    args=parser.parse_args()
    assert git(['rev-parse','HEAD']).decode().strip()==args.candidate
    assert not git(['diff','--name-only',BASE,args.candidate,'--','src','pyproject.toml','requirements.txt'])
    run=EVIDENCE/'run';run.mkdir(parents=True,exist_ok=False)
    frozen=EVIDENCE/'frozen';frozen.mkdir(exist_ok=False)
    view=frozen/'candidate-view'
    rows=export(args.candidate,['examples/i01','tests/fixtures/i01','tests/test_i01_preflight.py'],view)
    raw=EVIDENCE/'preparation/raw-view'
    env=dict(os.environ, I01_PROJECT=str(ROOT), I01_FROZEN_VIEW=str(view), PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=str(raw/'src')+os.pathsep+str(raw/'examples/a03/T1-capture'))
    phases=['A01-C01','A01-consume','N','E','U-execute','U-recover']
    write(frozen/'invocation.json',dict(candidate=args.candidate,base=BASE,product=PRODUCT,workflow=WORKFLOW,
        files=rows,phases=phases,targets_upper=3,dispatch_upper=3,worker_seconds=180,parent_seconds=240,
        read_seconds=2,entry_seconds=8,gate_seconds=5,lease_seconds=10,renew_seconds=2,
        reconcile_call='I01-U-one-MATCH-call',max_attempts=1,fault='actual effect plus unavailable execution observation',
        E_strategy='pre-dispatch TARGET_CHANGED; no terminal baseline; release/reclaim then new INITIAL chain',
        correction_upper=1,automatic_retry=False))
    for item in load(EVIDENCE/'preparation/identity.json')['inputs']:
        assert sha((view/item['path']).read_bytes())==item['sha256'],item['path']
    commands=[[sys.executable,'-X','utf8','-B',str(view/'examples/i01/public.py'),'--mode',mode,
        '--input',str(view/'tests/fixtures/i01/source-copy/exchange.json'),'--output',str(run/'public-imports'/ (mode+'.json'))]
        for mode in ('C01','A01')]
    matrix=[]
    try:
        for index,phase in enumerate(phases):
            if index<2:
                argv=commands[index]
            else:
                argv=[sys.executable,'-X','utf8','-B',str(view/'examples/i01/driver.py'),'--watch',
                    '--phase',phase,'--output',str(run/'cases'/phase)]
            result=run_child(run/'processes'/phase,argv,env=env,timeout=240)
            matrix.append(dict(phase=phase,process=result))
            if result['exit_code']!=0 or result['timeout']: raise RuntimeError('frozen phase failed; stop dependent execution')
            if phase=='A01-C01':
                assert load(run/'processes'/phase/'stdout.txt')['resources_verified'] is True
            if phase=='A01-consume':
                receipt=load(run/'processes'/phase/'stdout.txt')
                assert receipt['coverage_eligible'] is False and receipt['full_image_decode']=='OK'
                assert receipt['book_id']=='46007447'
    finally: write(run/'matrix.json',matrix)
    print('I01_AUTHOR_RUN_ENDED; review pending')


if __name__=='__main__': main()
