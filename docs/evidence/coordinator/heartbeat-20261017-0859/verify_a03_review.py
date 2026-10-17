"""Coordinator audit of the frozen R3 static review and its original counterexample."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('D:/1800')
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R3-evidence-closure'
MANIFEST = REVIEW / 'sha256-manifest.json'
REPORT = ROOT / 'docs/tasks/A03-P2-R3-evidence-closure-review-report.md'
TARGET = '87606b73e0754fa670491d9fb958a416c26bfe88'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def audit_manifest():
    manifest = load(MANIFEST)
    assert sha(MANIFEST.read_bytes()) == '676db217f198842bb8f2f5e0222b295d876815bf6b633da9dab44083372eedaf'
    assert sha(REPORT.read_bytes()) == '4da6e53d451875b285c0ee24e9fafa83d35e6dbcfc0f9af9c592958fe3fd992b'
    assert len(manifest['files']) == 249
    assert load(REVIEW / 'input-index.json')['delivery'] == TARGET
    expected = {row['path'] for row in manifest['files']}
    actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file() and p != MANIFEST}
    actual.add(REPORT.relative_to(ROOT).as_posix())
    assert expected == actual
    for row in manifest['files']:
        path = (ROOT / row['path']).resolve()
        assert path.is_relative_to(ROOT)
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    return manifest

def audit_inputs():
    rows = load(REVIEW / 'input-index.json')['files']
    assert len(rows) == 161
    requests = [row['commit'] + ':' + row['path'] for row in rows]
    result = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
                            input=('\n'.join(requests) + '\n').encode(), capture_output=True, timeout=30)
    assert result.returncode == 0
    data = result.stdout
    offset = 0
    for row in rows:
        end = data.index(b'\n', offset)
        oid, kind, size = data[offset:end].split()
        offset = end + 1
        raw = data[offset:offset + int(size)]
        offset += int(size)
        assert data[offset:offset + 1] == b'\n'
        offset += 1
        assert kind == b'blob' and oid.decode() == row['raw_git_sha1']
        assert raw == (REVIEW / row['file']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert offset == len(data)
    return len(rows)

def run(name, script, expected_exit):
    command = [sys.executable, '-X', 'utf8', '-B', str(script)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env.pop('PYTHONPATH', None)
    start = time.monotonic()
    with (OUT / (name + '.stdout.log')).open('xb') as stdout, (OUT / (name + '.stderr.log')).open('xb') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        write(OUT / (name + '.start.json'), {'argv': command, 'cwd': str(ROOT), 'pid': process.pid,
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'timeout_seconds': 30, 'PYTHONPATH': 'REMOVED', 'source_sha256': sha(script.read_bytes())})
        timed_out = False
        try:
            code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=5)
    record = {'argv': command, 'cwd': str(ROOT), 'pid': process.pid, 'exit_code': code,
              'expected_exit_code': expected_exit, 'elapsed_seconds': time.monotonic() - start,
              'timed_out': timed_out, 'alive': process.poll() is None}
    write(OUT / (name + '.completion.json'), record)
    assert not timed_out and code == expected_exit
    return record

manifest = audit_manifest()
inputs = audit_inputs()
archive = run('archive-verification', REVIEW / 'scripts/archive.py', 0)
counterexample = run('counterexample', REVIEW / 'scripts/replay_frozen.py', 0)
result = json.loads((OUT / 'counterexample.stdout.log').read_bytes())
assert 'UNDECLARED_REFERENCE' in json.dumps(result)
audit_manifest()
checks = {'task_id': 'A03', 'target_commit': TARGET, 'decision': 'ACCEPTED_STATIC_LIMITED',
          'scope': 'EvidenceRecord consumer closure only',
          'review_manifest_entries': len(manifest['files']), 'review_files_including_manifest': len(manifest['files']) + 1,
          'raw_git_inputs_verified': inputs, 'review_archive_unchanged_after_reproduction': True,
          'report_sha256': sha(REPORT.read_bytes()), 'manifest_sha256': sha(MANIFEST.read_bytes()),
          'archive_command': archive, 'counterexample_command': counterexample, 'counterexample': result,
          'retained_limited_static_acceptance': ['SESSION-02', 'CONVERSION-07'],
          'blocked_residuals': ['R17_VERSION_BRIDGE', 'REGISTRATION_SCOPE_POSITIVE'],
          'product_native_DB_platform_model_calls': 0, 'full_suite_rerun': False,
          'oracle_adopted': False, 'I01_released': False, 'remote_push': False,
          'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
          'release_basis': 'Completed independent-review turn and recorded synchronous process exits; no OS/profile scan.'}
write(OUT / 'A03-R3-review-check.json', checks)
print(json.dumps({k: checks[k] for k in ('decision', 'review_manifest_entries', 'raw_git_inputs_verified', 'full_suite_rerun')}))
