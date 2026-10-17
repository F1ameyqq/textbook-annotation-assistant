"""Read-only frozen R5 delivery preflight; never imports or runs delivery code."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = 'e608b54b973b14ff55dd2c4530153f5fe7c931f4'
TARGET = '323013c4f0dbae75368e56db60147a8057368d1f'
EVIDENCE = 'docs/evidence/A03/execution/P2-R5-registration-context/'
EXAMPLES = 'examples/a03/P2-R5-registration-context/'
REPORT = 'docs/tasks/A03-P2-R5-registration-context-delivery.md'
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
assert len(added) == 205
assert all(path.startswith((EVIDENCE, EXAMPLES)) or path == REPORT for path in added)
manifest_bytes = (WT / MANIFEST).read_bytes()
assert sha(manifest_bytes) == '2bb118b00b61f1c22109e3eed37777ee5c77cf88acc9c62911e515fac65dd2f7'
assert sha((WT / REPORT).read_bytes()) == '86dd088bc109bf1243cd015d3c2f0dde9c52e2c01397574845766c7bb8208389'
manifest = json.loads(manifest_bytes)
assert manifest['base'] == BASE
assert manifest['excluded_only'] == [MANIFEST]
rows = manifest['files']
assert len(rows) == 204 and len({row['path'] for row in rows}) == 204
assert {row['path'] for row in rows} | {MANIFEST} == added
records = rows + [{'path': MANIFEST, 'bytes': len(manifest_bytes), 'sha256': sha(manifest_bytes)}]
for row, (_, raw) in zip(records, blobs([TARGET + ':' + row['path'] for row in records])):
    path = (WT / row['path']).resolve()
    assert path.is_relative_to(WT.resolve())
    assert raw == path.read_bytes(), row['path']
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']

index = load(EVIDENCE + 'input-index.json')
inputs = index['inputs'] + load(EVIDENCE + 'repair-input-index.json')['inputs']
assert len(index['inputs']) == 68 and len(inputs) == 70
workflow_inputs = [row for row in inputs if row['commit'] == '5fcb2e0084c92c20092cac19e33619128ad86d54']
assert len(workflow_inputs) == 9
for row, (oid, raw) in zip(inputs, blobs([row['commit'] + ':' + row['path'] for row in inputs])):
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    assert raw == (WT / row.get('copy', row['path'])).read_bytes(), row['path']
    assert oid == row['git_blob']
release = load(EVIDENCE + 'process-release.json')
assert release['native_sessions'] == 0 and release['background_tasks'] == 0
expected_exits = {name: (1 if name == 'case-07' else 0) for name in ['archive-01','case-01','case-02','case-03','case-04','case-05','case-06','case-07','case-07-repair-01','freeze-01','prepare-01','repair-01','static-01']}
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
assert sha((WT / EXAMPLES / 'registration.py').read_bytes()) == '3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
assert not git('status', '--porcelain').strip()

result = {
    'task_id': 'A03', 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'READY_FOR_BOUNDED_INDEPENDENT_STATIC_REVIEW', 'base_commit': BASE,
    'target_commit': TARGET, 'worktree': str(WT), 'worktree_clean': True,
    'manifest_entries_verified_disk_and_raw_git': len(rows), 'new_files_including_manifest': len(added),
    'old_git_paths_preserved': len(before), 'out_of_scope_paths': [],
    'workflow_raw_git_inputs_verified': len(workflow_inputs), 'total_raw_git_inputs_verified': len(inputs),
    'report_sha256': sha((WT / REPORT).read_bytes()), 'manifest_sha256': sha(manifest_bytes),
    'recorded_owned_runs_exited': len(release['runs']),
    'session_release_basis': 'Completed execution turn plus frozen owned synchronous child exit/log records; no current OS or profile scan.',
    'execution_thread_id': '01a145aa-2fea-7942-97f9-ad260acf4e30',
    'execution_turn_id': '01a1495e-bc63-7683-8f22-974e010c447a',
    'execution_cursor': '506fd3cf-091f-418b-b002-636f503b5e4b:24',
    'delivery_code_imported_or_executed': False, 'functional_tests_run': False,
    'product_native_DB_platform_model_calls': 0, 'I01_released': False,
    'product_accepted': False, 'integrated': False, 'remote_push': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
    'reasoning_policy': 'PRESERVE_USER_SETTING; omit thinking on A03 continuation.'
}
with (OUT / 'A03-R5-delivery-preflight.json').open('x', encoding='utf-8', newline='\n') as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps(result, ensure_ascii=False))
