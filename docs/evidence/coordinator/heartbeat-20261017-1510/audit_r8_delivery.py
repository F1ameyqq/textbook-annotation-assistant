"""Read frozen Git objects only; never import or run the R8 candidate."""
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = '8ad45dd07214ae406a3fab28d76a4b5abd6eef03'
TARGET = 'fa6edeb7e9dd0c9502781747e5fce012931d9441'
EVIDENCE = 'docs/evidence/A03/execution/P2-R8-native-bridge/'
MANIFEST = EVIDENCE + 'manifest.json'
REPORT = 'docs/tasks/A03-P2-R8-native-bridge-delivery.md'
OUT = Path(__file__).with_name('A03-R8-delivery-preflight.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=WT)


def tree(commit):
    result = {}
    for record in git('ls-tree', '-rz', commit).split(b'\0'):
        if record:
            meta, path = record.split(b'\t', 1)
            result[path.decode('utf-8')] = tuple(meta.decode('ascii').split())
    return result


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == TARGET
    assert not git('status', '--porcelain').strip()
    before, after = tree(BASE), tree(TARGET)
    proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=WT,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cache = {}
    def blob(commit, path):
        key = commit + ':' + path
        if key not in cache:
            proc.stdin.write(key.encode('utf-8') + b'\n'); proc.stdin.flush()
            header = proc.stdout.readline().split()
            assert len(header) == 3 and header[1] == b'blob', (key, header)
            raw = proc.stdout.read(int(header[2])); assert proc.stdout.read(1) == b'\n'
            cache[key] = raw
        return cache[key]
    def data(path):
        return json.loads(blob(TARGET, path))
    try:
        manifest = data(MANIFEST)
        entries = manifest['entries']
        paths = [e['path'] for e in entries]
        assert len(paths) == len(set(paths))
        changed = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
        assert changed == set(paths) | {MANIFEST}, sorted(changed ^ (set(paths) | {MANIFEST}))
        for entry in entries:
            path = PurePosixPath(entry['path'])
            assert not path.is_absolute() and '..' not in path.parts
            raw = blob(TARGET, entry['path'])
            assert len(raw) == entry['bytes'] and sha(raw) == entry['sha256'], entry['path']
        allowed = {
            'pyproject.toml', 'src/annotation/contracts/__init__.py',
            'src/annotation/contracts/validation.py', 'src/annotation/contracts/recovery.py',
            'src/annotation/quality/targetcheck/__init__.py',
            'src/annotation/delivery/planner/__init__.py',
            'src/annotation/delivery/mock/__init__.py', 'src/annotation/delivery/mock/persistent.py',
        }
        allowed_prefixes = ('src/annotation/runtime/storage/', 'src/annotation/runtime/recovery/',
                            'src/annotation/delivery/reconciler/')
        changed_old = sorted(p for p in before if before[p] != after.get(p))
        assert all(p in after and (p in allowed or p.startswith(allowed_prefixes)) for p in changed_old)
        new_prefixes = ('src/annotation/contracts/a03_native/', *allowed_prefixes,
                        'tests/fixtures/a03/P2-R8-native-bridge/', 'examples/a03/P2-R8-native-bridge/', EVIDENCE)
        new_exact = {'src/annotation/quality/synthetic_precheck.py', 'tests/test_a03_r8_native_bridge.py', REPORT}
        assert all(p in new_exact or p.startswith(new_prefixes) for p in set(after) - set(before))
        inputs = data(EVIDENCE + 'inputs.json')
        for entry in inputs['files']:
            raw = blob(entry['commit'], entry['path'])
            assert sha(raw) == entry['sha256'] and len(raw) == entry['bytes'], entry['path']
        release = data(EVIDENCE + 'process-release.json')
        started_paths = {p for p in after if p.startswith(EVIDENCE) and p.endswith('/started.json')}
        assert started_paths == {EVIDENCE + p['path'] for p in release['owned_processes']}
        processes = []
        for record in release['owned_processes']:
            start_path = EVIDENCE + record['path']; folder = start_path.rsplit('/', 1)[0] + '/'
            started = data(start_path); completed = data(folder + 'completed.json')
            prereg = data(folder + 'preregistered.json')
            assert started['pid'] == completed['pid'] == record['pid']
            assert completed['alive'] is False and record['alive'] is False
            assert completed.get('timed_out', False) is False and record['timeout'] is False
            assert completed['exit_code'] == record['exit_code']
            assert prereg['argv'] and prereg['cwd'] and prereg['timeout_seconds'] > 0
            for stream in ('stdout', 'stderr'):
                raw = blob(TARGET, folder + stream + '.txt')
                if stream + '_sha256' in completed:
                    assert sha(raw) == completed[stream + '_sha256']
            processes.append({'path':start_path,'pid':record['pid'],'exit_code':record['exit_code'],
                              'alive':False,'timeout':False})
        assert release['all_recorded_processes_completed'] and release['product_reruns_after_stop'] == 0
        assert release['new_delegations'] == 0
        py_diff = git('diff', BASE, TARGET, '--', 'pyproject.toml').decode('utf-8')
        old_lines = [x for x in py_diff.splitlines() if x.startswith('-') and not x.startswith('---')]
        new_lines = [x for x in py_diff.splitlines() if x.startswith('+') and not x.startswith('+++')]
        assert not old_lines and new_lines == ['+"annotation.contracts.a03_native" = ["data/*.json", "data/schemas/*.json"]'], py_diff
        result = {
            'base': BASE, 'target': TARGET, 'working_tree_clean': True,
            'scope': 'Raw Git delivery/preservation and recorded process-release check only. No candidate import, functional tests, platform actions or system/profile scan.',
            'report': REPORT, 'report_sha256': sha(blob(TARGET, REPORT)),
            'manifest': MANIFEST, 'manifest_sha256': sha(blob(TARGET, MANIFEST)),
            'manifest_entries_verified': len(entries), 'changed_entries_including_manifest':len(changed),
            'input_pins_verified':len(inputs['files']),
            'old_tree_entries':len(before), 'unchanged_old_entries':len(before)-len(changed_old),
            'allowed_old_changes':changed_old, 'pyproject_append_only':True,
            'recorded_processes_verified':processes,
            'release_sha256':sha(blob(TARGET,EVIDENCE+'process-release.json')),
            'bounded_outcome_sha256':sha(blob(TARGET,EVIDENCE+'bounded-outcome.json')),
            'author_outcome': data(EVIDENCE+'bounded-outcome.json')['N1'],
            'downstream_acceptance':False, 'I01_released':False,
        }
    finally:
        proc.stdin.close(); error = proc.stderr.read(); code = proc.wait(timeout=10)
        assert code == 0 and not error
    OUT.write_bytes((json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:result[k] for k in ('target','report_sha256','manifest_sha256','manifest_entries_verified','input_pins_verified','old_tree_entries','unchanged_old_entries')}))
    print('recorded_processes_verified',len(result['recorded_processes_verified']))


if __name__ == '__main__':
    main()
