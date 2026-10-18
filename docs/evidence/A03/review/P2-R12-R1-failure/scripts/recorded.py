# -*- coding: utf-8 -*-
"""Compile new analysis code first, preserve actual streams and a bounded wait."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path('D:/1800');OUT=Path(__file__).resolve().parents[1]
tag,entry=sys.argv[1:];p=Path(entry).resolve();assert p.is_relative_to(OUT)
d=OUT/'runs'/tag;d.mkdir(parents=True,exist_ok=False);b=p.read_bytes();compile(b.decode('utf8',errors='strict'),str(p),'exec')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,v):
    with (d/name).open('xb') as f:f.write(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
write('entry-source.py',b);argv=[sys.executable,'-X','utf8','-B',str(p)]
write('preregistered.json',{'argv':argv,'cwd':str(ROOT),'timeout_seconds':60,'source_sha256':sha(b),'registered_at_ns':time.time_ns(),
 'new_source_UTF8_decode_compile':'PASS','functional_calls_authorized':0})
env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
with (d/'stdout.log').open('xb') as stdout,(d/'stderr.log').open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    write('started.json',{'pid':child.pid,'started_at_ns':time.time_ns()});timed=False
    try:code=child.wait(timeout=60)
    except subprocess.TimeoutExpired:timed=True;child.kill();code=child.wait()
write('completed.json',{'pid':child.pid,'exit_code':code,'alive':child.poll() is None,'timed_out':timed,'ended_at_ns':time.time_ns(),
 'stdout_sha256':sha((d/'stdout.log').read_bytes()),'stderr_sha256':sha((d/'stderr.log').read_bytes())})
print(json.dumps({'run':tag,'pid':child.pid,'exit_code':code,'timed_out':timed,'alive':child.poll() is None}))
raise SystemExit(code if not timed else 124)
