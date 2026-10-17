"""Coordinator audit of the frozen R4 review and original positive false rejection."""
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
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R4-bridge-registration'
MANIFEST = REVIEW / 'sha256-manifest.json'
REPORT = ROOT / 'docs/tasks/A03-P2-R4-bridge-registration-review-report.md'
TARGET = 'e608b54b973b14ff55dd2c4530153f5fe7c931f4'

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
    assert sha(MANIFEST.read_bytes()) == '311f1fb987c111b21a92ddb7ea00ec36938f6d45be1b1d56dc64a13f59f555ac'
    assert sha(REPORT.read_bytes()) == '46d2d7aa43eb5a055827ecbacfe9db67ab959575098e52378a1fe9bfa1574049'
    assert len(manifest['files']) == 198
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
    assert len(rows) == 133
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

def run(name, script, expected_exit, extra=()):
    command = [sys.executable, '-X', 'utf8', '-B', str(script), *extra]
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
positive = run('positive-replay', REVIEW / 'scripts/read_only_replay.py', 1, ['registration-positive'])
result = json.loads((OUT / 'positive-replay.stdout.log').read_bytes())
assert result['actual'] == 'FRAME_REGISTRATION_BINDING'
assert result['conclusion'] == 'REWORK_FALSE_REJECTION'
assert result['guard_phases'] == ['ACTUAL_ARTIFACT_CONSUMPTION','GLOBAL_UNBOUND_EVIDENCE']
assert result['package_calls'] == 1
assert result['error']['path'] == 'r4-static/registration-positive/prefix.json'
audit_manifest()
checks = {'task_id': 'A03', 'target_commit': TARGET, 'decision': 'REWORK_CONFIRMED',
          'interface_design': 'ACCEPTED_DESIGN_LIMITED',
          'scope': 'Interface inventory and bridge design only; registration false rejection confirmed',
          'review_manifest_entries': len(manifest['files']), 'review_files_including_manifest': len(manifest['files']) + 1,
          'raw_git_inputs_verified': inputs, 'review_archive_unchanged_after_reproduction': True,
          'report_sha256': sha(REPORT.read_bytes()), 'manifest_sha256': sha(MANIFEST.read_bytes()),
          'archive_command': archive, 'positive_command': positive, 'positive_result': result,
          'retained_limited_static_acceptance': ['EVIDENCE_RECORD_CONSUMER_CLOSURE','SESSION-02', 'CONVERSION-07'],
          'blocked_residuals': ['R17_PRODUCT_VERSION_BRIDGE', 'REGISTRATION_CONTEXT_AND_TARGET'],
          'product_native_DB_platform_model_calls': 0, 'full_suite_rerun': False,
          'oracle_adopted': False, 'I01_released': False, 'integrated':False, 'remote_push': False,
          'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
          'release_basis': 'Completed independent-review turn and recorded synchronous process exits; no OS/profile scan.'}
write(OUT / 'A03-R4-review-check.json', checks)
print(json.dumps({k: checks[k] for k in ('decision','interface_design', 'review_manifest_entries', 'raw_git_inputs_verified', 'full_suite_rerun')}))
