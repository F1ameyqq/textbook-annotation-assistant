"""Read fixed Git blobs and recorded evidence only; never execute A07 business."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('D:/1800')
BASE = 'b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a'
CANDIDATE = '6dad9b9a40a10989c102d91cf7b54f19c012015f'
DELIVERY = 'd2e710c817cf85505ac4fad4919dd51d1062d33a'
PREFIX = 'docs/evidence/A07/execution/'
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1')

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT, env=ENV)

def blob(path):
    return git('show', DELIVERY + ':' + path)

def data(path):
    return json.loads(blob(PREFIX + path))

def tree(ref):
    result = {}
    for entry in git('ls-tree', '-rz', ref).split(b'\0'):
        if entry:
            metadata, path = entry.split(b'\t', 1)
            result[path.decode('utf-8')] = metadata.decode('ascii')
    return result

base, candidate, delivery = map(tree, [BASE, CANDIDATE, DELIVERY])
assert all(delivery.get(p) == v for p, v in base.items())
assert all(delivery.get(p) == v for p, v in candidate.items())
manifest_path = PREFIX + 'delivery-raw-git-manifest.json'
m = json.loads(blob(manifest_path))
listed = set()
byte_count = 0
for member in m['members']:
    path = member['path']
    assert path not in listed
    listed.add(path)
    raw = blob(path)
    assert len(raw) == member['bytes'], path
    assert hashlib.sha256(raw).hexdigest() == member['sha256'], path
    assert delivery[path].split()[2] == member['blob_oid'], path
    byte_count += len(raw)
assert m['members_count'] == len(listed) == 63
assert listed == set(delivery) - set(base) - {manifest_path}
summary = data('candidate-1/run/summary.json')
supervisor = data('candidate-1/supervisor.json')
release = data('process-release.json')
assert summary['complete_attempts'] == summary['dispatches'] == summary['successful_closures'] == 1
assert summary['question_count'] == 1 and summary['frame_count'] == 6
assert summary['outcome'] == 'APPLIED' and summary['execution_mode'] == 'SIMULATED'
assert summary['platform_calls'] == summary['model_calls'] == 0
assert summary['approval_sha256'] == 'cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c'
assert supervisor['candidate_commit'] == CANDIDATE
assert supervisor['child_exit_code'] == 0 and supervisor['child_reaped'] and not supervisor['timed_out']
assert release['release_state'] == 'RELEASED' and not release['owned_pids_still_running']
release_command = '$p=@(Get-Process -Id 75456,26148 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName); [pscustomobject]@{recordedPids=@(75456,26148);stillRunning=$p} | ConvertTo-Json -Depth 3 -Compress'
live_release = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', release_command]))
assert live_release['stillRunning'] == []
report = 'docs/tasks/A07-Q1-execution-report.md'
result = {
    'at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    'task_id': 'A07', 'kind': 'DELIVERY_PREFLIGHT_NOT_ACCEPTANCE',
    'workflow_commit': BASE, 'candidate_commit': CANDIDATE, 'delivery_commit': DELIVERY,
    'workflow_paths_preserved': len(base), 'candidate_new_paths': len(candidate) - len(base),
    'delivery_new_paths': len(delivery) - len(base), 'manifest_members_verified': len(listed),
    'manifest_member_bytes': byte_count,
    'manifest_sha256': hashlib.sha256(blob(manifest_path)).hexdigest(),
    'execution_report_sha256': hashlib.sha256(blob(report)).hexdigest(),
    'candidate_product_bytes_preserved': True, 'old_git_paths_preserved': True,
    'author_reported_results': {'attempts': 1, 'dispatches': 1, 'questions': 1, 'frames': 6, 'outcome': 'APPLIED', 'elapsed_seconds': summary['elapsed_seconds']},
    'release_rechecked': live_release, 'runtime_checks_executed_by_coordinator': 0,
    'acceptance_claim': False, 'result': 'READY_FOR_REGISTERED_INDEPENDENT_REVIEW',
    'run_guard': 'Independent runtime checkout HEAD must be the fixed product candidate, not final evidence delivery HEAD.'
}
Path(__file__).with_name('preflight.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(result, ensure_ascii=True))
