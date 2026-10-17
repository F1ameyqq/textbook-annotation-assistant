"""R4 remaining controls; accepted N1 imported normally, no product patches."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import traceback
import unittest

import test_a03_r8_r3_post_hold as accepted

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R4-remaining'
EVIDENCE = OUT / 'validation/r4-native-01'
accepted.EVIDENCE = EVIDENCE
accepted.BASE_EVIDENCE = OUT


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    path = EVIDENCE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def exception_record(error):
    return {'type': type(error).__name__, 'code': getattr(error, 'code', None),
        'issues': getattr(error, 'issues', None), 'message': str(error), 'traceback': traceback.format_exc()}


def database(path):
    if not path.is_file():
        return {'status': 'NOT_CREATED'}
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            if name in tables else 'TABLE_NOT_CREATED' for name in ('plans', 'intents', 'permits', 'effects')}
        meta = {r['key']: r['value'] for r in db.execute('SELECT * FROM meta')} if 'meta' in tables else None
    assert path.read_bytes() == raw
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'counts': counts, 'meta': meta}


def modules():
    result = {}
    for name, module in list(sys.modules.items()):
        if name.startswith('annotation') or name in ('test_a03_r8_r3_post_hold', '__main__'):
            path = getattr(module, '__file__', None)
            if path and Path(path).is_file():
                result[name] = {'path': str(Path(path).resolve()), 'sha256': sha(Path(path).read_bytes())}
    return {'executable': sys.executable, 'modules': result}


class R4RemainingTests(unittest.TestCase):
    def test_N1(self):
        # The complete accepted method and its original child execute unchanged.
        # Only its two explicit output/input-index roots are routed above.
        accepted.R8R3NativeBridgeTests('test_N1').test_N1()

    def test_N6(self):
        from annotation.contracts import artifact_ref
        from annotation.delivery.planner import create_plan, verify_generated_plan
        from annotation.runtime.recovery import configuration
        from annotation.runtime.storage.common import canonical, plain
        store = accepted.open_case(EVIDENCE / 'cases/N1')
        reg = store.registration()
        runtime_path = store.database
        target_path = Path(reg['target_dir']) / 'target.sqlite3'
        before = {'runtime': database(runtime_path), 'target': database(target_path)}
        current = store.bundle(reg['id'])
        write('N6/full-current-history.json', canonical(current))
        bundle = store._validate(current, asset_root=reg['package_root'])
        plan = next(a for a in bundle.artifacts if a.kind == 'ApplyPlan')
        with store.connect() as db:
            anchor = dict(db.execute('SELECT * FROM native_creation_anchors WHERE plan_artifact_id=?', (plan.artifact_id,)).fetchone())
            artifacts = [dict(r) for r in db.execute('SELECT * FROM artifacts')]
            intents = [dict(r) for r in db.execute('SELECT * FROM intents')]
        anchor_raw = Path(anchor['input_path']).read_bytes()
        self.assertEqual(sha(anchor_raw), anchor['input_sha'])
        self.assertEqual(canonical(json.loads(anchor_raw)), anchor_raw)
        write('N6/creation-input-canonical.json', anchor_raw)
        write('N6/creation-anchor-SQL.json', {'anchor': anchor, 'artifacts': artifacts, 'intents': intents})
        captured = []
        consumed = []

        def capture(frame, event, returned):
            # Observe the single normal verification's real return, without
            # changing arguments/results or making a second product call.
            if event == 'return' and frame.f_code is create_plan.__code__ and returned is not None:
                captured.append(plain(returned.artifacts[-1]))
            if event == 'return' and frame.f_code is store.resource_manifest.__code__ and returned is not None:
                consumed.append(copy.deepcopy(returned))

        self.assertIsNone(sys.getprofile())
        sys.setprofile(capture)
        try:
            verify_generated_plan(bundle, plan, plan.payload.snapshot, configuration(json.loads(reg['config'])),
                bridge_context=bundle.bridge_context)
        finally:
            sys.setprofile(None)
            write('N6/actual-recompute-returns.json', {'generated_plans': captured, 'resource_manifests': consumed})
        self.assertEqual(len(captured), 1)
        original_plan = plain(plan)
        self.assertEqual(captured[0], original_plan)
        write('N6/original-plan-canonical.json', canonical(original_plan))
        write('N6/recomputed-plan-canonical.json', canonical(captured[0]))
        self.assertIn(json.loads(anchor['manifest']), consumed)
        resources = []
        for item in json.loads(anchor['manifest']):
            path = Path(reg['package_root']) / item['path']
            raw = path.read_bytes()
            self.assertEqual(sha(raw), item['sha256'])
            resources.append({'resource': item, 'bytes': len(raw), 'actual_sha256': sha(raw)})
        write('N6/consumed-resource-readback.json', resources)
        unknowns = [a for a in current['artifacts'] if a['kind'] == 'ExecutionProgress'
            and any(r['effective_outcome'] == 'UNKNOWN' for r in a['payload']['actions'])]
        self.assertTrue(unknowns)
        kinds = [a['kind'] for a in current['artifacts']]
        for kind in ('ExecutionReceipt', 'ReconciliationResult', 'BatchReport'):
            self.assertIn(kind, kinds)
        # A named PRE check directly consumes this formal EvidenceRecord.
        # Remove only that record in a new in-memory copy of the creation input.
        missing = json.loads(anchor_raw)
        pre = next(a for a in missing['artifacts'] if artifact_ref(a) == plain(plan.payload.precheck))
        check = pre['payload']['checks'][0]
        evidence_id = check['evidence_refs'][0]
        record = next(r for r in missing['evidence'] if r['evidence_id'] == evidence_id)
        consumer = {'artifact_ref': artifact_ref(pre), 'path': '$.artifacts/PRE.payload.checks[0].evidence_refs[0]',
            'check_id': check['check_id'], 'evidence_id': evidence_id, 'record': copy.deepcopy(record)}
        missing['evidence'] = [r for r in missing['evidence'] if r['evidence_id'] != evidence_id]
        write('N6/missing-dependency-input.json', missing)
        write('N6/missing-dependency-consumer.json', consumer)
        try:
            store.native_registry.context(missing, reg['package_root'], historical=True)
        except Exception as error:
            refusal = exception_record(error)
            write('N6/missing-dependency-refusal.json', refusal)
            print(json.dumps(refusal, ensure_ascii=False), flush=True)
            codes = [i.get('code') for i in (refusal['issues'] or [])] + [refusal['code']]
            self.assertIn('EVIDENCE_ID_MISSING', codes)
            self.assertIn(evidence_id, refusal['message'])
        else:
            self.fail('formally referenced missing PRE EvidenceRecord unexpectedly allowed')
        self.assertEqual(Path(anchor['input_path']).read_bytes(), anchor_raw)
        after = {'runtime': database(runtime_path), 'target': database(target_path)}
        self.assertEqual(before, after)
        write('N6-result.json', {'status': 'REVIEW', 'same_plan_four_tuple': artifact_ref(plan),
            'original_and_recomputed_plan_canonical_sha256': sha(canonical(original_plan)),
            'creation_anchor_canonical_sha256': sha(anchor_raw), 'full_history_artifact_count': len(current['artifacts']),
            'full_UNKNOWN_count': len(unknowns), 'all_formal_history_retained': True,
            'missing_dependency': consumer, 'actual_refusal': refusal, 'database_before': before, 'database_after': after,
            'permit_and_effect_added': 0, 'clock_SQL_filter_reseal_downgrade': False})

    def test_N7_initialization(self):
        from annotation.runtime.storage.native import init_native_state, open_native_state
        path = EVIDENCE / 'cases/N7-before-completion'
        path.mkdir(parents=True, exist_ok=False)
        anchor, runtime = path / 'anchor.json', path / 'runtime'
        class ControlledStop(RuntimeError):
            pass
        injected = ControlledStop('R4 controlled same-process interruption before native formal completion')
        calls = []
        def stop():
            calls.append('before_completion')
            raise injected
        try:
            init_native_state(anchor, runtime, expected_ledger_id='ledger-r4-incomplete',
                expected_target_store_id='target-r4-incomplete', before_completion=stop)
        except ControlledStop as error:
            self.assertIs(error, injected)
            write('N7/original-controlled-interruption.json', exception_record(error))
        else:
            self.fail('before_completion interruption did not propagate')
        self.assertEqual(calls, ['before_completion'])
        self.assertFalse(anchor.exists())
        before = database(runtime / 'runtime.sqlite3')
        self.assertNotEqual((before.get('meta') or {}).get('initialization'), 'COMPLETE')
        try:
            open_native_state(anchor, expected_ledger_id='ledger-r4-incomplete', expected_target_store_id='target-r4-incomplete')
        except Exception as error:
            refusal = exception_record(error)
            write('N7/normal-open-refusal.json', refusal)
            print(json.dumps(refusal, ensure_ascii=False), flush=True)
            self.assertEqual(refusal['code'], 'STATE_DIRECTORY_IDENTITY_MISMATCH')
            self.assertIn('anchor.json', refusal['message'])
        else:
            self.fail('incomplete initialization unexpectedly opened')
        after = database(runtime / 'runtime.sqlite3')
        self.assertEqual(before, after)
        for name in ('plans', 'intents', 'permits'):
            self.assertEqual(after['counts'][name], 0)
        self.assertFalse((path / 'target').exists())
        files = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
            for p in sorted(path.rglob('*')) if p.is_file()]
        write('N7-result.json', {'status': 'REVIEW', 'hook_calls': calls, 'same_process_controlled_exception': True,
            'real_process_crash_claim': False, 'anchor_exists': anchor.exists(), 'formal_completion': 'ABSENT',
            'database_before_open': before, 'database_after_open': after, 'normal_open_refusal': refusal,
            'retained_files': files, 'target_database': 'NOT_CREATED', 'target_effects': 'NOT_CREATED',
            'all_target_interruption_points_claim': False, 'old_failed_target_entry_or_variant_calls': 0,
            'migration': 'NOT_IMPLEMENTED_BLOCKED'})


if __name__ == '__main__':
    label = sys.argv[1]
    method = {'N1': 'test_N1', 'N6': 'test_N6', 'N7': 'test_N7_initialization'}[label]
    try:
        result = unittest.TextTestRunner(verbosity=2, failfast=True).run(unittest.TestSuite([R4RemainingTests(method)]))
    finally:
        write('imports/' + label + '.json', modules())
    raise SystemExit(0 if result.wasSuccessful() else 1)
