"""Frozen SQL/resource/process cross-readback; no product imports or calls."""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R11-crash-cuts'
RUN = OUT / 'validation/r11-01'
POINTS = {'F1': 'BEFORE_INTENT_COMMIT', 'F2': 'AFTER_DISPATCH_STARTED', 'F3': 'AFTER_READBACK_CAPTURE', 'F4': 'AFTER_RECEIPT_COMMIT'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def database(path):
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in tables}
        quick = db.execute('PRAGMA quick_check').fetchone()[0]
    assert raw == path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'bytes': len(raw), 'quick_check': quick,
        'counts': {k: len(v) for k, v in rows.items()}, 'tables': rows, 'bytes_unchanged_after_read': True}


def ref(a):
    return {k: a[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


if __name__ == '__main__':
    result = {'mode': 'stdlib only; mode=ro&immutable=1; query_only', 'cases': {}}
    for group, point in POINTS.items():
        case = RUN / 'cases' / group
        marker = load(case / 'crash.marker.json')
        started = load(RUN / 'processes' / (group + '-crash') / 'started.json')
        completed = load(RUN / 'processes' / (group + '-crash') / 'completed.json')
        query_start = load(RUN / 'processes' / (group + '-query') / 'started.json')
        query_end = load(RUN / 'processes' / (group + '-query') / 'completed.json')
        assert marker['point'] == point and marker['pid'] == started['pid'] == completed['pid']
        assert completed['exit_code'] == 90 and not completed['alive'] and not completed['timed_out']
        assert query_start['pid'] != completed['pid'] and query_start['started_at_ns'] >= completed['ended_at_ns']
        assert query_end['exit_code'] == 0 and not query_end['alive']
        runtime, target = database(case / 'runtime/runtime.sqlite3'), database(case / 'target/target.sqlite3')
        reg = runtime['tables']['registrations'][0]
        bundle_path = Path(reg['bundle_path'])
        bundle_raw = bundle_path.read_bytes()
        bundle = json.loads(bundle_raw)
        registered = [json.loads(r['ref']) for r in runtime['tables']['artifacts']]
        assert all(ref(a) in registered for a in bundle['artifacts'])
        resources = []
        for row in runtime['tables']['actions']:
            if row['fact']:
                resource = json.loads(row['fact'])
                raw = (Path(reg['package_root']) / resource['path']).read_bytes()
                assert sha(raw) == resource['sha256']
                resources.append({'resource': resource, 'body': json.loads(raw)})
        after_exit = load(RUN / (group + '-after-exit90-before-reopen.json'))
        case_result = load(case / 'result.json')
        if group in ('F1', 'F4'):
            assert runtime['sha256'] == after_exit['runtime']['raw_sha256_after']
            assert target['sha256'] == after_exit['target']['raw_sha256_after']
            assert runtime['counts']['calls'] == runtime['counts']['attempts'] == runtime['counts']['resolutions'] == 0
        else:
            assert runtime['counts']['calls'] == runtime['counts']['attempts'] == runtime['counts']['resolutions'] == 1
            assert case_result['attempt_fact_before'] == case_result['attempt_fact_after']
        assert target['counts']['effects'] == (0 if group in ('F1', 'F2') else 1)
        result['cases'][group] = {'point': point, 'marker': marker, 'crash_started': started, 'crash_completed': completed,
            'new_process_started_after_crash_wait': query_start, 'query_completed': query_end,
            'before_run_runtime_copy': database(case / 'before-run-runtime.sqlite3'),
            'before_run_target_copy': database(case / 'before-run-target.sqlite3'),
            'pre_run_copy_limit': 'Sequential raw copies while own keeper existed, not a cross-database atomic backup.',
            'after_exit_before_reopen': after_exit, 'final_runtime': runtime, 'final_target': target,
            'current_bundle': bundle, 'current_bundle_path': bundle_path.relative_to(ROOT).as_posix(),
            'current_bundle_sha256': sha(bundle_raw), 'facts': resources, 'actual_result': case_result,
            'fault_before_actual_imports': load(case / 'before-run.json')['imports'],
            'crash_exit_import_file_present': (RUN / 'imports' / (group + '-crash.json')).is_file(),
            'query_actual_imports': load(RUN / 'imports' / (group + '-query.json'))}
    with (OUT / 'database-and-boundary-readback.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'four_actual_exit90': True, 'each_new_query_after_crash_wait': True,
        'F1_F4_reconcile_calls': 0, 'F2_F3_each_reconcile_calls': 1, 'effect_counts': [0, 0, 1, 1],
        'product_calls': 0}))
