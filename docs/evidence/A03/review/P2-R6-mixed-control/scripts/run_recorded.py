"""Synchronous bounded reviewer runs; streams opened before spawn, no background jobs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parents[1]
ROOT=Path('D:/1800')
tag,timeout_text,script,*args=sys.argv[1:]
assert tag.replace('-','').isalnum()
directory=OUT/'runs'/tag;directory.mkdir(parents=True,exist_ok=False)
target=Path(script).resolve();assert target.is_relative_to(OUT)
raw=target.read_bytes();(directory/'entry-source.py').write_bytes(raw)
argv=[sys.executable,'-X','utf8','-B',str(target),*args]
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
def write(name,value):
    with (directory/name).open('x',encoding='utf8',newline='\n')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
write('registration.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':float(timeout_text),
 'entry_sha256':hashlib.sha256(raw).hexdigest(),'entry_snapshot':'entry-source.py',
 'registered_at':datetime.now(timezone.utc).isoformat(),'PYTHONPATH':'removed','PYTHONDONTWRITEBYTECODE':'1'})
t=time.monotonic();timed_out=False
with (directory/'stdout.log').open('xb')as stdout,(directory/'stderr.log').open('xb')as stderr:
    proc=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    write('started.json',{'pid':proc.pid,'started_at':datetime.now(timezone.utc).isoformat()})
    try:code=proc.wait(timeout=float(timeout_text))
    except subprocess.TimeoutExpired:
        timed_out=True;proc.kill();code=proc.wait()
write('completion.json',{'argv':argv,'cwd':str(ROOT),'pid':proc.pid,'exit_code':code,
 'timed_out':timed_out,'alive_after_wait':proc.poll()is None,'elapsed_seconds':round(time.monotonic()-t,3),
 'finished_at':datetime.now(timezone.utc).isoformat(),'stdout':'stdout.log','stderr':'stderr.log'})
print(json.dumps({'tag':tag,'pid':proc.pid,'exit_code':code,'timed_out':timed_out,'alive':proc.poll()is None}))
sys.exit(code if not timed_out else 124)
