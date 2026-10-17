"""Frozen R3 readback; stdlib immutable SQL and saved JSON only."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R3-post-hold'
BASE = '58d8a64734271d15654bb00b03d760f0f3eccd10'
WORKFLOW = 'b79b12fe6a82f9d88b6533b54aea016c4f67f60b'
ALLOWED = {'src/annotation/runtime/storage/native.py', 'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def ref(value):
    return {key: value[key] for key in ('artifact_id', 'revision', 'kind', 'content_hash')}


def read_database(path, runtime=True):
    before = sha(path.read_bytes())
    db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    try:
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        selected = ('books', 'registrations', 'plans', 'actions', 'intents', 'permits', 'resolutions',
            'native_pre_runs', 'native_creation_anchors', 'native_report_reads') if runtime else ('effects', 'observations')
        tables = {name: [dict(row) for row in db.execute('SELECT * FROM ' + name)] for name in selected if name in names}
        if runtime:
            tables['artifacts'] = [dict(row) for row in db.execute('SELECT * FROM artifacts')]
            tables['events'] = [json.loads(row[0]) for row in db.execute('SELECT body FROM events ORDER BY sequence')]
        result = {'path': path.relative_to(ROOT).as_posix(), 'raw_sha256': before, 'quick_check': db.execute('PRAGMA quick_check').fetchone()[0],
            'application_id': db.execute('PRAGMA application_id').fetchone()[0], 'user_version': db.execute('PRAGMA user_version').fetchone()[0],
            'meta': dict(db.execute('SELECT key,value FROM meta')), 'counts': {name: len(rows) for name, rows in tables.items()}, 'tables': tables}
    finally:
        db.close()
    if sha(path.read_bytes()) != before:
        raise RuntimeError('immutable read changed bytes')
    result['bytes_unchanged_after_read'] = True
    return result


def main():
    root = OUT / 'validation/native-r3-01'
    case = root / 'cases/N1'
    runtime = read_database(case / 'runtime/runtime.sqlite3')
    target = read_database(case / 'target/target.sqlite3', runtime=False)
    reg = runtime['tables']['registrations'][0]
    package = Path(reg['package_root'])
    bundle_raw = Path(reg['bundle_path']).read_bytes()
    bundle = json.loads(bundle_raw)
    artifacts = bundle['artifacts']
    sql_refs = [json.loads(row['ref']) for row in runtime['tables']['artifacts']]
    action = runtime['tables']['actions'][0]
    fact_ref = json.loads(action['fact'])
    fact_raw = (package / fact_ref['path']).read_bytes()
    if sha(fact_raw) != fact_ref['sha256']:
        raise RuntimeError('fact hash differs')
    fact = json.loads(fact_raw)
    receipt = next(a for a in artifacts if a['kind'] == 'ExecutionReceipt')
    if ref(receipt) not in sql_refs or json.loads(runtime['tables']['intents'][0]['receipt']) != ref(receipt):
        raise RuntimeError('formal receipt differs across SQL/current/intent')
    material_progress = []
    unknown = []
    for artifact in artifacts:
        if artifact['kind'] != 'ExecutionProgress':
            continue
        for item in artifact['payload']['actions']:
            if item['effective_outcome'] == 'UNKNOWN':
                unknown.append({'ref': ref(artifact), 'item': item})
            if item['result_fact'] == fact_ref:
                comparisons = {'plan': artifact['payload']['plan_ref'] == fact['plan_ref'], 'action': item['action_id'] == fact['action_id'],
                    'intent': item['intent_ref'] == fact['intent_ref'], 'attempt': item['attempt_fact'] == fact['result']['attempt_fact'],
                    'attempt_evidence': item['attempt_evidence_refs'] == fact['result']['attempt_evidence_refs'],
                    'receipt': item['receipt_ref'] == ref(receipt), 'SQL_ref': ref(artifact) in sql_refs}
                if not all(comparisons.values()):
                    raise RuntimeError('formal progress binding mismatch')
                material_progress.append({'ref': ref(artifact), 'item': item, 'checks': comparisons})
    n1 = json.loads((root / 'N1-result.json').read_bytes())
    reports = [next(a for a in artifacts if ref(a) == n1['quality'][name]) for name in ('postcheck_ref', 'batch_ref')]
    for artifact in reports:
        if ref(artifact) not in sql_refs or artifact['payload']['content_check_status'] != 'PENDING' or artifact['payload']['submission_status'] != 'NOT_SUBMITTED':
            raise RuntimeError('formal report differs')
    heads = [a for a in artifacts if a['kind'] == 'ReconciliationResult']
    if not unknown or any(a['payload']['original_receipt_ref'] is not None for a in heads):
        raise RuntimeError('UNKNOWN/null original receipt not preserved')
    hold_events = [event for event in runtime['tables']['events'] if event['event'] == 'TARGET_DRIFT_HOLD']
    hold = runtime['tables']['books'][0]['hold']
    if hold_events[-1]['payload']['hold_id'] != hold:
        raise RuntimeError('current hold mismatch')
    run_details = []
    for row in runtime['tables']['native_pre_runs']:
        binding = json.loads(row['binding'])
        pre_ref = json.loads(row['pre_ref'])
        pre = next(a for a in artifacts if ref(a) == pre_ref)
        resource = pre['payload']['synthetic_run_ref']
        raw = (package / resource['path']).read_bytes()
        run = json.loads(raw)
        if sha(raw) != resource['sha256'] or row['run_sha'] != resource['sha256'] or row['status'] != 'ADMITTED':
            raise RuntimeError('admitted PRE identity mismatch')
        if run['context'] != binding['context'] or run['checks'] != {key: 'PASS' for key in ('source_integrity', 'structure', 'answer_matching', 'coverage', 'policy')}:
            raise RuntimeError('saved PRE binding/check mismatch')
        if binding['context']['kind'] == 'POST_HOLD':
            ctx = binding['context']
            hold_raw = (package / ctx['hold_ref']['path']).read_bytes()
            if sha(hold_raw) != ctx['hold_ref']['sha256'] or json.loads(hold_raw) != hold_events[-1]:
                raise RuntimeError('exact hold event resource mismatch')
            if ctx['hold_id'] != hold or ctx['hold_head'] != {'sequence': row['head_sequence'], 'hash': row['head_hash']}:
                raise RuntimeError('exact hold/head mismatch')
        run_details.append({'row': row, 'binding': binding, 'pre_ref': pre_ref, 'run_resource': resource, 'run': run})
    if target['counts']['effects'] != 1:
        raise RuntimeError('main target effect count changed')
    n2 = json.loads((root / 'N2-result.json').read_bytes())
    post_runs = [row for row in run_details if row['binding']['context']['kind'] == 'POST_HOLD']
    if len(post_runs) != 2 or any(r['actual_code'] != r['expected_code'] for r in n2['refusals']):
        raise RuntimeError('POST_HOLD lifecycle evidence differs')
    write(OUT / 'database-readback.json', {'mode': 'ro&immutable=1; connection-local query_only', 'runtime': runtime, 'target': target,
        'current_bundle': {'path': Path(reg['bundle_path']).relative_to(ROOT).as_posix(), 'raw_sha256': sha(bundle_raw),
            'formal_receipt': receipt, 'formal_reports': reports, 'terminal_heads': heads, 'original_UNKNOWN': unknown,
            'material_progress': material_progress, 'fact_resource': fact_ref, 'fact': fact},
        'admitted_run_details': run_details, 'hold_events': hold_events, 'N1': n1, 'N2': n2,
        'N6_creation_anchor_recompute': 'NOT_RUN_AFTER_N7_DIAGNOSTIC_FAILURE'})
    controls = {}
    for name in ('local-pending', 'N4-a', 'N4-b', 'N7'):
        directory = root / 'cases' / name
        controls[name] = {'runtime': read_database(directory / 'runtime/runtime.sqlite3')}
        if (directory / 'target/target.sqlite3').exists():
            controls[name]['target'] = read_database(directory / 'target/target.sqlite3', runtime=False)
    if any(controls[name]['target']['counts']['effects'] != 0 for name in ('local-pending', 'N4-a', 'N4-b')):
        raise RuntimeError('negative controls produced target effects')
    write(OUT / 'control-database-readback.json', controls)
    write(OUT / 'bounded-outcome.json', {'status': 'REVIEW_N7_DIAGNOSTIC_ASSERTION_FAILED', 'product_corrections': 1,
        'local': 'PASS_NORMAL_API_NO_HOLD_OWNER_PENDING_CONTROLS', 'N1': 'PASS_COMPLETE_ACTUAL_CHAIN',
        'N2': 'PASS_TWO_ACTUAL_POST_HOLD_ADMISSIONS_OLD_PROOF_NORMAL_PROGRESS_REAL_EXPIRY',
        'N3': 'PASS_FIVE_SCHEMA_VALID_SEMANTIC_MISMATCHES', 'N4': 'PASS_MISSING_SERIALIZED_FOREIGN_RUN_OBSERVATION',
        'N5': 'PASS_STATIC_HISTORY_NATIVE_AUTHORITY_REFUSALS', 'N6': 'NOT_RUN_AFTER_N7_DIAGNOSTIC_FAILURE',
        'N7': 'FAILED_EXACT_CODE_ASSERTION_AFTER_STRICT_REOPEN_AND_OLD_ENTRY_REFUSAL',
        'N7_incomplete_initialization': 'NOT_REACHED',
        'N7_actual_outer_code': 'TARGET_STORE_CORRUPT', 'N7_inner_version_refusal': 'TARGET_STORE_VERSION_UNSUPPORTED',
        'N7_driver_expected_code': 'TARGET_STORE_VERSION_UNSUPPORTED', 'old_target_adopted_or_reset': False,
        'new_scope_required': 'delivery/mock/persistent.py open version-refusal/ValueError catch; not changed in R3',
        'target_effect_count_main': 1, 'target_effect_count_local_N4': 0, 'hold_cleared': False,
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION', 'I01': 'NOT_RELEASED'})
    def git(*args):
        return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)
    def tree(commit):
        return {line.split('\t', 1)[1]: line.split('\t', 1)[0].split() for line in git('ls-tree', '-r', commit).decode().splitlines()}
    baseline, current = tree(BASE), tree('HEAD')
    if any(current.get(name) != value for name, value in baseline.items() if name not in ALLOWED):
        raise RuntimeError('protected old Git entry changed')
    changed = git('diff', '--name-only', BASE).decode().splitlines()
    if any(path in baseline and path not in ALLOWED for path in changed):
        raise RuntimeError('out-of-scope existing path changed')
    write(OUT / 'preservation.json', {'base': BASE, 'base_entries': len(baseline), 'protected_entries': len(baseline) - len(ALLOWED),
        'protected_mode_type_blob_unchanged': True, 'allowed_old_changes': sorted(path for path in changed if path in baseline),
        'protected_tuple_sha256': sha(json.dumps(sorted((p, v) for p, v in baseline.items() if p not in ALLOWED), ensure_ascii=False, separators=(',', ':')).encode()),
        'shared_lease_projection_producer_contract_schema_and_all_old_evidence_unchanged': True})
    supplemental = []
    for name in ('A03-runtime-recovery.md', 'A03-independent-review.md'):
        raw = git('show', WORKFLOW + ':docs/tasks/' + name)
        path = OUT / 'inputs/matrix' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        supplemental.append({'commit': WORKFLOW, 'path': 'docs/tasks/' + name, 'bytes': len(raw), 'sha256': sha(raw)})
    write(OUT / 'supplemental-input-index.json', supplemental)
    print(json.dumps({'main_effects': 1, 'formal_receipt': ref(receipt), 'formal_POST_Batch': len(reports),
        'POST_HOLD_admitted': len(post_runs), 'hold_preserved': hold, 'N7_outer_code': 'TARGET_STORE_CORRUPT',
        'N6_and_incomplete_init': 'NOT_RUN'}))


if __name__ == '__main__':
    main()
