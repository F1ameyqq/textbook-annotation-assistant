"""Bounded, preregistered native read subprocess. Retries are always zero."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def _write(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def observe_native_bounded(observer, *, read_fault=None, timeout=2):
    from annotation.runtime.storage.common import unique, plain
    folder = observer.directory / 'process-audit' / unique('read')
    folder.mkdir(parents=True, exist_ok=False)
    request = {'descriptor': plain(observer.descriptor), 'target_dir': str(observer.directory),
        'observation_id': unique('native-observation'), 'read_fault': read_fault}
    _write(folder / 'request.json', request)
    argv = [sys.executable, '-X', 'utf8', '-B', '-m', 'annotation.runtime.recovery.native_observation', str(folder / 'request.json')]
    _write(folder / 'preregistered.json', {'argv': argv, 'cwd': os.getcwd(), 'timeout_seconds': timeout,
        'input_sha256': hashlib.sha256((folder / 'request.json').read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'retries': 0})
    with (folder / 'script-snapshot.py').open('xb') as stream:
        stream.write(Path(__file__).read_bytes())
    started = time.monotonic()
    forced = False
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
        _write(folder / 'started.json', {'pid': process.pid, 'parent_pid': os.getpid()})
        try:
            code = process.wait(timeout=max(.01, timeout - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            forced = True
            process.kill()
            code = process.wait(timeout=5)
    elapsed = time.monotonic() - started
    _write(folder / 'completed.json', {'pid': process.pid, 'exit_code': code, 'alive': process.poll() is None,
        'timeout': forced, 'elapsed_seconds': elapsed})
    result = {'ok': False, 'code': 'TARGET_READ_TIMEOUT' if forced else 'TARGET_READ_FAILED'}
    if code == 0 and not forced:
        result = json.loads((folder / 'stdout.txt').read_bytes())
    result.update(read_elapsed_seconds=elapsed, process_pid=process.pid, process_exit_code=code,
        process_reaped=process.poll() is not None, forced_termination=forced, process_audit_path=str(folder))
    return result


def worker(path):
    from annotation.runtime.storage.native_target import NativeTargetSession
    request = json.loads(Path(path).read_bytes())
    descriptor = request['descriptor']
    observer = NativeTargetSession.open(request['target_dir'], expected_store_id=descriptor['store_id'],
        expected_target_session_id=descriptor['target_session_id'], expected_target_key=descriptor['target_key'],
        expected_scope_id=descriptor['fixed_scope_id'], expected_source_ref=descriptor['fixed_source_ref'])
    observation = observer.observe_target(descriptor['target_key'], observation_id=request['observation_id'], read_fault=request['read_fault'])
    print(json.dumps({'ok': True, 'observation': observation, 'pid': os.getpid()}))


if __name__ == '__main__':
    worker(sys.argv[1])
