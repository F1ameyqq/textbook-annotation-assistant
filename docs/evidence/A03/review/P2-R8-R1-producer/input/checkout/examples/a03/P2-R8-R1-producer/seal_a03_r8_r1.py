"""R1 file-only release/manifest audit; never imports product or reruns tests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R1-producer'
BASE = 'fa6edeb7e9dd0c9502781747e5fce012931d9441'
ALLOWED_OLD = {'src/annotation/quality/synthetic_precheck.py',
    'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args, data=None):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT, input=data)


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def trees(ref):
    return {line.split('\t', 1)[1]: line.split('\t', 1)[0].split() for line in git('ls-tree', '-r', ref).decode().splitlines()}


def inspect():
    base, head = trees(BASE), trees('HEAD')
    for path, value in base.items():
        if path not in ALLOWED_OLD and head.get(path) != value:
            raise RuntimeError('protected raw Git entry differs: ' + path)
    for name in git('diff', '--name-only', BASE).decode().splitlines():
        if name in base and name not in ALLOWED_OLD:
            raise RuntimeError('old path out of scope: ' + name)
    package = ROOT / 'src/annotation/contracts/a03_native'
    current = json.loads((package / 'data/profile.json').read_bytes())
    before = json.loads(git('show', BASE + ':src/annotation/contracts/a03_native/data/profile.json'))
    expected = json.loads(json.dumps(before))
    for row in expected['implementation_pins']:
        if row[0] == '@annotation/quality/synthetic_precheck.py':
            row[1] = sha((ROOT / 'src/annotation/quality/synthetic_precheck.py').read_bytes())
    if current != expected:
        raise RuntimeError('profile contains more than the permitted producer pin change')
    before_adoption = json.loads(git('show', BASE + ':src/annotation/contracts/a03_native/data/adoption.json'))
    before_adoption['profile_sha256'] = sha((package / 'data/profile.json').read_bytes())
    if json.loads((package / 'data/adoption.json').read_bytes()) != before_adoption:
        raise RuntimeError('adoption changed beyond profile identity')
    for logical, pin in current['implementation_pins']:
        path = ROOT / 'src/annotation' / logical[len('@annotation/'):] if logical.startswith('@annotation/') else package / logical
        if sha(path.read_bytes()) != pin:
            raise RuntimeError('implementation pin differs: ' + logical)
    for logical, pin in current['schema_pins']:
        if sha((package / 'data' / logical).read_bytes()) != pin:
            raise RuntimeError('schema pin differs')
    sources = [(OUT / 'runs' / label / 'product-source-index.json').read_bytes() for label in ('minimal', 'N1', 'C01', 'A02', 'R7')]
    if len(set(sources)) != 1:
        raise RuntimeError('final candidate source identities differ across validation/compatibility')
    report = ROOT / 'docs/tasks/A03-P2-R8-R1-producer-report.md'
    links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', report.read_text(encoding='utf-8'))
    for link in links:
        if not (report.parent / link.split('#', 1)[0]).resolve().exists():
            raise RuntimeError('broken report link: ' + link)
    return len(base) - len(ALLOWED_OLD), len(links), sha(sources[0])


def covered_paths():
    result = set(git('diff', '--name-only', BASE).decode().splitlines())
    for name in ('examples/a03/P2-R8-R1-producer', 'tests/fixtures/a03/P2-R8-R1-producer',
                 'docs/evidence/A03/execution/P2-R8-R1-producer'):
        result.update(p.relative_to(ROOT).as_posix() for p in (ROOT / name).rglob('*') if p.is_file())
    result.update(('tests/test_a03_r8_r1_minimal.py', 'tests/test_a03_r8_r1_producer.py', 'docs/tasks/A03-P2-R8-R1-producer-report.md'))
    result.discard('docs/evidence/A03/execution/P2-R8-R1-producer/manifest.json')
    return sorted(result)


def seal():
    records = []
    for path in sorted(OUT.rglob('started.json')):
        start = json.loads(path.read_bytes())
        completed_path = path.with_name('completed.json')
        if not completed_path.is_file():
            raise RuntimeError('process completion missing')
        end = json.loads(completed_path.read_bytes())
        if end.get('alive') is not False:
            raise RuntimeError('owned process remains alive')
        records.append({'path': path.relative_to(OUT).as_posix(), 'pid': start['pid'], 'exit_code': end['exit_code'],
            'alive': False, 'timeout': end.get('timed_out', end.get('timeout', False))})
    write('process-release.json', {'recorded_at': datetime.now(timezone.utc).isoformat(), 'records': records,
        'all_recorded_processes_waited_and_ended': True, 'product_reruns_after_N1_failure': 0,
        'delegation': False, 'platform_browser_profile_network': 'NOT_USED'})
    protected, links, source_index_sha = inspect()
    write('final-file-audit.json', {'protected_raw_Git_entries': protected, 'allowed_old_paths': sorted(ALLOWED_OLD),
        'only_producer_and_affected_pins_changed': True, 'old_R7_R8_bytes_unchanged': True,
        'schema_and_public_helper_unchanged': True, 'final_candidate_validation_source_index_sha256': source_index_sha,
        'minimal_N1_C01_A02_R7_sources_identical': True, 'report_links_checked': links,
        'product_tests_executed_by_file_audit': 0})
    entries = [{'path': name, 'bytes': (ROOT / name).stat().st_size, 'sha256': sha((ROOT / name).read_bytes())} for name in covered_paths()]
    write('manifest.json', {'base': BASE, 'source_target': git('rev-parse', 'HEAD').decode().strip(),
        'status': 'REVIEW_N1_BLOCKED', 'excludes_only': 'this manifest', 'entries': entries})
    print(json.dumps({'entries': len(entries), 'owned_processes_ended': len(records), 'protected_base_entries': protected,
        'manifest_sha256': sha((OUT / 'manifest.json').read_bytes())}))


def check():
    inspect()
    manifest = json.loads((OUT / 'manifest.json').read_bytes())
    entries = manifest['entries']
    if set(covered_paths()) != {row['path'] for row in entries}:
        raise RuntimeError('manifest set mismatch')
    staged = {}
    for line in git('ls-files', '--stage').decode().splitlines():
        metadata, path = line.split('\t', 1)
        mode, blob, stage = metadata.split()
        if stage != '0':
            raise RuntimeError('unmerged stage')
        staged[path] = blob
    wanted = []
    for row in entries:
        body = (ROOT / row['path']).read_bytes()
        if len(body) != row['bytes'] or sha(body) != row['sha256']:
            raise RuntimeError('frozen file bytes changed: ' + row['path'])
        wanted.append(staged[row['path']])
    stream = git('cat-file', '--batch', data=('\n'.join(wanted) + '\n').encode())
    offset = 0
    for row in entries:
        end = stream.index(b'\n', offset)
        length = int(stream[offset:end].split()[2])
        body = stream[end + 1:end + 1 + length]
        if length != row['bytes'] or sha(body) != row['sha256']:
            raise RuntimeError('raw staged blob differs: ' + row['path'])
        offset = end + length + 2
    print(json.dumps({'raw_Git_blobs_verified': len(entries), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
        'product_or_test_execution': False}))


if __name__ == '__main__':
    if sys.argv[1] == 'seal':
        seal()
    elif sys.argv[1] == 'check':
        check()
    else:
        raise SystemExit('unsupported file operation')
