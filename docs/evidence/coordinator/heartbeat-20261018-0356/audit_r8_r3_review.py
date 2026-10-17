"""Coordinator: frozen bytes, release records and independent N1 SQL copies only."""
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R8-R3-post-hold'
OUT = Path(__file__).parent
TARGET = 'd9ed692db9ab8e9277f8ffd09e040451e8b8f65f'
REPORT = 'docs/tasks/A03-P2-R8-R3-post-hold-review-report.md'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def ref(artifact):
    return {k: artifact[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}

manifest_path = REVIEW / 'sha256-manifest.json'
assert sha(manifest_path.read_bytes()) == 'a5b3a9b8ac8401078dcd224d25d979c99c3b890d3bee681a202270e4d4597052'
assert sha((ROOT / REPORT).read_bytes()) == 'a39afab68c15837122a34fb0f75dca7cae339dd2ba1be13dde007971b99b9a17'
entries = read(manifest_path)['files']
listed = {e['path'] for e in entries}
actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file()} | {REPORT}
assert len(entries) == len(listed) == 1137
assert actual == listed | {manifest_path.relative_to(ROOT).as_posix()}
for e in entries:
    data = (ROOT / e['path']).read_bytes()
    assert len(data) == e['bytes'] and sha(data) == e['sha256'], e['path']

exports = read(REVIEW / 'input-index.json')['exports'] + read(REVIEW / 'supplemental-input-index.json')['files']
specs = [e['commit'] + ':' + e['path'] for e in exports]
raw = subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(WT), 'cat-file', '--batch'], input=('\n'.join(specs) + '\n').encode())
pos = 0
for e in exports:
    end = raw.index(b'\n', pos)
    oid, kind, size = raw[pos:end].decode().split()
    pos = end + 1
    data = raw[pos:pos + int(size)]
    pos += int(size) + 1
    assert kind == 'blob' and oid == e['raw_git_sha1']
    assert len(data) == e['bytes'] and sha(data) == e['sha256']
    assert data == (REVIEW / e['file']).read_bytes(), e['file']
assert pos == len(raw) and len(exports) == 679

release = read(REVIEW / 'process-release.json')
for item in release['parents']:
    run = REVIEW / 'runs' / item['run']
    for filename, key in [('registration.json', 'registration_sha256'), ('completion.json', 'completion_sha256'), ('entry-source.py', 'entry_sha256'), ('stdout.log', 'stdout_sha256'), ('stderr.log', 'stderr_sha256')]:
        assert sha((run / filename).read_bytes()) == item[key]
    registration, start, finish = [read(run / name) for name in ['registration.json', 'started.json', 'completion.json']]
    assert start['pid'] == finish['pid'] == item['pid']
    assert finish['argv'] == registration['argv'] and finish['cwd'] == registration['cwd']
    assert finish['exit_code'] == item['exit_code'] == (1 if item['run'] in release['retained_reviewer_metadata_failures'] else 0)
    assert not finish['timed_out'] and not finish['alive_after_wait'] and not item['alive']
for item in release['nested_children']:
    run = REVIEW / item['record']
    for filename, key in [('preregistered.json', 'preregistered_sha256'), ('completed.json', 'completed_sha256'), ('stdout.txt', 'stdout_sha256'), ('stderr.txt', 'stderr_sha256')]:
        assert sha((run / filename).read_bytes()) == item[key]
    registration, start, finish = [read(run / name) for name in ['preregistered.json', 'started.json', 'completed.json']]
    assert start['pid'] == finish['pid'] == item['pid']
    assert start['parent_pid'] in {x['pid'] for x in release['parents'] + release['nested_children']}
    assert registration['argv'] == item['argv'] and registration['cwd'] == item['cwd']
    assert finish['exit_code'] == item['exit_code']
    assert not finish['alive'] and not finish.get('timeout', finish.get('timed_out', False))
    if item['pid'] == 19840:
        assert finish['exit_code'] == 87 and finish['barrier_released']
assert len(release['parents']) == 19 and len(release['nested_children']) == 10
assert release['product_group_failures_or_reruns'] == release['N6_N7_variant_compatibility_runs'] == release['background_jobs'] == 0
for phase in ['local','n1','n2','n3','n4','n5']:
    assert 'Ran 1 test in ' in (REVIEW / ('runs/independent-' + phase + '-01/stderr.log')).read_text(encoding='utf-8')

