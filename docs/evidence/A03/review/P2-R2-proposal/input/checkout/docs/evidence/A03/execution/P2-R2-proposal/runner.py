"""Only new offline static scripts; durable streams precede owned child start."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
label, mode = sys.argv[1:]
scripts = {'freeze': OUT/'freeze_inputs.py', 'author': ROOT/'examples/a03/P2-R2-proposal/author.py',
           'check': ROOT/'examples/a03/P2-R2-proposal/check.py', 'verify': OUT/'verify.py', 'seal': OUT/'prepare_seal.py'}
assert mode in scripts and label.replace('-', '').isalnum()
directory = OUT/'runs'/label
directory.mkdir(parents=True, exist_ok=False)
command = [sys.executable, '-X', 'utf8', '-B', str(scripts[mode])]
record = {'command': command, 'cwd': str(ROOT), 'pre_registered_at': datetime.now(timezone.utc).isoformat(),
          'script_sha256': hashlib.sha256(scripts[mode].read_bytes()).hexdigest(),
          'scope': 'NEW_STATIC_ONLY', 'budget_seconds': 60, 'product_runs': 0, 'native_sessions': 0}
(directory/'registration.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
(directory/'registered-script.py').write_bytes(scripts[mode].read_bytes())
if mode=='check':
    for name in ('schema_check.py','oracle_verifier.py'):
        (directory/name).write_bytes((scripts[mode].parent/name).read_bytes())
child = None
code = 1
started = time.monotonic()
with (directory/'stdout.txt').open('xb') as stdout, (directory/'stderr.txt').open('xb') as stderr:
    try:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        record['owned_pid'] = child.pid
        (directory/'started.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
        code = child.wait(timeout=60)
    except BaseException as error:
        stderr.write((repr(error)+'\n').encode('utf8')); stderr.flush()
        record['exception'] = repr(error)
        if child is not None and child.poll() is None:
            child.kill(); child.wait(timeout=5)
    finally:
        record.update(exit_code=code, owned_child_alive=bool(child is not None and child.poll() is None),
                      elapsed_seconds=time.monotonic()-started, completed_at=datetime.now(timezone.utc).isoformat(),
                      background_tasks=0, native_sessions=0, stdout='stdout.txt', stderr='stderr.txt')
        (directory/'exit.json').write_bytes(json.dumps(record,indent=2).encode()+b'\n')
if mode=='seal' and code==0:
    releases=[]
    for run in sorted((OUT/'runs').iterdir()):
        value=json.loads((run/'exit.json').read_bytes())
        assert not value['owned_child_alive'] and value['native_sessions']==0
        releases.append({'run':run.name,'owned_pid':value['owned_pid'],'exit_code':value['exit_code'],'alive':False,
                         'stdout_sha256':hashlib.sha256((run/'stdout.txt').read_bytes()).hexdigest(),
                         'stderr_sha256':hashlib.sha256((run/'stderr.txt').read_bytes()).hexdigest()})
    with (OUT/'process-release.json').open('xb')as f:
        f.write(json.dumps({'status':'ALL_OWNED_STATIC_CHILDREN_EXITED','runs':releases,'background_tasks':0,'native_sessions':0,
            'scope':'owned synchronized children only; no all-system scan','seal_parent':'returns immediately after manifest; no background child'},indent=2).encode()+b'\n')
    report=ROOT/'docs/tasks/A03-P2-R2-proposal-delivery.md';manifest=OUT/'sha256-manifest.json'
    paths=[report]+[p for root in (OUT,ROOT/'examples/a03/P2-R2-proposal')for p in root.rglob('*')if p.is_file()and p!=manifest]
    entries=[]
    for p in sorted(paths):
        raw=p.read_bytes();entries.append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    with manifest.open('xb')as f:
        f.write(json.dumps({'format_version':'a03-p2-r2-proposal-manifest-1','status':'REVIEW_STATIC_UNIMPLEMENTED',
          'base':'7fdbde8f16569fd3bc399013115e13269d5d33fa','workflow':'d834bf531f95abac7ed30b89b3ca55105fa6f491',
          'excluded_only':[manifest.relative_to(ROOT).as_posix()],'files':entries},ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    record['frozen_entries']=len(entries);record['manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
print(json.dumps(record)); sys.exit(code)
