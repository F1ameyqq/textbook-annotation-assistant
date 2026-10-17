"""Verify frozen R11 failure-package bytes and release only; no product imports."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

ROOT = Path('D:/1800')
PREFIX = 'docs/evidence/A03/review/P2-R11-crash-cuts/'
EVIDENCE = ROOT / PREFIX
OUT = ROOT / 'docs/evidence/coordinator/heartbeat-20261018-0745'
REPORT = 'docs/tasks/A03-P2-R11-crash-cuts-review-report.md'
TARGET = 'cc5966dc58c62017a27266c40ca0cedc5c68485c'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read_json(path):
    return json.loads(path.read_bytes())

manifest_path = EVIDENCE / 'sha256-manifest.json'
manifest_bytes = manifest_path.read_bytes()
assert sha(manifest_bytes) == 'eff77340f2577d1cf66eaa3c69ad4609b2673b87002951333d7f856b158f494c'
manifest = json.loads(manifest_bytes)
entries = manifest['files']
paths = {row['path'] for row in entries}
assert len(entries) == len(paths) == 1208
actual = {p.relative_to(ROOT).as_posix() for p in EVIDENCE.rglob('*') if p.is_file()}
assert paths | {PREFIX + 'sha256-manifest.json'} == actual | {REPORT}
for row in entries:
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']

inputs = read_json(EVIDENCE / 'input-index.json')['exports']
queries = [row['commit'] + ':' + row['path'] for row in inputs]
batch = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'cat-file', '--batch'],
                                cwd=ROOT, input=('\n'.join(queries) + '\n').encode())
offset = 0
for row in inputs:
    end = batch.index(b'\n', offset)
    header = batch[offset:end].split()
    assert header[1] == b'blob'
    length = int(header[2])
    raw = batch[end + 1:end + 1 + length]
    assert sha(raw) == row['sha256'] and length == row['bytes'], row['path']
    assert header[0].decode() == row['raw_git_sha1']
    assert raw == (EVIDENCE / row['file']).read_bytes(), row['file']
    offset = end + length + 2
assert offset == len(batch)

seed = read_json(EVIDENCE / 'isolated-source-index.json')['files']
for row in seed:
    raw = (EVIDENCE / row['file']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['file']

release_path = EVIDENCE / 'process-release.json'
release_bytes = release_path.read_bytes()
assert sha(release_bytes) == 'eded396dddfa7b46d1b4e0c35bd5ed9af9853ba9d2ad89ce955e36c5d6c98d4a'
release = json.loads(release_bytes)
checked = []
for group in ['review_and_functional_parents', 'git_children', 'nested_business_and_observation_children']:
    for row in release[group]:
        folder = EVIDENCE / row['record']
        registration = folder / ('registration.json' if (folder / 'registration.json').exists() else 'preregistered.json')
        completion = folder / ('completion.json' if (folder / 'completion.json').exists() else 'completed.json')
        assert sha(registration.read_bytes()) == row['registration_sha256']
        assert sha(completion.read_bytes()) == row['completion_sha256']
        start = read_json(folder / 'started.json')
        finish = read_json(completion)
        assert row['pid'] == start['pid'] == finish['pid']
        assert row['exit_code'] == finish['exit_code']
        assert finish.get('alive', finish.get('alive_after_wait')) is False
        assert finish.get('timed_out', finish.get('timeout', False)) is False
        for stream in ['stdout', 'stderr']:
            candidates = [folder / (stream + ext) for ext in ['.log', '.bin', '.txt']]
            matches = [p for p in candidates if p.exists() and sha(p.read_bytes()) == row[stream + '_sha256']]
            assert matches, (row['record'], stream)
        checked.append({'record': row['record'], 'pid': row['pid'], 'exit_code': row['exit_code']})
wrapper = read_json(EVIDENCE / 'seal-recorder-completion.json')
assert wrapper == release['seal_recorder_wrapper']
assert wrapper['exit_code'] == 0 and not wrapper['alive'] and not wrapper['timed_out']
assert read_json(EVIDENCE / 'seal-recorder-started.json')['pid'] == wrapper['pid']
for stream in ['stdout', 'stderr']:
    assert sha((EVIDENCE / ('seal-recorder.' + stream + '.log')).read_bytes()) == wrapper[stream + '_sha256']
checked.append({'record': 'seal-recorder', 'pid': wrapper['pid'], 'exit_code': wrapper['exit_code']})
assert len(checked) == release['known_registered_child_count'] == 33
assert len({row['pid'] for row in checked}) == 33
failures = {row['record'] for row in checked if row['exit_code'] == 1}
assert failures == {'runs/process-audit-01', 'runs/report-01'}
assert sum(row['exit_code'] == 90 for row in checked) == 4

outcome = read_json(EVIDENCE / 'final-outcome.json')
assert outcome['target'] == TARGET and outcome['status'] == 'REWORK'
assert outcome['functional_reruns'] == 0
assert not outcome['second_failure_corrected_or_retried']
report_bytes = (ROOT / REPORT).read_bytes()
assert sha(report_bytes) == 'a964ef76d836c9935dd391ad72e073f49395196ffbcd5aa43040a8cd5498127c'
assert manifest_path.read_bytes() == manifest_bytes
result = {
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'decision': 'REWORK_FAILURE_ARCHIVE_VERIFIED_NOT_ACCEPTED',
    'target_commit': TARGET,
    'report': REPORT, 'report_sha256': sha(report_bytes),
    'manifest': PREFIX + 'sha256-manifest.json', 'manifest_sha256': sha(manifest_bytes),
    'manifest_entries_verified': len(entries), 'raw_git_inputs_verified': len(inputs),
    'source_seed_bytes_verified': len(seed),
    'process_release': PREFIX + 'process-release.json', 'process_release_sha256': sha(release_bytes),
    'process_records_checked': checked,
    'archive_failures_retained': sorted(failures),
    'second_failure': 'report-01 source encoding SyntaxError before report generation; one earlier static metadata correction already used',
    'author_intermediate_binary_limit': 'PRESERVED_NOT_RETROACTIVELY_REPAIRED',
    'coordinator_product_imports': 0, 'coordinator_functional_runs': 0,
    'coordinator_SQL_checks': 0, 'OS_PID_scan': False,
    'scope': 'Bytes, exact Git inputs, completed-turn release records and declared failure boundary only; functional claims not independently corroborated by coordinator yet.',
    'whole_A03_accepted': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
}
with (OUT / 'review-failure-preflight.json').open('xb') as f:
    f.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps({key: result[key] for key in ['decision', 'manifest_entries_verified', 'raw_git_inputs_verified', 'source_seed_bytes_verified', 'archive_failures_retained']}, ensure_ascii=False))
