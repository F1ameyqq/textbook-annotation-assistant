"""Read frozen R2 state and exact formal bindings; never imports product code."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R2-projection'
BASE = 'a0c40886f3076f84c46377e03fc2206d2fdc5585'
ALLOWED = {'src/annotation/runtime/storage/__init__.py',
    'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(artifact):
    return {key: artifact[key] for key in ('artifact_id', 'revision', 'kind', 'content_hash')}


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def connection(path):
    result = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    result.row_factory = sqlite3.Row
    result.execute('PRAGMA query_only=ON')
    return result


def main():
    case = OUT / 'validation/native-r2-01/cases/N1'
    runtime, target = case / 'runtime/runtime.sqlite3', case / 'target/target.sqlite3'
    before_runtime, before_target = sha(runtime.read_bytes()), sha(target.read_bytes())
    db = connection(runtime)
    try:
        metadata = dict(db.execute('SELECT key,value FROM meta'))
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in
            ('books', 'registrations', 'plans', 'actions', 'intents', 'permits', 'resolutions',
             'artifacts', 'events', 'native_pre_runs', 'native_creation_anchors', 'native_report_reads')}
        reg = dict(db.execute('SELECT * FROM registrations').fetchone())
        tables = {name: [dict(row) for row in db.execute('SELECT * FROM ' + name)] for name in
            ('books', 'plans', 'actions', 'intents', 'permits', 'resolutions', 'native_pre_runs', 'native_creation_anchors', 'native_report_reads')}
        artifacts_sql = [dict(row) for row in db.execute('SELECT * FROM artifacts')]
        events = [json.loads(row[0]) for row in db.execute('SELECT body FROM events ORDER BY sequence')]
        runtime_check = db.execute('PRAGMA quick_check').fetchone()[0]
        runtime_version = {'application_id': db.execute('PRAGMA application_id').fetchone()[0], 'user_version': db.execute('PRAGMA user_version').fetchone()[0]}
    finally:
        db.close()
    db = connection(target)
    try:
        effects = [json.loads(row[0]) for row in db.execute('SELECT body FROM effects ORDER BY sequence')]
        observed_count = db.execute('SELECT count(*) FROM observations').fetchone()[0]
        target_descriptor = json.loads(db.execute("SELECT value FROM meta WHERE key='descriptor'").fetchone()[0])
        target_check = db.execute('PRAGMA quick_check').fetchone()[0]
    finally:
        db.close()
    if sha(runtime.read_bytes()) != before_runtime or sha(target.read_bytes()) != before_target:
        raise RuntimeError('immutable readback changed database bytes')
    bundle_path = Path(reg['bundle_path'])
    bundle = json.loads(bundle_path.read_bytes())
    artifacts = bundle['artifacts']
    package_root = Path(reg['package_root'])
    kind_counts = {kind: sum(a['kind'] == kind for a in artifacts) for kind in sorted({a['kind'] for a in artifacts})}
    sql_refs = [json.loads(row['ref']) for row in artifacts_sql]
    receipt = next(a for a in artifacts if a['kind'] == 'ExecutionReceipt')
    receipt_ref = ref(receipt)
    intent = tables['intents'][0]
    action = tables['actions'][0]
    fact_resource = json.loads(action['fact'])
    fact_raw = (package_root / fact_resource['path']).read_bytes()
    if sha(fact_raw) != fact_resource['sha256']:
        raise RuntimeError('material fact raw hash mismatch')
    fact = json.loads(fact_raw)
    progresses = [a for a in artifacts if a['kind'] == 'ExecutionProgress']
    material_progress = [a for a in progresses if any(item['result_fact'] == fact_resource for item in a['payload']['actions'])]
    matches = []
    for progress in material_progress:
        item = progress['payload']['actions'][0]
        same = {'plan': progress['payload']['plan_ref'] == fact['plan_ref'],
            'action': item['action_id'] == fact['action_id'], 'intent': item['intent_ref'] == fact['intent_ref'],
            'attempt': item['attempt_fact'] == fact['result']['attempt_fact'],
            'attempt_evidence': item['attempt_evidence_refs'] == fact['result']['attempt_evidence_refs'],
            'receipt': item['receipt_ref'] == receipt_ref, 'SQL_artifact': ref(progress) in sql_refs}
        if not all(same.values()):
            raise RuntimeError('formal material progress differs')
        matches.append({'progress_ref': ref(progress), 'checks': same, 'action': item})
    if not matches or receipt_ref not in sql_refs or json.loads(intent['receipt']) != receipt_ref:
        raise RuntimeError('formal SQL/current bundle/intent receipt does not agree')
    heads = [a for a in artifacts if a['kind'] == 'ReconciliationResult']
    if any(a['payload']['original_receipt_ref'] is not None for a in heads):
        raise RuntimeError('null original receipt was rewritten')
    n1 = json.loads((OUT / 'validation/native-r2-01/N1-result.json').read_bytes())
    reports = []
    for report_ref in (n1['quality']['postcheck_ref'], n1['quality']['batch_ref']):
        artifact = next(a for a in artifacts if ref(a) == report_ref)
        if report_ref not in sql_refs or artifact['payload']['content_check_status'] != 'PENDING' or artifact['payload']['submission_status'] != 'NOT_SUBMITTED':
            raise RuntimeError('formal report identity or completion guard differs')
        reports.append(artifact)
    run = tables['native_pre_runs'][0]
    pre = next(a for a in artifacts if ref(a) == json.loads(run['pre_ref']))
    run_resource = pre['payload']['synthetic_run_ref']
    run_raw = (package_root / run_resource['path']).read_bytes()
    if sha(run_raw) != run_resource['sha256']:
        raise RuntimeError('PRE raw run hash mismatch')
    hold_events = [event for event in events if event['event'] == 'TARGET_DRIFT_HOLD']
    hold_id = tables['books'][0]['hold']
    if not hold_id or hold_events[-1]['payload']['hold_id'] != hold_id:
        raise RuntimeError('actual current hold/event mismatch')
    if len(effects) != 1 or any(json.loads(row['binding'])['context']['kind'] == 'POST_HOLD' for row in tables['native_pre_runs']):
        raise RuntimeError('effect count or pre-run boundary differs from saved failure')
    anchors = []
    for row in tables['native_creation_anchors']:
        raw = Path(row['input_path']).read_bytes()
        anchors.append({'plan_artifact_id': row['plan_artifact_id'], 'stored_sha256': row['input_sha'],
            'actual_sha256': sha(raw), 'same': sha(raw) == row['input_sha'],
            'artifact_count': len(json.loads(raw)['artifacts']), 'resource_manifest_entries': len(json.loads(row['manifest'])),
            'N6_history_recompute': 'NOT_RUN'})
    write('database-readback.json', {'mode': 'ro&immutable=1; connection-local query_only=ON', 'bytes_unchanged_after_read': True,
        'runtime': {'raw_sha256': before_runtime, 'path': runtime.relative_to(ROOT).as_posix(), 'quick_check': runtime_check,
            'version': runtime_version, 'meta': metadata, 'counts': counts, 'tables': tables, 'SQL_artifacts': artifacts_sql},
        'target': {'raw_sha256': before_target, 'path': target.relative_to(ROOT).as_posix(), 'quick_check': target_check,
            'descriptor': target_descriptor, 'effects': effects, 'effect_count': len(effects), 'observation_count': observed_count},
        'current_bundle': {'path': bundle_path.relative_to(ROOT).as_posix(), 'raw_sha256': sha(bundle_path.read_bytes()),
            'artifact_kind_counts': kind_counts, 'formal_receipt': receipt, 'formal_reports': reports,
            'terminal_heads': heads, 'progresses': progresses},
        'material_fact': {'resource': fact_resource, 'raw_sha256': sha(fact_raw), 'data': fact},
        'formal_progress_binding': matches, 'receipt_SQL_current_intent_same': True,
        'PRE': {'status': run['status'], 'ref': json.loads(run['pre_ref']), 'run_resource': run_resource,
            'run': json.loads(run_raw)}, 'creation_anchors': anchors, 'hold_events': hold_events,
        'event_names': [event['event'] for event in events]})
    source = ROOT / 'src/annotation/runtime/storage/__init__.py'
    native = ROOT / 'src/annotation/runtime/storage/native.py'
    write('post-hold-blocker.json', {'code': 'TARGET_DRIFT_HOLD', 'actual_trace': 'runs/N2/stderr.txt',
        'hold_id': hold_id, 'actual_kind_argument': 'POST_HOLD', 'current_book': tables['books'][0],
        'native_source_sha256': sha(native.read_bytes()), 'storage_source_sha256': sha(source.read_bytes()),
        'call_site': 'runtime/storage/native.py:318, begin_native_pre calls _lease without pending_ok',
        'actual_guard': 'runtime/storage/__init__.py:346-347, not pending_ok and row[hold] rejects',
        'later_branch': 'runtime/storage/native.py:319-320, POST_HOLD context check was not reached',
        'POST_HOLD_run_rows': 0, 'product_rerun_or_second_fix': False})
    write('bounded-outcome.json', {'status': 'REVIEW_N2_BLOCKED', 'product_corrections': 1,
        'minimal': 'PASS_FACT_PROVENANCE_NO_FACT_FALLBACK_IDENTITY_REJECTION', 'N1': 'PASS_COMPLETE_ACTUAL_SYNTHETIC_CHAIN',
        'N2': 'FAILED_BEFORE_POST_HOLD_RUN_AT_DEFAULT_LEASE_HOLD_GUARD',
        'N3_N7': 'NOT_RUN_AFTER_NEW_INDEPENDENT_PRODUCT_BLOCKER',
        'reconcile_returned': True, 'formal_receipt_progress_registered': True, 'independent_POST_Batch_registered': True,
        'effect_count': len(effects), 'original_UNKNOWN_retained': any(item['effective_outcome'] == 'UNKNOWN' for a in progresses for item in a['payload']['actions']),
        'original_receipt_ref': None, 'content_check_status': 'PENDING', 'submission_status': 'NOT_SUBMITTED',
        'current_hold_id': hold_id, 'C01': '70_PASS_FINAL_CANDIDATE', 'A02': '52_PASS_FINAL_CANDIDATE', 'R7': '13_PASS_FINAL_CANDIDATE',
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION', 'I01': 'NOT_RELEASED'})
    def tree(commit):
        raw = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'ls-tree', '-r', commit], cwd=ROOT)
        return {line.split('\t', 1)[1]: line.split('\t', 1)[0].split() for line in raw.decode().splitlines()}
    baseline, current = tree(BASE), tree('HEAD')
    if any(current.get(name) != value for name, value in baseline.items() if name not in ALLOWED):
        raise RuntimeError('protected raw Git entries changed')
    changed = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'diff', '--name-only', BASE], cwd=ROOT).decode().splitlines()
    if any(path in baseline and path not in ALLOWED for path in changed):
        raise RuntimeError('out-of-scope existing file changed')
    write('preservation.json', {'base': BASE, 'base_entries': len(baseline), 'protected_entries': len(baseline) - len(ALLOWED),
        'protected_mode_type_blob_unchanged': True, 'allowed_old_changes': sorted(path for path in changed if path in baseline),
        'protected_tuple_sha256': sha(json.dumps(sorted((p, v) for p, v in baseline.items() if p not in ALLOWED), ensure_ascii=False, separators=(',', ':')).encode()),
        'old_R7_R8_R1_evidence_and_failures_unchanged': True})
    print(json.dumps({'N1_formal_receipt': receipt_ref, 'material_progresses_with_matching_provenance': len(matches),
        'formal_POST_Batch': len(reports), 'effects': len(effects), 'N2_blocker': 'TARGET_DRIFT_HOLD', 'POST_HOLD_runs': 0}))


if __name__ == '__main__':
    main()
