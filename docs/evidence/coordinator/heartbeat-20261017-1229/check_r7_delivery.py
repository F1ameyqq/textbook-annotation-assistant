"""Coordinator byte/scope/release audit only; never imports the candidate."""
import datetime
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[4]
WT = pathlib.Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = '81d3ec7e42e0a1a76ad744bf59536fc5f68adee4'
TARGET = '8ad45dd07214ae406a3fab28d76a4b5abd6eef03'
E = 'docs/evidence/A03/execution/P2-R7-readonly-codec/'
MANIFEST = E + 'sha256-manifest.json'
REPORT = 'docs/tasks/A03-P2-R7-readonly-codec-delivery.md'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(WT), *args])

def read(path):
    return (WT / path).read_bytes()

def js(path):
    return json.loads(read(path))

def batch(specs):
    specs = list(dict.fromkeys(specs))
    p = subprocess.run(['git', '-c', 'core.longpaths=true', '-C', str(WT), 'cat-file', '--batch'],
                       input=('\n'.join(specs) + '\n').encode(), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=True)
    out, offset, found = p.stdout, 0, {}
    for spec in specs:
        end = out.index(b'\n', offset)
        oid, kind, size = out[offset:end].split()
        assert kind == b'blob', (spec, kind)
        start = end + 1
        data = out[start:start + int(size)]
        assert out[start + int(size):start + int(size) + 1] == b'\n'
        offset = start + int(size) + 1
        found[spec] = (oid.decode(), data)
    assert offset == len(out)
    return found

def tree(rev):
    result = {}
    for row in git('ls-tree', '-r', '-z', rev).split(b'\0'):
        if row:
            metadata, path = row.split(b'\t', 1)
            result[path.decode()] = metadata.decode()
    return result

