"""Bounded coordinator checks; retained immutable evidence only, no product import."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name('T2-checks.json')
assert not OUT.exists()
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

pins = {
    'docs/tasks/A03-T2-static-archive-review-report.md': '19ef1aff1575a7f1546f4774dc9a57832d6de9430dfed851af341e866dcb137a',
    'docs/evidence/A03/T2/review/static-archive-recheck.json': 'a3f7b00da6b2a9e2923b7b5a1bf27bd60b8d625b40302d1a5db2dc25c1c6a3f8',
    'docs/evidence/coordinator/heartbeat-20261018-0337/T2-archive-inventory.json': '55d35f4724962fd6e7de0878976aa2de92c5c5849c6c7886d3a31c9a02d3dcd2',
    'docs/tasks/A03-T2-review-report.md': 'e77aa974729845c687f9ce205966e87d59250f12f7b23a4429facb4aa17ab103',
}
for p, expected in pins.items():
    assert sha(ROOT / p) == expected, p
review = read(ROOT / 'docs/evidence/A03/T2/review/static-archive-recheck.json')
inventory = read(ROOT / 'docs/evidence/coordinator/heartbeat-20261018-0337/T2-archive-inventory.json')
assert review['conclusion'] == 'ACCEPTED_FIXED_C12_H1_AND_NEW_ARCHIVE_INVENTORY_ONLY'
assert review['unique_archive_blocker_closed'] is True
assert review['process']['completed']['exit_code'] == 0
assert not review['process']['completed']['alive']
assert len(inventory['files']) == len(review['members']) == 267
for item in inventory['files']:
    p = ROOT / item['path']
    assert p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], p
base = ROOT / 'docs/evidence/A03/T2/review/independent-01'
assert not (base / 'manifest.json').exists()
release = read(base / 'final-release.json')
assert release['all_registered_children_waited_and_reaped']
assert not release['own_business_or_background_resources_remaining']
assert len(release['processes']) == 11
assert all(p['completed']['exit_code'] == 0 and not p['completed']['alive'] and not p['completed']['timeout'] for p in release['processes'])
assert all(not k['alive'] for k in release['keeper_release']['keepers']['all_keeper_threads'])
c = read(base / 'independent-run/C-result.json')
assert c['cases_run'] == 12 and c['functional_assertions'] == 'PASS'
assert all((r['expected_code'] in r['actual_codes']) if r['expected_code'] else not r['actual_codes'] for r in c['results'])

stages = ['unknown-established', 'after-release', 'after-reconcile', 'before-report', 'after-report']
rows = {}
db_hashes = {}
for stage in stages:
    folder = base / 'independent-run/cases/H1/captures' / stage
    recorded = read(folder / 'SQL.json')
    stage_rows = {}
    for kind, tables in [('runtime', ['books', 'actions', 'intents', 'permits', 'resolutions', 'native_report_reads']), ('target', ['effects'])]:
        p = folder / (kind + '.sqlite3')
        before = sha(p)
        conn = sqlite3.connect(p.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
        try:
            conn.row_factory = sqlite3.Row
            for table in tables:
                actual = [dict(r) for r in conn.execute('SELECT * FROM "' + table + '"')]
                assert sorted(map(lambda x: json.dumps(x, sort_keys=True), actual)) == sorted(map(lambda x: json.dumps(x, sort_keys=True), recorded[kind]['tables'][table])), (stage, kind, table)
                stage_rows[table] = actual
        finally:
            conn.close()
        assert sha(p) == before
        db_hashes[str(p.relative_to(ROOT)).replace('\\', '/')] = before
    assert len(stage_rows['effects']) == 1
    assert len(stage_rows['intents']) == 1 and len(stage_rows['permits']) == 1
    assert stage_rows['permits'][0]['state'] == 'CONSUMED'
    rows[stage] = stage_rows
assert rows['unknown-established']['intents'][0]['state'] == 'PENDING'
assert rows['after-release']['intents'][0]['state'] == 'PENDING'
for stage in ['after-reconcile', 'before-report', 'after-report']:
    assert rows[stage]['intents'][0]['state'] == 'RESOLVED_APPLIED'
    assert rows[stage]['intents'][0]['receipt'] == rows['unknown-established']['intents'][0]['receipt']
assert rows['before-report']['native_report_reads'] == []
assert len(rows['after-report']['native_report_reads']) == 1
assert rows['after-report']['native_report_reads'][0]['reads'] == 1
owner = rows['after-report']['books'][0]
assert owner['owner'] is None and owner['pid'] is None and owner['lease'] == 0 and owner['phase'] == 'RELEASED' and owner['generation'] == 3
out = {
    'at': datetime.now(timezone.utc).isoformat(), 'decision': 'ACCEPTED_C12_H1_AND_ARCHIVE_ONLY',
    'target_commit': '699f748a124162b3118e3996c03757725daac363',
    'archive_workflow': '94c376914db82942ceb0246f338e5caa574cfb42',
    'report_and_inventory_pins': pins, 'retained_archive_members_rehashed': 267,
    'raw_Git_validation_reused': 'Independent one-batch frozen workflow check plus prior coordinator archive staging check',
    'immutable_database_reads': db_hashes, 'database_bytes_unchanged': True,
    'checked_stages': stages, 'checks': ['C12 recorded expected codes', 'UNKNOWN pending and CONSUMED permit', 'MATCH resolution retains original receipt', 'effect count remains one', 'report-only read counter zero to one', 'final owner generation 3 released', '11 business children exited and keepers joined'],
    'business_reruns': 0, 'product_imports': 0, 'old_manifest_absent_preserved': True,
    'old_failures_and_missing_metadata_preserved': True, 'whole_A03_accepted': False, 'I01_released': False,
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'decision': out['decision'], 'archive_members': 267, 'immutable_databases': len(db_hashes), 'business_reruns': 0}))
