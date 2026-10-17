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
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R8-R4-remaining'
OUT = Path(__file__).parent
TARGET = '435aaee2d140e82d3237ce8902d594a1aee70aad'
REPORT = 'docs/tasks/A03-P2-R8-R4-remaining-review-report.md'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def ref(artifact):
    return {k: artifact[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}

manifest_path = REVIEW / 'sha256-manifest.json'
assert sha(manifest_path.read_bytes()) == '1551830c8ced8f808c98e275b41f8718fc2a66941988f06745b30d4d695a14df'
assert sha((ROOT / REPORT).read_bytes()) == '4666400a3bc1f9227601bcc1d47b4335e33a8ebf427a3dc72872221dda4d5945'
entries = read(manifest_path)['files']
listed = {e['path'] for e in entries}
actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file()} | {REPORT}
assert len(entries) == len(listed) == 660
assert actual == listed | {manifest_path.relative_to(ROOT).as_posix()}
for e in entries:
    data = (ROOT / e['path']).read_bytes()
    assert len(data) == e['bytes'] and sha(data) == e['sha256'], e['path']

exports = read(REVIEW / 'input-index.json')['exports'] + read(REVIEW / 'isolated-source-index.json')['files']
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
assert pos == len(raw) and len(exports) == 485

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
    if item['pid'] == 57664:
        assert finish['exit_code'] == 87 and finish['barrier_released']
assert len(release['parents']) == 14 and len(release['nested_children']) == 4
assert release['product_group_failures_or_reruns'] == release['other_groups_or_old_target_variant_runs'] == release['background_jobs'] == 0
for phase in ['n1','n6','n7']:
    assert 'Ran 1 test in ' in (REVIEW / ('runs/independent-' + phase + '-01/stderr.log')).read_text(encoding='utf-8')

tmp_parent = Path(tempfile.gettempdir()).resolve()
tmp = Path(tempfile.mkdtemp(prefix='a03-coordinator-r8-r4-', dir=str(tmp_parent))).resolve()
assert tmp.parent == tmp_parent and tmp.name.startswith('a03-coordinator-r8-r4-')
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
        names = ['actions', 'plans', 'intents', 'registrations', 'artifacts', 'native_pre_runs', 'native_report_reads', 'native_creation_anchors', 'permits', 'resolutions', 'books', 'events'] if entry['role'] == 'runtime' else ['effects', 'observations']
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
assert len(rows['native_pre_runs']) == 1 and all(x['status'] == 'ADMITTED' for x in rows['native_pre_runs'])
assert rows['permits'][0]['state'] == 'CONSUMED' and plan['status'] == 'FINISHED'
assert len(snapshots['target']['effects']) == 1 and len(snapshots['target']['observations']) == 4

def safe_read(original):
    path = Path(original).resolve()
    assert path.is_relative_to(REVIEW.resolve())
    assert path.relative_to(ROOT).as_posix() in listed
    return read(path)

bundle = safe_read(reg['bundle_path'])
artifacts = bundle['artifacts']
assert len(artifacts) == len(rows['artifacts']) == 20
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

# Check the fresh N6 captured return and named dependency against SQL/resources.
workspace = REVIEW / 'isolation/workspace'
validation = workspace / 'docs/evidence/A03/execution/P2-R8-R4-remaining/validation/review-r4-2bd4a13ab0fe'
def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
anchor = rows['native_creation_anchors'][0]
assert anchor == read(REVIEW / 'independent-N6-review.json')['anchor_SQL_row']
anchor_path = Path(anchor['input_path'])
anchor_value = safe_read(anchor_path)
anchor_raw = anchor_path.read_bytes()
assert canonical(anchor_value) == anchor_raw
assert sha(anchor_raw) == anchor['input_sha'] == '28c396774fc750b1b90dab7af4c4626a7b1b947f390e120215db8cfd666f568d'
assert (validation / 'N6/creation-input-canonical.json').read_bytes() == anchor_raw
full = read(validation / 'N6/full-current-history.json')
assert full == bundle and len(full['artifacts']) == 20 and len(anchor_value['artifacts']) == 7
actual_plan = next(a for a in artifacts if a['kind'] == 'ApplyPlan')
returns = read(validation / 'N6/actual-recompute-returns.json')
assert returns['generated_plans'] == [actual_plan]
assert returns['resource_manifests'] == [json.loads(anchor['manifest'])]
plan_bytes = canonical(actual_plan)
assert (validation / 'N6/original-plan-canonical.json').read_bytes() == plan_bytes
assert (validation / 'N6/recomputed-plan-canonical.json').read_bytes() == plan_bytes
assert sha(plan_bytes) == '056ef925a3a3a424145f538302f97467127a4e971d49d4f73724cd83f7d200c2'
resource_index = {}
def walk(value):
    if isinstance(value, dict):
        if {'path','sha256','media_type','origin'} <= set(value):
            resource_index[value['path']] = value
        for child in value.values(): walk(child)
    elif isinstance(value, list):
        for child in value: walk(child)
walk(anchor_value)
manifest = json.loads(anchor['manifest'])
assert resource_index == {v['path']: v for v in manifest} and len(resource_index)==6
for r in manifest:
    source = (Path(reg['package_root']) / r['path']).resolve()
    assert source.is_relative_to(REVIEW.resolve()) and source.relative_to(ROOT).as_posix() in listed
    assert sha(source.read_bytes()) == r['sha256']
