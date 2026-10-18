"""Finite L/G differences on R1's own fresh synthetic states.

Never accepts old T3 states. SQL inspection uses T1's stationary copies only.
The ledger test continues the completed M2-sufficient state without repeating
its actions; each extra native target and dispatch is explicitly counted.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, default=str)+'\n').encode('utf-8'))


def imports():
    return {name: {'file': str(Path(mod.__file__).resolve()),
        'sha256': hashlib.sha256(Path(mod.__file__).read_bytes()).hexdigest()}
        for name, mod in sorted(sys.modules.items()) if name.startswith('annotation.') and getattr(mod, '__file__', None)}


def reject(call):
    from annotation.contracts import ContractError
    from annotation.runtime.storage.common import RuntimeFailure
    try:
        call()
    except ContractError as error:
        return {'layer': 'CONTRACT', 'issues': error.issues}
    except RuntimeFailure as error:
        return {'layer': 'RUNTIME', 'code': error.code, 'message': str(error)}
    raise AssertionError('expected refusal')


def open_state(case):
    from annotation.runtime.storage.native import open_native_state
    desc = json.loads((case/'anchor.json').read_bytes())
    return open_native_state(case/'anchor.json', expected_ledger_id=desc['ledger_id'],
        expected_target_store_id=desc['target_store_id'])


def snapshot(store, registration, output, stage):
    from capture import capture_databases, Boundary
    reg = store.registration(registration)
    return capture_databases(output/'captures'/stage,
        {'runtime': store.directory/'runtime.sqlite3', 'target': Path(reg['target_dir'])/'target.sqlite3'}, boundary=Boundary())


def setup(store, output, registration):
    from annotation.contracts import artifact_ref
    from annotation.delivery.mock.persistent import PersistentMockSession
    from annotation.quality.targetcheck import SimulationConfig
    # Native fixture bytes are pinned to Git, including the PGM line endings.
    view = Path(os.environ.get('A03_R1_RAW_VIEW', str(ROOT/'docs/evidence/A03/R1/execution/candidate-1/business/runtime-view')))
    fixture = view/'examples/a03/T3-closure/inputs/single'
    dest = output/'input'
    shutil.copytree(fixture, dest)
    data = json.loads((dest/'initial.json').read_bytes())
    bundle = store._validate(data, asset_root=dest)
    source, _, _, snap = bundle.artifacts
    key = dict(platform_namespace='a03-R1-ledger', target_id=snap.payload.target_id, book_id=source.book_id)
    config = SimulationConfig(source.book_id, snap.payload.target_id, source.scope_id, {'directory-M':'platform-M'})
    reg = store.register_book(bundle, target_key=key, target_dir=output/'target', target_session_id='session-'+registration,
        source_ref=artifact_ref(source), asset_root=dest, config=vars(config), registration_id=registration)
    observer = PersistentMockSession.create(output/'target', bundle, artifact_ref(snap), platform_namespace=key['platform_namespace'],
        source_ref=artifact_ref(source), asset_root=reg.package_root, expected_store_id=store.target_store_id,
        target_session_id='session-'+registration, bridge_context=store.bridge_for(bundle, reg.package_root))
    return observer, config


def plan(store, rid, observer, claim, label):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.runtime.recovery import configuration
    from annotation.runtime.storage.common import plain, reference, now
    from annotation.quality.synthetic_precheck import produce_a03_pre_run, admit_a03_pre_run
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    reg = store.registration(rid)
    config = configuration(json.loads(reg['config']))
    actual = store.begin_native_pre(rid, owner_id=claim.owner_id, generation=claim.generation, observer=observer)
    source = next(a for a in actual.bundle.artifacts if a.kind == 'SourceBundle')
    evidence = next(a for a in actual.bundle.artifacts if a.kind == 'EvidenceBundle')
    graph = next(a for a in actual.bundle.artifacts if a.kind == 'QuestionGraph')
    b, pre = produce_a03_pre_run(actual.bundle, artifact_ref(source), artifact_ref(evidence), artifact_ref(graph),
        policy_ref(actual.bundle.policies[0]), bridge_context=actual.bundle.bridge_context,
        registered_run_handle=actual.handle, actual_snapshot_ref=actual.snapshot_ref, actual_observation=actual.observation,
        asset_root=reg['package_root'], artifact_id='pre-'+label, created_at=now())
    admit_a03_pre_run(b, pre, bridge_context=b.bridge_context, registered_run_handle=actual.handle,
        actual_snapshot_ref=actual.snapshot_ref, asset_root=reg['package_root'])
    b = check_target(b, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref, policy_ref(b.policies[0]), config,
        artifact_id='target-'+label, created_at=now(), bridge_context=b.bridge_context)
    b = create_plan(b, artifact_ref(graph), pre, artifact_ref(b.artifacts[-1]), actual.snapshot_ref, actual.snapshot_ref,
        policy_ref(b.policies[0]), config, artifact_id='plan-'+label, created_at=now(), bridge_context=b.bridge_context)
    p = plain(b.artifacts[-1])
    store.record_native_plan(rid, b, reference(p), config, owner_id=claim.owner_id, generation=claim.generation)
    return p, config


def unknown(store, rid, observer, claim, p, config, *, absent):
    from annotation.runtime.storage.common import reference
    from annotation.delivery.planner import compare_action_effect
    reg = store.registration(rid)
    key = store.target_key(rid)
    store.accept_plan(rid, reference(p), owner_id=claim.owner_id, generation=claim.generation)
    observer.import_book_context(store.load_book_context(key, owner_id=claim.owner_id, generation=claim.generation), authority=store)
    b = store._validate(store.bundle(rid), asset_root=reg['package_root'])
    action = p['payload']['actions'][0]
    prepared = observer.prepare_action(b, reference(p), action['action_id'], config, current_snapshot_ref=p['payload']['snapshot'],
        asset_root=reg['package_root'], bridge_context=b.bridge_context)
    intent = store.commit_intent(prepared, owner_id=claim.owner_id, generation=claim.generation)
    permit = store.issue_first_dispatch(intent['intent_ref'], owner_id=claim.owner_id, generation=claim.generation,
        plan_ref=reference(p), action_id=action['action_id'], observation_binding=prepared['observation_binding'])
    observer.dispatch_action(prepared, committed_intent=intent, dispatch_permit=permit, authority=store,
        effect_fault='not_applied' if absent else None)
    observation = observer.observe_target(key, observation_id='unavailable-'+p['artifact_id'], read_fault='unavailable')
    result = store.commit_action_result(intent, prepared, observation, compare_action_effect(action, prepared['observation'], observation),
        owner_id=claim.owner_id, generation=claim.generation)
    assert result['result']['outcome'] == 'UNKNOWN'
    return store.project_plan(rid, p)


def legacy(args):
    from annotation.contracts import artifact_ref, validate_bundle, seal_artifact, write_bundle
    from annotation.delivery.mock import MockSession
    helper = load_module(ROOT/'examples/a02/R1/scenarios.py', 'legacy_helpers')
    case = args.mroot/'cases/M2-sufficient'
    result = json.loads((case/'phase-finish-result.json').read_bytes())
    source = next(a for a in result['artifacts'] if a['kind']=='SourceBundle')
    snap = next(a for a in result['artifacts'] if a['kind']=='PlatformSnapshot')
    rows = []
    for ordinal in (1, 2):
        out = args.output/('history-'+str(ordinal)); out.mkdir()
        b, config = helper.own_input(ROOT, out, source['book_id'], 'R1-history-'+str(ordinal), scope='R1-history-scope-'+str(ordinal))
        data = b.model_dump()
        for a in data['artifacts']:
            if a['kind'] == 'PlatformSnapshot':
                a['payload']['target_id'] = snap['payload']['target_id']
                a.update(seal_artifact(a))
        config = __import__('dataclasses').replace(config, target_id=snap['payload']['target_id'])
        b = validate_bundle(data, asset_root=out)
        b, p, s = helper.prepare(b, config, out, 'R1-history-'+str(ordinal))
        session = MockSession(); session.register_target(b, artifact_ref(s), asset_root=out)
        executed = session.execute(b, artifact_ref(p), config, asset_root=out, receipt_id='R1-legacy-'+str(ordinal),
            created_at='2026-10-18T00:00:00Z', faults={p.payload.actions[0].action_id:'lost_response'})
        write_bundle(executed, out/'history.json')
        receipt = next(a for a in executed.artifacts if a.kind=='ExecutionReceipt')
        assert any(r.outcome == 'UNKNOWN' for r in receipt.payload.results)
        rows.append(dict(path=str(out/'history.json'), receipt_ref=artifact_ref(receipt), legacy_dispatch=1))
    write(args.output/'result.json', rows)


def ledger(args):
    from annotation.runtime.recovery import reconcile, open_observer, publish_quality
    from annotation.runtime.recovery.lease import LeaseKeeper
    from annotation.runtime.storage.common import plain
    case = args.mroot/'cases/M2-sufficient'
    store = open_state(case); rid = 'registration-M'
    before = store.status(rid); assert before['pending_count'] == 1
    counts = [before['pending_count']]
    for ordinal in (1, 2):
        archive = args.output.parent/'legacy'/('history-'+str(ordinal))/'history.json'
        store.import_history_archive(archive, expected_ledger_id=store.ledger_id, target_key=store.target_key(rid))
        counts.append(store.status(rid)['pending_count'])
    result = reconcile(store, rid, call_id='R1-L1-once', max_attempts=1)
    counts.append(store.status(rid)['pending_count'])
    assert counts == [1,2,3,2], counts
    observer = open_observer(store, rid); key = store.target_key(rid)
    claim = store.claim(key, observer=observer)
    keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()
    try:
        refusal = reject(lambda: store.begin_native_pre(rid, owner_id=claim.owner_id, generation=claim.generation, observer=observer))
        assert refusal.get('code') == 'BOOK_WRITE_PAUSED', refusal
        report = publish_quality(store, rid, owner_id=claim.owner_id, generation=claim.generation)
    finally:
        keeper.stop(); store.release(key, owner_id=claim.owner_id, generation=claim.generation)
    sql = snapshot(store, rid, args.output, 'after-release')
    write(args.output/'result.json', dict(counts=counts, reconcile=plain(result), full_book_refusal=refusal,
        report=plain(report), status=store.status(rid), target_effects=len(sql['target']['tables']['effects']),
        validation=store.native_registry.validation_counts, threads=[t.name for t in threading.enumerate()]))


def other_book(args):
    from annotation.runtime.recovery import run_plan
    from annotation.runtime.recovery.lease import LeaseKeeper
    from annotation.runtime.storage.common import plain
    store = open_state(args.mroot/'cases/M2-sufficient')
    before = store.status('registration-M')
    observer, config = setup(store, args.output, 'registration-B')
    key = store.target_key('registration-B'); claim = store.claim(key, observer=observer)
    keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()
    try:
        p, config = plan(store, 'registration-B', observer, claim, 'R1-book-B')
    finally:
        keeper.stop()
    result = run_plan(store, 'registration-B', owner_id=claim.owner_id, generation=claim.generation, config=vars(config))
    assert result['status']=='FINISHED' and result['pending_count']==0
    assert store.status('registration-M')['pending']==before['pending']
    snapshot(store, 'registration-B', args.output, 'after-release')
    write(args.output/'result.json', dict(result=plain(result), book_A=store.status('registration-M'), book_B=store.status('registration-B'),
        native_dispatch=1, validation=store.native_registry.validation_counts, threads=[t.name for t in threading.enumerate()]))


def recurrence(args):
    from annotation.runtime.storage.native import init_native_state
    from annotation.runtime.recovery import reconcile, open_observer
    from annotation.runtime.recovery.lease import LeaseKeeper
    from annotation.runtime.storage.common import plain
    case = args.output.parent/'L3-execute'
    rid = 'registration-L3'
    if args.phase == 'L3-execute':
        store = init_native_state(args.output/'anchor.json', args.output/'runtime', expected_ledger_id='ledger-R1-L3', expected_target_store_id='store-R1-L3')
        observer, _ = setup(store, args.output, rid)
    else:
        store = open_state(case); observer = open_observer(store, rid)
    if args.phase == 'L3-recover':
        result = reconcile(store, rid, call_id='R1-L3-first', max_attempts=1)
        assert store.status(rid)['pending_count']==0
        snapshot(store, rid, args.output, 'after-release')
        write(args.output/'result.json', dict(result=plain(result), status=store.status(rid), bundle=store.bundle(rid)))
        return
    key = store.target_key(rid); claim = store.claim(key, observer=observer)
    keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()
    try:
        p, config = plan(store, rid, observer, claim, args.phase)
        projection = unknown(store, rid, observer, claim, p, config, absent=args.phase=='L3-execute')
        if args.phase == 'L3-second':
            refusal = reject(lambda: store.begin_native_pre(rid, owner_id=claim.owner_id, generation=claim.generation, observer=observer))
            assert refusal.get('code')=='BOOK_WRITE_PAUSED', refusal
        else:
            refusal = None
    finally:
        keeper.stop(); store.release(key, owner_id=claim.owner_id, generation=claim.generation)
    assert store.status(rid)['pending_count']==1
    sql = snapshot(store, rid, args.output, 'after-release')
    write(args.output/'result.json', dict(projection=plain(projection), status=store.status(rid), refusal=refusal,
        bundle=store.bundle(rid), target_effects=len(sql['target']['tables']['effects']),
        validation=store.native_registry.validation_counts, threads=[t.name for t in threading.enumerate()]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('legacy','L1','B','L3-execute','L3-recover','L3-second'), required=True)
    parser.add_argument('--mroot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output=args.output.resolve(); args.mroot=args.mroot.resolve()
    assert args.mroot==ROOT/'docs/evidence/A03/R1/execution/candidate-1/business'
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.mroot/'runtime-view/examples/a03/T1-capture'))
    started=(time.monotonic(), time.process_time())
    write(args.output/'request.json', dict(argv=sys.argv, product_candidate='6097a06de937fee8876feccedf46920510850b83',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), phase=args.phase))
    try:
        if args.phase=='legacy': legacy(args)
        elif args.phase=='L1': ledger(args)
        elif args.phase=='B': other_book(args)
        else: recurrence(args)
    except BaseException as error:
        write(args.output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise
    finally:
        write(args.output/'process-result.json', dict(pid=os.getpid(), wall_seconds=time.monotonic()-started[0],
            cpu_seconds=time.process_time()-started[1], imports=imports(), threads=[t.name for t in threading.enumerate()]))


if __name__=='__main__':
    main()
