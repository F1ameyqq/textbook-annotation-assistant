"""N/E/U thin composition of unchanged native APIs. One target/dispatch per path."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
from support import ROOT, EVIDENCE, load, write, imports, run_child

RID = 'registration-I01'


class Trace:
    def __init__(self, out): self.out, self.index = out, 0
    def call(self, name, operation):
        self.index += 1
        folder = self.out/'calls'/('%02d-' % self.index + name)
        start = time.monotonic(), time.process_time()
        write(folder/'started.json', dict(name=name, pid=os.getpid(), at_ns=time.time_ns()))
        try:
            result = operation()
            write(folder/'ended.json', dict(name=name, status='RETURNED', wall_seconds=time.monotonic()-start[0],
                cpu_seconds=time.process_time()-start[1]))
            return result
        except BaseException as error:
            write(folder/'ended.json', dict(name=name, status='RAISED', error=repr(error),
                wall_seconds=time.monotonic()-start[0], cpu_seconds=time.process_time()-start[1]))
            raise


def snapshot(store, out, stage):
    from capture import capture_databases, Boundary
    reg = store.registration(RID)
    return capture_databases(out/'captures'/stage,
        {'runtime':store.directory/'runtime.sqlite3', 'target':Path(reg['target_dir'])/'target.sqlite3'}, boundary=Boundary())


def setup(out, tag, trace):
    from annotation.contracts import artifact_ref
    from annotation.runtime.storage.native import init_native_state
    from annotation.delivery.mock.persistent import PersistentMockSession
    from annotation.quality.targetcheck import SimulationConfig
    fixture = Path(os.environ['I01_FROZEN_VIEW'])/'tests/fixtures/i01'/tag
    store = trace.call('init-native-state', lambda:init_native_state(out/'anchor.json', out/'runtime',
        expected_ledger_id='ledger-I01-'+tag, expected_target_store_id='store-I01-'+tag))
    bundle = trace.call('validate-fixed-input', lambda:store._validate(load(fixture/'initial.json'), asset_root=fixture))
    source, _, _, snap = bundle.artifacts
    key = dict(platform_namespace='I01-A-fixed-synthetic', target_id=snap.payload.target_id, book_id=source.book_id)
    config = SimulationConfig(source.book_id, snap.payload.target_id, source.scope_id, {'directory-M':'platform-M'})
    reg = trace.call('register-book', lambda:store.register_book(bundle, target_key=key, target_dir=out/'target',
        target_session_id='session-I01-'+tag, source_ref=artifact_ref(source), asset_root=fixture,
        config=vars(config), registration_id=RID))
    # This marker consumes the sole fresh target even if creation subsequently fails.
    write(out/'target-creation-attempt.json', dict(path=tag, target_key=key, native_targets_consumed=1, pid=os.getpid()))
    observer = trace.call('create-target', lambda:PersistentMockSession.create(out/'target', bundle, artifact_ref(snap),
        platform_namespace=key['platform_namespace'], source_ref=artifact_ref(source), asset_root=reg.package_root,
        expected_store_id=store.target_store_id, target_session_id='session-I01-'+tag,
        bridge_context=store.bridge_for(bundle, reg.package_root)))
    return store, observer, config


def plan(store, observer, owner, config, label, trace):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.runtime.storage.common import now, plain, reference
    from annotation.quality.synthetic_precheck import produce_a03_pre_run, admit_a03_pre_run
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    reg = store.registration(RID)
    actual = trace.call('INITIAL-'+label, lambda:store.begin_native_pre(RID, owner_id=owner.owner_id,
        generation=owner.generation, observer=observer))
    source = next(a for a in actual.bundle.artifacts if a.kind=='SourceBundle')
    evidence = next(a for a in actual.bundle.artifacts if a.kind=='EvidenceBundle')
    graph = next(a for a in actual.bundle.artifacts if a.kind=='QuestionGraph')
    bundle, pre = trace.call('five-checks-PRE-'+label, lambda:produce_a03_pre_run(actual.bundle,
        artifact_ref(source), artifact_ref(evidence), artifact_ref(graph), policy_ref(actual.bundle.policies[0]),
        bridge_context=actual.bundle.bridge_context, registered_run_handle=actual.handle,
        actual_snapshot_ref=actual.snapshot_ref, actual_observation=actual.observation,
        asset_root=reg['package_root'], artifact_id='pre-I01-'+label, created_at=now()))
    trace.call('admit-PRE-'+label, lambda:admit_a03_pre_run(bundle, pre, bridge_context=bundle.bridge_context,
        registered_run_handle=actual.handle, actual_snapshot_ref=actual.snapshot_ref, asset_root=reg['package_root']))
    bundle = trace.call('TARGET-'+label, lambda:check_target(bundle, artifact_ref(graph), actual.snapshot_ref,
        actual.snapshot_ref, policy_ref(bundle.policies[0]), config, artifact_id='target-I01-'+label,
        created_at=now(), bridge_context=bundle.bridge_context))
    bundle = trace.call('planner-'+label, lambda:create_plan(bundle, artifact_ref(graph), pre,
        artifact_ref(bundle.artifacts[-1]), actual.snapshot_ref, actual.snapshot_ref, policy_ref(bundle.policies[0]),
        config, artifact_id='plan-I01-'+label, created_at=now(), bridge_context=bundle.bridge_context))
    p = plain(bundle.artifacts[-1])
    trace.call('record-plan-'+label, lambda:store.record_native_plan(RID, bundle, reference(p), config,
        owner_id=owner.owner_id, generation=owner.generation))
    write(trace.out/('plan-'+label+'.json'), p)
    return p


def claim(store, observer, trace, suffix):
    from annotation.runtime.recovery.lease import LeaseKeeper
    owner = trace.call('claim-'+suffix, lambda:store.claim(store.target_key(RID), observer=observer))
    keeper = LeaseKeeper(store, store.target_key(RID), owner.owner_id, owner.generation).start()
    write(trace.out/('owner-'+suffix+'.json'), dict(owner=dict(owner), keeper_thread=keeper.thread.ident))
    return owner, keeper


def release(store, owner, keeper, trace, suffix):
    if keeper is not None:
        trace.call('keeper-stop-join-'+suffix, keeper.stop)
        assert not keeper.thread.is_alive()
        keeper.check()
    if owner is not None:
        trace.call('release-'+suffix, lambda:store.release(store.target_key(RID),
            owner_id=owner.owner_id, generation=owner.generation))


def prepare_action(store, observer, owner, p, config):
    from annotation.runtime.storage.common import reference
    reg = store.registration(RID)
    bundle = store._validate(store.bundle(RID), asset_root=reg['package_root'])
    return observer.prepare_action(bundle, reference(p), p['payload']['actions'][0]['action_id'], config,
        current_snapshot_ref=p['payload']['snapshot'], asset_root=reg['package_root'], bridge_context=bundle.bridge_context)


def unknown(store, observer, owner, p, config, trace):
    from annotation.delivery.planner import compare_action_effect
    from annotation.runtime.storage.common import reference, plain
    trace.call('accept-plan', lambda:store.accept_plan(RID, reference(p), owner_id=owner.owner_id, generation=owner.generation))
    context = trace.call('load-context', lambda:store.load_book_context(store.target_key(RID), owner_id=owner.owner_id,
        generation=owner.generation))
    trace.call('import-context', lambda:observer.import_book_context(context, authority=store))
    prepared = trace.call('prepare-action', lambda:prepare_action(store, observer, owner, p, config))
    intent = trace.call('persist-intent', lambda:store.commit_intent(prepared, owner_id=owner.owner_id, generation=owner.generation))
    permit = trace.call('issue-first-dispatch-permit', lambda:store.issue_first_dispatch(intent['intent_ref'],
        owner_id=owner.owner_id, generation=owner.generation, plan_ref=reference(p),
        action_id=p['payload']['actions'][0]['action_id'], observation_binding=prepared['observation_binding']))
    write(trace.out/'intent.json', plain(intent)); write(trace.out/'permit.json', plain(permit))
    write(trace.out/'dispatch-attempt.json', dict(pid=os.getpid(), intent_ref=intent['intent_ref'], dispatches_consumed=1))
    dispatched = trace.call('dispatch-once-real-effect', lambda:observer.dispatch_action(prepared, committed_intent=intent,
        dispatch_permit=permit, authority=store))
    write(trace.out/'dispatch-return.json', plain(dispatched))
    observed = trace.call('execution-read-unavailable', lambda:observer.observe_target(store.target_key(RID),
        observation_id='I01-U-execution-unavailable', read_fault='unavailable'))
    result = trace.call('persist-UNKNOWN', lambda:store.commit_action_result(intent, prepared, observed,
        compare_action_effect(p['payload']['actions'][0], prepared['observation'], observed),
        owner_id=owner.owner_id, generation=owner.generation))
    assert result['result']['outcome']=='UNKNOWN'
    projection = trace.call('formal-UNKNOWN-receipt-progress', lambda:store.project_plan(RID, p))
    assert store.status(RID)['pending_count']==1 and store.status(RID)['paused']
    return dict(result=plain(result), projection=plain(projection), dispatch_return=plain(dispatched))


def native(phase, out, trace):
    from annotation.runtime.recovery import run_plan, reconcile, publish_quality, open_observer
    from annotation.runtime.storage.native import open_native_state
    from annotation.contracts import ContractError
    from annotation.runtime.storage.common import RuntimeFailure, plain
    owner = keeper = None
    result = {}
    if phase=='U-recover':
        original = out.parent/'U-execute'
        desc = load(original/'anchor.json')
        store = trace.call('reopen-same-native-identity', lambda:open_native_state(original/'anchor.json',
            expected_ledger_id=desc['ledger_id'], expected_target_store_id=desc['target_store_id']))
        assert load(original/'worker-started.json')['pid'] != os.getpid()
        before = store.bundle(RID)
        result['reconcile'] = trace.call('reconcile-fixed-call-max1', lambda:reconcile(store, RID,
            call_id='I01-U-one-MATCH-call', max_attempts=1))
        assert result['reconcile']['attempt_count']==1
        assert result['reconcile']['resolutions'][0]['classification']=='MATCH'
        assert result['reconcile']['resolutions'][0]['status']=='RESOLVED_APPLIED'
        result['quality'] = trace.call('one-final-fresh-report', lambda:publish_quality(store, RID))
        after = store.bundle(RID)
        for a in before['artifacts']:
            assert a in after['artifacts'], 'original UNKNOWN history changed'
        write(out/'history-before-recovery.json', before)
        result['execution_pid'] = load(original/'worker-started.json')['pid']
        observer = open_observer(store, RID)
    else:
        tag = phase[0]
        store, observer, config = setup(out, tag, trace)
        try:
            owner, keeper = claim(store, observer, trace, 'initial')
            p = plan(store, observer, owner, config, tag+'-old' if tag=='E' else tag, trace)
            if tag=='E':
                trace.call('operator-add-directory-once', lambda:observer.synthetic_external_add_directory('synthetic-external-I01-E'))
                try:
                    trace.call('old-candidate-pre-dispatch-refusal', lambda:prepare_action(store, observer, owner, p, config))
                except ContractError as error:
                    rejection = dict(layer='CONTRACT', issues=error.issues)
                    assert any(i.get('code')=='TARGET_CHANGED' for i in error.issues), rejection
                except RuntimeFailure as error:
                    rejection = dict(layer='RUNTIME', code=error.code, message=str(error))
                    assert error.code=='TARGET_CHANGED'
                else: raise AssertionError('old candidate must be refused before dispatch')
                write(out/'old-candidate-refusal.json', rejection)
                release(store, owner, keeper, trace, 'old'); owner=keeper=None
                oldsql = snapshot(store, out, 'old-candidate-refused-released')
                assert not oldsql['runtime']['tables']['intents'] and not oldsql['target']['tables']['effects']
                owner, keeper = claim(store, observer, trace, 'correction')
                new = plan(store, observer, owner, config, 'E-new', trace)
                assert new['payload']['precheck'] != p['payload']['precheck']
                assert new['payload']['snapshot'] != p['payload']['snapshot']
                assert new['payload']['actions'][0]['action_id'] != p['payload']['actions'][0]['action_id']
                result['correction'] = dict(old_plan=p, new_plan=new, old_dispatches=0, operator_changes=1,
                    strategy='fresh INITIAL after normal release/reclaim; no terminal baseline so no hold was entered')
                p = new
            if tag=='U':
                result['unknown'] = unknown(store, observer, owner, p, config, trace)
            else:
                # run_plan owns its normal LeaseKeeper and publishes once.
                keeper.stop(); keeper.check(); assert not keeper.thread.is_alive(); keeper=None
                write(out/'dispatch-attempt.json', dict(pid=os.getpid(), plan_id=p['artifact_id'], dispatches_consumed=1,
                    layer='one-action run_plan invocation; actual dispatch confirmed in retained target effects'))
                result['run'] = trace.call('normal-run-plan-once', lambda:run_plan(store, RID,
                    owner_id=owner.owner_id, generation=owner.generation, config=vars(config)))
                owner=None
                assert result['run']['status']=='FINISHED' and result['run']['records'][0]['result']['outcome']=='APPLIED'
        finally:
            release(store, owner, keeper, trace, 'final')
    result['status'] = store.status(RID)
    result['bundle'] = store.bundle(RID)
    result['target'] = plain(observer.export_book_context(store.target_key(RID)))
    sql = snapshot(store, out, 'after-release')
    books = sql['runtime']['tables']['books']
    assert all(b['owner'] is None and b['pid'] is None and b['lease']==0 for b in books)
    assert result['target']['dispatch_count']==1 and result['target']['effect_count']==1
    if phase!='U-execute': assert result['status']['pending_count']==0
    write(out/'result.json', result)


def worker(args):
    out=args.output.resolve()
    write(out/'worker-started.json', dict(pid=os.getpid(), argv=sys.argv, phase=args.phase, cwd=str(Path.cwd())))
    trace=Trace(out); started=time.monotonic(),time.process_time()
    try:
        native(args.phase, out, trace)
    except BaseException as error:
        write(out/'failure.json', dict(error=repr(error), traceback=traceback.format_exc(), no_automatic_rerun=True))
        raise
    finally:
        write(out/'worker-ended.json', dict(pid=os.getpid(), wall_seconds=time.monotonic()-started[0],
            cpu_seconds=time.process_time()-started[1], imports=imports(), threads=[t.name for t in threading.enumerate()]))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('N','E','U-execute','U-recover'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--watch', action='store_true')
    args=parser.parse_args()
    if args.watch:
        result=run_child(args.output/'worker-process', [sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),
            '--phase',args.phase,'--output',str(args.output)], env=dict(os.environ), timeout=180)
        if result['exit_code']!=0 or result['timeout']: raise RuntimeError('worker failed; retain original; no implicit retry')
    else: worker(args)


if __name__=='__main__': main()
