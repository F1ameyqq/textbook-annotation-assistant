# -*- coding: utf-8 -*-
"""Compile new reviewer code, then one bounded static child. No retry."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
OUT=Path(__file__).resolve().parents[1];ROOT=Path('D:/1800')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
sources=[]
for p in sorted((OUT/'scripts').glob('*.py')):
    b=p.read_bytes();compile(b.decode('utf8',errors='strict'),str(p),'exec')
    sources.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'strict_UTF8_decode':'PASS','compile_only':'PASS'})
write(OUT/'source-preflight.json',{'at_ns':time.time_ns(),'sources':sources,'candidate_imports_or_calls':0,'SQL_connections':0})
d=OUT/'runs/static-review-01';d.mkdir(parents=True,exist_ok=False);entry=OUT/'scripts/review_static.py';body=entry.read_bytes();write(d/'entry-source.py',body)
argv=[sys.executable,'-X','utf8','-B',str(entry)]
write(d/'preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':45,'source_sha256':sha(body),
 'registered_at_ns':time.time_ns(),'source_preflight_sha256':sha((OUT/'source-preflight.json').read_bytes()),'scope':'ONE_STATIC_REVIEW_NO_PRODUCT_CALLS_NO_SQL'})
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
with (d/'stdout.log').open('xb') as stdout,(d/'stderr.log').open('xb') as stderr:
    p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    write(d/'started.json',{'pid':p.pid,'parent_pid':os.getpid(),'started_at_ns':time.time_ns()});timed=False
    try:code=p.wait(timeout=45)
    except subprocess.TimeoutExpired:timed=True;p.kill();code=p.wait()
write(d/'completed.json',{'pid':p.pid,'exit_code':code,'timed_out':timed,'alive':p.poll() is None,'ended_at_ns':time.time_ns(),
 'stdout_sha256':sha((d/'stdout.log').read_bytes()),'stderr_sha256':sha((d/'stderr.log').read_bytes())})
print(json.dumps({'pid':p.pid,'exit_code':code,'timed_out':timed,'alive':p.poll() is None,'functional_calls':0,'SQL_connections':0}))
raise SystemExit(code if not timed else 124)
