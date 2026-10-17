"""Append-only bounded coordinator process recorder; environment not serialized."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

base=Path(__file__).resolve().parent
name=sys.argv[1]; script=Path(sys.argv[2]).resolve(); limit=int(sys.argv[3])
root=Path('D:/1800'); out=base/'runs'/name
out.mkdir(parents=True,exist_ok=False)
def now(): return datetime.now(timezone.utc).isoformat()
def write(name,data): (out/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
argv=[sys.executable,'-B',str(script)]+sys.argv[4:]
raw=script.read_bytes(); (out/'entry-source.py').write_bytes(raw)
write('registration.json',dict(argv=argv,cwd=str(root),timeout_seconds=limit,script_sha256=hashlib.sha256(raw).hexdigest(),registered_at=now(),environment='not serialized; PYTHONPATH removed and bytecode disabled'))
env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
started=time.monotonic(); timed_out=False
with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
    p=subprocess.Popen(argv,cwd=root,env=env,stdout=stdout,stderr=stderr)
    write('started.json',dict(pid=p.pid,started_at=now()))
    try: code=p.wait(timeout=limit)
    except subprocess.TimeoutExpired:
        timed_out=True;p.kill();code=p.wait(timeout=15)
write('completion.json',dict(argv=argv,cwd=str(root),pid=p.pid,exit_code=code,timed_out=timed_out,alive_after_wait=p.poll() is None,elapsed_seconds=round(time.monotonic()-started,3),finished_at=now(),stdout_sha256=hashlib.sha256((out/'stdout.log').read_bytes()).hexdigest(),stderr_sha256=hashlib.sha256((out/'stderr.log').read_bytes()).hexdigest()))
print(json.dumps(dict(run=name,exit_code=code,timed_out=timed_out,elapsed_seconds=round(time.monotonic()-started,3))))
raise SystemExit(code)
