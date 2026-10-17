"""Read-only post-stop evidence audit. Never imports or executes product code."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-native-bridge'
BASE = '8ad45dd07214ae406a3fab28d76a4b5abd6eef03'
ALLOWED_SHARED = {
    'pyproject.toml', 'src/annotation/contracts/__init__.py', 'src/annotation/contracts/validation.py',
    'src/annotation/contracts/recovery.py', 'src/annotation/quality/targetcheck/__init__.py',
    'src/annotation/delivery/planner/__init__.py', 'src/annotation/delivery/mock/persistent.py',
    'src/annotation/delivery/reconciler/__init__.py', 'src/annotation/runtime/recovery/__init__.py',
    'src/annotation/runtime/recovery/observation.py', 'src/annotation/runtime/storage/__init__.py',
    'src/annotation/runtime/storage/holds.py'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    path = OUT / name
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)


def snapshot_database(path):
    if not path.exists():
        return {'path': path.relative_to(ROOT).as_posix(), 'state': 'NOT_CREATED', 'effects': 0}
    before = sha(path.read_bytes())
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result = {'path': path.relative_to(ROOT).as_posix(), 'raw_sha256': before,
            'application_id': connection.execute('PRAGMA application_id').fetchone()[0],
            'user_version': connection.execute('PRAGMA user_version').fetchone()[0],
            'counts': {name: connection.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                for name in ('effects', 'observations', 'books', 'registrations', 'plans', 'intents', 'permits', 'native_pre_runs') if name in names}}
        if 'native_pre_runs' in names:
            result['runs'] = [dict(zip(('id', 'status', 'reads', 'pre_ref', 'run_sha'), row))
                for row in connection.execute('SELECT id,status,reads,pre_ref,run_sha FROM native_pre_runs')]
    if sha(path.read_bytes()) != before:
        raise RuntimeError('read-only audit changed database bytes')
    return result


def main():
    changes = git('diff', '--name-only', BASE).decode().splitlines()
    illegal = [path for path in changes if path not in ALLOWED_SHARED and not path.startswith('src/annotation/contracts/a03_native/')]
    if illegal:
        raise RuntimeError('out-of-scope existing path: ' + repr(illegal))
    old = json.loads((OUT / 'old-tree.json').read_bytes())
    tree = {}
    for line in git('ls-tree', '-r', 'HEAD').decode().splitlines():
        metadata, path = line.split('\t', 1)
        mode, kind, blob = metadata.split()
        tree[path] = (mode, kind, blob)
    preserved = []
    for row in old:
        if row['path'] in ALLOWED_SHARED:
            continue
        if tree.get(row['path']) != (row['mode'], row['type'], row['blob']):
            raise RuntimeError('old Git blob changed: ' + row['path'])
        preserved.append([row['path'], row['mode'], row['type'], row['blob']])
    write('preservation.json', {'base': BASE, 'old_entries': len(old), 'unchanged_old_entries': len(preserved),
        'aggregate_sha256': sha(json.dumps(preserved, ensure_ascii=False, separators=(',', ':')).encode()),
        'allowed_shared_changed': sorted(path for path in changes if path in ALLOWED_SHARED),
        'R7_product_data_unchanged': True, 'legacy_schema_tests_examples_evidence_unchanged': True})
    starts = []
    for path in OUT.rglob('started.json'):
        record = json.loads(path.read_bytes())
        end_path = path.with_name('completed.json')
        if not end_path.is_file():
            raise RuntimeError('owned process missing completion: ' + str(path))
        end = json.loads(end_path.read_bytes())
        if end.get('alive') is not False:
            raise RuntimeError('owned process not reaped')
        starts.append({'path': path.relative_to(OUT).as_posix(), 'pid': record['pid'],
            'exit_code': end['exit_code'], 'alive': end['alive'], 'timeout': end.get('timed_out', end.get('timeout', False))})
    write('process-release.json', {'recorded_at': datetime.now(timezone.utc).isoformat(), 'owned_processes': starts,
        'all_recorded_processes_completed': True, 'product_reruns_after_stop': 0, 'new_delegations': 0})
    databases = []
    for run in ('bounded-01', 'bounded-02'):
        case = OUT / 'validation' / run / 'cases/N1'
        databases.extend(snapshot_database(case / name) for name in ('runtime/runtime.sqlite3', 'target/target.sqlite3'))
    runs = []
    for path in (OUT / 'validation/bounded-02/cases/N1').rglob('assets/native-pre/*.json'):
        data = json.loads(path.read_bytes())
        if data.get('format_version') == 'a03-native-pre-run-1':
            runs.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path.read_bytes()),
                'checks': data['checks'], 'runtime_status': data['runtime_status'], 'admission': data['admission'],
                'input_raw_sha256': data['input_raw_sha256'], 'actual_observation': data['actual_observation']})
    write('bounded-outcome.json', {'status': 'REVIEW_BLOCKED', 'local_corrections': 1,
        'first_failure': {'code': 'HASH_MISMATCH', 'path': 'contracts.recovery._legacy_projection', 'fixed_once': True},
        'frozen_failure': {'code': 'SHAPE_oneOf', 'path': 'quality.synthetic_precheck.produce_a03_pre_run -> targetcheck.make_artifact -> native CheckReport.payload',
            'static_cause': 'coverage_for returns (coverage, complete); producer passes the pair into the object-valued coverage field without unpacking',
            'trace': 'runs/N1-local-fix/stderr.txt'},
        'N1': 'FAILED_BEFORE_PRE_SEAL_AND_ADMISSION', 'N2': 'NOT_RUN_AFTER_INDEPENDENT_BLOCKER',
        'N3': 'NOT_RUN_AFTER_INDEPENDENT_BLOCKER', 'N4': 'NOT_RUN_AFTER_INDEPENDENT_BLOCKER',
        'N5': 'NOT_RUN_AFTER_INDEPENDENT_BLOCKER', 'N6': 'NOT_RUN_AFTER_INDEPENDENT_BLOCKER',
        'N7': 'NOT_RUN_AFTER_INDEPENDENT_BLOCKER', 'computed_unadmitted_runs': runs, 'read_only_database_snapshots': databases,
        'target_effect_count': 0, 'no_TARGET_plan_intent_permit_or_recovery_success_claim': True,
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION', 'I01': 'NOT_RELEASED'})
    print(json.dumps({'processes_reaped': len(starts), 'databases': len(databases), 'computed_unadmitted_runs': len(runs), 'status': 'REVIEW_BLOCKED'}))


if __name__ == '__main__':
    main()
