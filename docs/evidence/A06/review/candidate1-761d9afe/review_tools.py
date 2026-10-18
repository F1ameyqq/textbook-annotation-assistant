"""Record independent synchronous subprocesses without replacing candidate logic."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
CODE = ROOT / 'code'
ENV = dict(os.environ, PYTHONPATH=str(CODE / 'src'), PYTHONIOENCODING='utf-8',
           PYTHONDONTWRITEBYTECODE='1', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')

def run(name, argv, cwd, destination):
    destination = Path(destination)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    process = subprocess.Popen([str(v) for v in argv], cwd=str(cwd), env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(timeout=180)
    (destination / (name + '.stdout.txt')).write_bytes(stdout)
    (destination / (name + '.stderr.txt')).write_bytes(stderr)
    record = dict(name=name, argv=[str(v) for v in argv], cwd=str(cwd), parent_pid=os.getpid(), pid=process.pid,
                  started_utc=started, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  exit_code=process.returncode, process_reaped=process.poll() is not None,
                  environment_overrides={k: ENV[k] for k in ('PYTHONPATH', 'PYTHONIOENCODING', 'PYTHONDONTWRITEBYTECODE', 'GIT_NO_LAZY_FETCH', 'GIT_OPTIONAL_LOCKS')},
                  stdout=dict(file=name + '.stdout.txt', bytes=len(stdout), sha256=sha(stdout)),
                  stderr=dict(file=name + '.stderr.txt', bytes=len(stderr), sha256=sha(stderr)))
    dump(destination / (name + '.process.json'), record)
    return process.returncode, stdout, stderr, record
