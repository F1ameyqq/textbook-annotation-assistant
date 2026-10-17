"""File-only final audit, process release and raw Git manifest checks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle'
BASE = 'c83f956c5c29c64ab10735ba11c153201d3f3f4b'
IMPLEMENTATIONS = {'src/annotation/runtime/recovery/__init__.py', 'src/annotation/runtime/recovery/native_quality.py'}
PROFILE = 'src/annotation/contracts/a03_native/data/profile.json'
ADOPTION = 'src/annotation/contracts/a03_native/data/adoption.json'
ALLOWED = IMPLEMENTATIONS | {PROFILE, ADOPTION}
DIRS = ('examples/a03/P2-R9-R1-owner-lifecycle', 'docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle')
FILES = {'tests/test_a03_p2_r9_r1_owner_lifecycle.py', 'docs/tasks/A03-P2-R9-R1-owner-lifecycle-report.md'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args, data=None):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT, input=data)


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def tree(commit):
    return {line.split('\t', 1)[1]: line.split('\t', 1)[0].split() for line in git('ls-tree', '-r', commit).decode().splitlines()}


def inspect():
    baseline, head = tree(BASE), tree('HEAD')
    assert all(head.get(p) == row for p, row in baseline.items() if p not in ALLOWED), 'protected raw Git entry changed'
    changed = git('diff', '--name-only', BASE).decode().splitlines()
    assert not (set(changed) & set(baseline)) - ALLOWED
    assert all(p in ALLOWED | FILES or any(p.startswith(d + '/') for d in DIRS) for p in changed)
    frozen = json.loads((OUT / 'candidate-frozen.json').read_bytes())
    for row in frozen['drivers'] + frozen['product']:
        raw = (ROOT / row['path']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    expected = json.loads(git('show', BASE + ':' + PROFILE))
    for row in expected['implementation_pins']:
        name = 'src/' + row[0].lstrip('@')
        if name in IMPLEMENTATIONS:
            row[1] = sha((ROOT / name).read_bytes())
    assert json.loads((ROOT / PROFILE).read_bytes()) == expected
    expected_adoption = json.loads(git('show', BASE + ':' + ADOPTION))
    expected_adoption['profile_sha256'] = sha((ROOT / PROFILE).read_bytes())
    assert json.loads((ROOT / ADOPTION).read_bytes()) == expected_adoption
    indices = [p.read_bytes() for p in sorted((OUT / 'runs').glob('*/product-source-index.json'))]
    assert indices and len(set(indices)) == 1
    for row in json.loads(indices[0]):
        raw = (ROOT / row['path']).read_bytes()
        assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
    report = ROOT / 'docs/tasks/A03-P2-R9-R1-owner-lifecycle-report.md'
    links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', report.read_text(encoding='utf-8'))
    assert all((report.parent / link.split('#', 1)[0]).resolve().exists() for link in links)
    return {'base_entries': len(baseline), 'protected_raw_Git_entries': len(baseline) - len(ALLOWED),
        'allowed_old_paths': sorted(ALLOWED), 'all_other_product_schema_guards_producer_and_old_evidence_unchanged': True,
        'only_exact_two_implementation_pins_and_adoption_chain_updated': True, 'frozen_candidate_and_drivers_unchanged': True,
        'product_source_index_sha256': sha(indices[0]), 'all_executed_sources_identical': True,
        'report_links_checked': len(links), 'product_or_test_execution': False}


def paths():
    result = set(git('diff', '--name-only', BASE).decode().splitlines()) | FILES
    for directory in DIRS:
        result.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*') if p.is_file())
    result.discard('docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle/manifest.json')
    return sorted(result)


def seal():
    records = []
    for path in sorted(OUT.rglob('started.json')):
        start = json.loads(path.read_bytes())
        end = json.loads(path.with_name('completed.json').read_bytes())
        assert end['alive'] is False
        records.append({'path': path.relative_to(OUT).as_posix(), 'pid': start['pid'], 'parent_pid': start.get('parent_pid'),
            'exit_code': end['exit_code'], 'alive': False, 'timed_out': end.get('timed_out', end.get('timeout', False))})
    write('process-release.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'all_recorded_owned_processes_waited_and_ended': True, 'records': records, 'functional_reruns_after_failure': 0,
        'D2': 'NOT_RUN', 'delegation_platform_network': 'NONE'})
    audit = inspect()
    write('final-file-audit.json', audit)
    rows = [{'path': p, 'bytes': (ROOT / p).stat().st_size, 'sha256': sha((ROOT / p).read_bytes())} for p in paths()]
    write('manifest.json', {'base': BASE, 'status': 'REVIEW_BORROW_READ_LIMIT_EXCEPTION_EXPECTATION_FAILED',
        'excludes_only': 'this manifest', 'entries': rows})
    print(json.dumps({'entries': len(rows), 'recorded_processes_ended': len(records), **audit,
        'manifest_sha256': sha((OUT / 'manifest.json').read_bytes())}))


def check():
    audit = inspect()
    rows = json.loads((OUT / 'manifest.json').read_bytes())['entries']
    assert set(paths()) == {r['path'] for r in rows}
    indexed = {}
    for line in git('ls-files', '--stage').decode().splitlines():
        metadata, path = line.split('\t', 1)
        mode, blob, stage = metadata.split()
        assert stage == '0'
        indexed[path] = blob
    requests = []
    for row in rows:
        raw = (ROOT / row['path']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
        requests.append(indexed[row['path']])
    result = git('cat-file', '--batch', data=('\n'.join(requests) + '\n').encode())
    offset = 0
    for row in rows:
        end = result.index(b'\n', offset)
        size = int(result[offset:end].split()[2])
        raw = result[end + 1:end + 1 + size]
        assert size == row['bytes'] and sha(raw) == row['sha256'], row['path']
        offset = end + size + 2
    raw = (OUT / 'manifest.json').read_bytes()
    assert git('cat-file', 'blob', indexed['docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle/manifest.json']) == raw
    print(json.dumps({'raw_Git_blobs_verified_including_manifest': len(rows) + 1, **audit, 'manifest_sha256': sha(raw)}))


if __name__ == '__main__':
    {'seal': seal, 'check': check}[sys.argv[1]]()
