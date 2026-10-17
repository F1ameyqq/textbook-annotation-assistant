"""Read-only delivery preflight; no candidate imports, tests or DB connections."""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = '435aaee2d140e82d3237ce8902d594a1aee70aad'
TARGET = 'c83f956c5c29c64ab10735ba11c153201d3f3f4b'
PREFIX = 'docs/evidence/A03/execution/P2-R9-minimal-demos'
REPORT = 'docs/tasks/A03-P2-R9-minimal-demos-report.md'
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
assert len(base) == 31482
assert all(final.get(path) == identity for path, identity in base.items())
added = set(final) - set(base)
assert len(added) == 183
assert all(p.startswith(PREFIX + '/') or p.startswith('examples/a03/P2-R9-minimal-demos/')
           or p in (REPORT, 'tests/test_a03_p2_r9_minimal_demos.py') for p in added)
manifest = EVIDENCE / 'manifest.json'
assert sha(manifest.read_bytes()) == '7712cad90e09e0883dc4dc95d36608a066d76ca62aa10a2664df0b7a48917c86'
assert sha((WT / REPORT).read_bytes()) == '6f68b69ed13cbdc3194346181054eef70b9abc45c1a714ab35b60ab847b3c72d'
entries = read(manifest)['entries']
assert len(entries) == len({e['path'] for e in entries}) == 182
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
for entry in inputs['unchanged_references_and_copied_fixture_sources']:
    data = git('cat-file', 'blob', BASE + ':' + entry['path'])
    assert sha(data) == entry['sha256'] and data == (WT / entry['path']).read_bytes()
for entry in read(EVIDENCE / 'driver-preregistered.json')['drivers']:
    data = (WT / entry['path']).read_bytes()
    assert sha(data) == entry['sha256'] and len(data) == entry['bytes']

release = read(EVIDENCE / 'process-release.json')
assert release['all_recorded_owned_processes_waited_and_ended']
assert len(release['records']) == 4
for item in release['records']:
    folder = (EVIDENCE / item['path']).parent
    start, pre, done = [read(folder / p) for p in ('started.json', 'preregistered.json', 'completed.json')]
    assert start['pid'] == done['pid'] == item['pid']
    assert start['parent_pid'] == item['parent_pid']
    assert done['exit_code'] == item['exit_code'] == (1 if item['pid'] in (42924, 61832) else 0)
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

trace = EVIDENCE / 'validation/r9-01/processes/D1-execute/stderr.txt'
assert sha(trace.read_bytes()) == '0db6947c2321a6a6fe42b68486f7dc0f0cd7e5340a50a6f412f013fe9fc4852d'
assert 'OWNER_BUSY' in trace.read_text(encoding='utf-8')
assert not (EVIDENCE / 'runs/D2').exists()
assert not (EVIDENCE / 'validation/r9-01/cases/D2').exists()

result = {
    'at': datetime.now().astimezone().isoformat(), 'status': 'DELIVERY_BYTES_AND_RELEASE_VERIFIED_READY_FOR_INDEPENDENT_REVIEW',
    'base': BASE, 'target': TARGET, 'working_tree_clean': True,
    'baseline_entries_unchanged': len(base), 'new_entries': len(added), 'manifest_entries_verified': len(entries),
    'raw_git_blobs_verified': len(names), 'workflow_inputs_verified': len(inputs['files']),
    'report_sha256': sha((WT / REPORT).read_bytes()), 'manifest_sha256': sha(manifest.read_bytes()),
    'process_release_sha256': sha((EVIDENCE / 'process-release.json').read_bytes()),
    'recorded_processes_exited': 4, 'effect_child': {'pid': 61832, 'exit_code': 1, 'error': 'OWNER_BUSY'},
    'author_reported_scope': 'D1 first functional failure; author reports one effect and committed receipt before duplicate ownership claim; D1 restart/replay and D2 NOT_RUN',
    'review_required': 'Independent frozen-source, failure trace and immutable-copy data binding review; no fresh D1/D2 run and no product fixes during failure classification.',
    'product_changed': False, 'product_calls_or_tests': 0, 'DB_connections': 0, 'network_or_platform': 0,
    'settings_changed': False, 'accepted': False, 'integrated': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
}
Path(__file__).with_name('delivery-preflight.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps(result, ensure_ascii=False))
