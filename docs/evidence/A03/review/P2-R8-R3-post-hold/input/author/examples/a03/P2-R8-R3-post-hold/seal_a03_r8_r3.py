"""R3 file-only seal and raw-index verification; no product/test execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R3-post-hold'
BASE = '58d8a64734271d15654bb00b03d760f0f3eccd10'
ALLOWED = {'src/annotation/runtime/storage/native.py', 'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args, data=None):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT, input=data)


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def tree(commit):
    return {line.split('\t', 1)[1]: line.split('\t', 1)[0].split() for line in git('ls-tree', '-r', commit).decode().splitlines()}


def inspect():
    baseline, head = tree(BASE), tree('HEAD')
    if any(head.get(path) != value for path, value in baseline.items() if path not in ALLOWED):
        raise RuntimeError('old protected raw Git entry differs')
    if any(path in baseline and path not in ALLOWED for path in git('diff', '--name-only', BASE).decode().splitlines()):
        raise RuntimeError('old out-of-scope file changed')
    package = ROOT / 'src/annotation/contracts/a03_native'
    profile_path = package / 'data/profile.json'
    current = json.loads(profile_path.read_bytes())
    expected = json.loads(git('show', BASE + ':src/annotation/contracts/a03_native/data/profile.json'))
    for row in expected['implementation_pins']:
        if row[0] == '@annotation/runtime/storage/native.py':
            row[1] = sha((ROOT / 'src/annotation/runtime/storage/native.py').read_bytes())
    if current != expected:
        raise RuntimeError('profile changed beyond exact native implementation pin')
    expected_adoption = json.loads(git('show', BASE + ':src/annotation/contracts/a03_native/data/adoption.json'))
    expected_adoption['profile_sha256'] = sha(profile_path.read_bytes())
    if json.loads((package / 'data/adoption.json').read_bytes()) != expected_adoption:
        raise RuntimeError('adoption changed beyond profile identity')
    for logical, expected_sha in current['implementation_pins']:
        path = ROOT / 'src/annotation' / logical[len('@annotation/'):] if logical.startswith('@annotation/') else package / logical
        if sha(path.read_bytes()) != expected_sha:
            raise RuntimeError('implementation pin differs: ' + logical)
    for logical, expected_sha in current['schema_pins']:
        if sha((package / 'data' / logical).read_bytes()) != expected_sha:
            raise RuntimeError('schema pin differs')
    labels = ('local', 'N1', 'N2', 'N3', 'N4', 'N5', 'N7', 'C01', 'A02', 'R7')
    indices = [(OUT / 'runs' / name / 'product-source-index.json').read_bytes() for name in labels]
    if len(set(indices)) != 1:
        raise RuntimeError('executed product source identities differ')
    report = ROOT / 'docs/tasks/A03-P2-R8-R3-post-hold-report.md'
    links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', report.read_text(encoding='utf-8'))
    for link in links:
        if not (report.parent / link.split('#', 1)[0]).resolve().exists():
            raise RuntimeError('missing report link: ' + link)
    return len(baseline) - len(ALLOWED), len(links), sha(indices[0])


def paths():
    result = set(git('diff', '--name-only', BASE).decode().splitlines())
    for name in ('examples/a03/P2-R8-R3-post-hold', 'tests/fixtures/a03/P2-R8-R3-post-hold', 'docs/evidence/A03/execution/P2-R8-R3-post-hold'):
        result.update(path.relative_to(ROOT).as_posix() for path in (ROOT / name).rglob('*') if path.is_file())
    result.update(('tests/test_a03_r8_r3_local.py', 'tests/test_a03_r8_r3_post_hold.py', 'docs/tasks/A03-P2-R8-R3-post-hold-report.md'))
    result.discard('docs/evidence/A03/execution/P2-R8-R3-post-hold/manifest.json')
    return sorted(result)


def seal():
    records = []
    for path in sorted(OUT.rglob('started.json')):
        started = json.loads(path.read_bytes())
        completed = json.loads(path.with_name('completed.json').read_bytes())
        if completed.get('alive') is not False:
            raise RuntimeError('owned process not completed')
        records.append({'path': path.relative_to(OUT).as_posix(), 'pid': started['pid'], 'exit_code': completed['exit_code'],
            'alive': False, 'timeout': completed.get('timed_out', completed.get('timeout', False))})
    write('process-release.json', {'recorded_at': datetime.now(timezone.utc).isoformat(), 'records': records,
        'all_recorded_processes_waited_and_ended': True, 'product_paths_rerun_after_N7_failure': 0,
        'delegation_network_platform_browser_credentials_models': 'NOT_USED'})
    preserved, links, index_sha = inspect()
    write('final-file-audit.json', {'protected_base_raw_Git_entries': preserved, 'allowed_old_paths': sorted(ALLOWED),
        'shared_lease_projection_producer_contract_schema_and_old_evidence_unchanged': True,
        'only_native_post_hold_interface_and_affected_pins_changed': True,
        'executed_candidate_source_index_sha256': index_sha, 'local_N1_N2_N3_N4_N5_N7_and_compat_sources_identical': True,
        'report_links_checked': links, 'product_test_execution_by_file_audit': 0})
    rows = [{'path': path, 'bytes': (ROOT / path).stat().st_size, 'sha256': sha((ROOT / path).read_bytes())} for path in paths()]
    write('manifest.json', {'base': BASE, 'source_target': git('rev-parse', 'HEAD').decode().strip(),
        'status': 'REVIEW_N7_DIAGNOSTIC_ASSERTION_FAILED', 'excludes_only': 'this manifest', 'entries': rows})
    print(json.dumps({'entries': len(rows), 'recorded_processes_ended': len(records), 'protected_base_entries': preserved,
        'manifest_sha256': sha((OUT / 'manifest.json').read_bytes())}))


def check():
    inspect()
    manifest = json.loads((OUT / 'manifest.json').read_bytes())
    rows = manifest['entries']
    if set(paths()) != {row['path'] for row in rows}:
        raise RuntimeError('manifest set mismatch')
    staged = {}
    for line in git('ls-files', '--stage').decode().splitlines():
        metadata, path = line.split('\t', 1)
        mode, blob, stage = metadata.split()
        if stage != '0':
            raise RuntimeError('unmerged stage')
        staged[path] = blob
    requested = []
    for row in rows:
        raw = (ROOT / row['path']).read_bytes()
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise RuntimeError('frozen worktree file changed: ' + row['path'])
        requested.append(staged[row['path']])
    data = git('cat-file', '--batch', data=('\n'.join(requested) + '\n').encode())
    offset = 0
    for row in rows:
        end = data.index(b'\n', offset)
        length = int(data[offset:end].split()[2])
        raw = data[end + 1:end + 1 + length]
        if length != row['bytes'] or sha(raw) != row['sha256']:
            raise RuntimeError('raw Git blob differs: ' + row['path'])
        offset = end + length + 2
    print(json.dumps({'raw_Git_blobs_verified': len(rows), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()), 'product_or_test_execution': False}))


if __name__ == '__main__':
    if sys.argv[1] == 'seal':
        seal()
    elif sys.argv[1] == 'check':
        check()
    else:
        raise SystemExit('file-only operation required')
