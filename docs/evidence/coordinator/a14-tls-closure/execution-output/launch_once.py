"""Retain the exact wrapper handle through OS exit; never relaunch."""
import json
from pathlib import Path
import subprocess
import sys
import time
import tls_wrapper as w

def main():
    intent = json.loads((w.PUBLIC / 'launch-intent.json').read_text(encoding='utf-8'))
    w.save(w.PRIVATE / 'launch-claim.json', {'at': w.utc(), 'thread_id': w.THREAD_ID,
                                          'handshake_limit': 1, 'restart_allowed': False,
                                          'intent_sha256': w.digest(w.PUBLIC / 'launch-intent.json')['sha256']})
    for path, expected in intent['bindings'].items():
        if w.digest(path) != expected:
            raise ValueError('FROZEN_BINDING_MISMATCH')
    if w.proxy_metadata() != intent['proxy']:
        raise ValueError('FROZEN_PROXY_MISMATCH')
    record = {'thread_id': w.THREAD_ID, 'wrapper_launches': 1, 'shell': False,
              'started_utc': w.utc(), 'budget_seconds': 22, 'timeout': False}
    with (w.PRIVATE / 'wrapper.stdout.bin').open('xb') as out, (w.PRIVATE / 'wrapper.stderr.bin').open('xb') as err:
        t0 = time.perf_counter()
        p = subprocess.Popen([sys.executable, '-B', str(w.PUBLIC / 'tls_wrapper.py'), str(t0)],
                             shell=False, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                             close_fds=True, cwd=str(w.PRIVATE), env=w.safe_env(),
                             creationflags=subprocess.CREATE_NO_WINDOW)
        record.update({'pid': p.pid, 'handle': int(p._handle), 'creation': w.times(p._handle)})
        try:
            p.wait(timeout=max(0, t0 + 22 - time.perf_counter()))
        except subprocess.TimeoutExpired:
            record['timeout'] = True
            record['exit_status'] = 'UNKNOWN_AT_22_SECOND_DEADLINE_NO_RESTART'
        record['exit_code'] = p.poll()
        record['exit'] = w.times(p._handle)
        record['wait_signaled'] = w.K32.WaitForSingleObject(w.wintypes.HANDLE(int(p._handle)), 0) == 0
        record['elapsed_ms_to_wrapper_observed_exit'] = round((time.perf_counter() - t0) * 1000, 3)
        ph = int(p._handle)
        p._handle.Close()
        record['handle_close_called'] = True
        record['handle_post_close'] = w.invalid_handle(ph)
    record['redirect_files_closed'] = out.closed and err.closed
    record['wrapper_stdout'] = w.digest(w.PRIVATE / 'wrapper.stdout.bin')
    record['wrapper_stderr'] = w.digest(w.PRIVATE / 'wrapper.stderr.bin')
    record['finished_utc'] = w.utc()
    w.save(w.PUBLIC / 'wrapper-os-release.json', record)
    print(json.dumps({'wrapper_exit_code': record['exit_code'], 'wrapper_timeout': record['timeout'],
                      'wrapper_elapsed_ms': record['elapsed_ms_to_wrapper_observed_exit']}))
    return 0 if record['exit_code'] == 0 and not record['timeout'] else 2

if __name__ == '__main__':
    sys.exit(main())
