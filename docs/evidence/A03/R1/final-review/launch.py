"""One invocation of unchanged fixed batch, with only env/path routing."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('D:/1800-worktrees/a03-r1-final-review-19ab03c8')
OUT=Path(__file__).resolve().parent
PROJECT=ROOT/'route-project'
E=PROJECT/'docs/evidence/A03/R1/final-correction'
FIXED=ROOT/'docs/evidence/A03/R1/final-correction'
CANDIDATE='9992cd8aba10987d25dd0dc0d0874abec02b27ef'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,v):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as f:f.write((json.dumps(v,indent=2)+'\n').encode())
def main():
    assert not(E/'run').exists()and not(OUT/'process').exists(),'Never repeat an existing frozen run'
    checks=json.loads((E/'preparation/checks.json').read_bytes())
    original=json.loads((FIXED/'preparation/checks.json').read_bytes())
    assert 'inputs'not in checks
    checks['inputs']=original['inputs']
    for row in checks['inputs']:
        raw=(ROOT/row['path']).read_bytes()
        assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256']
    # This is new review routing metadata, never an edit to the frozen input.
    (E/'preparation/checks.json').write_bytes((json.dumps(checks,indent=2)+'\n').encode())
    argv=[sys.executable,'-X','utf8','-B',str(ROOT/'examples/a03/R1/final.py'),'--batch','--candidate',CANDIDATE]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',A03_R1_PROJECT=str(PROJECT))
    frozen={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'examples/a03/R1').glob('*.py')}
    frozen['review-routing-wrapper:launch.py']=sha(Path(__file__).resolve())
    frozen['review-routing-checks']=sha(E/'preparation/checks.json')
    write(OUT/'preregistered.json',dict(candidate=CANDIDATE,final_delivery='19ab03c849bfab3dcde2dc86be37c59f3add1ebe',
        product='6097a06de937fee8876feccedf46920510850b83',argv=argv,cwd=str(ROOT),env_overrides=dict(PYTHONPATH=env['PYTHONPATH'],A03_R1_PROJECT=str(PROJECT)),
        frozen_driver_and_wrapper_sha256=frozen,child_seconds=180,parent_seconds=240,
        aggregate_recorder_seconds=2500,phases=['L2','L3-execute','L3-reconcile','L3-second','G6-first','G6-reopen','L4','G2-G3','G5','F'],
        new_targets_upper=2,dispatch_upper=3,new_M_L1_G4_legacy_business=0,no_repair_or_retry=True))
    process=OUT/'process';process.mkdir()
    begin=time.monotonic()
    with(process/'stdout.txt').open('xb')as stdout,(process/'stderr.txt').open('xb')as stderr:
        p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
        write(process/'started.json',dict(pid=p.pid,argv=argv,started_at_ns=time.time_ns()))
        timeout=False
        try:p.wait(timeout=2500)
        except subprocess.TimeoutExpired:
            timeout=True;p.kill();p.wait(timeout=10)
    result=dict(pid=p.pid,exit_code=p.returncode,waited=True,alive=p.poll()is None,timeout=timeout,
        wall_seconds=time.monotonic()-begin,stdout_sha256=sha(process/'stdout.txt'),stderr_sha256=sha(process/'stderr.txt'))
    write(process/'completed.json',result)
    print(json.dumps(result))
    sys.exit(1 if timeout else p.returncode)

if __name__=='__main__':main()
