"""Read-only coordinator corroboration of frozen R9-R1 review; no product imports."""
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R9-R1-owner-lifecycle'
TARGET = 'bfd7fe896a7eee663ea8e0b6cf967548d8dd8f39'
AUTHOR = 'C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

report = ROOT / 'docs/tasks/A03-P2-R9-R1-owner-lifecycle-review-report.md'
manifest = REVIEW / 'sha256-manifest.json'
release_path = REVIEW / 'process-release.json'
assert sha(report.read_bytes()) == 'e3963a6b8cd387e22eaa1a88008cde39f5ce5769488798f798dab2c2b8e61fd5'
assert sha(manifest.read_bytes()) == 'ad14e05658beaea7431d0856e3039664958d33c7b632c9d0ca008bf6a14071ce'
assert sha(release_path.read_bytes()) == 'dc6a32ef830b0a5fd9f320f4dcc62d9794bcccff18e82dd02b70e804d52b48d3'
entries = read(manifest)['files']
assert len(entries) == len({e['path'] for e in entries}) == 1124
actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file()} | {report.relative_to(ROOT).as_posix()}
assert actual == {e['path'] for e in entries} | {manifest.relative_to(ROOT).as_posix()}
for e in entries:
    raw = (ROOT / e['path']).read_bytes()
    assert len(raw) == e['bytes'] and sha(raw) == e['sha256'], e['path']

index = read(REVIEW / 'input-index.json')
assert index['target'] == TARGET
exports = index['exports']
batch = subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(ROOT), 'cat-file', '--batch'],
    input=('\n'.join(e['commit'] + ':' + e['path'] for e in exports) + '\n').encode())
pos = 0
for e in exports:
    end = batch.index(b'\n', pos)
    oid, kind, size = batch[pos:end].decode().split()
    pos = end + 1
    raw = batch[pos:pos + int(size)]
    pos += int(size) + 1
    assert kind == 'blob' and oid == e['raw_git_sha1']
    assert raw == (REVIEW / e['file']).read_bytes()
    assert len(raw) == e['bytes'] and sha(raw) == e['sha256']
assert pos == len(batch) and len(exports) == 585
export_paths = {(e['commit'], e['path']): REVIEW / e['file'] for e in exports}

def resolve(path):
    normalized = path.replace('\\', '/')
    if normalized.startswith(AUTHOR):
        return export_paths[TARGET, normalized[len(AUTHOR):]]
    p = Path(normalized)
    if p.is_absolute():
        assert p.is_relative_to(REVIEW)
        return p
    return export_paths[TARGET, normalized]

release = read(release_path)
children = release['review_checks'] + release['functional_and_observation_children'] + release['git_children']
for item in children:
    folder = REVIEW / item['record']
    done_path = folder / ('completion.json' if (folder / 'completion.json').exists() else 'completed.json')
    registration = folder / ('registration.json' if (folder / 'registration.json').exists() else 'preregistered.json')
    done = read(done_path)
    assert done['pid'] == read(folder / 'started.json')['pid'] == item['pid']
    assert done['exit_code'] == item['exit_code']
    assert not item['alive'] and not item['timed_out']
    assert not done.get('alive', done.get('alive_after_wait', False))
    assert not done.get('timed_out', done.get('timeout', False))
    assert sha(done_path.read_bytes()) == item['completion_sha256']
    assert sha(registration.read_bytes()) == item['registration_sha256']
    for stream in ['stdout', 'stderr']:
        paths = [folder / (stream + ext) for ext in ['.log', '.txt', '.bin'] if (folder / (stream + ext)).exists()]
        assert len(paths) == 1 and sha(paths[0].read_bytes()) == item[stream + '_sha256']
    if 'entry_sha256' in item:
        assert sha((folder / 'entry-source.py').read_bytes()) == item['entry_sha256']
seal = read(REVIEW / 'seal-recorder-completion.json')
assert seal == release['seal_recorder_wrapper']
assert seal['pid'] == read(REVIEW / 'seal-recorder-started.json')['pid']
assert seal['exit_code'] == 0 and not seal['alive'] and not seal['timed_out']
for stream in ['stdout', 'stderr']:
    assert sha((REVIEW / ('seal-recorder.' + stream + '.log')).read_bytes()) == seal[stream + '_sha256']
assert len(children) + 1 == release['known_registered_child_count'] == 33
assert release['functional_group_rounds'] == dict.fromkeys(['D1', 'standalone', 'borrow', 'D2'], 1)
assert release['functional_failures_or_reruns'] == 0
assert sorted(x['exit_code'] for x in release['review_checks']).count(1) == 2

boundaries = read(REVIEW / 'case-boundaries-review.json')
db_count = 0
def verify_db(entry):
    global db_count
    source = resolve(entry['source'])
    raw = source.read_bytes()
    assert sha(raw) == entry['source_sha256_before_after'] == entry['copy_sha256_before_after']
    with tempfile.NamedTemporaryFile(prefix='a03-r9-r1-coordinator-', suffix='.sqlite3', delete=False) as temp:
        copy = Path(temp.name)
        temp.write(raw)
    try:
        conn = sqlite3.connect(copy.as_uri() + '?mode=ro&immutable=1', uri=True)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA query_only=ON')
            assert conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            rows = {t: [dict(r) for r in conn.execute('SELECT * FROM "' + t.replace('"', '""') + '"')] for t in names}
            assert rows == entry['rows']
            assert {t: len(v) for t, v in rows.items()} == entry['counts']
        finally:
            conn.close()
        assert raw == copy.read_bytes() == source.read_bytes()
    finally:
        copy.unlink()  # This exact self-created temporary file only.
    db_count += 1
    return rows

