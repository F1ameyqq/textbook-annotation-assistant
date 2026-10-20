"""Launch exactly the authorized frozen E1-E4 once and retain native output bytes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path('D:/1800-worktrees/a15-independent-fixed')
OUT = ROOT / 'docs/evidence/A15/independent-preflight'
DELTA_OUT = ROOT / 'docs/evidence/A15/certificate-exception/first-independent-delta'
CANDIDATE_SHA = '78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652'

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_new(name, data):
    with (OUT / name).open('xb') as stream:
        stream.write(data)

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')

preflight_raw = (OUT / 'fixed-input-preflight.json').read_bytes()
preflight = json.loads(preflight_raw)
assert preflight['status'] == 'READY_FOR_SINGLE_INDEPENDENT_E1_E4'
assert preflight['candidate_sha256'] == CANDIDATE_SHA
assert preflight['independent_delta_executions_before'] == 0
assert not DELTA_OUT.exists()
command = [sys.executable, '-B', 'tools/a15_cert_exception_gate_delta.py',
           '--candidate-sha256', CANDIDATE_SHA,
           '--output', 'docs/evidence/A15/certificate-exception/first-independent-delta']
started = now()
write_new('independent-run-started.json', encode({'task': 'A15', 'invocations': 1,
 'started_at': started, 'argv': command, 'cwd': str(ROOT), 'shell': False,
 'fixed_input_preflight_sha256': sha(preflight_raw), 'candidate_sha256': CANDIDATE_SHA,
 'execution_limit': 1, 'live_activated': False}))
timeout = False
try:
    result = subprocess.run(command, cwd=ROOT,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
except subprocess.TimeoutExpired as error:
    stdout, stderr, exit_code = error.stdout or b'', error.stderr or b'', None
    timeout = True
write_new('independent-delta-stdout.txt', stdout)
write_new('independent-delta-stderr.txt', stderr)
receipt = {'task': 'A15', 'argv': command, 'cwd': str(ROOT), 'shell': False,
 'started_at': started, 'finished_at': now(), 'exit_code': exit_code,
 'invocations': 1, 'timeout': timeout, 'stdout_bytes': len(stdout), 'stderr_bytes': len(stderr),
 'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr),
 'candidate_sha256': CANDIDATE_SHA, 'new_candidate_created': False,
 'old_suites_run': False, 'live_activated': False,
 'runner_process_scope': 'One interpreter for the authorized pure delta; no product subprocess permission.'}
write_new('independent-command-result.json', encode(receipt))
result_path = DELTA_OUT / 'suite-result.json'
if result_path.is_file():
    raw = result_path.read_bytes()
    suite = json.loads(raw)
    summary = {'exit_code': exit_code, 'invocations': 1, 'cases': {
        case['case']: case['status'] for case in suite['cases']},
        'duration_ms': suite['duration_ms'], 'first_failure': suite['first_failure'],
        'suite_result_sha256': sha(raw), 'resource_calls': suite['resource_calls']}
else:
    summary = {'exit_code': exit_code, 'invocations': 1,
               'cases': {case: 'NOT_RUN_NO_RESULT' for case in ('E1', 'E2', 'E3', 'E4')},
               'first_failure': 'DELTA_DID_NOT_PRODUCE_RESULT', 'timeout': timeout}
write_new('independent-run-summary.json', encode(summary))
print(json.dumps(summary))
raise SystemExit(0 if exit_code == 0 and not timeout and
                 summary.get('first_failure') is None and not stderr else 2)
