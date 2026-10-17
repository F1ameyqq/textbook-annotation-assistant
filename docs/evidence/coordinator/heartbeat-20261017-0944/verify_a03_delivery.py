"""Read-only frozen R4 delivery preflight; never imports or runs delivery code."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = '87606b73e0754fa670491d9fb958a416c26bfe88'
TARGET = 'e608b54b973b14ff55dd2c4530153f5fe7c931f4'
EVIDENCE = 'docs/evidence/A03/execution/P2-R4-bridge-registration/'
EXAMPLES = 'examples/a03/P2-R4-bridge-registration/'
REPORT = 'docs/tasks/A03-P2-R4-bridge-registration-delivery.md'
MANIFEST = EVIDENCE + 'sha256-manifest.json'
OUT = Path(__file__).resolve().parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args, data=None):
    result = subprocess.run(['git', '-c', 'core.longpaths=true', *args], cwd=WT,
                            input=data, capture_output=True, timeout=60)
    assert result.returncode == 0, (args, result.stderr.decode('utf-8', errors='replace'))
    return result.stdout

def blobs(requests):
    raw = git('cat-file', '--batch', data=('\n'.join(requests) + '\n').encode())
    offset = 0
    output = []
    for request in requests:
        end = raw.index(b'\n', offset)
        oid, kind, size = raw[offset:end].split()
        assert kind == b'blob', request
        offset = end + 1
        content = raw[offset:offset + int(size)]
        offset += int(size)
        assert raw[offset:offset + 1] == b'\n'
        offset += 1
        output.append((oid.decode(), content))
    assert offset == len(raw)
    return output

def tree(commit):
    result = {}
    for row in git('ls-tree', '-r', '-z', commit).split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        result[path.decode('utf-8')] = meta
    return result

def load(name):
    return json.loads((WT / name).read_bytes())

assert git('rev-parse', 'HEAD').decode().strip() == TARGET
assert not git('status', '--porcelain').strip()
before, after = tree(BASE), tree(TARGET)
assert all(after.get(path) == oid for path, oid in before.items())
added = set(after) - set(before)
assert len(added) == 111
assert all(path.startswith((EVIDENCE, EXAMPLES)) or path == REPORT for path in added)
manifest_bytes = (WT / MANIFEST).read_bytes()
assert sha(manifest_bytes) == '5c5823f1b146574202fbfd00e066aafc1697d017e40c12cab66b9330cb75d28e'
assert sha((WT / REPORT).read_bytes()) == '95cf2746bb9ceb5a1857f3e8babca04892d8481c74c11d3ee256d5eeb26055f9'
manifest = json.loads(manifest_bytes)
assert manifest['base'] == BASE
assert manifest['excluded_only'] == [MANIFEST]
rows = manifest['files']
assert len(rows) == 110 and len({row['path'] for row in rows}) == 110
assert {row['path'] for row in rows} | {MANIFEST} == added
records = rows + [{'path': MANIFEST, 'bytes': len(manifest_bytes), 'sha256': sha(manifest_bytes)}]
for row, (_, raw) in zip(records, blobs([TARGET + ':' + row['path'] for row in records])):
    path = (WT / row['path']).resolve()
    assert path.is_relative_to(WT.resolve())
    assert raw == path.read_bytes(), row['path']
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']

index = load(EVIDENCE + 'input-index.json')
workflow_inputs = index['documents']
product_inputs = index['product_text']
static_inputs = index['reused_inputs']
resources = load(EVIDENCE + 'resource-input-pins.json')['inputs']
assert [len(x) for x in (workflow_inputs, product_inputs, static_inputs, resources)] == [6,12,15,5]
inputs = workflow_inputs + product_inputs + static_inputs + resources
for row, (oid, raw) in zip(inputs, blobs([row['commit'] + ':' + row['path'] for row in inputs])):
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    assert raw == (WT / row.get('copy', row['path'])).read_bytes(), row['path']
    if 'raw_git_blob' in row:
        assert oid == row['raw_git_blob']
release = load(EVIDENCE + 'process-release.json')
assert release['native_sessions'] == 0 and release['background_tasks'] == 0
expected_exits = {'freeze-01':0, 'prepare-01':1, 'assess-01':1, 'assess-02':0, 'seal-01':0, 'verify-01':1, 'verify-02':0}
assert {x['run']:x['exit_code'] for x in release['runs']} == expected_exits
for run in release['runs']:
    exit_record = load(EVIDENCE + 'runs/' + run['run'] + '/exit.json')
    assert exit_record['owned_pid'] == run['pid']
    assert run['exit_code'] == exit_record['exit_code'] == expected_exits[run['run']]
    assert run['alive'] is False and exit_record['alive'] is False
    assert exit_record['native_sessions'] == 0 and exit_record['background_tasks'] == 0
    for stream in ('stdout', 'stderr'):
        path = WT / EVIDENCE / 'runs' / run['run'] / (stream + '.txt')
        assert sha(path.read_bytes()) == run[stream + '_sha256']
assert sha((WT / EXAMPLES / 'bridge-interface-proposal.json').read_bytes()) == 'b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207'
assert not git('status', '--porcelain').strip()

result = {
    'task_id': 'A03', 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'READY_FOR_BOUNDED_INDEPENDENT_STATIC_REVIEW', 'base_commit': BASE,
    'target_commit': TARGET, 'worktree': str(WT), 'worktree_clean': True,
    'manifest_entries_verified_disk_and_raw_git': len(rows), 'new_files_including_manifest': len(added),
    'old_git_paths_preserved': len(before), 'out_of_scope_paths': [],
    'workflow_raw_git_inputs_verified': len(workflow_inputs), 'product_text_raw_inputs_verified': len(product_inputs), 'static_raw_inputs_verified': len(static_inputs), 'resource_raw_inputs_verified': len(resources),
    'report_sha256': sha((WT / REPORT).read_bytes()), 'manifest_sha256': sha(manifest_bytes),
    'recorded_owned_runs_exited': len(release['runs']),
    'session_release_basis': 'Completed execution turn plus frozen owned synchronous child exit/log records; no current OS or profile scan.',
    'execution_thread_id': '01a145aa-2fea-7942-97f9-ad260acf4e30',
    'execution_turn_id': '01a1491e-d32b-71d0-a7a7-9c1224a76169',
    'execution_cursor': '506fd3cf-091f-418b-b002-636f503b5e4b:21',
    'delivery_code_imported_or_executed': False, 'functional_tests_run': False,
    'product_native_DB_platform_model_calls': 0, 'I01_released': False,
    'product_accepted': False, 'integrated': False, 'remote_push': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
    'reasoning_policy': 'PRESERVE_USER_SETTING; omit thinking on A03 continuation.'
}
with (OUT / 'A03-R4-delivery-preflight.json').open('x', encoding='utf-8', newline='\n') as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps(result, ensure_ascii=False))
