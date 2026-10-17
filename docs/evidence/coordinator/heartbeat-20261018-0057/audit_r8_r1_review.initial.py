"""Bounded coordinator verification: raw bytes, release and immutable SQL only."""
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R8-R1-producer'
OUT = Path(__file__).parent
REPORT = 'docs/tasks/A03-P2-R8-R1-producer-review-report.md'
TARGET = 'a0c40886f3076f84c46377e03fc2206d2fdc5585'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

manifest_path = REVIEW / 'sha256-manifest.json'
assert sha(manifest_path.read_bytes()) == '13406d827e98d1e158ddd78592b00f1efbf328e53a340afa43a9d4c046edba4e'
assert sha((ROOT / REPORT).read_bytes()) == '37ad11cbecefcfc97c2c1487786f66418bd231c79e7b7654bd9d6c7a8fbf9cbf'
manifest = read(manifest_path)
entries = manifest['files']
listed = {e['path'] for e in entries}
assert len(listed) == len(entries)
actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file()}
actual.add(REPORT)
assert actual == listed | {manifest_path.relative_to(ROOT).as_posix()}
for entry in entries:
    data = (ROOT / entry['path']).read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], entry['path']

exports = read(REVIEW / 'input-index.json')['exports']
specs = [e['commit'] + ':' + e['path'] for e in exports]
raw = subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(WT), 'cat-file', '--batch'], input=('\n'.join(specs) + '\n').encode())
pos = 0
for entry in exports:
    end = raw.index(b'\n', pos)
    oid, kind, size = raw[pos:end].decode().split()
    assert kind == 'blob'
    pos = end + 1
    data = raw[pos:pos + int(size)]
    pos += int(size) + 1
    assert oid == entry['raw_git_sha1'] and len(data) == entry['bytes'] and sha(data) == entry['sha256'], entry['path']
    assert data == (REVIEW / entry['file']).read_bytes(), entry['file']
assert pos == len(raw)

release = read(REVIEW / 'process-release.json')
for item in release['runs']:
    run = REVIEW / 'runs' / item['run']
    for filename, key in [('registration.json', 'registration_sha256'), ('completion.json', 'completion_sha256'), ('entry-source.py', 'entry_sha256'), ('stdout.log', 'stdout_sha256'), ('stderr.log', 'stderr_sha256')]:
        assert sha((run / filename).read_bytes()) == item[key]
    registration, start, finish = [read(run / name) for name in ['registration.json', 'started.json', 'completion.json']]
    assert start['pid'] == finish['pid'] == item['pid']
    assert finish['argv'] == registration['argv'] and finish['cwd'] == registration['cwd']
    assert finish['exit_code'] == item['exit_code'] == 0
    assert not finish['timed_out'] and not finish['alive_after_wait'] and not item['alive']

