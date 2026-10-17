"""Read-only delivery preflight; no candidate imports, tests or DB connections."""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = 'c83f956c5c29c64ab10735ba11c153201d3f3f4b'
TARGET = 'bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39'
PREFIX = 'docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle'
REPORT = 'docs/tasks/A03-P2-R9-R1-owner-lifecycle-report.md'
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
assert len(base) == 31665
changed_old = {path for path, identity in base.items() if final.get(path) != identity}
expected_old = {'src/annotation/runtime/recovery/__init__.py', 'src/annotation/runtime/recovery/native_quality.py',
    'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'}
assert changed_old == expected_old
added = set(final) - set(base)
assert len(added) == 487
assert all(p.startswith(PREFIX + '/') or p.startswith('examples/a03/P2-R9-R1-owner-lifecycle/')
           or p in (REPORT, 'tests/test_a03_p2_r9_r1_owner_lifecycle.py') for p in added)
manifest = EVIDENCE / 'manifest.json'
assert sha(manifest.read_bytes()) == 'fa79fc21f550ea5491d2e122fb39b46976f9850666fe503423195ae90cdfd7be'
assert sha((WT / REPORT).read_bytes()) == 'd4241688c338d988d122d177305b464ad7aa14e8531b0f6589b492f72cdf956e'
entries = read(manifest)['entries']
assert len(entries) == len({e['path'] for e in entries}) == 490
assert {e['path'] for e in entries} | {PREFIX + '/manifest.json'} == added | changed_old
for e in entries:
    raw = (WT / e['path']).read_bytes()
    assert sha(raw) == e['sha256'] and len(raw) == e['bytes'], e['path']
names = sorted(added | changed_old)
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
    assert sha(data) == entry['sha256'] and len(data) == entry['bytes']
    if entry['path'] not in changed_old:
        assert data == (WT / entry['path']).read_bytes()
frozen = read(EVIDENCE / 'candidate-frozen.json')
for entry in frozen['drivers'] + frozen['product']:
    data = (WT / entry['path']).read_bytes()
    assert sha(data) == entry['sha256'] and len(data) == entry['bytes']

release = read(EVIDENCE / 'process-release.json')
assert release['all_recorded_owned_processes_waited_and_ended']
assert len(release['records']) == 15
for item in release['records']:
    folder = (EVIDENCE / item['path']).parent
    start, pre, done = [read(folder / p) for p in ('started.json', 'preregistered.json', 'completed.json')]
    assert start['pid'] == done['pid'] == item['pid']
    assert start['parent_pid'] == item['parent_pid']
    assert done['exit_code'] == item['exit_code'] == (1 if item['pid'] in (66208, 66792) else 0)
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

trace = EVIDENCE / 'validation/owner-r1-01/processes/borrow-execute/stderr.txt'
assert sha(trace.read_bytes()) == 'bc895733e5e37d479f5da9c57f73b29f23694a30a5b09e02a833a11cc7436fb5'
assert 'STORAGE_TRANSACTION_FAILED' in trace.read_text(encoding='utf-8') and 'UNIQUE constraint failed' in trace.read_text(encoding='utf-8')
assert not (EVIDENCE / 'runs/D2').exists()
assert not (EVIDENCE / 'validation/owner-r1-01/cases/D2').exists()

profile_path = 'src/annotation/contracts/a03_native/data/profile.json'
adoption_path = 'src/annotation/contracts/a03_native/data/adoption.json'
old_profile, new_profile = json.loads(git('cat-file','blob',BASE+':'+profile_path)), read(WT/profile_path)
old_pins, new_pins = dict(old_profile.pop('implementation_pins')), dict(new_profile.pop('implementation_pins'))
assert old_profile == new_profile
changed_pins = {key for key in old_pins if old_pins[key] != new_pins.get(key)}
assert changed_pins == {'@annotation/runtime/recovery/__init__.py', '@annotation/runtime/recovery/native_quality.py'}
assert set(old_pins) == set(new_pins)
for pin in changed_pins:
    assert sha((WT/'src'/pin[1:]).read_bytes()) == new_pins[pin]
old_adoption, new_adoption = json.loads(git('cat-file','blob',BASE+':'+adoption_path)), read(WT/adoption_path)
assert new_adoption.pop('profile_sha256') == sha((WT/profile_path).read_bytes())
old_adoption.pop('profile_sha256')
assert old_adoption == new_adoption

result = {
    'at': datetime.now().astimezone().isoformat(), 'status': 'DELIVERY_BYTES_AND_RELEASE_VERIFIED_READY_FOR_INDEPENDENT_REVIEW',
    'base': BASE, 'target': TARGET, 'working_tree_clean': True,
    'baseline_entries_unchanged': len(base) - len(changed_old), 'changed_old_paths': sorted(changed_old), 'new_entries': len(added), 'manifest_entries_verified': len(entries),
    'raw_git_blobs_verified': len(names), 'workflow_inputs_verified': len(inputs['files']),
    'report_sha256': sha((WT / REPORT).read_bytes()), 'manifest_sha256': sha(manifest.read_bytes()),
    'process_release_sha256': sha((EVIDENCE / 'process-release.json').read_bytes()),
    'recorded_processes_exited': 15, 'failed_child': {'pid': 66792, 'exit_code': 1, 'error': 'STORAGE_TRANSACTION_FAILED'}, 'D2': 'NOT_RUN',
    'author_reported_scope': 'Author D1 normal/restart/replay and standalone passed; borrowed group failed on exception expectation after successful publishing; D2 NOT_RUN. No independent product acceptance yet.',
    'review_required': 'Independent frozen-product four-group review with separately preregistered correct exception assertions; preserve original failed driver and evidence; first functional failure stops.',
    'product_changed': True, 'profile_scope_unchanged': True, 'implementation_pins_changed': sorted(changed_pins), 'product_calls_or_tests': 0, 'DB_connections': 0, 'network_or_platform': 0,
    'settings_changed': False, 'accepted': False, 'integrated': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
}
Path(__file__).with_name('delivery-preflight.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps(result, ensure_ascii=False))
