"""File/SQL-only readback of the first D1 failure; never import product."""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R9-minimal-demos'
VALIDATION = OUT / 'validation/r9-01'
CASE = VALIDATION / 'cases/D1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_db(path):
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in tables}
        result = {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'bytes': len(raw),
            'quick_check': db.execute('PRAGMA quick_check').fetchone()[0],
            'counts': {name: len(values) for name, values in rows.items()}, 'tables': rows}
    assert raw == path.read_bytes()
    result['bytes_unchanged_after_read'] = True
    return result


def ref(artifact):
    return {k: artifact[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


if __name__ == '__main__':
    result = {'mode': 'stdlib only; mode=ro&immutable=1; connection-local query_only',
        'before_runtime': read_db(CASE / 'before-run-runtime.sqlite3'),
        'before_target': read_db(CASE / 'before-run-target.sqlite3'),
        'after_runtime': read_db(CASE / 'runtime/runtime.sqlite3'),
        'after_target': read_db(CASE / 'target/target.sqlite3'),
        'before_copy_limit': 'Raw file bytes were copied before run_plan while the own lease keeper existed; no transactional-backup claim. Reads here are of completed frozen files.'}
    runtime = result['after_runtime']['tables']
    reg = runtime['registrations'][0]
    bundle_path = Path(reg['bundle_path'])
    bundle_raw = bundle_path.read_bytes()
    bundle = json.loads(bundle_raw)
    refs = [json.loads(row['ref']) for row in runtime['artifacts']]
    assert all(ref(a) in refs for a in bundle['artifacts'])
    receipts = [a for a in bundle['artifacts'] if a['kind'] == 'ExecutionReceipt']
    plan = next(a for a in bundle['artifacts'] if a['kind'] == 'ApplyPlan')
    intent = next(a for a in bundle['artifacts'] if a['kind'] == 'WriteIntent')
    assert len(receipts) == 1
    receipt = receipts[0]
    assert json.loads(runtime['intents'][0]['receipt']) == ref(receipt)
    fact_resource = json.loads(runtime['actions'][0]['fact'])
    fact_raw = (Path(reg['package_root']) / fact_resource['path']).read_bytes()
    assert sha(fact_raw) == fact_resource['sha256']
    fact = json.loads(fact_raw)
    assert fact['plan_ref'] == ref(plan)
    assert fact['intent_ref'] == ref(intent)
    assert fact['action_id'] == plan['payload']['actions'][0]['action_id']
    assert fact['result']['outcome'] == 'APPLIED'
    assert result['before_target']['counts']['effects'] == 0
    assert result['after_target']['counts']['effects'] == 1
    result['formal_boundary'] = {'current_bundle_path': bundle_path.relative_to(ROOT).as_posix(),
        'current_bundle_sha256': sha(bundle_raw), 'all_current_refs_formally_registered': True,
        'plan_ref': ref(plan), 'intent_ref': ref(intent), 'receipt_ref': ref(receipt),
        'receipt': receipt, 'fact_resource': fact_resource, 'fact': fact,
        'progress': [a for a in bundle['artifacts'] if a['kind'] == 'ExecutionProgress'],
        'POST_count': sum(a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY' for a in bundle['artifacts']),
        'Batch_count': sum(a['kind'] == 'BatchReport' for a in bundle['artifacts']),
        'report_read_count': len(runtime['native_report_reads']), 'target_effect_delta': 1,
        'D1_restarted_query_duplicate_check': 'NOT_RUN_AFTER_FIRST_EXECUTE_FAILURE',
        'D2': 'NOT_RUN_AFTER_D1_FAILURE'}
    with (OUT / 'first-failure-readback.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'effect_count_before': 0, 'effect_count_after': 1, 'receipt_count': 1,
        'attempt_fact': fact['result']['attempt_fact'], 'POST_count': result['formal_boundary']['POST_count'],
        'Batch_count': result['formal_boundary']['Batch_count'], 'product_calls': 0}))
