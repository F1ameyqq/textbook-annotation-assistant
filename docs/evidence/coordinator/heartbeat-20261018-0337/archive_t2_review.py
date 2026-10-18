"""Inventory already completed review; never modify failed review or run business."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/1800')
SOURCE = ROOT / '.local/A03-T2-independent-review/r1'
REVIEW = ROOT / 'docs/evidence/A03/T2/review/independent-01'
OUT = ROOT / 'docs/evidence/coordinator/heartbeat-20261018-0337'
REPORT = ROOT / 'docs/tasks/A03-T2-review-report.md'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

assert not (REVIEW / 'manifest.json').exists()
before = {p: sha(p) for p in REVIEW.rglob('*') if p.is_file()}
before[REPORT] = sha(REPORT)
copied = []
def compare(source, dest):
    assert source.is_file() and dest.is_file(), (source, dest)
    assert source.read_bytes() == dest.read_bytes(), (source, dest)
    copied.append({'source': str(source), 'archived': dest.relative_to(ROOT).as_posix(), 'sha256': sha(dest)})

for name in ('bootstrap.py', 'launch.py', 'audit.py', 'audit-r1.py', 'correct-audit.py', 'seal.py',
             'validation-plan.json', 'static-review.md', 'materialization.json', 'audit.json',
             'author-manifest-check.json', 'audit-first-failure.json', 'static-audit-correction.json'):
    compare(SOURCE / name, REVIEW / name)
execution = SOURCE / 'c/docs/evidence/A03/T2/execution'
for source, dest in [(execution / 'validation/independent-01', REVIEW / 'independent-run'),
                     (execution / 'launch/independent-01', REVIEW / 'driver-launch'),
                     (execution / 'import-processes', REVIEW / 'launch-imports'),
                     (SOURCE / 'launches', REVIEW / 'outer-processes')]:
    for file in source.rglob('*'):
        if file.is_file():
            compare(file, dest / file.relative_to(source))
for file in (REVIEW / 'static-processes').rglob('*.json'):
    compare(SOURCE / 'static-processes' / file.relative_to(REVIEW / 'static-processes'), file)

external = load(REVIEW / 'external-static-records.json')['records']
for member in external:
    path = Path(member['path'])
    path.resolve().relative_to(SOURCE.resolve())
    assert path.stat().st_size == member['bytes'] and sha(path) == member['sha256'], path

stages = []
for capture in sorted((REVIEW / 'independent-run/cases/H1/captures').glob('*/capture.json')):
    value = load(capture)
    assert value['cross_database_atomic'] is False
    for member in value['records']:
        path = capture.parent / (member['kind'] + '.sqlite3')
        assert path.stat().st_size == member['size'] and sha(path) == member['sha256']
        assert sha(Path(member['retained'])) == member['sha256']
        stages.append({'stage': capture.parent.name, 'kind': member['kind'], 'sha256': member['sha256']})
assert len(stages) == 14
audit = load(REVIEW / 'audit.json')
assert len(audit['independent_processes']) == 11
assert all(p['completed']['exit_code'] == 0 and not p['completed'].get('alive', False)
           and not p['completed'].get('timeout', False) for p in audit['independent_processes'])
release = load(REVIEW / 'final-release.json')
assert release['final_owner'] == {'generation': 3, 'lease': 0.0, 'owner': None, 'phase': 'RELEASED', 'pid': None}
assert all(not t['alive'] and t['error'] is None for t in release['keeper_release']['keepers']['all_keeper_threads'])
for raw in release['source_equals_after_report']:
    assert sha(Path(raw['source'])) == raw['sha256']
failure = load(REVIEW / 'sealing-failure.json')
assert failure['actual_exit_code'] == 1 and not failure['manifest_created']
assert all(sha(p) == digest for p, digest in before.items())

result = {'created_at': datetime.datetime.now().astimezone().isoformat(),
    'task': 'A03-T2', 'scope': 'Coordinator archive inventory only; independent acceptance still REWORK pending static closure',
    'target_commit': '699f748a124162b3118e3996c03757725daac363',
    'copied_source_pairs_verified': len(copied), 'source_pairs': copied,
    'external_static_streams_verified': len(external), 'external_streams_copied_into_repository': False,
    'raw_stage_databases_verified': stages, 'business_chain_exit0_count': 11,
    'owner_and_keeper_released': True, 'old_review_unchanged': True,
    'missing_original_manifest_preserved': True, 'failed_tools_repaired_or_rerun': False,
    'business_calls': 0, 'SQL_calls': 0, 'historical_missing_data_reconstructed': False,
    'files': [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest}
              for p, digest in sorted(before.items())],
    'limitations': ['Original reviewer manifest remains absent and original final conclusion remains REWORK.',
                   'Second sealer failure has decoded tool output only, no fabricated raw stderr or PID.',
                   'External raw Git streams remain local and are hash-bound by the original external index.',
                   'No independent acceptance, product integration, A03 completion or I01 release granted here.']}
with (OUT / 'T2-archive-inventory.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'files': len(before), 'source_pairs': len(copied), 'external_streams': len(external),
                  'stage_databases': len(stages), 'original_review_unchanged': True}))
