"""Process and byte recording only; no candidate behavior replacement."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
CODE = ROOT / 'code'
ENV = dict(os.environ, PYTHONPATH=str(CODE / 'src'), PYTHONIOENCODING='utf-8',
           PYTHONDONTWRITEBYTECODE='1', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')

def run(name, argv, cwd, destination):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    child = subprocess.Popen([str(a) for a in argv], cwd=str(cwd), env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        timed_out = True
        child.kill()
        stdout, stderr = child.communicate()
    destination = Path(destination)
    (destination / (name + '.stdout.txt')).write_bytes(stdout)
    (destination / (name + '.stderr.txt')).write_bytes(stderr)
    record = dict(name=name, argv=[str(a) for a in argv], cwd=str(cwd), pid=child.pid, parent_pid=os.getpid(),
                  started_utc=started, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  exit_code=child.returncode, timed_out=timed_out, process_reaped=child.poll() is not None,
                  environment_overrides={k: ENV[k] for k in ('PYTHONPATH', 'PYTHONIOENCODING', 'PYTHONDONTWRITEBYTECODE', 'GIT_NO_LAZY_FETCH', 'GIT_OPTIONAL_LOCKS')},
                  stdout=dict(file=name + '.stdout.txt', bytes=len(stdout), sha256=sha(stdout)),
                  stderr=dict(file=name + '.stderr.txt', bytes=len(stderr), sha256=sha(stderr)))
    dump(destination / (name + '.process.json'), record)
    return child.returncode, stdout, stderr, record
