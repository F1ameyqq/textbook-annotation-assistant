"""Coordinator corroboration of frozen R11 files and private immutable SQL copies."""
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path('D:/1800')
OLD = ROOT / 'docs/evidence/A03/review/P2-R11-crash-cuts'
NEW = ROOT / 'docs/evidence/A03/review/P2-R11-R1-archive-closure'
OUT = ROOT / 'docs/evidence/coordinator/heartbeat-20261018-0800'
REPORT = ROOT / 'docs/tasks/A03-P2-R11-R1-archive-closure-review-report.md'
WORKFLOW = '188fed05cd51789521b27efb04b2426f630571d0'
TARGET = 'cc5966dc58c62017a27266c40ca0cedc5c68485c'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

assert sha(REPORT.read_bytes()) == '27fdcf5ff1938811db38b3ae18027e1fd0d062745148ca4f70c3cbc976078c95'
manifest = NEW / 'sha256-manifest.json'
assert sha(manifest.read_bytes()) == 'ae8153f0ea77731ad01d379ad870bdba83b2fc45c87203f94f595e23b2d986ba'
entries = read(manifest)['files']
assert len(entries) == len({r['path'] for r in entries}) == 34
actual = {p.relative_to(ROOT).as_posix() for p in NEW.rglob('*') if p.is_file()} | {REPORT.relative_to(ROOT).as_posix()}
assert actual == {r['path'] for r in entries} | {manifest.relative_to(ROOT).as_posix()}
for r in entries:
    raw = (ROOT / r['path']).read_bytes()
    assert len(raw) == r['bytes'] and sha(raw) == r['sha256'], r['path']

# Match all old bytes to the frozen archive Git tree, including failed outputs.
old_index = read(NEW / 'original-preservation-before.json')['files']
assert len(old_index) == 1209
batch = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'cat-file', '--batch'], cwd=ROOT,
    input=('\n'.join(WORKFLOW + ':' + x['path'] for x in old_index) + '\n').encode('utf-8'), timeout=45)
offset = 0
for x in old_index:
    end = batch.index(b'\n', offset)
    oid, kind, size = batch[offset:end].decode().split()
    raw = batch[end + 1:end + 1 + int(size)]
    offset = end + int(size) + 2
    assert kind == 'blob' and oid == x['workflow_git_blob']
    assert raw == (ROOT / x['path']).read_bytes()
    assert len(raw) == x['bytes'] and sha(raw) == x['sha256']
assert offset == len(batch)

release = read(NEW / 'process-release.json')
assert release['known_registered_child_count'] == len(release['records']) == 3
assert release['functional_calls'] == release['SQL_connections'] == release['corrections_or_retries'] == 0
for item in release['records']:
    folder = NEW / item['record']
    done, started, prereg = (read(folder / n) for n in ['completed.json', 'started.json', 'preregistered.json'])
    assert done['pid'] == started['pid'] == item['pid']
    assert done['exit_code'] == item['exit_code'] == 0
    assert not done['alive'] and not done['timed_out'] and not item['alive'] and not item['timed_out']
    assert prereg['argv'] == item['argv'] and prereg['cwd'] == item['cwd']
    assert prereg['timeout_seconds'] == item['timeout_seconds'] <= 45
    for stream in ['stdout', 'stderr']:
        paths = [folder / (stream + ext) for ext in ['.bin', '.log'] if (folder / (stream + ext)).exists()]
        assert len(paths) == 1 and sha(paths[0].read_bytes()) == done[stream + '_sha256'] == item[stream + '_sha256']
    if 'entry_sha256' in prereg:
        assert sha((folder / 'entry-source.py').read_bytes()) == prereg['entry_sha256']

audit = read(OLD / 'case-and-boundary-review.json')
dbs = {}
db_hashes = {}
for entry in audit['all_SQL_audits']:
    label = entry['label']
    if not label.startswith('independent-') or label.endswith(('-pre-runtime', '-pre-target')):
        continue
    source = Path(entry['source'])
    assert source.is_relative_to(OLD)
    raw = source.read_bytes()
    assert len(raw) == entry['bytes'] and sha(raw) == entry['sha256_before_after']
    with tempfile.NamedTemporaryFile(prefix='a03-r11-coordinator-', suffix='.sqlite3', delete=False) as f:
        copy = Path(f.name)
        f.write(raw)
    try:
        con = sqlite3.connect(copy.as_uri() + '?mode=ro&immutable=1', uri=True)
        con.row_factory = sqlite3.Row
        try:
            con.execute('PRAGMA query_only=ON')
            assert con.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            rows = {t: [dict(r) for r in con.execute('SELECT * FROM "' + t.replace('"', '""') + '"')] for t in tables}
            assert rows == entry['SQL'], label
        finally:
            con.close()
        assert copy.read_bytes() == raw == source.read_bytes()
    finally:
        copy.unlink()  # Only the exact private file created immediately above.
    dbs[label], db_hashes[label] = rows, sha(raw)
assert len(dbs) == 40

stages = read(NEW / 'stage-file-index.json')['files']
assert len(stages) == 32
for stage in stages:
    raw = (ROOT / stage['file']).read_bytes()
    assert sha(raw) == stage['sha256'] == db_hashes[stage['completed_SQL_audit_label']]
    assert len(raw) == stage['bytes']
    assert sha((ROOT / stage['capture_file']).read_bytes()) == stage['capture_sha256']