db_inputs = [e for e in exports if e['path'].endswith('.sqlite3')]
assert len(db_inputs) == 2
tmp_parent = Path(tempfile.gettempdir()).resolve()
tmp = Path(tempfile.mkdtemp(prefix='a03-coordinator-r8-r1-', dir=str(tmp_parent))).resolve()
assert tmp.parent == tmp_parent and tmp.name.startswith('a03-coordinator-r8-r1-')
snapshots = {}
try:
    for i, entry in enumerate(db_inputs):
        original = REVIEW / entry['file']
        data = original.read_bytes()
        copy = tmp / ('copy-' + str(i) + '.sqlite3')
        copy.write_bytes(data)
        conn = sqlite3.connect(copy.as_uri() + '?mode=ro&immutable=1', uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        assert conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        if entry['path'].endswith('/runtime.sqlite3'):
            names = ['actions', 'plans', 'intents', 'registrations', 'artifacts', 'native_pre_runs', 'native_report_reads', 'permits']
            snapshots['runtime'] = {name: [dict(r) for r in conn.execute('SELECT * FROM ' + name)] for name in names}
        else:
            snapshots['effects'] = conn.execute('SELECT count(*) FROM effects').fetchone()[0]
        conn.close()
        assert sha(copy.read_bytes()) == sha(data) == sha(original.read_bytes())
        copy.unlink()
finally:
    # Only this check's explicit files; no recursive deletion.
    for copy in tmp.glob('copy-*.sqlite3'):
        copy.unlink()
    tmp.rmdir()

rows = snapshots['runtime']
action, plan, intent, reg = [rows[name][0] for name in ['actions', 'plans', 'intents', 'registrations']]
assert all(len(rows[name]) == 1 for name in ['actions', 'plans', 'intents', 'registrations', 'native_pre_runs', 'permits'])
assert rows['native_pre_runs'][0]['status'] == 'ADMITTED'
assert rows['permits'][0]['state'] == 'CONSUMED' and snapshots['effects'] == 1
assert intent['receipt'] is None and len(rows['native_report_reads']) == 0
def exported_absolute(original):
    relative = Path(original).relative_to(WT).as_posix()
    return REVIEW / 'input/checkout' / relative

fact_ref = json.loads(action['fact'])
fact_file = exported_absolute(str(Path(reg['package_root']) / fact_ref['path']))
assert sha(fact_file.read_bytes()) == fact_ref['sha256']
fact = read(fact_file)
bundle = read(exported_absolute(reg['bundle_path']))
assert not any(a['kind'] == 'ExecutionReceipt' for a in bundle['artifacts'])
progress = [a for a in bundle['artifacts'] if a['kind'] == 'ExecutionProgress']
assert len(progress) == 2
assert any(a['payload']['actions'][0]['effective_outcome'] == 'UNKNOWN' for a in progress)
assert all(a['payload']['actions'][0]['result_fact'] is None for a in progress)
source = (REVIEW / 'input/checkout/src/annotation/runtime/storage/__init__.py').read_text(encoding='utf-8')
assert '"attempt_fact": "NOT_ATTEMPTED" if not intent else "MAY_HAVE_BEEN_ATTEMPTED" if row["state"] in ("INTENT", "UNKNOWN") else "ATTEMPTED"' in source
assert action['state'] == 'APPLIED' and action['intent'] == intent['id']
comparison = {
    'plan_ref': fact['plan_ref'] == json.loads(plan['ref']),
    'action_id': fact['action_id'] == action['id'],
    'intent_ref': fact['intent_ref'] == json.loads(intent['ref']),
    'attempt_fact': fact['result']['attempt_fact'] == 'ATTEMPTED',
}
assert comparison == {'plan_ref': True, 'action_id': True, 'intent_ref': True, 'attempt_fact': False}
assert fact['result']['attempt_fact'] == 'MAY_HAVE_BEEN_ATTEMPTED'

result = {
    'at': datetime.now().astimezone().isoformat(), 'target_commit': TARGET,
    'decision': 'REWORK_CONFIRMED_COVERAGE_GAP_CLOSED',
    'manifest_entries': len(entries), 'total_review_files': len(actual),
    'review_report_sha256': sha((ROOT / REPORT).read_bytes()),
    'review_manifest_sha256': sha(manifest_path.read_bytes()),
    'raw_git_exports_verified': len(exports), 'review_processes_exited': len(release['runs']),
    'coordinator_check': 'Raw bytes and five release records; two self-owned immutable DB copies, exact fact resource and four static projection comparisons.',
    'four_guard_fields_equal': comparison, 'fact_attempt_fact': fact['result']['attempt_fact'],
    'projection_attempt_fact_static_inference': 'ATTEMPTED', 'projection_artifact_created': False,
    'effect_count': snapshots['effects'], 'PRE_status': rows['native_pre_runs'][0]['status'],
    'registered_receipt_present': False, 'original_UNKNOWN_preserved': True,
    'native_report_reads': 0, 'candidate_imports': 0, 'functional_tests_run': False,
    'product_mutations': 0, 'original_DB_opened': False, 'temporary_copies_removed': True,
    'A03_functional_acceptance': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
}
(OUT / 'review-audit.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(result, ensure_ascii=False))
