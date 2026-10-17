"""Four existing crash cuts, each once in fresh dual stores and real processes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, 'D:\\1800\\docs\\evidence\\A03\\review\\P2-R11-crash-cuts\\isolation\\workspace\\tests')
import test_a03_p2_r10_owner_fencing as files

ROOT = Path('D:\\1800\\docs\\evidence\\A03\\review\\P2-R11-crash-cuts\\isolation\\workspace')
SCRIPT = Path(__file__).resolve()
OUT = ROOT / 'docs/evidence/A03/execution/P2-R11-crash-cuts'
POINTS = {'F1': 'BEFORE_INTENT_COMMIT', 'F2': 'AFTER_DISPATCH_STARTED',
    'F3': 'AFTER_READBACK_CAPTURE', 'F4': 'AFTER_RECEIPT_COMMIT'}
write, sha = files.write, files.sha


def capture_stage(case, stage, *, own_writer_keeper):
    """Retain actual sequential raw bytes, then SQL from retained immutable copies."""
    d = case / 'stages' / stage
    d.mkdir(parents=True, exist_ok=False)
    started = time.time_ns()
    result = {'stage': stage, 'pid': os.getpid(), 'started_at_ns': started,
        'own_writer_keeper_active': own_writer_keeper,
        'limit': 'Sequential raw files, not an atomic cross-database snapshot; no SQLite reconstruction.', 'databases': {}}
    for name in ('runtime', 'target'):
        source = case / name / (name + '.sqlite3')
        read_start = time.time_ns()
        body = source.read_bytes()
        read_end = time.time_ns()
        dest = d / (name + '.sqlite3')
        write(dest, body)
        sql = files.read_db(dest, True)
        assert sql['quick_check'] == 'ok' and sql['raw_sha256_before'] == sha(body) == sql['raw_sha256_after']
        sidecars = []
        for suffix in ('-journal', '-wal', '-shm'):
            p = Path(str(source) + suffix)
            if p.is_file():
                value = p.read_bytes()
                write(d / (name + '.sqlite3' + suffix + '.captured'), value)
                sidecars.append({'suffix': suffix, 'bytes': len(value), 'sha256': sha(value)})
        result['databases'][name] = {'source': str(source), 'copy': str(dest), 'bytes': len(body),
            'sha256': sha(body), 'read_started_at_ns': read_start, 'read_ended_at_ns': read_end,
            'source_sha256_after_copy': sha(source.read_bytes()), 'sidecars': sidecars, 'SQL': sql}
    result['ended_at_ns'] = time.time_ns()
    write(d / 'capture.json', result)
    return result


def imports():
    value = files.imports()
    value['modules']['test_a03_p2_r10_owner_fencing'] = {'path': files.__file__, 'sha256': sha(Path(files.__file__).read_bytes())}
    return value


def ref(artifact):
    return {k: artifact[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


def qualify(case):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    from annotation.runtime.storage.common import now, plain
    store, observer, claim, keeper, bundle, pre_ref, actual, admitted, config = files.helper.setup_pre(case)
    try:
        reg = store.registration()
        graph = next(a for a in bundle.artifacts if a.kind == 'QuestionGraph')
        bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref, policy_ref(bundle.policies[0]),
            config, artifact_id='target-r11-' + case.name, created_at=now(), bridge_context=bundle.bridge_context)
        target = artifact_ref(bundle.artifacts[-1])
        bundle = create_plan(bundle, artifact_ref(graph), pre_ref, target, actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='plan-r11-' + case.name, created_at=now(), bridge_context=bundle.bridge_context)
        plan = bundle.artifacts[-1]
        assert len(plan.payload.actions) == 1 and plan.payload.actions[0].operation == 'CREATE_FRAMES'
        store.record_native_plan(reg['id'], bundle, artifact_ref(plan), config, owner_id=claim.owner_id, generation=claim.generation)
        write(case / 'before-run.json', {'pid': os.getpid(), 'instance': store.instance, 'claim': plain(claim),
            'plan_ref': artifact_ref(plan), 'plan': plain(plan), 'pre_ref': pre_ref, 'snapshot_ref': actual.snapshot_ref,
            'native_pre_run_id': admitted.run_id, 'imports': imports(), 'at_ns': time.time_ns()})
        # Retain actual pre-run bytes; this is a sequential raw copy while the
        # own keeper exists, not a cross-database transactional backup.
        write(case / 'before-run-runtime.sqlite3', store.database.read_bytes())
        write(case / 'before-run-target.sqlite3', (case / 'target/target.sqlite3').read_bytes())
        capture_stage(case, 'pre-fault', own_writer_keeper=True)
        return store, claim, keeper, config
    except BaseException:
        keeper.stop()
        raise


def crash(case, group):
    from annotation.runtime.recovery import run_plan
    store, claim, keeper, config = qualify(case)
    try:
        run_plan(store, store.registration()['id'], owner_id=claim.owner_id, generation=claim.generation, config=vars(config),
            fault={'point': POINTS[group], 'marker': str(case / 'crash.marker.json')})
        raise AssertionError('existing FaultController did not exit90 at ' + POINTS[group])
    finally:
        # A true os._exit bypasses this and the exit-import writer deliberately.
        keeper.stop()


def bundle_boundary(store, case):
    reg = store.registration()
    bundle = store.bundle(reg['id'])
    snapshot = files.state(case, True)
    registered = [json.loads(row['ref']) for row in snapshot['runtime']['tables']['artifacts']]
    assert all(ref(a) in registered for a in bundle['artifacts'])
    resources = []
    for row in snapshot['runtime']['tables']['actions']:
        if row['fact']:
            resource = json.loads(row['fact'])
            raw = (Path(reg['package_root']) / resource['path']).read_bytes()
            assert sha(raw) == resource['sha256']
            resources.append({'resource': resource, 'body': json.loads(raw)})
    return {'bundle': bundle, 'state': snapshot, 'facts': resources, 'all_current_refs_formally_registered': True}


def query(case, group):
    from annotation.runtime.recovery import reconcile
    store = files.helper.open_case(case)
    reg = store.registration()
    if group in ('F2', 'F3'):
        capture_stage(case, 'pending-before-projection', own_writer_keeper=False)
    before_status = store.status(reg['id'])
    before = bundle_boundary(store, case)
    write(case / 'reopened-before.json', {'pid': os.getpid(), 'instance': store.instance, 'status': before_status, **before, 'imports': imports()})
    effect_before = before['state']['target']['counts']['effects']
    current = before['bundle']
    plan = next(a for a in current['artifacts'] if a['kind'] == 'ApplyPlan')
    assert ref(plan) == json.loads((case / 'before-run.json').read_bytes())['plan_ref']
    if group == 'F1':
        assert before['state']['runtime']['counts']['plans'] == before['state']['runtime']['counts']['actions'] == 1
        assert before['state']['runtime']['counts']['intents'] == before['state']['runtime']['counts']['permits'] == effect_before == 0
        assert not any(a['kind'] in ('WriteIntent', 'ExecutionReceipt') for a in current['artifacts'])
        result = {'open_status_query_only': True, 'reconcile_calls': 0, 'effect_count': effect_before,
            'attempt_fact': None, 'attempt_fact_note': 'NO_FORMAL_RESULT_NOT_FABRICATED', 'plan_action_reserved_without_intent': True}
    elif group == 'F4':
        assert effect_before == 1
        receipts = [a for a in current['artifacts'] if a['kind'] == 'ExecutionReceipt']
        assert len(receipts) == 1 and len(before['facts']) == 1
        receipt, fact = receipts[0], before['facts'][0]
        intent = before['state']['runtime']['tables']['intents'][0]
        assert json.loads(intent['receipt']) == ref(receipt)
        assert receipt['payload']['plan'] == ref(plan)
        assert receipt['payload']['action_fact_refs'] == [fact['resource']]
        assert fact['body']['plan_ref'] == ref(plan) and fact['body']['intent_ref'] == json.loads(intent['ref'])
        assert fact['body']['action_id'] == plan['payload']['actions'][0]['action_id']
        assert fact['body']['result']['outcome'] == 'APPLIED'
        assert before['state']['runtime']['counts']['resolutions'] == 0
        result = {'open_status_query_only': True, 'reconcile_calls': 0, 'effect_count': effect_before,
            'receipt_ref': ref(receipt), 'fact': fact, 'attempt_fact': fact['body']['result']['attempt_fact']}
    else:
        assert before_status['pending_count'] == 1
        assert before['state']['runtime']['counts']['intents'] == before['state']['runtime']['counts']['permits'] == 1
        assert before['state']['runtime']['tables']['permits'][0]['state'] == 'CONSUMED'
        assert effect_before == (0 if group == 'F2' else 1)
        events = [e['event'] for e in before_status['events']]
        assert 'DISPATCH_STARTED' in events and 'ACTION_RESULT_COMMITTED' not in events
        assert not any(a['kind'] == 'ExecutionReceipt' for a in current['artifacts'])
        projection = store.project_plan(reg['id'])
        assert projection['receipt_ref'] is None and projection['actions'][0]['effective_outcome'] == 'UNKNOWN'
        write(case / 'pre-reconcile-UNKNOWN.json', {'projection': projection, **bundle_boundary(store, case)})
        capture_stage(case, 'UNKNOWN-before-reconcile', own_writer_keeper=False)
        read_sequences = [json.loads(row['body'])['read_sequence'] for row in before['state']['target']['tables']['observations']]
        max_read_sequence = max(x for x in read_sequences if x is not None)
        reconciled = reconcile(store, reg['id'], call_id='call-r11-' + group, max_attempts=1)
        write(case / 'reconcile-once.json', reconciled)
        expected = 'RESOLVED_NOT_APPLIED' if group == 'F2' else 'RESOLVED_APPLIED'
        assert reconciled['attempt_count'] == 1 and reconciled['resolutions'][0]['status'] == expected
        after = bundle_boundary(store, case)
        assert after['state']['target']['counts']['effects'] == effect_before
        assert after['state']['target']['counts']['observations'] == before['state']['target']['counts']['observations'] + 1
        resolution = next(a for a in after['bundle']['artifacts'] if ref(a) == reconciled['resolutions'][0]['result_ref'])
        payload = resolution['payload']
        intent = before['state']['runtime']['tables']['intents'][0]
        assert payload['plan_ref'] == ref(plan) and payload['intent_ref'] == json.loads(intent['ref'])
        assert payload['action_id'] == plan['payload']['actions'][0]['action_id']
        assert payload['observation'] == ('ABSENT' if group == 'F2' else 'MATCH')
        assert payload['original_receipt_ref'] is None and payload['replay_allowed'] is False
        readback_raw = (Path(reg['package_root']) / payload['readback']['path']).read_bytes()
        assert sha(readback_raw) == payload['readback']['sha256']
        readback = json.loads(readback_raw)
        assert readback['read_status'] == 'OK' and readback['scope_complete'] is True
        assert readback['target_key'] == before_status['target_key']
        assert readback['target_store_id'] == store.target_store_id and readback['target_session_id'] == reg['session']
        assert readback['scope_id'] == reg['scope'] and readback['source_ref'] == json.loads(reg['source'])
        assert readback['observation_id'] == payload['observation_id'] and readback['read_sequence'] == payload['read_sequence'] > max_read_sequence
        observed_snapshot = next(a for a in after['bundle']['artifacts'] if ref(a) == payload['observed_snapshot_ref'])
        assert observed_snapshot['kind'] == 'PlatformSnapshot'
        target_observation = next(json.loads(row['body']) for row in after['state']['target']['tables']['observations']
            if row['observation_id'] == payload['observation_id'])
        assert target_observation['read_sequence'] == payload['read_sequence']
        progress = [a for a in after['bundle']['artifacts'] if a['kind'] == 'ExecutionProgress'][-1]
        assert progress['payload']['actions'][0]['attempt_fact'] == projection['actions'][0]['attempt_fact']
        assert progress['payload']['actions'][0]['attempt_fact'] != 'NOT_ATTEMPTED'
        assert any(a['kind'] == 'ExecutionProgress' and any(r['effective_outcome'] == 'UNKNOWN' for r in a['payload']['actions']) for a in after['bundle']['artifacts'])
        write(case / 'fresh-terminal-readback.json', {'resolution': resolution, 'readback_resource': payload['readback'], 'readback': readback,
            'old_max_target_read_sequence': max_read_sequence, 'actual_new_target_observation': target_observation, 'observed_snapshot': observed_snapshot})
        result = {'reconcile_calls': 1, 'max_attempts': 1, 'effect_count_before_after': [effect_before, effect_before],
            'resolution_ref': ref(resolution), 'resolution': payload['resolution'], 'observation': payload['observation'],
            'attempt_fact_before': projection['actions'][0]['attempt_fact'], 'attempt_fact_after': progress['payload']['actions'][0]['attempt_fact'],
            'new_read_sequence': payload['read_sequence'], 'old_max_read_sequence': max_read_sequence,
            'old_action_replay_calls': 0, 'formal_original_UNKNOWN_retained': True}
    after_status = store.status(reg['id'])
    final = bundle_boundary(store, case)
    result.update(status='REVIEW', group=group, actual_plan_status=final['state']['runtime']['tables']['plans'][0]['status'],
        POST_count=sum(a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY' for a in final['bundle']['artifacts']),
        Batch_count=sum(a['kind'] == 'BatchReport' for a in final['bundle']['artifacts']),
        report_read_count=final['state']['runtime']['counts']['native_report_reads'])
    write(case / 'reopened-after.json', {'pid': os.getpid(), 'status': after_status, **final})
    write(case / 'result.json', result)


def run_phase(root, group, phase):
    folder = root / 'processes' / (group + '-' + phase)
    folder.mkdir(parents=True, exist_ok=False)
    expected = 90 if phase == 'crash' else 0
    argv = [sys.executable, '-X', 'utf8', '-B', str(SCRIPT), group, '--phase', phase, '--output-root', root.relative_to(ROOT).as_posix()]
    write(folder / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 45, 'expected_exit': expected,
        'script_sha256': sha(SCRIPT.read_bytes()), 'inputs_sha256': sha((OUT / 'inputs.json').read_bytes()),
        'helpers': {m.__file__: sha(Path(m.__file__).read_bytes()) for m in (files, files.helper)}})
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
    assert code == expected and not timed_out, 'first phase failure: ' + str(folder / 'stderr.txt')
    return process.pid


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('group', choices=tuple(POINTS))
    parser.add_argument('--phase', choices=('crash', 'query'))
    parser.add_argument('--output-root', default='docs/evidence/A03/execution/P2-R11-crash-cuts/validation/r11-01')
    args = parser.parse_args()
    root = (ROOT / args.output_root).resolve()
    assert root.is_relative_to(OUT)
    case = root / 'cases' / args.group
    if args.phase:
        try:
            (crash if args.phase == 'crash' else query)(case, args.group)
        finally:
            # os._exit does not run this; fault-before imports above are the
            # actual identity evidence for crash workers. No fabricated exits.
            write(root / 'imports' / (args.group + '-' + args.phase + '.json'), imports())
    else:
        try:
            pid = run_phase(root, args.group, 'crash')
            marker = json.loads((case / 'crash.marker.json').read_bytes())
            assert marker['pid'] == pid and marker['point'] == POINTS[args.group]
            capture_stage(case, 'cut-after-wait', own_writer_keeper=False)
            frozen = files.state(case, True)
            write(root / (args.group + '-after-exit90-before-reopen.json'), frozen)
            assert frozen['target']['counts']['effects'] == (1 if args.group in ('F3', 'F4') else 0)
            assert frozen['runtime']['counts']['intents'] == (0 if args.group == 'F1' else 1)
            if args.group in ('F2', 'F3'):
                events = [json.loads(row['body'])['event'] for row in frozen['runtime']['tables']['events']]
                assert 'DISPATCH_STARTED' in events and 'ACTION_RESULT_COMMITTED' not in events
            run_phase(root, args.group, 'query')
            capture_stage(case, 'after-query-or-recovery', own_writer_keeper=False)
            write(root / (args.group + '-final-SQL.json'), files.state(case, True))
        except BaseException:
            write(root / (args.group + '-first-failure-SQL.json'), files.state(case, True))
            raise
