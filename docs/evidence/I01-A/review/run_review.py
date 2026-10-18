"""One-shot external recorder for the unchanged frozen I01 entry point."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('D:/1800-i01-review-01a14e1c')
OUT = Path('D:/1800/docs/evidence/I01-A/review')
CANDIDATE = 'be68b8d7c645de556d601458d1d493258f063721'

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write((json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+'\n').encode())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', I01_PROJECT=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
    assert not (ROOT/'docs/evidence/I01-A/execution/run').exists()
    argv = [sys.executable, '-X', 'utf8', '-B', 'examples/i01/run.py', '--candidate', CANDIDATE]
    identities = []
    for tag in ('N','E','U'):
        fixture = ROOT/'tests/fixtures/i01'/tag/'initial.json'
        bundle = json.loads(fixture.read_bytes())
        source, evidence, graph, snapshot = bundle['artifacts']
        folder = ROOT/'docs/evidence/I01-A/execution/run/cases'/('U-execute' if tag=='U' else tag)
        identities.append(dict(path=tag, book_id=source['book_id'], scope_id=source['scope_id'], target_id=snapshot['payload']['target_id'], ledger_id='ledger-I01-'+tag, target_store_id='store-I01-'+tag, target_session_id='session-I01-'+tag, anchor=str(folder/'anchor.json'), runtime_directory=str(folder/'runtime'), target_directory=str(folder/'target'), input_sha256=sha(fixture.read_bytes()), input_bytes=len(fixture.read_bytes()), source=source['content_hash'], evidence=evidence['content_hash'], graph=graph['content_hash'], qualified_namespace=str(ROOT)))
        assert not folder.exists()
    freeze = dict(candidate=CANDIDATE, argv=argv, cwd=str(ROOT), GIT_NO_LAZY_FETCH=1, target_upper=3, dispatch_upper=3, worker_seconds=180, phase_parent_seconds=240, phases=['A01-C01','A01-consume','N','E','U-execute','U-recover'], identity_routing=identities, identity_note='Frozen fixture labels and driver identifiers retained byte-exact; independent identity is bound to this new anchor/state/target directory namespace. No author database is copied or opened.', policy='Unchanged frozen driver and product; stop on first business failure; no retry', at_ns=time.time_ns())
    save(OUT/'independent-invocation.json', freeze)
    started = time.monotonic()
    record = OUT/'top-level'
    record.mkdir(exist_ok=False)
    with (record/'stdout.txt').open('xb') as stdout, (record/'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        save(record/'started.json', dict(pid=process.pid, parent_pid=os.getpid(), at_ns=time.time_ns(), argv=argv, cwd=str(ROOT)))
        timeout = False
        try:
            code = process.wait(timeout=1500)
        except subprocess.TimeoutExpired:
            timeout=True
            terminated = subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], capture_output=True)
            save(record/'termination.json',dict(exit_code=terminated.returncode,stdout=terminated.stdout.decode('utf8','replace'),stderr=terminated.stderr.decode('utf8','replace')))
            code=process.wait(timeout=5)
        creation, ended, kernel, user = (wintypes.FILETIME() for _ in range(4))
        gettimes = ctypes.WinDLL('kernel32', use_last_error=True).GetProcessTimes
        gettimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        assert gettimes(wintypes.HANDLE(int(process._handle)),ctypes.byref(creation),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user))
        ticks=lambda t:(t.dwHighDateTime<<32)|t.dwLowDateTime
        result=dict(pid=process.pid,exit_code=code,timeout=timeout,waited=True,alive=process.poll() is None,wall_seconds=time.monotonic()-started,cpu_seconds=(ticks(kernel)+ticks(user))/10000000,creation_filetime=ticks(creation),exit_filetime=ticks(ended),completed_ns=time.time_ns())
        save(record/'completed.json',result)
    print(json.dumps(result))
    return code

if __name__=='__main__':
    sys.exit(main())
