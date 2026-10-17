"""Coordinator read-only corroboration. No candidate imports or functional reruns."""
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R9-failure'
TARGET = 'c83f956c5c29c64ab10735ba11c153201d3f3f4b'
AUTHOR = 'C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


report = ROOT / 'docs/tasks/A03-P2-R9-failure-review-report.md'
manifest = REVIEW / 'sha256-manifest.json'
release_file = REVIEW / 'process-release.json'
assert sha(report.read_bytes()) == '8c8302ff0ca1e4adb69d4c22de4131ca8ba713494a485f02d7fd89d2448e3a0e'
assert sha(manifest.read_bytes()) == '9940f5501acd392a5a29fbdddc7ffd249b6632d35a1ce7e370a95ae1d64f75a7'
assert sha(release_file.read_bytes()) == '791686a788d9db5e33cb79c2b0fe89937f4956b1ea49f8e016cd8a75be00985a'
entries = read(manifest)['files']
assert len(entries) == len({e['path'] for e in entries}) == 351
actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file()} | {report.relative_to(ROOT).as_posix()}
assert actual == {e['path'] for e in entries} | {manifest.relative_to(ROOT).as_posix()}
for entry in entries:
    data = (ROOT / entry['path']).read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], entry['path']

index = read(REVIEW / 'input-index.json')
assert index['target'] == TARGET
exports = index['exports']
batch = subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(ROOT), 'cat-file', '--batch'],
    input=('\n'.join(e['commit'] + ':' + e['path'] for e in exports) + '\n').encode())
pos = 0
for entry in exports:
    end = batch.index(b'\n', pos)
    oid, kind, size = batch[pos:end].decode().split()
    pos = end + 1
    data = batch[pos:pos + int(size)]
    pos += int(size) + 1
    assert kind == 'blob' and oid == entry['raw_git_sha1']
    assert data == (REVIEW / entry['file']).read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256']
assert pos == len(batch) and len(exports) == 273

release = read(release_file)
assert release['known_registered_child_count'] == 10
for item in release['review_checks']:
    folder = REVIEW / 'runs' / item['run']
    done = read(folder / 'completion.json')
    assert done['pid'] == read(folder / 'started.json')['pid'] == item['pid']
    assert done['exit_code'] == item['exit_code'] == (1 if item['run'] == 'independent-review-01' else 0)
    assert not done['alive_after_wait'] and not done['timed_out']
    for filename, key in [('registration.json', 'registration_sha256'), ('completion.json', 'completion_sha256'),
                          ('entry-source.py', 'entry_sha256'), ('stdout.log', 'stdout_sha256'), ('stderr.log', 'stderr_sha256')]:
        assert sha((folder / filename).read_bytes()) == item[key]
for item in release['git_children']:
    folder = REVIEW / item['record']
    done = read(folder / 'completed.json')
    assert done['pid'] == read(folder / 'started.json')['pid'] == item['pid']
    assert done['exit_code'] == item['exit_code'] == 0 and not item['alive'] and not item['timed_out']
    for filename, key in [('preregistered.json', 'registration_sha256'), ('completed.json', 'completion_sha256'),
                          ('stdin.bin', 'stdin_sha256'), ('stdout.bin', 'stdout_sha256'), ('stderr.bin', 'stderr_sha256')]:
        assert sha((folder / filename).read_bytes()) == item[key]
seal = read(REVIEW / 'seal-recorder-completion.json')
assert seal == release['seal_recorder_wrapper']
assert seal['pid'] == read(REVIEW / 'seal-recorder-started.json')['pid']
assert seal['exit_code'] == 0 and not seal['alive'] and not seal['timed_out']
for stream in ('stdout', 'stderr'):
    assert sha((REVIEW / ('seal-recorder.' + stream + '.log')).read_bytes()) == seal[stream + '_sha256']

db_review = read(REVIEW / 'database-review.json')
tables = {}
for name, entry in db_review['copies'].items():
    source = REVIEW / 'input/target' / entry['source']
    raw = source.read_bytes()
    assert sha(raw) == entry['source_sha256_before'] == entry['source_sha256_after'] == entry['copy_sha256_before_after']
    with tempfile.NamedTemporaryFile(prefix='a03-r9-coordinator-', suffix='.sqlite3', delete=False) as temp:
        copy = Path(temp.name)
        temp.write(raw)
    try:
        conn = sqlite3.connect(copy.as_uri() + '?mode=ro&immutable=1', uri=True)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA query_only=ON')
            assert conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            tables[name] = {table: [dict(r) for r in conn.execute('SELECT * FROM "' + table.replace('"', '""') + '"')] for table in names}
            assert tables[name] == entry['tables']
            assert {table: len(rows) for table, rows in tables[name].items()} == entry['counts']
        finally:
            conn.close()
        assert copy.read_bytes() == raw == source.read_bytes()
    finally:
        copy.unlink()  # Only this script's exact temporary file, never a directory.


