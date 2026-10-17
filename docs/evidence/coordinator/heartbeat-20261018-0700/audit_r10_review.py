"""Corroborate frozen R10 evidence via raw files and own immutable DB copies."""
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R10-owner-fencing'
TARGET = '1c26b4a8eb378af33e57668472d2071e9ea6afff'
AUTHOR = 'C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800/'
REPORT = ROOT / 'docs/tasks/A03-P2-R10-owner-fencing-review-report.md'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

manifest = REVIEW / 'sha256-manifest.json'
release_path = REVIEW / 'process-release.json'
assert sha(REPORT.read_bytes()) == 'a9a2cc37c46ac5bdb215c40e882d6e87904022317c0f9ace63f7dedc9b0ce92e'
assert sha(manifest.read_bytes()) == 'e0ceaf6b63e2c30377087ba73c3cfbd9e6070ce111964fe93eb662ec32043c28'
assert sha(release_path.read_bytes()) == 'b97d07f99667c2416370708e0ae7ad1c3f1d4b80af1c5fac871d63d635c660c4'
entries = read(manifest)['files']
assert len(entries) == len({x['path'] for x in entries}) == 568
actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file()} | {REPORT.relative_to(ROOT).as_posix()}
assert actual == {r['path'] for r in entries} | {manifest.relative_to(ROOT).as_posix()}
for r in entries:
    raw = (ROOT / r['path']).read_bytes()
    assert len(raw) == r['bytes'] and sha(raw) == r['sha256'], r['path']

index = read(REVIEW / 'input-index.json')
assert index['target'] == TARGET
exports = index['exports']
raw_batch = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'cat-file', '--batch'], cwd=ROOT,
    input=('\n'.join(x['commit'] + ':' + x['path'] for x in exports) + '\n').encode())
offset = 0
for x in exports:
    end = raw_batch.index(b'\n', offset)
    oid, kind, size = raw_batch[offset:end].decode().split()
    raw = raw_batch[end + 1:end + 1 + int(size)]
    offset = end + int(size) + 2
    assert kind == 'blob' and oid == x['raw_git_sha1']
    assert raw == (REVIEW / x['file']).read_bytes()
    assert len(raw) == x['bytes'] and sha(raw) == x['sha256']
assert offset == len(raw_batch) and len(exports) == 356
export_paths = {(x['commit'], x['path']): REVIEW / x['file'] for x in exports}

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
children = release['review_and_functional_parents'] + release['nested_business_and_observation_children'] + release['git_children']
for item in children:
    folder = REVIEW / item['record']
    done_path = folder / ('completion.json' if (folder / 'completion.json').exists() else 'completed.json')
    registration = folder / ('registration.json' if (folder / 'registration.json').exists() else 'preregistered.json')
    done = read(done_path)
    assert done['pid'] == read(folder / 'started.json')['pid'] == item['pid']
    assert done['exit_code'] == item['exit_code'] == 0
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
assert len(children) + 1 == release['known_registered_child_count'] == 18
assert release['groups_rounds'] == {'C1': 1, 'C2': 1}
assert release['functional_failures_timeouts_or_reruns'] == 0

