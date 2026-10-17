"""Frozen read-only R1 receipts/state inspection; no product import or rerun."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R1-producer'
BASE = 'fa6edeb7e9dd0c9502781747e5fce012931d9441'
ALLOWED = {'src/annotation/quality/synthetic_precheck.py',
    'src/annotation/contracts/a03_native/data/profile.json', 'src/annotation/contracts/a03_native/data/adoption.json'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def database(path):
    before = sha(path.read_bytes())
    connection = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    return connection, before


def main():
    case = OUT / 'validation/native-r1-01/cases/N1'
    runtime = case / 'runtime/runtime.sqlite3'
    target = case / 'target/target.sqlite3'
    db, runtime_sha = database(runtime)
    with db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in
            ('books', 'registrations', 'native_pre_runs', 'plans', 'actions', 'intents', 'permits', 'resolutions', 'native_creation_anchors', 'native_report_reads')}
        registrations = [dict(row) for row in db.execute('SELECT * FROM registrations')]
        reg = registrations[0]
        current_path = Path(reg['bundle_path'])
        bundle = json.loads(current_path.read_bytes())
        package_root = Path(reg['package_root'])
        runs = [dict(r) for r in db.execute('SELECT * FROM native_pre_runs')]
        plans = [dict(r) for r in db.execute('SELECT * FROM plans')]
        intents = [dict(r) for r in db.execute('SELECT * FROM intents')]
        actions = [dict(r) for r in db.execute('SELECT * FROM actions')]
        permits = [dict(r) for r in db.execute('SELECT * FROM permits')]
        resolutions = [dict(r) for r in db.execute('SELECT * FROM resolutions')]
        anchors = [dict(r) for r in db.execute('SELECT * FROM native_creation_anchors')]
        events = [json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY sequence')]
        native_metadata = dict(db.execute('SELECT key,value FROM meta'))
        runtime_check = db.execute('PRAGMA quick_check').fetchone()[0]
        native_versions = {'application_id': db.execute('PRAGMA application_id').fetchone()[0], 'user_version': db.execute('PRAGMA user_version').fetchone()[0]}
    db.close()
    td, target_sha = database(target)
    with td:
        effects = [json.loads(r[0]) for r in td.execute('SELECT body FROM effects ORDER BY sequence')]
        target_observations = td.execute('SELECT count(*) FROM observations').fetchone()[0]
        target_descriptor = json.loads(td.execute("SELECT value FROM meta WHERE key='descriptor'").fetchone()[0])
        target_check = td.execute('PRAGMA quick_check').fetchone()[0]
    td.close()
    if sha(runtime.read_bytes()) != runtime_sha or sha(target.read_bytes()) != target_sha:
        raise RuntimeError('immutable readback changed database bytes')
    fact_ref = json.loads(actions[0]['fact'])
    fact_path = package_root / fact_ref['path']
    fact_raw = fact_path.read_bytes()
    if sha(fact_raw) != fact_ref['sha256']:
        raise RuntimeError('material fact resource hash differs')
    fact = json.loads(fact_raw)
    artifacts = bundle['artifacts']
    kind_counts = {kind: sum(a['kind'] == kind for a in artifacts) for kind in sorted({a['kind'] for a in artifacts})}
    heads = [a for a in artifacts if a['kind'] == 'ReconciliationResult']
    progress = [{'ref': {k: a[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}, 'actions': a['payload']['actions']}
        for a in artifacts if a['kind'] == 'ExecutionProgress']
    pre = next(a for a in artifacts if a['kind'] == 'CheckReport' and a['payload']['stage'] == 'PRE_APPLY')
    run_ref = pre['payload']['synthetic_run_ref']
    run_raw = (package_root / run_ref['path']).read_bytes()
    if sha(run_raw) != run_ref['sha256']:
        raise RuntimeError('PRE actual run raw hash differs')
    run = json.loads(run_raw)
    candidates = []
    for path in package_root.glob('bundle-*.json'):
        value = json.loads(path.read_bytes())
        for artifact in value['artifacts']:
            if artifact['kind'] == 'ExecutionReceipt':
                candidates.append({'bundle_path': path.relative_to(ROOT).as_posix(), 'current_registered_bundle': path == current_path,
                    'bundle_sha256': sha(path.read_bytes()), 'receipt_ref': {k: artifact[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}})
    anchor_checks = []
    for anchor in anchors:
        raw = Path(anchor['input_path']).read_bytes()
        anchor_data = json.loads(raw)
        anchor_checks.append({'input_sha256': sha(raw), 'stored_input_sha256': anchor['input_sha'],
            'same': sha(raw) == anchor['input_sha'], 'artifact_count': len(anchor_data['artifacts']),
            'resource_manifest_entries': len(json.loads(anchor['manifest'])), 'plan_artifact_id': anchor['plan_artifact_id'],
            'history_recompute_after_UNKNOWN': 'NOT_RUN'})
    write('database-readback.json', {'read_mode': 'ro&immutable=1; connection-local query_only=ON',
        'runtime': {'path': runtime.relative_to(ROOT).as_posix(), 'raw_sha256': runtime_sha, 'quick_check': runtime_check,
            'versions': native_versions, 'meta': native_metadata, 'counts': counts, 'runs': runs, 'plans': plans,
            'intents': intents, 'actions': actions, 'permits': permits, 'resolutions': resolutions},
        'target': {'path': target.relative_to(ROOT).as_posix(), 'raw_sha256': target_sha, 'quick_check': target_check,
            'descriptor': target_descriptor, 'effects': effects, 'effect_count': len(effects), 'observation_count': target_observations},
        'current_bundle': {'path': current_path.relative_to(ROOT).as_posix(), 'sha256': sha(current_path.read_bytes()),
            'artifact_kind_counts': kind_counts, 'stage_counts': {stage: sum(a['kind'] == 'CheckReport' and a['payload']['stage'] == stage for a in artifacts) for stage in ('PRE_APPLY', 'TARGET', 'POST_APPLY')},
            'progress': progress, 'terminal_heads': heads},
        'actual_PRE': {'ref': json.loads(runs[0]['pre_ref']), 'coverage_type': type(pre['payload']['coverage']).__name__,
            'decision': pre['payload']['decision'], 'run_status': runs[0]['status'], 'run_resource': run_ref, 'computed_checks': run['checks']},
        'late_material_fact': {'path': fact_path.relative_to(ROOT).as_posix(), 'raw_sha256': sha(fact_raw), 'data': fact},
        'candidate_receipts_in_noncurrent_files': candidates, 'creation_anchors': anchor_checks,
        'event_names': [event['event'] for event in events], 'bytes_unchanged_after_read': True})
    # Compare protected raw Git entries, not checkout newline-converted copies.
    def tree(ref):
        raw = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'ls-tree', '-r', ref], cwd=ROOT)
        return {line.split('\t', 1)[1]: line.split('\t', 1)[0].split() for line in raw.decode().splitlines()}
    base, current = tree(BASE), tree('HEAD')
    bad = [path for path, row in base.items() if path not in ALLOWED and current.get(path) != row]
    if bad:
        raise RuntimeError('protected old blob changed: ' + repr(bad))
    changes = subprocess.check_output(['git', '-c', 'core.longpaths=true', 'diff', '--name-only', BASE], cwd=ROOT).decode().splitlines()
    if any(path in base and path not in ALLOWED for path in changes):
        raise RuntimeError('out-of-scope existing worktree path')
    write('preservation.json', {'base': BASE, 'base_entries': len(base), 'protected_entries': len(base) - len(ALLOWED),
        'protected_mode_type_blob_unchanged': True, 'protected_tuple_sha256': sha(json.dumps(sorted((p, v) for p, v in base.items() if p not in ALLOWED), ensure_ascii=False, separators=(',', ':')).encode()),
        'allowed_old_changes': sorted(path for path in changes if path in base), 'old_R7_R8_evidence_untouched': True})
    write('bounded-outcome.json', {'status': 'REVIEW_N1_BLOCKED', 'authorized_product_corrections': 1,
        'minimal': 'PASS_OBJECT_SHAPE_AND_COMPLETE_PASS_INCOMPLETE_HOLD',
        'N1': 'FAILED_LATE_RECEIPT_PROGRESS_PROJECTION', 'N2_N7': 'NOT_RUN_AFTER_NEW_INDEPENDENT_PRODUCT_BLOCKER',
        'first_new_failure': {'code': 'RECOVERY_CHAIN_INVALID', 'path': 'runtime.storage._project_plan_locked -> contracts.recovery._receipts_progress',
            'detail': 'late recovery fact retains MAY_HAVE_BEEN_ATTEMPTED; projected APPLIED action progress changes attempt_fact to ATTEMPTED',
            'scope_required_for_a_future_change': 'src/annotation/runtime/storage/__init__.py and/or src/annotation/runtime/storage/native.py; not authorized by this R1 task',
            'actual_trace': 'runs/N1/stderr.txt'},
        'actual_boundaries': {'PRE_sealed': True, 'PRE_durably_admitted': runs[0]['status'] == 'ADMITTED',
            'TARGET_count': sum(a['kind'] == 'CheckReport' and a['payload']['stage'] == 'TARGET' for a in artifacts),
            'plan_count': counts['plans'], 'permit_count': counts['permits'], 'target_effect_count': len(effects),
            'child_exit': json.loads((OUT / 'validation/native-r1-01/processes/n1-child/completed.json').read_bytes()),
            'original_UNKNOWN_retained': any(item['effective_outcome'] == 'UNKNOWN' for p in progress for item in p['actions']),
            'terminal_original_receipt_ref': heads[0]['payload']['original_receipt_ref'],
            'terminal_resolution': heads[0]['payload']['resolution'],
            'late_material_fact': fact['origin_phase'], 'current_registered_receipts': kind_counts.get('ExecutionReceipt', 0),
            'intent_receipt': intents[0]['receipt'], 'POST_Batch': 'NOT_REACHED'},
        'C01': '70_PASS_FINAL_CANDIDATE', 'A02': '52_PASS_FINAL_CANDIDATE', 'R7': '13_PASS_FINAL_CANDIDATE',
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION', 'I01': 'NOT_RELEASED'})
    print(json.dumps({'PRE': runs[0]['status'], 'effect_count': len(effects), 'resolution': heads[0]['payload']['resolution'],
        'current_receipt_count': kind_counts.get('ExecutionReceipt', 0), 'fact_attempt': fact['result']['attempt_fact'],
        'candidate_receipt_files': len(candidates), 'frozen': 'RECOVERY_CHAIN_INVALID'}))


if __name__ == '__main__':
    main()
