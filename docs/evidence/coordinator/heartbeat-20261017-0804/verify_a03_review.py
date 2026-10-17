"""Coordinator audit of the frozen R2 static review and its one counterexample."""
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
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R2-proposal'
MANIFEST = REVIEW / 'sha256-manifest.json'
REPORT = ROOT / 'docs/tasks/A03-P2-R2-proposal-review-report.md'
TARGET = '526d264284f36f856c306db88c1d7e71c04152e1'

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
    assert sha(MANIFEST.read_bytes()) == '5b62f0ee7c893dfd419609445a118a974219269b1e87a4b9e65f2ce402092612'
    assert sha(REPORT.read_bytes()) == '32d23d9e3f42ace9d6eadd88e7af2d45ffbaa58c765268056f78464f54898030'
    assert manifest['delivery_commit'] == TARGET and len(manifest['files']) == 177
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
    assert len(rows) == 122
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
        assert kind == b'blob' and oid.decode() == row['git_blob']
        assert raw == (ROOT / row['copy']).read_bytes()
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
archive = run('archive-verification', REVIEW / 'scripts/verify_archive.py', 0)
counterexample = run('counterexample', REVIEW / 'scripts/reproduce_counterexample.py', 1)
result = json.loads((OUT / 'counterexample.stdout.log').read_bytes())
assert result['id'] == 'R2-SCOPE-EVIDENCE-ID-01' and result['actual'] == 'STATIC_ACCEPTED'
assert result['result'] == 'FAIL_EXPECTED_REJECTION'
audit_manifest()
checks = {'task_id': 'A03', 'target_commit': TARGET, 'decision': 'REWORK_CONFIRMED',
          'review_manifest_entries': len(manifest['files']), 'review_files_including_manifest': len(manifest['files']) + 1,
          'raw_git_inputs_verified': inputs, 'review_archive_unchanged_after_reproduction': True,
          'report_sha256': sha(REPORT.read_bytes()), 'manifest_sha256': sha(MANIFEST.read_bytes()),
          'archive_command': archive, 'counterexample_command': counterexample, 'counterexample': result,
          'limited_static_acceptance': ['SESSION-02', 'CONVERSION-07'],
          'blocked_residuals': ['R17_VERSION_BRIDGE', 'REGISTRATION_SCOPE_POSITIVE'],
          'product_native_DB_platform_model_calls': 0, 'full_suite_rerun': False,
          'oracle_adopted': False, 'I01_released': False, 'remote_push': False,
          'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
          'release_basis': 'Completed independent-review turn and recorded synchronous process exits; no OS/profile scan.'}
write(OUT / 'A03-R2-review-check.json', checks)
print(json.dumps({k: checks[k] for k in ('decision', 'review_manifest_entries', 'raw_git_inputs_verified', 'full_suite_rerun')}))
