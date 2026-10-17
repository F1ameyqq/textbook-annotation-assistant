# -*- coding: utf-8 -*-
"""Single-use bounded N1 launcher, preregistered before starting the real test parent."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone
import uuid
from evidence import OUT,WORK,EV,load,sha,write
assert load(OUT/'static-review.json')['status']=='STATIC_READY_FOR_ONE_INDEPENDENT_N1'
assert load(OUT/'author-boundary-review.json')['status']=='FORMAL_N1_BOUNDARIES_VERIFIED'
directory=OUT/'runs/independent-n1-01';directory.mkdir(exist_ok=False)
seed=load(OUT/'isolated-source-index.json')
for row in seed['files']:assert sha((OUT/row['file']).read_bytes())==row['sha256']
assert not (WORK/EV/'validation').exists()
run_id='review-n1-'+uuid.uuid4().hex[:12];run_root=WORK/EV/'validation'/run_id
entry=OUT/'scripts/n1_entry.py';body=entry.read_bytes();(directory/'entry-source.py').write_bytes(body)
argv=[sys.executable,'-X','utf8','-B',str(entry)]
env=dict(os.environ);env['PYTHONPATH']=str(WORK/'src');env['PYTHONDONTWRITEBYTECODE']='1';env['A03_R8_R2_RUN_ID']=run_id
write(directory/'registration.json',{'argv':argv,'cwd':str(WORK),'timeout_seconds':60,'entry_sha256':sha(body),
 'entry_snapshot':'entry-source.py','registered_at':datetime.now(timezone.utc).isoformat(),
 'input_index_sha256':sha((OUT/'input-index.json').read_bytes()),'isolated_source_index_sha256':sha((OUT/'isolated-source-index.json').read_bytes()),
 'PYTHONPATH':str(WORK/'src'),'run_id':run_id,'test':'R8R2NativeBridgeTests.test_N1','fresh_validation_root_absent_before_spawn':True})
write(OUT/'independent-run.json',{'run_id':run_id,'workspace':str(WORK),'run_root':str(run_root),'case':str(run_root/'cases/N1'),
 'fixture_source':'exact fixed target bytes','author_success_databases_or_validation_copied':False,'parent_record':'runs/independent-n1-01'})
start=time.monotonic();timed=False
with (directory/'stdout.log').open('xb') as stdout,(directory/'stderr.log').open('xb') as stderr:
    process=subprocess.Popen(argv,cwd=WORK,env=env,stdout=stdout,stderr=stderr)
    write(directory/'started.json',{'pid':process.pid,'started_at':datetime.now(timezone.utc).isoformat()})
    try:code=process.wait(timeout=60)
    except subprocess.TimeoutExpired:timed=True;process.kill();code=process.wait()
write(directory/'completion.json',{'argv':argv,'cwd':str(WORK),'pid':process.pid,'exit_code':code,'timed_out':timed,
 'alive_after_wait':process.poll() is None,'elapsed_seconds':round(time.monotonic()-start,3),
 'finished_at':datetime.now(timezone.utc).isoformat(),'stdout':'stdout.log','stderr':'stderr.log'})
preserved=[]
for row in seed['files']:
    actual=sha((OUT/row['file']).read_bytes());assert actual==row['sha256'];preserved.append({'file':row['file'],'sha256':actual})
write(OUT/'independent-input-preservation.json',{'all_seed_files_unchanged':True,'files':preserved,'candidate_rounds':1})
print(json.dumps({'run_id':run_id,'pid':process.pid,'exit_code':code,'timed_out':timed,'alive':process.poll() is None}))
raise SystemExit(code if not timed else 124)