consumer = read(validation / 'N6/missing-dependency-consumer.json')
pre = next(a for a in anchor_value['artifacts'] if ref(a) == consumer['artifact_ref'])
assert pre['payload']['checks'][0]['check_id'] == consumer['check_id'] == 'source_integrity'
assert pre['payload']['checks'][0]['evidence_refs'][0] == consumer['evidence_id']
missing = read(validation / 'N6/missing-dependency-input.json')
expected_missing = json.loads(anchor_raw)
assert consumer['record'] in expected_missing['evidence']
expected_missing['evidence'].remove(consumer['record'])
assert missing == expected_missing
refusal = read(validation / 'N6/missing-dependency-refusal.json')
assert refusal['type']=='StaticCodecError' and refusal['code']=='EVIDENCE_ID_MISSING'
assert refusal['issues'][0]['path']==pre['artifact_id']+'/checks/0/evidence_refs['+consumer['evidence_id']+']'
r6 = read(validation/'N6-result.json')
assert r6['database_before']==r6['database_after']
assert r6['permit_and_effect_added']==0
for e in db_records:
    assert r6['database_before'][e['role']]['sha256']==sha(Path(e['source']).read_bytes())
for group in ['N1','N6','N7']:
    imports = read(REVIEW / ('imports-'+group+'.json'))
    assert imports['normal_import']
    for module in imports['modules']:
        file = Path(module['actual_file']).resolve()
        assert file.is_relative_to(workspace.resolve())
        assert sha(file.read_bytes())==module['sha256']
# One incomplete runtime: coordinator uses a fresh immutable copy, no product calls.
r7 = read(validation/'N7-result.json')
assert r7['hook_calls']==['before_completion'] and r7['same_process_controlled_exception']
assert not r7['real_process_crash_claim'] and not r7['anchor_exists']
assert r7['database_before_open']==r7['database_after_open']
assert r7['normal_open_refusal']['code']=='STATE_DIRECTORY_IDENTITY_MISMATCH'
assert r7['target_database']==r7['target_effects']=='NOT_CREATED'
assert r7['old_failed_target_entry_or_variant_calls']==0
n7base = validation/'cases/N7-before-completion'
assert not (n7base/'anchor.json').exists() and not (n7base/'target').exists()
n7path = n7base/'runtime/runtime.sqlite3'
n7raw=n7path.read_bytes()
assert sha(n7raw)=='dd19ba8a492195879043099bb964c4a086aa6bc8077193c139fe2bfad5aecf0d'
tmp = Path(tempfile.mkdtemp(prefix='a03-coordinator-r8-r4-init-',dir=str(tmp_parent))).resolve()
assert tmp.parent==tmp_parent and tmp.name.startswith('a03-coordinator-r8-r4-init-')
copy = tmp/'copy.sqlite3'
try:
    copy.write_bytes(n7raw)
    conn=sqlite3.connect(copy.as_uri()+'?mode=ro&immutable=1',uri=True)
    conn.execute('PRAGMA query_only=ON')
    assert conn.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    counts={t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables}
    conn.close()
    assert all(counts[t]==0 for t in ['meta','native_creation_anchors','plans','intents','permits'])
    assert sha(copy.read_bytes())==sha(n7path.read_bytes())==sha(n7raw)
finally:
    if copy.exists():copy.unlink()
    tmp.rmdir()
result = {
 'at':datetime.now().astimezone().isoformat(),'target_commit':TARGET,
 'decision':'ACCEPTED_R4_N6_AND_SINGLE_RUNTIME_INIT_CONTROL_LIMITED_OVERALL_A03_REWORK',
 'report_sha256':sha((ROOT/REPORT).read_bytes()),'manifest_sha256':sha(manifest_path.read_bytes()),
 'release_sha256':sha((REVIEW/'process-release.json').read_bytes()),
 'manifest_entries_verified':len(entries),'total_review_files':len(actual),
 'raw_exports_and_isolation_seeds_verified':len(exports),'parents_exited':14,'nested_children_exited':4,
 'retained_metadata_failures':2,'product_group_failures_or_reruns':0,
 'formal_artifacts':20,'effect_count':1,'observations':4,'original_UNKNOWN_preserved':True,
 'receipt_progress_fact_intent_bound':True,'content':'PENDING','submission':'NOT_SUBMITTED',
 'creation_anchor_sha256':sha(anchor_raw),'full_recomputed_plan_sha256':sha(plan_bytes),
 'full_history_retained':True,'actual_recompute_returns':1,'resource_closure':6,
 'named_missing_PRE_dependency_refusal':refusal['code'],'permit_effect_added':0,
 'N7_runtime_sha256':sha(n7raw),'N7_incomplete_counts':counts,
 'N7_scope':'one same-process runtime before_completion hook, no real crash/target-init claim',
 'original_R3_N7_failure':'PRESERVED_NO_RERUN_OR_VARIANT',
 'coordinator_check':'Raw Git/manifest/import/release binding plus fresh immutable copies of independent N1 double DB and N7 incomplete DB, SQL/artifact/resource/captured-return checks only',
 'candidate_imports':0,'functional_tests_run':False,'original_DB_connections':0,'temporary_copies_removed':True,
 'whole_A03_accepted':False,'product_integrated':False,'I01_released':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
(OUT/'review-audit.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(result,ensure_ascii=False))
