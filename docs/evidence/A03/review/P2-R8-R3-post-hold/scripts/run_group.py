# -*- coding: utf-8 -*-
"""Single-use exact-group launcher. Prerequisites are recorded, no retries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone
import uuid
from evidence import OUT,WORK,EV,load,sha,write
phase=sys.argv[1];phases=('local','N1','N2','N3','N4','N5');assert phase in phases
assert load(OUT/'static-review.json')['status']=='STATIC_READY_FOR_BOUNDED_LOCAL_N1_N2_N3_N4_N5'
for predecessor in phases[:phases.index(phase)]:assert load(OUT/('result-'+predecessor+'.json'))['successful']
directory=OUT/'runs'/('independent-'+phase.lower()+'-01');directory.mkdir(exist_ok=False)
seed=load(OUT/'isolated-source-index.json')
for r in seed['files']:assert sha((OUT/r['file']).read_bytes())==r['sha256']
if phase=='local':
    assert not (WORK/EV/'validation').exists()
    run_id='review-r3-'+uuid.uuid4().hex[:12];run_root=WORK/EV/'validation'/run_id
    write(OUT/'independent-run.json',{'run_id':run_id,'workspace':str(WORK),'run_root':str(run_root),
      'author_validation_or_databases_copied':False,'allowed_phases':list(phases),'seed_files':len(seed['files'])})
else:
    identity=load(OUT/'independent-run.json');run_id=identity['run_id'];run_root=Path(identity['run_root'])
entry=OUT/'scripts/group_entry.py';body=entry.read_bytes();(directory/'entry-source.py').write_bytes(body)
limit=120 if phase=='N2' else 60
argv=[sys.executable,'-X','utf8','-B',str(entry),phase]
env=dict(os.environ);env['PYTHONPATH']=str(WORK/'src');env['PYTHONDONTWRITEBYTECODE']='1';env['A03_R8_R3_RUN_ID']=run_id
write(directory/'registration.json',{'argv':argv,'cwd':str(WORK),'timeout_seconds':limit,'entry_sha256':sha(body),'entry_snapshot':'entry-source.py',
 'registered_at':datetime.now(timezone.utc).isoformat(),'input_index_sha256':sha((OUT/'input-index.json').read_bytes()),
 'source_index_sha256':sha((OUT/'isolated-source-index.json').read_bytes()),'PYTHONPATH':str(WORK/'src'),'run_id':run_id,'phase':phase,
 'product_clock_or_deadline_modified':False,'functional_round':1})
start=time.monotonic();timed=False
with (directory/'stdout.log').open('xb') as stdout,(directory/'stderr.log').open('xb') as stderr:
    process=subprocess.Popen(argv,cwd=WORK,env=env,stdout=stdout,stderr=stderr)
    write(directory/'started.json',{'pid':process.pid,'started_at':datetime.now(timezone.utc).isoformat()})
    try:code=process.wait(timeout=limit)
    except subprocess.TimeoutExpired:timed=True;process.kill();code=process.wait()
write(directory/'completion.json',{'argv':argv,'cwd':str(WORK),'pid':process.pid,'exit_code':code,'timed_out':timed,
 'alive_after_wait':process.poll() is None,'elapsed_seconds':round(time.monotonic()-start,3),'finished_at':datetime.now(timezone.utc).isoformat(),
 'stdout':'stdout.log','stderr':'stderr.log'})
assert all(sha((OUT/r['file']).read_bytes())==r['sha256'] for r in seed['files'])
print(json.dumps({'phase':phase,'pid':process.pid,'exit_code':code,'timed_out':timed,'alive':process.poll() is None,'run_id':run_id}))
raise SystemExit(code if not timed else 124)
