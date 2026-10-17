"""Read-only delivery preflight; no candidate imports, tests or DB connections."""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = 'd9ed692db9ab8e9277f8ffd09e040451e8b8f65f'
TARGET = '435aaee2d140e82d3237ce8902d594a1aee70aad'
PREFIX = 'docs/evidence/A03/execution/P2-R8-R4-remaining'
REPORT = 'docs/tasks/A03-P2-R8-R4-remaining-report.md'
EVIDENCE = WT / PREFIX


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(WT), *args])


def tree(commit):
    result = {}
    for line in git('ls-tree', '-r', '-z', commit).split(b'\0'):
        if line:
            metadata, path = line.split(b'\t', 1)
            result[path.decode()] = metadata.decode()
    return result


assert git('rev-parse', 'HEAD').decode().strip() == TARGET
assert not git('status', '--porcelain').strip()
base, final = tree(BASE), tree(TARGET)
assert len(base) == 31167
assert all(final.get(path) == identity for path, identity in base.items())
added = set(final) - set(base)
assert len(added) == 315
assert all(p.startswith(PREFIX + '/') or p.startswith('examples/a03/P2-R8-R4-remaining/')
           or p in (REPORT, 'tests/test_a03_r8_r4_remaining.py') for p in added)
manifest = EVIDENCE / 'manifest.json'
assert sha(manifest.read_bytes()) == '337ba0aa1ce0fd8a70032a6b2580797752f0e4ea5b0216b56913dae2ebd91f4c'
assert sha((WT / REPORT).read_bytes()) == 'eaba2a007216999ca70e506609a50a049e89b48b86b4c39af0e51dfa50e9e324'
entries = read(manifest)['entries']
assert len(entries) == len({e['path'] for e in entries}) == 314
assert {e['path'] for e in entries} | {PREFIX + '/manifest.json'} == added
for e in entries:
    raw = (WT / e['path']).read_bytes()
    assert sha(raw) == e['sha256'] and len(raw) == e['bytes'], e['path']
names = sorted(added)
raw = subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(WT), 'cat-file', '--batch'],
    input=('\n'.join(TARGET + ':' + p for p in names) + '\n').encode())
pos = 0
for name in names:
    end = raw.index(b'\n', pos)
    oid, kind, size = raw[pos:end].decode().split()
    pos = end + 1
    data = raw[pos:pos + int(size)]
    pos += int(size) + 1
    assert kind == 'blob' and data == (WT / name).read_bytes(), name
assert pos == len(raw)

inputs = read(EVIDENCE / 'inputs.json')
assert inputs['base'] == BASE and inputs['base_entries'] == len(base)
for entry in inputs['files']:
    data = git('cat-file', 'blob', entry['workflow'] + ':' + entry['path'])
    assert sha(data) == entry['sha256'] and len(data) == entry['bytes']
    assert data == (EVIDENCE / 'inputs' / Path(entry['path']).name).read_bytes()
for entry in inputs['unchanged_references']:
    data = git('cat-file', 'blob', BASE + ':' + entry['path'])
    assert sha(data) == entry['sha256'] and data == (WT / entry['path']).read_bytes()
for entry in read(EVIDENCE / 'driver-preregistered.json')['drivers']:
    data = (WT / entry['path']).read_bytes()
    assert sha(data) == entry['sha256'] and len(data) == entry['bytes']

release = read(EVIDENCE / 'process-release.json')
assert release['all_recorded_owned_processes_waited_and_ended']
assert len(release['records']) == 8
for item in release['records']:
    folder = (EVIDENCE / item['path']).parent
    start, pre, done = [read(folder / p) for p in ('started.json', 'preregistered.json', 'completed.json')]
    assert start['pid'] == done['pid'] == item['pid']
    assert start['parent_pid'] == item['parent_pid']
    assert done['exit_code'] == item['exit_code'] == (87 if item['pid'] == 60488 else 0)
    assert not done['alive'] and not done.get('timed_out', done.get('timeout', False))
    assert pre['argv'] and pre['cwd'] == str(WT) and pre['timeout_seconds'] > 0
    for stream in ('stdout', 'stderr'):
        data = (folder / (stream + '.txt')).read_bytes()
        if stream + '_sha256' in done:
            assert sha(data) == done[stream + '_sha256']
    if 'script_pins' in pre:
        for path, expected in pre['script_pins'].items():
            assert sha((WT / path).read_bytes()) == expected
            assert sha((folder / 'script-snapshots' / Path(path).name).read_bytes()) == expected
        for name, key in [('product-source-index.json', 'product_source_index_sha256'), ('fixture-index.json', 'fixture_index_sha256')]:
            assert sha((folder / name).read_bytes()) == pre[key]
        assert sha((EVIDENCE / 'inputs.json').read_bytes()) == pre['input_index_sha256']
        assert pre['registered_at_ns'] <= start['started_at_ns'] <= done['ended_at_ns']
    if 'script_sha256' in pre:
        assert sha((folder / 'script-snapshot.py').read_bytes()) == pre['script_sha256']
    if item['pid'] == 60488:
        assert done['barrier_released']
for group in ('N1', 'N6', 'N7'):
    assert 'Ran 1 test in ' in (EVIDENCE / 'runs' / group / 'stderr.txt').read_text(encoding='utf-8')
    assert '\nOK' in (EVIDENCE / 'runs' / group / 'stderr.txt').read_text(encoding='utf-8')

result = {
    'at': datetime.now().astimezone().isoformat(), 'status': 'DELIVERY_BYTES_AND_RELEASE_VERIFIED_READY_FOR_INDEPENDENT_REVIEW',
    'base': BASE, 'target': TARGET, 'working_tree_clean': True,
    'baseline_entries_unchanged': len(base), 'new_entries': len(added), 'manifest_entries_verified': len(entries),
    'raw_git_blobs_verified': len(names), 'workflow_inputs_verified': len(inputs['files']),
    'report_sha256': sha((WT / REPORT).read_bytes()), 'manifest_sha256': sha(manifest.read_bytes()),
    'process_release_sha256': sha((EVIDENCE / 'process-release.json').read_bytes()),
    'recorded_processes_exited': 8, 'effect_child': {'pid': 60488, 'exit_code': 87, 'barrier_released': True},
    'author_reported_scope': 'Fresh N1 prerequisite, N6 same-plan/full-UNKNOWN-history and one missing PRE evidence control, N7 runtime before_completion only',
    'review_required': 'Independent fresh bounded runs and data binding audit; author assertions are not acceptance.',
    'product_changed': False, 'product_calls_or_tests': 0, 'DB_connections': 0, 'network_or_platform': 0,
    'settings_changed': False, 'accepted': False, 'integrated': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
}
Path(__file__).with_name('delivery-preflight.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps(result, ensure_ascii=False))