def author_file(path):
    normalized = path.replace('\\', '/')
    assert normalized.startswith(AUTHOR)
    entry = next(e for e in exports if e['commit'] == TARGET and e['path'] == normalized[len(AUTHOR):])
    return REVIEW / entry['file']


after = tables['after_runtime']
reg, action, intent = [after[t][0] for t in ('registrations', 'actions', 'intents')]
bundle = read(author_file(reg['bundle_path']))
artifacts = bundle['artifacts']
for artifact in artifacts:
    assert sha(canonical({k: v for k, v in artifact.items() if k != 'content_hash'})) == artifact['content_hash']
receipt_ref = json.loads(intent['receipt'])
receipt = next(a for a in artifacts if a['artifact_id'] == receipt_ref['artifact_id'])
assert {k: receipt[k] for k in ('kind', 'artifact_id', 'revision', 'content_hash')} == receipt_ref
assert receipt_ref in [json.loads(a['ref']) for a in after['artifacts']]
fact_ref = json.loads(action['fact'])
fact_path = author_file(reg['package_root'].replace('\\', '/') + '/' + fact_ref['path'])
assert sha(fact_path.read_bytes()) == fact_ref['sha256']
fact = read(fact_path)
assert fact['plan_ref'] == json.loads(after['plans'][0]['ref']) == receipt['payload']['plan']
assert fact['intent_ref'] == json.loads(intent['ref'])
assert fact['action_id'] == action['id'] == intent['action'] and fact['action_digest'] == action['digest']
assert receipt['payload']['action_fact_refs'] == [fact_ref] and receipt['payload']['results'] == [fact['result']]
assert fact['result']['attempt_fact'] == 'ATTEMPTED' and fact['result']['outcome'] == 'APPLIED'
assert [len(tables[n]['effects']) for n in ('before_target', 'after_target')] == [0, 1]
effect = json.loads(tables['after_target']['effects'][0]['body'])
assert effect['plan_ref'] == fact['plan_ref'] and effect['action_id'] == action['id'] and effect['mutated']
assert not after['native_report_reads'] and not any(a['kind'] == 'BatchReport' or
    (a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY') for a in artifacts)
assert after['books'][0]['phase'] == 'RELEASED' and after['books'][0]['owner'] is None

source = (REVIEW / 'input/target/src/annotation/runtime/recovery/__init__.py').read_text(encoding='utf-8')
native = (REVIEW / 'input/target/src/annotation/runtime/recovery/native_quality.py').read_text(encoding='utf-8')
storage = (REVIEW / 'input/target/src/annotation/runtime/storage/__init__.py').read_text(encoding='utf-8')
run = source.split('def run_plan(', 1)[1].split('\ndef reconcile(', 1)[0]
assert run.index('LeaseKeeper(') < run.index('quality = publish_quality(store, reg["id"], projection)') < run.index('keeper.stop()')
assert 'claim = claim_current(store, observer, key)' in native
assert 'if row["lease"] > time.time() or self._pid_alive(row["pid"]):' in storage

result = {'at': datetime.now().astimezone().isoformat(), 'target': TARGET,
    'decision': 'PRODUCT_OWNER_LIFECYCLE_FAILURE_CONFIRMED_REWORK', 'manifest_entries': len(entries),
    'raw_git_inputs_verified': len(exports), 'review_processes_exited': 10, 'own_immutable_db_copies': 4,
    'effects_before_after': [0, 1], 'attempt_fact': 'ATTEMPTED', 'POST_Batch_report_reads': [0, 0, 0],
    'report_sha256': sha(report.read_bytes()), 'manifest_sha256': sha(manifest.read_bytes()),
    'process_release_sha256': sha(release_file.read_bytes()), 'candidate_product_calls': 0,
    'D1_D2_reruns': 0, 'old_evidence_modified': False, 'product_accepted': False, 'product_integrated': False,
    'I01_released': False, 'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
Path(__file__).with_name('review-audit.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps(result, ensure_ascii=False))
