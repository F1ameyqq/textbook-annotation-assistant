"""A13 exact single frozen product launch. No behavior pre-run is permitted."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path('D:/1800-worktrees/a13-reuse-observation')
OUT = ROOT / 'execution-output'
LIVE = Path('D:/1800/.local/stages/a12-native-reuse-live')
PRODUCT = ROOT / 'tools/headless_native_reuse_probe_r1.py'
CANDIDATE = '38eb3f836f14b44db77ce516f461bd4f3934df71807c1fac962560603a210920'
PRODUCT_SHA = '3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--intent-sha256', required=True)
    args = parser.parse_args()
    raw = (OUT / 'launch-intent.json').read_bytes()
    intent = json.loads(raw)
    if (sha(raw) != args.intent_sha256 or
            sha(Path(__file__).read_bytes()) != intent['wrapper_sha256'] or
            sha(PRODUCT.read_bytes()) != PRODUCT_SHA or
            intent['candidate_sha256'] != CANDIDATE or
            LIVE.exists() or (OUT / 'launch-started.json').exists()):
        raise RuntimeError('FIXED_LAUNCH_PRECONDITION_REJECTED')
    command = [sys.executable, '-B', str(PRODUCT), '--live',
               '--candidate-sha256', CANDIDATE,
               '--profile-fingerprint', intent['profile_fingerprint']]
    command_sha = sha(json.dumps(command, separators=(',', ':')).encode('utf-8'))
    if command_sha != intent['product_command_sha256']:
        raise RuntimeError('FIXED_COMMAND_REJECTED')
    sys.path.insert(0, str(ROOT / 'docs/evidence/A12/native-reuse-probe/reviewed-native'))
    from native_windows import WindowsAPI
    api = WindowsAPI()
    save('launch-started.json', {'at': utc(), 'intent_sha256': args.intent_sha256,
        'wrapper_sha256': intent['wrapper_sha256'], 'command': command,
        'product_command_sha256': command_sha, 'thread_id': intent['thread_id'],
        'wrapper_identity': api.held_identity(-1), 'live_starts_used': 1,
        'live_starts_remaining': 0})
    record = {'started_at': utc(), 'wait_limit_seconds': 88,
        'cleanup_limit_seconds': 2, 'timeout': False, 'errors': [],
        'exact_popen_handle_retained': False, 'handle_closed': False,
        'pipes_closed': False, 'state': 'UNKNOWN', 'returncode': None}
    child = None
    started = time.monotonic()
    try:
        child = subprocess.Popen(command, cwd=str(ROOT), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                 'PYTHONIOENCODING': 'utf-8', 'GIT_NO_LAZY_FETCH': '1'})
        record['exact_popen_handle_retained'] = True
        record['before'] = api.held_identity(int(child._handle))
        save('outer-process-created.json', {'at': utc(), 'before': record['before'],
            'command_sha256': command_sha, 'exact_popen_handle_retained': True})
        output, errors = child.communicate(timeout=max(0.01, 88 - (time.monotonic() - started)))
        record['stdout'] = {'bytes': len(output), 'sha256': sha(output), 'raw_text_withheld': True}
        record['stderr'] = {'bytes': len(errors), 'sha256': sha(errors), 'raw_text_withheld': True}
        record['returncode'] = child.returncode
    except subprocess.TimeoutExpired:
        record['timeout'] = True
        record['errors'].append('OUTER_WAIT_TIMEOUT')
    except BaseException:
        record['errors'].append('OUTER_PROCESS_OR_RECORD_ERROR')
    finally:
        if child is not None:
            cleanup_started = time.monotonic()
            try:
                if child.poll() is None:
                    record['exact_handle_termination_attempted'] = True
                    child.kill()
                    child.wait(timeout=max(0.01, 2 - (time.monotonic() - cleanup_started)))
                record['after'] = api.held_identity(int(child._handle))
                record['returncode'] = child.returncode
                record['same_pid_and_creation'] = (
                    record.get('before', {}).get('pid') == record['after']['pid'] and
                    record.get('before', {}).get('created_filetime') == record['after']['created_filetime'])
            except BaseException:
                record['errors'].append('EXACT_PROCESS_EXIT_UNPROVEN')
            finally:
                for stream in (child.stdout, child.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()
                record['pipes_closed'] = all(stream is None or stream.closed for stream in (child.stdout, child.stderr))
                child._handle.Close()
                record['handle_closed'] = True
                record['cleanup_duration_ms'] = round((time.monotonic() - cleanup_started) * 1000)
        record['duration_ms'] = round((time.monotonic() - started) * 1000)
        record['finished_at'] = utc()
        if (not record['errors'] and record.get('same_pid_and_creation') and
                record.get('after', {}).get('exit_observed') and
                record['handle_closed'] and record['pipes_closed']):
            record['state'] = 'RELEASED'
        save('outer-release.json', record)
    print(json.dumps({'outer_release': record['state'], 'product_returncode': record['returncode'],
                      'duration_ms': record['duration_ms'], 'timeout': record['timeout']}))
    return 0 if record['state'] == 'RELEASED' and record['returncode'] == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
