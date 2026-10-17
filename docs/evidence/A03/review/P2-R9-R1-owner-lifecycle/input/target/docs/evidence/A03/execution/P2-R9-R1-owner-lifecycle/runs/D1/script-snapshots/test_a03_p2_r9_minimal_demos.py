"""Two bounded, fresh, singleton process demos using unchanged native APIs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest

import test_a03_r8_r3_post_hold as helper

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
INPUTS = ROOT / 'docs/evidence/A03/execution/P2-R9-minimal-demos/inputs.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def imports():
    values = {}
    for name, module in list(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if path and Path(path).is_file() and (name.startswith('annotation') or name == 'test_a03_r8_r3_post_hold' or name == '__main__'):
            values[name] = {'path': str(Path(path).resolve()), 'sha256': sha(Path(path).read_bytes())}
    return {'pid': os.getpid(), 'executable': sys.executable, 'modules': values}


def frozen_database(path):
    if not path.is_file():
        return {'status': 'NOT_CREATED'}
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}
    assert raw == path.read_bytes(), 'frozen read changed concurrently'
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'bytes': len(raw),
        'counts': {k: len(v) for k, v in rows.items()}, 'tables': rows, 'bytes_unchanged_after_read': True}


def snapshot(case):
    return {'runtime': frozen_database(case / 'runtime/runtime.sqlite3'), 'target': frozen_database(case / 'target/target.sqlite3')}


def effect_count(case):
    path = case / 'target/target.sqlite3'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        return db.execute('SELECT count(*) FROM effects').fetchone()[0]


def execute(case, label):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    from annotation.runtime.storage.common import now, plain
    from annotation.runtime.recovery import run_plan
    store, observer, claim, keeper, bundle, pre_ref, actual, admitted, config = helper.setup_pre(case)
    try:
        reg = store.registration()
        graph = next(a for a in bundle.artifacts if a.kind == 'QuestionGraph')
        bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='target-r9-' + label, created_at=now(), bridge_context=bundle.bridge_context)
        target_ref = artifact_ref(bundle.artifacts[-1])
        bundle = create_plan(bundle, artifact_ref(graph), pre_ref, target_ref, actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='plan-r9-' + label, created_at=now(), bridge_context=bundle.bridge_context)
        plan = bundle.artifacts[-1]
        assert len(plan.payload.actions) == 1 and plan.payload.actions[0].operation == 'CREATE_FRAMES'
        store.record_native_plan(reg['id'], bundle, artifact_ref(plan), config, owner_id=claim.owner_id, generation=claim.generation)
        write(case / 'before-run.json', {'registration_id': reg['id'], 'plan_ref': artifact_ref(plan),
            'plan': plain(plan), 'pre_ref': pre_ref, 'snapshot_ref': actual.snapshot_ref,
            'native_run_id': admitted.run_id, 'owner': plain(claim), 'effect_count': effect_count(case),
            'configuration': vars(config), 'imports': imports()})
        write(case / 'before-run-runtime.sqlite3', store.database.read_bytes())
        write(case / 'before-run-target.sqlite3', (case / 'target/target.sqlite3').read_bytes())
        fault = None if label == 'D1' else {'point': 'AFTER_INTENT_COMMIT', 'exit_code': 90, 'marker': str(case / 'after-intent-commit.marker.json')}
        result = run_plan(store, reg['id'], owner_id=claim.owner_id, generation=claim.generation, config=vars(config), fault=fault)
        if label == 'D2':
            raise AssertionError('D2 must actually exit90 at the existing fault point')
        write(case / 'normal-run-result.json', plain(result))
        assert result['status'] == 'FINISHED'
        assert result['quality']['content_check_status'] == 'PENDING'
        assert result['quality']['submission_status'] == 'NOT_SUBMITTED'
        assert effect_count(case) == 1
    finally:
        keeper.stop()


def restart(case, label):
    from annotation.runtime.recovery import open_observer, reconcile, run_plan
    from annotation.runtime.recovery.observation import observe_bounded
    from annotation.runtime.storage.common import plain, reference
    store = helper.open_case(case)
    reg = store.registration()
    write(case / 'restarted-status-before.json', store.status(reg['id']))
    projection = store.project_plan(reg['id'])
    write(case / 'restarted-projection-before.json', plain(projection))
    write(case / 'restarted-bundle-before.json', store.bundle(reg['id']))
    count = effect_count(case)
    if label == 'D2':
        assert count == 0
        assert store.status(reg['id'])['pending_count'] == 1
        assert projection['receipt_ref'] is None
        assert projection['actions'][0]['effective_outcome'] == 'UNKNOWN'
        result = reconcile(store, reg['id'], call_id='call-r9-D2', max_attempts=1)
        write(case / 'reconcile-once.json', plain(result))
        assert result['attempt_count'] == 1
        assert result['resolutions'][0]['status'] == 'RESOLVED_NOT_APPLIED'
        assert result['resolutions'][0]['classification'] == 'ABSENT'
        projection = store.project_plan(reg['id'])
        write(case / 'restarted-projection-after.json', plain(projection))
        assert effect_count(case) == count
    else:
        assert count == 1
        observer = open_observer(store, reg['id'])
        observed = observe_bounded(observer, timeout=2)
        write(case / 'independent-restart-observation.json', plain(observed))
        assert observed['ok']
        assert effect_count(case) == 1
        current = store.bundle(reg['id'])
        assert any(a['kind'] == 'BatchReport' for a in current['artifacts'])
    before_replay = snapshot(case)
    write(case / 'before-duplicate-query.json', before_replay)
    try:
        replay = run_plan(store, reg['id'])
    except Exception as error:
        write(case / 'duplicate-result.json', {'type': type(error).__name__, 'code': getattr(error, 'code', None),
            'issues': getattr(error, 'issues', None), 'message': str(error), 'business_outcome': 'REFUSED'})
    else:
        write(case / 'duplicate-result.json', {'business_outcome': 'RETURNED', 'result': plain(replay)})
    after_replay = snapshot(case)
    write(case / 'after-duplicate-query.json', after_replay)
    assert effect_count(case) == count
    assert after_replay['runtime']['counts']['intents'] == before_replay['runtime']['counts']['intents']
    assert after_replay['runtime']['counts']['permits'] == before_replay['runtime']['counts']['permits']
    current = store.bundle(reg['id'])
    write(case / 'restarted-bundle-final.json', current)
    write(case / 'demo-result.json', {'status': 'REVIEW', 'case': label, 'effect_count': count,
        'duplicate_effect_delta': 0, 'formal_refs': [reference(a) for a in current['artifacts']],
        'projection': plain(projection), 'attempt_fact_preserved_as_recorded': True,
        'multi_action_or_new_plan_claim': False})


def run_child(root, label, phase, expected):
    folder = root / 'processes' / (label + '-' + phase)
    folder.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, '-X', 'utf8', '-B', str(SCRIPT), label, '--child-mode', phase,
        '--output-root', root.relative_to(ROOT).as_posix()]
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 45,
        'script_sha256': sha(SCRIPT.read_bytes()), 'input_index_sha256': sha(INPUTS.read_bytes()),
        'helper_sha256': sha(Path(helper.__file__).read_bytes()), 'expected_exit': expected})
    write(folder / 'script-snapshot.py', SCRIPT.read_bytes())
    with (folder / 'stdout.txt').open('xb') as stdout, (folder / 'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr)
        write(folder / 'started.json', {'pid': process.pid, 'parent_pid': os.getpid(), 'started_at_ns': time.time_ns()})
        timed_out = False
        try:
            code = process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=5)
    write(folder / 'completed.json', {'pid': process.pid, 'exit_code': code, 'timed_out': timed_out,
        'alive': process.poll() is None, 'ended_at_ns': time.time_ns(), 'stdout_sha256': sha((folder / 'stdout.txt').read_bytes()),
        'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())})
    assert code == expected and not timed_out, 'first child failure: ' + str(folder / 'stderr.txt')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=('D1', 'D2'))
    parser.add_argument('--child-mode', choices=('execute', 'restart'))
    parser.add_argument('--output-root', default='docs/evidence/A03/execution/P2-R9-minimal-demos/validation/r9-01')
    args = parser.parse_args()
    root = (ROOT / args.output_root).resolve()
    assert root.is_relative_to(ROOT / 'docs/evidence/A03/execution/P2-R9-minimal-demos')
    case = root / 'cases' / args.case
    if args.child_mode:
        try:
            (execute if args.child_mode == 'execute' else restart)(case, args.case)
        finally:
            write(root / 'imports' / (args.case + '-' + args.child_mode + '.json'), imports())
    else:
        # A failed execute never starts a restart or the dependent second demo.
        try:
            run_child(root, args.case, 'execute', 0 if args.case == 'D1' else 90)
            write(root / (args.case + '-after-execute-SQL.json'), snapshot(case))
            run_child(root, args.case, 'restart', 0)
            write(root / (args.case + '-after-restart-SQL.json'), snapshot(case))
        except BaseException:
            # File/SQL-only frozen record, no product import or recovery call.
            write(root / (args.case + '-first-failure-SQL.json'), snapshot(case))
            raise
