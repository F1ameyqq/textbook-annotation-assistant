# -*- coding: utf-8 -*-
"""Single-use exact R10 driver launch with frozen source and fail-stop order."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone
import uuid
from evidence import OUT,WORK,EV,load,sha,write
group=sys.argv[1];assert group in ('C1','C2')
assert load(OUT/'static-review.json')['status']=='READY_FOR_C1_THEN_C2_ONCE'
if group=='C2':assert load(OUT/'result-C1.json')['exit_code']==0
seed=load(OUT/'isolated-source-index.json')['files'];assert len(seed)==76
for r in seed:assert sha((OUT/r['file']).read_bytes())==r['sha256'] and (OUT/r['file']).stat().st_size==r['bytes']
driver=WORK/'tests/test_a03_p2_r10_owner_fencing.py';registration=load(OUT/'driver-preregistration.json');body=driver.read_bytes();assert sha(body)==registration['driver_sha256']
if group=='C1':
    assert not (WORK/EV/'validation').exists() and not list(WORK.rglob('*.sqlite3'))
    run_id='review-r10-'+uuid.uuid4().hex[:12];root=WORK/EV/'validation'/run_id
    write(OUT/'independent-run.json',{'run_id':run_id,'workspace':str(WORK),'run_root':str(root),'author_DB_or_validation_copied':False,'groups_once':['C1','C2']})
else:root=Path(load(OUT/'independent-run.json')['run_root'])
assert not (root/'cases'/group).exists()
d=OUT/'runs'/('independent-'+group.lower()+'-01');d.mkdir(exist_ok=False);(d/'entry-source.py').write_bytes(body)
argv=[sys.executable,'-X','utf8','-B',str(driver),group,'--output-root',root.relative_to(WORK).as_posix()]
env=dict(os.environ);env['PYTHONPATH']=str(WORK/'src');env['PYTHONDONTWRITEBYTECODE']='1'
write(d/'registration.json',{'argv':argv,'cwd':str(WORK),'timeout_seconds':90,'entry_sha256':sha(body),'entry_snapshot':'entry-source.py',
 'registered_at':datetime.now(timezone.utc).isoformat(),'input_index_sha256':sha((OUT/'input-index.json').read_bytes()),
 'source_index_sha256':sha((OUT/'isolated-source-index.json').read_bytes()),'driver_registration_sha256':sha((OUT/'driver-preregistration.json').read_bytes()),
 'group':group,'functional_round':1,'expected':registration['expected'][group],'product_clock_PID_or_limits_modified':False})
begin=time.monotonic();timed=False
with (d/'stdout.log').open('xb') as stdout,(d/'stderr.log').open('xb') as stderr:
    p=subprocess.Popen(argv,cwd=WORK,env=env,stdout=stdout,stderr=stderr)
    write(d/'started.json',{'pid':p.pid,'started_at':datetime.now(timezone.utc).isoformat()})
    try:code=p.wait(timeout=90)
    except subprocess.TimeoutExpired:timed=True;p.kill();code=p.wait()
write(d/'completion.json',{'argv':argv,'cwd':str(WORK),'pid':p.pid,'exit_code':code,'timed_out':timed,'alive_after_wait':p.poll() is None,
 'elapsed_seconds':round(time.monotonic()-begin,3),'finished_at':datetime.now(timezone.utc).isoformat(),'stdout':'stdout.log','stderr':'stderr.log'})
assert all(sha((OUT/r['file']).read_bytes())==r['sha256'] for r in seed)
if code==0 and not timed:
    result=load(root/(group+'-result.json'));assert result['final_state']['target']['counts']['effects']==0 and result['final_state']['book']['phase']=='RELEASED'
    write(OUT/('result-'+group+'.json'),{'group':group,'exit_code':0,'functional_rounds':1,'pid':p.pid,'run_root':str(root),
      'result':result,'other_groups_replayed':False,'parent_stdout_sha256':sha((d/'stdout.log').read_bytes()),'parent_stderr_sha256':sha((d/'stderr.log').read_bytes())})
print(json.dumps({'group':group,'pid':p.pid,'exit_code':code,'timed_out':timed,'alive':p.poll() is None,'run_root':str(root)}))
raise SystemExit(code if not timed else 124)
