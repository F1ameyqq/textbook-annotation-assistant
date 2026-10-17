"""One frozen round: normal demo, standalone report, borrowed lease, ABSENT."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import traceback

import test_a03_p2_r9_minimal_demos as original

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
OUT = ROOT / 'docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle'
write, sha = original.write, original.sha


def imports():
    result = original.imports()
    result['modules']['test_a03_p2_r9_minimal_demos'] = {
        'path': original.__file__, 'sha256': sha(Path(original.__file__).read_bytes())}
    return result


def target_read_counts(case):
    path = case / 'target/target.sqlite3'
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('effects', 'observations')}
    assert path.read_bytes() == raw
    return {'sha256': sha(raw), 'counts': counts}


def state(store, case):
    reg = store.registration()
    with store.connect() as db:
        book = dict(db.execute('SELECT * FROM books').fetchone())
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('plans', 'intents', 'permits', 'artifacts', 'native_report_reads')}
        events = [json.loads(r[0])['event'] for r in db.execute('SELECT body FROM events ORDER BY sequence')]
    bundle = store.bundle(reg['id'])
    return {'book': book, 'counts': counts, 'events': events,
        'effect_count': original.effect_count(case), 'bundle': bundle, 'target': target_read_counts(case),
        'report_artifact_counts': {'POST': sum(a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY' for a in bundle['artifacts']),
            'Batch': sum(a['kind'] == 'BatchReport' for a in bundle['artifacts'])}}


def receipt_without_report(case):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    from annotation.delivery.mock import compare_action
    from annotation.runtime.storage.common import now, reference, plain, unique
    store, observer, claim, keeper, bundle, pre_ref, actual, admitted, config = original.helper.setup_pre(case)
    try:
        reg = store.registration()
        graph = next(a for a in bundle.artifacts if a.kind == 'QuestionGraph')
        bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='target-owner-r1-' + case.name,
            created_at=now(), bridge_context=bundle.bridge_context)
        target_ref = artifact_ref(bundle.artifacts[-1])
        bundle = create_plan(bundle, artifact_ref(graph), pre_ref, target_ref, actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='plan-owner-r1-' + case.name,
            created_at=now(), bridge_context=bundle.bridge_context)
        plan = plain(bundle.artifacts[-1])
        assert len(plan['payload']['actions']) == 1
        store.record_native_plan(reg['id'], bundle, reference(plan), config, owner_id=claim.owner_id, generation=claim.generation)
        store.accept_plan(reg['id'], reference(plan), owner_id=claim.owner_id, generation=claim.generation)
        context = store.load_book_context(store.target_key(reg['id']), owner_id=claim.owner_id, generation=claim.generation)
        observer.import_book_context(context, authority=store)
        bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
        action = plan['payload']['actions'][0]
        prepared = observer.prepare_action(bundle, reference(plan), action['action_id'], config,
            current_snapshot_ref=plan['payload']['snapshot'], asset_root=reg['package_root'], bridge_context=bundle.bridge_context)
        intent = store.commit_intent(prepared, owner_id=claim.owner_id, generation=claim.generation)
        permit = store.issue_first_dispatch(intent['intent_ref'], owner_id=claim.owner_id, generation=claim.generation,
            plan_ref=reference(plan), action_id=action['action_id'], observation_binding=prepared['observation_binding'])
        observer.dispatch_action(prepared, committed_intent=intent, dispatch_permit=permit, authority=store)
        observed = observer.observe_target(store.target_key(reg['id']), observation_id=unique('owner-r1-readback'))
        comparison = compare_action(prepared['action'], prepared['observation'], observed)
        result = store.commit_action_result(intent, prepared, observed, comparison, owner_id=claim.owner_id, generation=claim.generation)
        assert result['result']['outcome'] == 'APPLIED'
        projection = store.project_plan(reg['id'])
        assert projection['receipt_ref'] is not None
        before = state(store, case)
        assert before['counts']['native_report_reads'] == 0 and before['effect_count'] == 1
        write(case / 'complete-receipt-before-report.json', {'state': before, 'projection': projection,
            'supported_path': 'accept/prepare/commit_intent/first_permit/dispatch/observe/commit_result/project',
            'direct_SQL_business_mutations': 0})
        return store, claim, keeper, projection
    except BaseException:
        keeper.stop()
        raise


def cleanup(store, claim, keeper):
    keeper.stop()
    reg = store.registration()
    with store.connect() as db:
        row = db.execute('SELECT owner,generation,phase FROM books').fetchone()
    if row['owner'] == claim.owner_id and row['generation'] == claim.generation and row['phase'] == 'ACTIVE':
        store.release(store.target_key(reg['id']), owner_id=claim.owner_id, generation=claim.generation)


def report(case, borrowed):
    from annotation.runtime.recovery import publish_quality
    from annotation.runtime.storage.common import plain, RuntimeFailure
    store, claim, keeper, projection = receipt_without_report(case)
    reg = store.registration()
    try:
        if not borrowed:
            keeper.stop()
            store.release(store.target_key(reg['id']), owner_id=claim.owner_id, generation=claim.generation)
            before = state(store, case)
            quality = publish_quality(store, reg['id'], projection)
            after = state(store, case)
            assert after['book']['generation'] == before['book']['generation'] + 1
            assert after['book']['owner'] is None and after['book']['phase'] == 'RELEASED'
            for event in ('OWNER_CLAIM_RESERVED', 'OWNER_ACTIVE', 'OWNER_RELEASED'):
                assert after['events'].count(event) == before['events'].count(event) + 1
            write(case / 'standalone-owner-proof.json', {'before': before, 'after': after, 'quality': plain(quality)})
        else:
            before = state(store, case)
            controls = []
            for name, kwargs in (
                ('owner_only', {'owner_id': claim.owner_id}),
                ('generation_only', {'generation': claim.generation}),
                ('stale_generation', {'owner_id': claim.owner_id, 'generation': claim.generation + 1}),
                ('foreign_owner', {'owner_id': 'foreign-owner-r1', 'generation': claim.generation})):
                start = state(store, case)
                try:
                    publish_quality(store, reg['id'], projection, **kwargs)
                except RuntimeFailure as error:
                    record = {'control': name, 'type': type(error).__name__, 'code': getattr(error, 'code', None), 'message': str(error)}
                    controls.append(record)
                    print(json.dumps(record), flush=True)
                    assert record['code'] == 'OWNER_GENERATION_STALE'
                else:
                    raise AssertionError('invalid borrowed ownership unexpectedly allowed: ' + name)
                end = state(store, case)
                assert start['counts'] == end['counts'] and start['events'] == end['events']
                assert start['target'] == end['target'] and start['bundle'] == end['bundle']
                assert (end['book']['owner'], end['book']['generation'], end['book']['phase']) == (claim.owner_id, claim.generation, 'ACTIVE')
                assert keeper.thread.is_alive()
                write(case / ('control-' + name + '.json'), {'record': record, 'before': start, 'after': end})
            quality = publish_quality(store, reg['id'], projection, owner_id=claim.owner_id, generation=claim.generation)
            after = state(store, case)
            assert (after['book']['owner'], after['book']['generation'], after['book']['phase']) == (claim.owner_id, claim.generation, 'ACTIVE')
            assert before['events'] == after['events'] and keeper.thread.is_alive()
            keeper.check()
            assert after['counts']['native_report_reads'] == 1 and after['report_artifact_counts'] == {'POST': 1, 'Batch': 1}
            write(case / 'borrowed-owner-proof.json', {'before': before, 'after': after, 'controls': controls,
                'quality': plain(quality), 'outer_keeper_alive': True, 'saved_before_read_limit_control': True})
            # Existing durable single-read fence must fail before another read.
            try:
                publish_quality(store, reg['id'], projection, owner_id=claim.owner_id, generation=claim.generation)
            except RuntimeFailure as error:
                assert error.code == 'STORAGE_TRANSACTION_FAILED'
                assert str(error) == 'UNIQUE constraint failed: native_report_reads.plan_id'
                assert isinstance(error.__context__, sqlite3.IntegrityError)
                assert str(error.__context__) == 'UNIQUE constraint failed: native_report_reads.plan_id'
                limit = {'type': type(error).__name__, 'code': error.code, 'message': str(error),
                    'context_type': type(error.__context__).__name__, 'context_message': str(error.__context__),
                    'traceback': traceback.format_exc()}
                print(json.dumps(limit), flush=True)
            else:
                raise AssertionError('durable report read reused')
            limited = state(store, case)
            assert limited['counts'] == after['counts'] and limited['events'] == after['events']
            assert limited['target'] == after['target'] and limited['bundle'] == after['bundle']
            assert limited['report_artifact_counts'] == after['report_artifact_counts'] == {'POST': 1, 'Batch': 1}
            keeper.check()
            assert (limited['book']['owner'], limited['book']['generation'], limited['book']['phase']) == (claim.owner_id, claim.generation, 'ACTIVE')
            assert keeper.thread.is_alive()
            write(case / 'single-read-refusal-proof.json', {'before': before, 'after': after, 'after_read_limit_refusal': limited,
                'controls': controls, 'read_limit_refusal': limit, 'quality': plain(quality), 'outer_keeper_alive': True})
        assert quality['content_check_status'] == 'PENDING' and quality['submission_status'] == 'NOT_SUBMITTED'
        assert after['counts']['native_report_reads'] == 1 and original.effect_count(case) == 1
    finally:
        cleanup(store, claim, keeper)


def child(case, group, phase):
    if group in ('D1', 'D2'):
        (original.execute if phase == 'execute' else original.restart)(case, group)
        if phase == 'restart' and group == 'D2':
            before = json.loads((case / 'restarted-projection-before.json').read_bytes())
            after = json.loads((case / 'restarted-projection-after.json').read_bytes())
            assert before['actions'][0]['attempt_fact'] == after['actions'][0]['attempt_fact']
            assert after['actions'][0]['attempt_fact'] != 'NOT_ATTEMPTED'
    else:
        report(case, group == 'borrow')


def run_child(root, group, phase, expected):
    folder = root / 'processes' / (group + '-' + phase)
    folder.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, '-X', 'utf8', '-B', str(SCRIPT), group, '--child-mode', phase,
        '--output-root', root.relative_to(ROOT).as_posix()]
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 45,
        'script_sha256': sha(SCRIPT.read_bytes()), 'inputs_sha256': sha((OUT / 'inputs.json').read_bytes()),
        'original_R9_driver_sha256': sha(Path(original.__file__).read_bytes()), 'expected_exit': expected})
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
    write(folder / 'completed.json', {'pid': process.pid, 'exit_code': code, 'timed_out': timed_out, 'alive': process.poll() is None,
        'ended_at_ns': time.time_ns(), 'stdout_sha256': sha((folder / 'stdout.txt').read_bytes()), 'stderr_sha256': sha((folder / 'stderr.txt').read_bytes())})
    assert code == expected and not timed_out, 'first child failure: ' + str(folder / 'stderr.txt')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('group', choices=('D1', 'standalone', 'borrow', 'D2'))
    parser.add_argument('--child-mode', choices=('execute', 'restart'))
    parser.add_argument('--output-root', default='docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle/validation/owner-r1-01')
    args = parser.parse_args()
    root = (ROOT / args.output_root).resolve()
    assert root.is_relative_to(OUT)
    case = root / 'cases' / args.group
    if args.child_mode:
        try:
            child(case, args.group, args.child_mode)
        finally:
            write(root / 'imports' / (args.group + '-' + args.child_mode + '.json'), imports())
    else:
        try:
            run_child(root, args.group, 'execute', 90 if args.group == 'D2' else 0)
            write(root / (args.group + '-after-execute-SQL.json'), original.snapshot(case))
            if args.group in ('D1', 'D2'):
                run_child(root, args.group, 'restart', 0)
                write(root / (args.group + '-after-restart-SQL.json'), original.snapshot(case))
            write(root / (args.group + '-result.json'), {'status': 'REVIEW', 'group': args.group,
                'effect_count': original.effect_count(case), 'case': case.relative_to(ROOT).as_posix()})
        except BaseException:
            write(root / (args.group + '-first-failure-SQL.json'), original.snapshot(case))
            raise