tmp_parent = Path(tempfile.gettempdir()).resolve()
tmp = Path(tempfile.mkdtemp(prefix='a03-coordinator-r8-r3-', dir=str(tmp_parent))).resolve()
assert tmp.parent == tmp_parent and tmp.name.startswith('a03-coordinator-r8-r3-')
db_records = read(REVIEW / 'independent-database-review.json')['copies']
snapshots = {}
try:
    for i, entry in enumerate(db_records):
        original = Path(entry['source']).resolve()
        assert original.is_relative_to(REVIEW.resolve())
        data = original.read_bytes()
        assert sha(data) == entry['source_sha256']
        copy = tmp / ('copy-' + str(i) + '.sqlite3')
        copy.write_bytes(data)
        conn = sqlite3.connect(copy.as_uri() + '?mode=ro&immutable=1', uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        assert conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        names = ['actions', 'plans', 'intents', 'registrations', 'artifacts', 'native_pre_runs', 'native_report_reads', 'permits', 'resolutions', 'books', 'events'] if entry['role'] == 'runtime' else ['effects', 'observations']
        snapshots[entry['role']] = {name: [dict(r) for r in conn.execute('SELECT * FROM ' + name)] for name in names}
        conn.close()
        assert sha(copy.read_bytes()) == sha(data) == sha(original.read_bytes())
        copy.unlink()
finally:
    for copy in tmp.glob('copy-*.sqlite3'):
        copy.unlink()
    tmp.rmdir()

rows = snapshots['runtime']
assert all(len(rows[name]) == 1 for name in ['actions', 'plans', 'intents', 'registrations', 'permits', 'resolutions', 'native_report_reads'])
action, plan, intent, reg = [rows[name][0] for name in ['actions', 'plans', 'intents', 'registrations']]
assert len(rows['native_pre_runs']) == 3 and all(x['status'] == 'ADMITTED' for x in rows['native_pre_runs'])
assert rows['permits'][0]['state'] == 'CONSUMED' and plan['status'] == 'FINISHED'
assert len(snapshots['target']['effects']) == 1 and len(snapshots['target']['observations']) == 7

def safe_read(original):
    path = Path(original).resolve()
    assert path.is_relative_to(REVIEW.resolve())
    assert path.relative_to(ROOT).as_posix() in listed
    return read(path)

bundle = safe_read(reg['bundle_path'])
artifacts = bundle['artifacts']
assert len(artifacts) == len(rows['artifacts']) == 25
for artifact in artifacts:
    matches = [x for x in rows['artifacts'] if json.loads(x['ref']) == ref(artifact)]
    assert len(matches) == 1 and safe_read(matches[0]['path']) == artifact
fact_ref = json.loads(action['fact'])
fact_path = Path(reg['package_root']) / fact_ref['path']
fact = safe_read(fact_path)
assert sha(fact_path.read_bytes()) == fact_ref['sha256']
receipt = next(a for a in artifacts if a['kind'] == 'ExecutionReceipt')
head = next(a for a in artifacts if a['kind'] == 'ReconciliationResult')
assert ref(receipt) == json.loads(intent['receipt'])
assert receipt['payload']['results'] == [fact['result']]
assert receipt['payload']['action_fact_refs'] == [fact_ref]
assert fact['plan_ref'] == json.loads(plan['ref']) and fact['action_id'] == action['id']
assert fact['intent_ref'] == json.loads(intent['ref']) and fact['action_digest'] == action['digest']
assert head['payload']['resolution'] == 'RESOLVED_APPLIED' and head['payload']['original_receipt_ref'] is None
assert ref(head) == json.loads(rows['resolutions'][0]['ref'])
progress = [a for a in artifacts if a['kind'] == 'ExecutionProgress']
unknown = [a for a in progress if a['payload']['actions'][0]['effective_outcome'] == 'UNKNOWN']
assert len(unknown) == 1 and unknown[0]['payload']['actions'][0]['receipt_ref'] is None
material = [a for a in progress if a['payload']['actions'][0]['result_fact'] is not None]
assert len(material) == 2
for p in material:
    a = p['payload']['actions'][0]
    assert p['payload']['plan_ref'] == fact['plan_ref']
    assert a['action_id'] == fact['action_id'] and a['intent_ref'] == fact['intent_ref']
    assert a['attempt_fact'] == fact['result']['attempt_fact'] == 'MAY_HAVE_BEEN_ATTEMPTED'
    assert a['attempt_evidence_refs'] == fact['result']['attempt_evidence_refs']
    assert a['receipt_ref'] == ref(receipt) and a['result_fact'] == fact_ref
post = next(a for a in artifacts if a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY')
batch = next(a for a in artifacts if a['kind'] == 'BatchReport')
assert post['payload']['receipt'] == batch['payload']['receipt'] == ref(receipt)
assert batch['payload']['postcheck'] == ref(post)
assert post['payload']['frame_structure'] == 'PASS'
assert post['payload']['content_check_status'] == batch['payload']['content_check_status'] == 'PENDING'
assert post['payload']['submission_status'] == batch['payload']['submission_status'] == 'NOT_SUBMITTED'
assert batch['payload']['state'] == 'CONTENT_PENDING'
assert post['payload']['report_snapshot_ref'] != head['payload']['observed_snapshot_ref']
assert post['payload']['report_observation'] != head['payload']['readback']
# Cross-check the admitted POST_HOLD runs against the independent persisted rows.
hold = read(REVIEW / 'independent-post-hold-review.json')
assert rows['books'][0]['hold'] == hold['final_hold'] and rows['books'][0]['owner'] is None
assert not hold['hold_cleared'] and not hold['different_hold_id_or_qualified_clearance_tested']
for admission in hold['admissions']:
    matching = [x for x in rows['native_pre_runs'] if x['id'] == admission['run_id']]
    assert len(matching) == 1
    run = matching[0]
    assert run['status'] == 'ADMITTED' and run['reads'] == 1
    assert json.loads(run['binding']) == admission['binding']
    assert admission['binding']['context']['hold_id'] == rows['books'][0]['hold']
    assert any(ref(a) == admission['pre_ref'] for a in artifacts)
assert len(hold['admissions']) == 2
assert hold['expiry']['parent_elapsed_seconds'] >= hold['expiry']['product_window_seconds'] == 60
assert hold['exact_refusals']['ordinary_write_still_blocked_after_POST_HOLD_admission'] == 'TARGET_DRIFT_HOLD'
assert hold['exact_refusals']['expired_current_hold_proof'] == 'NATIVE_PRE_DEADLINE_EXCEEDED'
classification = read(REVIEW / 'N7-readonly-classification.json')
assert classification['actual_rejection'] and not classification['product_change_required_by_this_failed_assertion']
assert classification['N7_replays_or_variants'] == 0
native = (REVIEW / 'isolation/workspace/src/annotation/runtime/storage/native.py').read_text(encoding='utf-8')
assert '_pre_lease(' in native and '_post_hold_event(' in native
persistent = (REVIEW / 'isolation/workspace/src/annotation/delivery/mock/persistent.py').read_text(encoding='utf-8')
assert 'except (sqlite3.Error, ValueError, TypeError, KeyError)' in persistent
result = {
    'at': datetime.now().astimezone().isoformat(), 'target_commit': TARGET,
    'decision': 'ACCEPTED_POST_HOLD_LOCAL_N1_N5_LIMITED_OVERALL_A03_REWORK',
    'review_report_sha256': sha((ROOT / REPORT).read_bytes()),
    'review_manifest_sha256': sha(manifest_path.read_bytes()),
    'manifest_entries_verified': len(entries), 'total_review_files': len(actual),
    'raw_git_exports_verified': len(exports), 'parents_exited': 19, 'nested_children_exited': 10,
    'coordinator_check': 'Raw manifest/Git/process records; two self-owned immutable copies of independent N1 DBs; direct SQL/current-bundle/resource binding checks including two admitted POST_HOLD runs; no candidate imports or reruns.',
    'independent_DB_hashes': {e['role']: e['source_sha256'] for e in db_records},
    'effects': 1, 'formal_artifacts_verified': 25, 'formal_receipt_three_way_match': True,
    'formal_receipt_ref': ref(receipt), 'four_guard_fields_equal': True,
    'material_progress_count': 2, 'original_UNKNOWN_preserved': True,
    'attempt_fact': fact['result']['attempt_fact'], 'report_read_count': 1,
    'new_POST_Batch_registered': True, 'content_status': 'PENDING', 'submission_status': 'NOT_SUBMITTED',
    'N2': 'Two admitted POST_HOLD runs, same hold, distinct normal generation/head; ordinary write remains blocked; real expiry verified from frozen records.',
    'remaining': 'N6 anchor/full-history control and N7 incomplete initialization not run; original wider P2 coverage retained. N7 original diagnostic assertion remains FAILED; no product fix required.',
    'candidate_imports': 0, 'functional_tests_run': False, 'original_DB_connections': 0,
    'temporary_copies_removed': True, 'product_mutations': 0,
    'whole_A03_accepted': False, 'product_integrated': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
}
(OUT / 'review-audit.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(result, ensure_ascii=False))