db_count = 0
def verify_db(entry):
    global db_count
    source = resolve(entry['source'])
    raw = source.read_bytes()
    assert sha(raw) == entry['source_sha256_before_after'] == entry['copy_sha256_before_after']
    with tempfile.NamedTemporaryFile(prefix='a03-r10-coordinator-', suffix='.sqlite3', delete=False) as f:
        copy = Path(f.name)
        f.write(raw)
    try:
        connection = sqlite3.connect(copy.as_uri() + '?mode=ro&immutable=1', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('PRAGMA query_only=ON')
            assert connection.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            rows = {t: [dict(r) for r in connection.execute('SELECT * FROM "' + t.replace('"', '""') + '"')] for t in tables}
            assert rows == entry['rows']
            assert {t: len(v) for t, v in rows.items()} == entry['counts']
        finally:
            connection.close()
        assert copy.read_bytes() == raw == source.read_bytes()
    finally:
        copy.unlink()  # Only the exact temporary file created above.
    db_count += 1
    return rows

cases = read(REVIEW / 'case-and-timeline-review.json')['cases']
summary = []
for c in cases:
    runtime, target = verify_db(c['runtime']), verify_db(c['target'])
    assert all(not runtime[t] for t in ['plans', 'actions', 'intents', 'permits'])
    assert len(target['effects']) == c['effects'] == 0
    book = runtime['books'][0]
    assert book == c['final_book'] and book['phase'] == 'RELEASED' and book['owner'] is None
    events = [json.loads(x['body']) for x in runtime['events']]
    assert events == c['events']
    previous = '0' * 64
    for event in events:
        assert event['previous_hash'] == previous
        assert sha(canonical({k: v for k, v in event.items() if k != 'event_hash'})) == event['event_hash']
        previous = event['event_hash']
    assert previous == book['head_hash'] and len(events) == book['head_sequence']
    target_state = json.loads(next(x['value'] for x in target['meta'] if x['key'] == 'state'))
    assert {k: target_state[k] for k in ['fence_owner_id', 'fence_generation']} == c['final_target_fence']
    for artifact in c['formal_artifacts']:
        raw = resolve(artifact['path']).read_bytes()
        assert sha(raw) == artifact['raw_sha256']
        body = json.loads(raw)
        assert {k: body[k] for k in ['kind', 'artifact_id', 'revision', 'content_hash']} == artifact['ref']
        assert sha(canonical({k:v for k,v in body.items() if k != 'content_hash'})) == body['content_hash']
        assert artifact['ref'] in [json.loads(x['ref']) for x in runtime['artifacts']]
    package_root = runtime['registrations'][0]['package_root'].replace('\\', '/')
    for resource in c['recursive_resource_checks']:
        ref = resource['ref']
        raw = resolve(package_root + '/' + ref['path']).read_bytes()
        assert len(raw) == resource['bytes'] and sha(raw) == ref['sha256'] == resource['actual_sha256']
    if c['group'] == 'C1':
        assert book['generation'] == 1 and len(events) == 3
        assert c['loser_refusal']['code'] == 'OWNER_BUSY'
        assert c['winner_claim']['claim']['owner_id'] == c['final_target_fence']['fence_owner_id']
        assert c['common_release_ns'] < c['both_live_observation_ns']
        for side in ['A', 'B']:
            assert c['ready'][side]['pid'] == c['markers'][side]['pid'] == c['workers'][side]['pid']
            assert c['ready'][side]['at_ns'] < c['common_release_ns']
            assert c['workers'][side]['ended_at_ns'] > c['both_live_observation_ns']
    else:
        assert book['generation'] == 2 and len(events) == 6
        assert c['stale_refusal']['code'] == 'OWNER_GENERATION_STALE'
        assert c['live_observation']['both_alive']
        assert c['ordered_stage_times_ns'] == sorted(c['ordered_stage_times_ns'])
        assert c['A_qualified']['claim']['generation'] == 1 and c['B_active']['claim']['generation'] == 2
        assert c['A_qualified']['claim']['owner_id'] != c['B_active']['claim']['owner_id']
        assert c['stale_before_after']['old_claim'] == c['A_qualified']['claim']
        before, after = c['stale_before_after']['before'], c['stale_before_after']['after']
        assert before['runtime']['counts'] == after['runtime']['counts']
        for state in [before, after, c['live_observation']['state']]:
            b = state['runtime']['tables']['books'][0]
            assert b['owner'] == c['B_active']['claim']['owner_id'] and b['generation'] == 2 and b['phase'] == 'ACTIVE'
            assert state['target']['counts']['effects'] == 0
        for worker in c['workers'].values():
            assert worker['ended_at_ns'] > c['live_observation']['at_ns']
        pre = runtime['native_pre_runs'][0]
        assert pre['status'] == 'ADMITTED' and pre['accepted_plan'] is None
        assert pre['id'] == c['native_PRE_run_id'] and json.loads(pre['pre_ref']) == c['PRE_ref']
        anchor = runtime['native_creation_anchors'][0]
        assert sha(resolve(anchor['input_path']).read_bytes()) == anchor['input_sha']
        assert c['plan_ref'] in [json.loads(x['ref']) for x in runtime['artifacts']]
    summary.append({'label': c['label'], 'group': c['group'], 'effects': 0, 'final_generation': book['generation'], 'event_count': len(events)})
assert db_count == 8
result = {'at': datetime.now().astimezone().isoformat(), 'target': TARGET,
    'decision': 'ACCEPTED_OWNER_FENCING_TWO_CASES_ONLY', 'manifest_entries': len(entries),
    'raw_git_inputs_verified': len(exports), 'recorded_children_exited': 18,
    'own_immutable_db_copies': db_count, 'cases': summary, 'functional_rounds': release['groups_rounds'],
    'preparation_failure_preserved': True, 'candidate_product_calls': 0, 'functional_reruns': 0,
    'product_integrated': False, 'I01_released': False, 'overall_A03': 'REWORK',
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
    'report_sha256': sha(REPORT.read_bytes()), 'manifest_sha256': sha(manifest.read_bytes()),
    'process_release_sha256': sha(release_path.read_bytes())}
with Path(__file__).with_name('review-audit.json').open('xb') as f:
    f.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
print(json.dumps(result, ensure_ascii=False))
