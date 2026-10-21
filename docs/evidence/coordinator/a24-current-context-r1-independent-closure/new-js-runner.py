"""Execute the exact page programs in one local Node VM with fake storage/fetch."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from annotation.source.usense.current_readonly import context_query as cq
from annotation.source.usense.current_readonly.gate import TARGET

OUT = Path(__file__).resolve().parent / 'js-runs'
OUT.mkdir(parents=True, exist_ok=True)
number = 1
while (OUT / ('run%02d.json' % number)).exists():
    number += 1
cases = []
for username, role in (('SYNTHETIC_USERNAME_SECRET', 'admin'), ('FAKE :$,+&/!?=()~*', 'delivery_admin'),
        ('FAKE Unicode \u9752\U0001f30d', ' admin '), ('FAKE_USER', '\ufeffadmin\ufeff'),
        ('FAKE_USER', '\u0085admin\u0085'), (' FAKE_USER ', 'user')):
    cases.append({'user': {'username': username, 'role': role, 'access_token': 'FAKE_TOKEN_STAYS_IN_PAGE'},
        'expected': cq.official_endpoint(username, role), 'expectPrepare': 'PREPARED',
        'expectSend': 'BOUND_CONTEXT_UNCHANGED', 'expectCount': 1})
original = {'username': 'FAKE_USER', 'role': 'user', 'access_token': 'FAKE_TOKEN_STAYS_IN_PAGE'}
cases.append({'user': original, 'expected': cq.official_endpoint('FAKE_USER', 'user'),
    'changedUser': dict(original, username='FAKE_CHANGED'), 'expectPrepare': 'PREPARED',
    'expectSend': 'CONTEXT_CHANGED', 'expectCount': 0})
for user, status in ((None, 'CONTEXT_UNAVAILABLE'), ({'username': 'FAKE_USER'}, 'CONTEXT_UNSUPPORTED'),
        ({'username': 'FAKE_USER', 'role': True}, 'CONTEXT_UNSUPPORTED'),
        ({'username': 'FAKE_USER', 'role': '\ud800'}, 'CONTEXT_UNSUPPORTED'),
        ({'username': "FAKE'USER", 'role': 'user'}, 'CONTEXT_UNSUPPORTED')):
    cases.append({'user': user, 'expectPrepare': status, 'expectSend': status, 'expectCount': 0})
cases.append({'raw': '{MALFORMED}', 'expectPrepare': 'CONTEXT_MALFORMED',
    'expectSend': 'CONTEXT_MALFORMED', 'expectCount': 0})
cases.append({'user': dict(original, access_token=''), 'expected': cq.official_endpoint('FAKE_USER', 'user'),
    'expectPrepare': 'PREPARED', 'expectSend': 'SESSION_TOKEN_UNAVAILABLE', 'expectCount': 0})
cases.append({'user': original, 'expected': cq.official_endpoint('FAKE_USER', 'user'), 'fetchThrows': True,
    'expectPrepare': 'PREPARED', 'expectSend': 'GET_RESULT_UNKNOWN', 'expectCount': 1})
payload = {'target': TARGET, 'prepare': cq.PREPARE_JS, 'send': cq.SEND_JS, 'cases': cases}
started = time.monotonic()
run = subprocess.run(['node', str(ROOT / 'tests/a24_current_context/js_fake_controls.cjs')],
    input=json.dumps(payload).encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    check=False, creationflags=0x08000000)
with (OUT / ('run%02d-node-stdout.txt' % number)).open('xb') as stream: stream.write(run.stdout)
with (OUT / ('run%02d-node-stderr.txt' % number)).open('xb') as stream: stream.write(run.stderr)
rows = json.loads(run.stdout)['results'] if run.returncode == 0 else []
checks = []
for case, row in zip(cases, rows):
    success = (row['preparedStatus'] == case['expectPrepare'] and row['preparedMatches'] and
        row['sendStatus'] == case['expectSend'] and row['sends'] == case['expectCount'] and
        row['sendsAfterPrepare'] == 0 and row['prepareKeysSafe'] and row['safeResult'] and
        row['sendStorageReads'] == 1 and (case['expectCount'] == 0 or row['headerExact']))
    checks.append({'index': row['index'], 'success': success, **{key: row[key] for key in (
        'preparedStatus', 'sendStatus', 'sends', 'sendStorageReads', 'prepareKeysSafe', 'safeResult')}})
result = {'task': 'A24', 'mode': 'OFFLINE_NODE_VM_FAKE_STORAGE_AND_FETCH', 'run': number,
    'success': run.returncode == 0 and len(checks) == len(cases) and all(row['success'] for row in checks),
    'cases': checks, 'case_count': len(cases), 'node_returncode': run.returncode,
    'stderr_bytes': len(run.stderr), 'duration_ms': round((time.monotonic() - started) * 1000),
    'actual_browser_network_profile_native_occupancy_product_launcher_calls': 0,
    'local_fake_JS_interpreter_processes': 1, 'old_suites_run': 0, 'runtime_account_context_read': False}
with (OUT / ('run%02d.json' % number)).open('xb') as stream:
    stream.write((json.dumps(result, indent=2) + '\n').encode('utf-8'))
print(json.dumps({key: result[key] for key in ('run', 'success', 'case_count', 'node_returncode', 'duration_ms')}))
raise SystemExit(0 if result['success'] else 1)