summaries = []
formal_count = resource_count = 0
for c in audit['cases']:
    if c['label'] != 'independent':
        continue
    group = c['group']
    prefix = 'independent-' + group + '-'
    runtime, target = dbs[prefix + 'final-runtime'], dbs[prefix + 'final-target']
    cut = dbs[prefix + 'cut-after-wait-runtime']
    expected_effects = 0 if group in ['F1', 'F2'] else 1
    assert len(target['effects']) == len(dbs[prefix + 'cut-after-wait-target']['effects']) == expected_effects == c['effects']
    assert runtime['plans'][0]['status'] == c['plan_status']
    assert len(runtime['plans']) == len(runtime['actions']) == 1
    assert runtime['native_report_reads'] == []
    assert c['result']['POST_count'] == c['result']['Batch_count'] == c['result']['report_read_count'] == 0
    crash, query = c['processes']['crash'], c['processes']['query']
    assert crash['exit_code'] == 90 and query['exit_code'] == 0 and crash['pid'] != query['pid']
    assert crash['end'] < query['start'] and c['original_instance'] != c['query_instance']
    assert c['marker']['pid'] == crash['pid']
    book = runtime['books'][0]
    assert book == c['final_owner']
    events = [json.loads(x['body']) for x in runtime['events']]
    assert events == c['events']
    previous = '0' * 64
    for i, event in enumerate(events, 1):
        assert event['sequence'] == i and event['previous_hash'] == previous
        assert sha(canonical({k: v for k, v in event.items() if k != 'event_hash'})) == event['event_hash']
        previous = event['event_hash']
    assert previous == book['head_hash']
    runtime_root = Path(runtime['registrations'][0]['package_root']).parent.parent
    package = Path(runtime['registrations'][0]['package_root'])
    for boundary in ['cut_boundary', 'final_boundary']:
        for f in c[boundary]['formal']:
            raw = Path(f['path']).read_bytes()
            entity = json.loads(raw)
            assert sha(raw) == f['sha256']
            assert {k: entity[k] for k in f['ref']} == f['ref']
            assert sha(canonical({k: v for k, v in entity.items() if k != 'content_hash'})) == entity['content_hash']
            assert any(json.loads(a['ref']) == f['ref'] and a['path'] == f['path'] for a in runtime['artifacts'])
            formal_count += 1
        for f in c[boundary]['files']:
            raw = (runtime_root / f['path']).read_bytes()
            assert len(raw) == f['bytes'] and sha(raw) == f['sha256']
        for r in c[boundary]['resources']:
            raw = (package / r['resource']['path']).read_bytes()
            assert len(raw) == r['bytes'] and sha(raw) == r['actual_sha256'] == r['resource']['sha256']
            resource_count += 1
    if group in ['F1', 'F4']:
        assert db_hashes[prefix + 'final-runtime'] == db_hashes[prefix + 'cut-after-wait-runtime']
        assert db_hashes[prefix + 'final-target'] == db_hashes[prefix + 'cut-after-wait-target']
        assert not runtime['resolutions'] and book['generation'] == 1 and book['phase'] == 'ACTIVE'
        if group == 'F1':
            assert not runtime['intents'] and not runtime['permits'] and not runtime['attempts']
        else:
            assert runtime['intents'][0]['state'] == 'APPLIED' and c['result']['attempt_fact'] == 'ATTEMPTED'
    else:
        expected = 'RESOLVED_NOT_APPLIED' if group == 'F2' else 'RESOLVED_APPLIED'
        assert cut['intents'][0]['state'] == 'PENDING' and cut['permits'][0]['state'] == 'CONSUMED'
        assert not cut['resolutions'] and not cut['intents'][0]['receipt']
        assert runtime['intents'][0]['state'] == expected and len(runtime['resolutions']) == 1
        assert book['generation'] == 2 and book['phase'] == 'RELEASED'
        result = c['result']
        assert result['reconcile_calls'] == result['max_attempts'] == 1
        assert result['old_action_replay_calls'] == 0 and result['formal_original_UNKNOWN_retained']
        assert result['new_read_sequence'] > result['old_max_read_sequence']
        assert result['attempt_fact_before'] == result['attempt_fact_after'] == 'MAY_HAVE_BEEN_ATTEMPTED'
    summaries.append({'case': group, 'effect_count': expected_effects, 'plan_status': c['plan_status'], 'crash_pid': crash['pid'], 'query_pid': query['pid'], 'event_count': len(events)})

result = {'status': 'ACCEPTED_FOUR_CRASH_CUTS_ONLY', 'at': datetime.now().astimezone().isoformat(),
    'target_commit': TARGET, 'closure_workflow': WORKFLOW, 'new_manifest_entries': len(entries),
    'original_files_against_raw_git': len(old_index), 'current_closure_children_exited': 3,
    'private_immutable_SQL_copies_checked': len(dbs), 'independent_stage_binary_files': len(stages),
    'formal_boundary_entries_checked': formal_count, 'resource_boundary_entries_checked': resource_count,
    'cases': summaries, 'functional_calls': 0, 'product_imports': 0, 'original_SQL_connections': 0,
    'author_F2_F3_intermediate_binaries_still_absent': True, 'old_REWORK_preserved': True,
    'whole_A03': 'REWORK', 'product_integration': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
(OUT / 'coordinator-corroboration.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(result, ensure_ascii=False))
