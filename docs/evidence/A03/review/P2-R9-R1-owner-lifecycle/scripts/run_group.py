# -*- coding: utf-8 -*-
"""One exclusive invocation per approved group; fail-closed prerequisites."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone
import uuid
from evidence import OUT,WORK,EV,load,sha,write
group=sys.argv[1];groups=('D1','standalone','borrow','D2');assert group in groups
assert load(OUT/'static-review.json')['status']=='READY_FOR_FOUR_BOUNDED_GROUPS_ONCE'
for previous in groups[:groups.index(group)]:assert load(OUT/('result-'+previous+'.json'))['exit_code']==0
own=load(OUT/'independent-driver.json');script=OUT/own['file'];assert sha(script.read_bytes())==own['sha256']
seed=load(OUT/'isolated-source-index.json')['files']+[{'file':own['file'],'bytes':own['bytes'],'sha256':own['sha256'],'path':script.relative_to(WORK).as_posix(),'role':'new reviewer-owned driver, explicit allowed changes'}]
for r in seed:assert len((OUT/r['file']).read_bytes())==r['bytes'] and sha((OUT/r['file']).read_bytes())==r['sha256']
if group=='D1':
    assert not (WORK/EV/'validation').exists() and not list(WORK.rglob('*.sqlite3'))
    run_id='review-owner-r1-'+uuid.uuid4().hex[:12];root=WORK/EV/'validation'/run_id
    write(OUT/'independent-run.json',{'run_id':run_id,'workspace':str(WORK),'run_root':str(root),'author_DB_or_validation_copied':False,'allowed_groups':list(groups)})
    write(OUT/'review-source-index.json',{'files':seed,'source_package_files':68,'frozen_seed_files':77,'reviewer_driver_files':1})
else:root=Path(load(OUT/'independent-run.json')['run_root'])
assert not (root/'cases'/group).exists()
d=OUT/'runs'/('independent-'+group.lower()+'-01');d.mkdir(exist_ok=False);entry=script.read_bytes();(d/'entry-source.py').write_bytes(entry)
argv=[sys.executable,'-X','utf8','-B',str(script),group,'--output-root',root.relative_to(WORK).as_posix()]
env=dict(os.environ);env['PYTHONPATH']=str(WORK/'src');env['PYTHONDONTWRITEBYTECODE']='1'
write(d/'registration.json',{'argv':argv,'cwd':str(WORK),'timeout_seconds':90,'entry_sha256':sha(entry),'entry_snapshot':'entry-source.py',
 'registered_at':datetime.now(timezone.utc).isoformat(),'input_index_sha256':sha((OUT/'input-index.json').read_bytes()),
 'source_index_sha256':sha((OUT/'review-source-index.json').read_bytes()),'driver_registration_sha256':sha((OUT/'independent-driver.json').read_bytes()),
 'group':group,'functional_round':1,'product_clock_or_deadline_modified':False,'expected_read_limit':own['expected_read_limit']})
start=time.monotonic();timed=False
with (d/'stdout.log').open('xb') as stdout,(d/'stderr.log').open('xb') as stderr:
    p=subprocess.Popen(argv,cwd=WORK,env=env,stdout=stdout,stderr=stderr)
    write(d/'started.json',{'pid':p.pid,'started_at':datetime.now(timezone.utc).isoformat()})
    try:code=p.wait(timeout=90)
    except subprocess.TimeoutExpired:timed=True;p.kill();code=p.wait()
completion={'argv':argv,'cwd':str(WORK),'pid':p.pid,'exit_code':code,'timed_out':timed,'alive_after_wait':p.poll() is None,
 'elapsed_seconds':round(time.monotonic()-start,3),'finished_at':datetime.now(timezone.utc).isoformat(),'stdout':'stdout.log','stderr':'stderr.log'}
write(d/'completion.json',completion)
assert all(sha((OUT/r['file']).read_bytes())==r['sha256'] for r in seed)
if code==0 and not timed:
    result=load(root/(group+'-result.json'));assert result['group']==group
    write(OUT/('result-'+group+'.json'),{'group':group,'exit_code':0,'functional_rounds':1,'run_root':str(root),
      'pid':p.pid,'result':result,'parent_stdout_sha256':sha((d/'stdout.log').read_bytes()),'parent_stderr_sha256':sha((d/'stderr.log').read_bytes()),
      'other_groups_or_prior_R3_R4_replayed':False})
print(json.dumps({'group':group,'pid':p.pid,'exit_code':code,'timed_out':timed,'alive':p.poll() is None,'run_root':str(root)}))
raise SystemExit(code if not timed else 124)