case_results = []
for case in boundaries['author_cases'] + boundaries['independent_cases']:
    runtime = verify_db(case['runtime'])
    target = verify_db(case['target'])
    reg, action, intent = [runtime[t][0] for t in ['registrations', 'actions', 'intents']]
    bundle_path = resolve(case['current_bundle_path'])
    assert sha(bundle_path.read_bytes()) == case['current_bundle_raw_sha256']
    bundle = read(bundle_path)
    for art in bundle['artifacts']:
        assert sha(canonical({k: v for k, v in art.items() if k != 'content_hash'})) == art['content_hash']
    for art in case['formal_artifacts']:
        p = resolve(art['path'])
        assert sha(p.read_bytes()) == art['raw_sha256']
        body = read(p)
        assert {k: body[k] for k in ['kind', 'artifact_id', 'revision', 'content_hash']} == art['ref']
        assert art['ref'] in [json.loads(r['ref']) for r in runtime['artifacts']]
    fact_ref = json.loads(action['fact'])
    fact_path = resolve(reg['package_root'].replace('\\', '/') + '/' + fact_ref['path'])
    assert sha(fact_path.read_bytes()) == fact_ref['sha256']
    fact = read(fact_path)
    assert fact == case['fact']
    assert fact['plan_ref'] == json.loads(runtime['plans'][0]['ref']) == case['plan_ref']
    assert fact['intent_ref'] == json.loads(intent['ref']) == case['intent_ref']
    assert fact['action_id'] == action['id'] == intent['action']
    assert fact['action_digest'] == action['digest']
    assert len(target['effects']) == case['effect_count']
    assert len(runtime['native_report_reads']) == case['report_read_count']
    assert runtime['plans'][0]['status'] == case['plan_status']
    assert runtime['books'][0]['phase'] == 'RELEASED' and runtime['books'][0]['owner'] is None
    if case['group'] == 'D2':
        assert case['effect_count'] == case['report_read_count'] == 0
        assert case['plan_status'] == 'INTERRUPTED'
        assert fact['result']['attempt_fact'] == 'MAY_HAVE_BEEN_ATTEMPTED'
        assert fact['result']['outcome'] == 'NOT_APPLIED' and fact['result']['effect_match'] == 'ABSENT'
        assert case['duplicate_result']['code'] == 'REPLAY_FORBIDDEN'
    else:
        assert case['effect_count'] == case['report_read_count'] == 1
        assert fact['result']['attempt_fact'] == 'ATTEMPTED' and fact['result']['outcome'] == 'APPLIED'
        post = next(a for a in bundle['artifacts'] if {k:a[k] for k in ['kind','artifact_id','revision','content_hash']} == case['POST_ref'])
        batch_art = next(a for a in bundle['artifacts'] if {k:a[k] for k in ['kind','artifact_id','revision','content_hash']} == case['Batch_ref'])
        assert post['payload']['stage'] == 'POST_APPLY'
        assert 'NOT_SUBMITTED' in canonical(batch_art).decode()
    case_results.append({'group':case['group'],'effect_count':case['effect_count'],'report_read_count':case['report_read_count'],'attempt_fact':fact['result']['attempt_fact'],'plan_status':case['plan_status']})
for entry in boundaries['independent_before_DB_copies']:
    verify_db(entry)
assert db_count == 18
ownership = read(REVIEW / 'ownership-boundaries-review.json')
assert ownership['exact_error']['code'] == 'STORAGE_TRANSACTION_FAILED'
assert ownership['exact_error']['context_type'] == 'IntegrityError'
assert ownership['extra_observations_reports_effects_after_refusal'] == 0
assert ownership['borrowed_generation_and_owner_retained_until_caller_cleanup']
for group in ['D1','standalone','borrow','D2']:
    result = read(REVIEW / ('result-' + group + '.json'))
    assert result['exit_code'] == 0 and result['functional_rounds'] == 1
result = {'at':datetime.now().astimezone().isoformat(),'target':TARGET,
    'decision':'ACCEPTED_OWNER_LIFECYCLE_AND_FOUR_FIXED_DEMOS_ONLY','manifest_entries':len(entries),
    'raw_git_inputs_verified':len(exports),'recorded_children_exited':33,'own_immutable_db_copies':db_count,
    'cases':case_results,'functional_group_rounds':release['functional_group_rounds'],
    'author_borrow':'FAILED_PRESERVED','author_D2':'NOT_RUN','review_auxiliary_failures_preserved':2,
    'candidate_product_calls':0,'functional_reruns':0,'product_integrated':False,'I01_released':False,
    'overall_A03':'REWORK','field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
    'report_sha256':sha(report.read_bytes()),'manifest_sha256':sha(manifest.read_bytes()),'process_release_sha256':sha(release_path.read_bytes())}
Path(__file__).with_name('review-audit.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(result,ensure_ascii=False))