def main():
    assert git('rev-parse', 'HEAD').decode().strip() == TARGET
    assert not git('status', '--porcelain').strip()
    manifest = js(MANIFEST)
    entries = manifest['files']
    assert manifest['base'] == BASE
    assert manifest['excluded_only'] == [MANIFEST]
    assert len({e['path'] for e in entries}) == len(entries) == 339
    inputs = js(E + 'raw-input-pins.json')['inputs']
    compatibility = js(E + 'compatibility-input-pins.json')['inputs']
    specs = [TARGET + ':' + e['path'] for e in entries] + [TARGET + ':' + MANIFEST, BASE + ':pyproject.toml']
    specs += [p['commit'] + ':' + p['path'] for p in inputs + compatibility]
    blobs = batch(specs)
    for e in entries:
        raw = blobs[TARGET + ':' + e['path']][1]
        assert read(e['path']) == raw, ('disk-git', e['path'])
        assert sha(raw) == e['sha256'] and len(raw) == e['bytes'], ('manifest', e['path'])
    assert read(MANIFEST) == blobs[TARGET + ':' + MANIFEST][1]
    for pin in inputs + compatibility:
        oid, raw = blobs[pin['commit'] + ':' + pin['path']]
        assert oid == pin['git_blob'] and sha(raw) == pin['sha256'] and len(raw) == pin['bytes'], pin['path']
        if pin.get('copy'):
            assert read(pin['copy']) == raw, pin['copy']
        # pyproject's old checkout pin predates the sole authorized existing-file change.
        if pin.get('checkout_sha256') and pin['path'] != 'pyproject.toml':
            assert sha(read(pin['path'])) == pin['checkout_sha256'], pin['path']
    before, after = tree(BASE), tree(TARGET)
    changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    assert changed == {e['path'] for e in entries} | {MANIFEST}
    modified = sorted(p for p in changed if p in before)
    assert modified == ['pyproject.toml']
    prefixes = ('src/annotation/contracts/a03_bridge/', 'tests/fixtures/a03/P2-R7-readonly-codec/',
                'examples/a03/P2-R7-readonly-codec/', E)
    assert all(p.startswith(prefixes) or p in ('pyproject.toml', 'tests/test_a03_r7_readonly_codec.py', REPORT) for p in changed)
    old_preserved = [p for p in before if p != 'pyproject.toml']
    assert all(before[p] == after[p] for p in old_preserved)
    old_pyproject = blobs[BASE + ':pyproject.toml'][1]
    new_pyproject = blobs[TARGET + ':pyproject.toml'][1]
    assert new_pyproject == old_pyproject + b'\n[tool.setuptools.package-data]\n"annotation.contracts.a03_bridge" = ["data/*.json", "data/schemas/*.json"]\n'
    release = js(E + 'process-release.json')
    nested = js(E + 'nested-process-release.json')
    assert release['native_sessions'] == release['background_tasks'] == 0
    records = []
    for child, record in [(False, r) for r in release['runs']] + [(True, r) for r in nested['children']]:
        folder = record['record'] if child else E + 'runs/' + record['run']
        reg, start, end = [js(folder + '/' + name + '.json') for name in ('registration', 'started', 'exit')]
        pid_key = 'pid' if child else 'owned_pid'
        assert start[pid_key] == end[pid_key] == record['pid'], folder
        assert isinstance(end['exit_code'], int) and end['exit_code'] == record['exit_code'], folder
        assert end['alive'] is record['alive'] is False and end['timed_out'] is record['timed_out'] is False, folder
        for key, value in reg.items():
            assert start[key] == value and end[key] == value, (folder, key)
        if not child:
            assert sha(read(folder + '/registered-script.py')) == reg['script_sha256'], folder
            assert end['native_sessions'] == end['background_tasks'] == 0
        for stream in ('stdout', 'stderr'):
            assert sha(read(folder + '/' + stream + '.txt')) == record[stream + '_sha256'], folder
        records.append({'record': folder, 'pid': record['pid'], 'exit_code': record['exit_code'],
                        'alive': False, 'timed_out': False, 'logs_verified': True})
    assert len(release['runs']) == 13 and len(nested['children']) == 10
    out = {
        'checked_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        'status': 'READY_FOR_INDEPENDENT_READONLY_PRODUCT_REVIEW', 'base': BASE, 'target': TARGET,
        'scope': 'Raw bytes, allowed diff, preserved old paths, input pins and recorded owned-process exits only. No candidate import or functional acceptance.',
        'worktree_clean': True, 'manifest_entries_verified_disk_and_raw_git': len(entries),
        'manifest_self_verified': True, 'changed_paths': len(changed), 'new_paths': len(changed) - len(modified),
        'modified_old_paths': modified, 'old_paths_mode_type_blob_preserved': len(old_preserved),
        'pyproject_only_exact_package_data_append': True, 'dependency_changes': False,
        'raw_input_pins_verified': len(inputs), 'compatibility_input_pins_verified': len(compatibility),
        'historical_pyproject_checkout_pin': 'Not compared to changed target checkout; raw baseline pin and exact package-data delta independently verified.',
        'fixed_cases': len(js(E + 'raw-input-pins.json')['cases']),
        'report': REPORT, 'report_sha256': sha(read(REPORT)), 'manifest': MANIFEST, 'manifest_sha256': sha(read(MANIFEST)),
        'owned_parent_process_records': len(release['runs']), 'owned_nested_process_records': len(nested['children']),
        'release_records': records, 'release_basis': 'Frozen registrations/starts/exits plus raw stdout/stderr hashes. Historical owned-process completion evidence; no OS/profile scan.',
        'author_nonzero_runs_preserved': [r['run'] for r in release['runs'] if r['exit_code'] != 0],
        'candidate_tests_run': False, 'old_matrix_rerun': False, 'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
        'accepted': False, 'integrated': False, 'remote_push': False, 'B_confirmation': False,
    }
    path = pathlib.Path(__file__).with_name('A03-R7-delivery-preflight.json')
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k != 'release_records'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
