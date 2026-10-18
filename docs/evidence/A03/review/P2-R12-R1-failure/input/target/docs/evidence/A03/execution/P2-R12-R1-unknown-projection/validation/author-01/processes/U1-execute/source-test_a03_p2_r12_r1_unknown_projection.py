"""Fixed L1 and U1--U5 scene assertions; invoke only via the bounded driver."""
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples/a03/P2-R12-R1-unknown-projection'))
from support import HERE, FAULTS, capture, write, imports, check_frozen


def setup_legacy(case):
    from annotation.contracts import load_recovery_bundle, artifact_ref
    from annotation.delivery.mock import PersistentMockSession
    from annotation.runtime.storage import init_state
    from annotation.runtime.recovery import configuration
    from annotation.runtime.recovery.cli import build_current_plan
    from annotation.runtime.recovery.lease import LeaseKeeper
    case.mkdir(parents=True, exist_ok=False)
    assets = HERE / 'legacy-recovery'
    bundle = load_recovery_bundle(assets / 'bundle.json', asset_root=assets)
    snapshot = next(a for a in bundle.artifacts if a.kind == 'PlatformSnapshot')
    source = next(a for a in bundle.artifacts if a.kind == 'SourceBundle')
    config_data = json.loads((HERE / 'legacy-config.json').read_bytes())
    config = configuration(config_data)
    store = init_state(case / 'anchor.json', state_dir=case / 'runtime',
        expected_ledger_id='ledger-r12-r1-L1', expected_target_store_id='target-store-r12-r1-L1')
    key = {'platform_namespace': 'a03-r12-r1-legacy', 'book_id': source.book_id, 'target_id': snapshot.payload.target_id}
    reg = store.register_book(bundle, target_key=key, target_dir=case / 'target', target_session_id='session-r12-r1-L1',
        source_ref=artifact_ref(source), asset_root=assets, config=config_data, registration_id='registration-r12-r1-L1')
    observer = PersistentMockSession.create(case / 'target', bundle, artifact_ref(snapshot), platform_namespace=key['platform_namespace'],
        source_ref=artifact_ref(source), asset_root=reg.package_root, expected_store_id=store.target_store_id,
        target_session_id='session-r12-r1-L1')
    plan = build_current_plan(store, reg.registration_id, observer, config_data)
    claim = store.claim(key, observer=observer)
    keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()
    return store, observer, claim, keeper, plan, config


def setup_native(case):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    from annotation.runtime.storage.common import now, plain, reference
    spec = importlib.util.spec_from_file_location('r8_fixed_helper', ROOT / 'tests/test_a03_r8_r3_post_hold.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    sys.modules[spec.name] = helper
    store, observer, claim, keeper, bundle, pre_ref, actual, admitted, config = helper.setup_pre(case)
    try:
        reg = store.registration()
        graph = next(a for a in bundle.artifacts if a.kind == 'QuestionGraph')
        bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='target-r12-r1-' + case.name,
            created_at=now(), bridge_context=bundle.bridge_context)
        target_ref = artifact_ref(bundle.artifacts[-1])
        bundle = create_plan(bundle, artifact_ref(graph), pre_ref, target_ref, actual.snapshot_ref, actual.snapshot_ref,
            policy_ref(bundle.policies[0]), config, artifact_id='plan-r12-r1-' + case.name,
            created_at=now(), bridge_context=bundle.bridge_context)
        plan = plain(bundle.artifacts[-1])
        store.record_native_plan(reg['id'], bundle, reference(plan), config, owner_id=claim.owner_id, generation=claim.generation)
        write(case / 'native-PRE-binding.json', {'pre_ref': pre_ref, 'snapshot_ref': actual.snapshot_ref,
            'run_id': admitted.run_id, 'owner': claim.owner_id, 'generation': claim.generation})
        return store, observer, claim, keeper, plan, config
    except BaseException:
        keeper.stop()
        store.release(store.target_key(store.registration()['id']), owner_id=claim.owner_id, generation=claim.generation)
        raise


def assert_unknown(store, values, native):
    from annotation.runtime.storage.common import reference
    reg = store.registration()
    bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
    raw = bundle.model_dump(mode='json')
    receipts = [a for a in raw['artifacts'] if a['kind'] == 'ExecutionReceipt']
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt['payload']['write_disposition'] == 'PAUSE_RECONCILE'
    assert len(receipt['payload']['unresolved_issue_ids']) == 1
    result, = receipt['payload']['results']
    assert result['outcome'] == 'UNKNOWN' and result['replay_allowed'] is False
    assert result['attempt_fact'] == 'MAY_HAVE_BEEN_ATTEMPTED'
    progress = [a for a in raw['artifacts'] if a['kind'] == 'ExecutionProgress'][-1]
    action, = progress['payload']['actions']
    assert action['effective_outcome'] == 'UNKNOWN' and action['receipt_ref'] == reference(receipt)
    assert action['attempt_fact'] == result['attempt_fact'] and action['intent_ref'] == result['intent_ref']
    tables = values['runtime']['tables']
    row, = tables['actions']
    intent, = tables['intents']
    permit, = tables['permits']
    assert row['state'] == 'UNKNOWN' and intent['state'] == 'PENDING'
    assert json.loads(intent['receipt']) == reference(receipt) and json.loads(intent['ref']) == result['intent_ref']
    assert permit['state'] == 'CONSUMED'
    fact = store.read_resource(json.loads(row['fact']), reg['id'])
    assert fact['result'] == result and fact['intent_ref'] == result['intent_ref']
    assert fact['action_id'] == row['id'] and fact['action_digest'] == row['digest']
    assert fact['plan_ref'] == receipt['payload']['plan']
    assert len(tables['plans']) == 1 and tables['plans'][0]['status'] == 'INTERRUPTED'
    assert len(values['target']['tables']['effects']) == 1
    status = store.status(reg['id'])
    assert status['paused'] and status['pending_count'] == 1
    posts = [a for a in raw['artifacts'] if a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY']
    batches = [a for a in raw['artifacts'] if a['kind'] == 'BatchReport']
    assert not batches
    if native:
        assert not posts and not tables['native_report_reads']
    else:
        post, = posts
        assert post['payload']['decision'] == 'HOLD' and post['payload']['receipt'] == reference(receipt)
        assert [i['issue_id'] for i in post['payload']['issues']] == receipt['payload']['unresolved_issue_ids']
        assert post['payload']['issues'][0]['code'] == 'SAVE_UNKNOWN'
    return {'status': status, 'receipt': receipt, 'progress': progress, 'fact': fact,
        'post_refs': [reference(a) for a in posts], 'bundle_validated': True}


def execute(case, name):
    from annotation.delivery.mock import compare_action
    from annotation.runtime.storage.common import plain, reference, unique
    store = claim = keeper = None
    try:
        store, observer, claim, keeper, plan, config = (setup_legacy if name == 'L1' else setup_native)(case)
        reg = store.registration()
        action, = plan['payload']['actions']
        assert action['operation'] == 'CREATE_FRAMES'
        store.accept_plan(reg['id'], reference(plan), owner_id=claim.owner_id, generation=claim.generation)
        context = store.load_book_context(store.target_key(reg['id']), owner_id=claim.owner_id, generation=claim.generation)
        observer.import_book_context(context, authority=store)
        bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
        before = capture(case, 'before-build', store=store, keeper=keeper)
        assert not before['runtime']['tables']['intents'] and not before['target']['tables']['effects']
        prepared = observer.prepare_action(bundle, reference(plan), action['action_id'], config,
            current_snapshot_ref=plan['payload']['snapshot'], asset_root=reg['package_root'],
            bridge_context=getattr(bundle, 'bridge_context', None))
        intent = store.commit_intent(prepared, owner_id=claim.owner_id, generation=claim.generation)
        permit = store.issue_first_dispatch(intent['intent_ref'], owner_id=claim.owner_id, generation=claim.generation,
            plan_ref=reference(plan), action_id=action['action_id'], observation_binding=prepared['observation_binding'])
        effect_fault, read_fault, _, _ = FAULTS[name]
        dispatched = observer.dispatch_action(prepared, committed_intent=intent, dispatch_permit=permit,
            authority=store, effect_fault=effect_fault)
        observed = observer.observe_target(store.target_key(reg['id']), observation_id=unique('r12-r1-execution'), read_fault=read_fault)
        comparison = compare_action(prepared['action'], prepared['observation'], observed)
        result = store.commit_action_result(intent, prepared, observed, comparison, owner_id=claim.owner_id, generation=claim.generation)
        write(case / 'execution.json', {'prepared': plain(prepared), 'intent': plain(intent),
            'dispatch': plain(dispatched), 'observation': plain(observed), 'comparison': plain(comparison), 'result': plain(result)})
        actual = capture(case, 'unknown-established', store=store, keeper=keeper)
        proof = assert_unknown(store, actual, name != 'L1')
        write(case / 'unknown-proof.json', proof)
        target = json.loads(next(r['value'] for r in actual['target']['tables']['meta'] if r['key'] == 'state'))
        expected_frames = 1 if name in ('L1', 'U1') else 2
        assert len(target['target']['questions']) == 1 and len(target['target']['frames']) == expected_frames
        assert len(json.loads(action['expected_after']['frames'])) == 2
    except BaseException:
        if store is not None:
            capture(case, 'first-failure', store=store, keeper=keeper)
        raise
    finally:
        if keeper is not None:
            keeper.stop()
            store.release(store.target_key(store.registration()['id']), owner_id=claim.owner_id, generation=claim.generation)
            write(case / 'owner-release.json', {'pid': os.getpid(), 'owner': claim.owner_id,
                'generation': claim.generation, 'keeper_alive': keeper.thread.is_alive(), 'normal_release': True})
            released = capture(case, 'after-release', store=store)
            write(case / 'released-status.json', store.status())
            assert released['runtime']['tables']['books'][0]['owner'] is None


def recover(case, name):
    from annotation.runtime.storage.native import open_native_state
    from annotation.runtime.recovery import reconcile
    store = open_native_state(case / 'anchor.json', expected_ledger_id='ledger-r8-r3-' + name,
        expected_target_store_id='target-store-r8-r3-' + name)
    before = capture(case, 'before-reconcile', store=store)
    initial = assert_unknown(store, before, True)
    assert initial['status']['owner_id'] is None and initial['status']['owner_phase'] == 'RELEASED'
    write(case / 'reopened-status.json', initial['status'])
    try:
        result = reconcile(store, read_fault=FAULTS[name][2], max_attempts=1, call_id='recovery-r12-r1-' + name)
        write(case / 'reconcile-result.json', result)
        after = capture(case, 'after-reconcile', store=store)
        final = assert_unknown(store, after, True)
        assert result['attempt_count'] == 1 and result['pending_count'] == 1 and result['paused']
        resolution, = result['resolutions']
        assert resolution['status'] == 'STILL_UNKNOWN' and resolution['classification'] == FAULTS[name][3]
        assert resolution['attempt_count'] == 1 and 'code' not in resolution
        bt, at = before['runtime']['tables'], after['runtime']['tables']
        assert bt['actions'] == at['actions'] and bt['intents'] == at['intents'] and bt['permits'] == at['permits']
        assert initial['fact'] == final['fact'] and initial['receipt'] == final['receipt']
        assert len(at['attempts']) == len(at['calls']) == len(at['resolutions']) == 1
        assert before['target']['tables']['effects'] == after['target']['tables']['effects']
        state = lambda v: json.loads(next(r['value'] for r in v['target']['tables']['meta'] if r['key'] == 'state'))
        assert all(state(before)[key] == state(after)[key] for key in ('target', 'internal_bindings', 'frame_projections'))
        reg = store.registration()
        bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
        artifact = next(a.model_dump(mode='json') for a in bundle.artifacts if a.kind == 'ReconciliationResult')
        payload = artifact['payload']
        observation = store.read_resource(payload['readback'], reg['id'])
        descriptor = json.loads(next(r['value'] for r in after['target']['tables']['meta'] if r['key'] == 'descriptor'))
        assert observation['target_key'] == descriptor['target_key']
        assert observation['store_id'] == observation['target_store_id'] == descriptor['store_id']
        assert observation['target_session_id'] == descriptor['target_session_id']
        assert observation['source_ref'] == descriptor['fixed_source_ref'] and observation['scope_id'] == descriptor['fixed_scope_id']
        persisted = next(json.loads(r['body']) for r in after['target']['tables']['observations'] if r['observation_id'] == observation['observation_id'])
        assert persisted == observation
        expected_status = {'U1': 'OK', 'U2': 'OK', 'U3': 'CONTRADICTORY', 'U4': 'TRUNCATED', 'U5': 'UNAVAILABLE'}[name]
        assert observation['read_status'] == expected_status
        assert payload['resolution'] == 'STILL_UNKNOWN' and payload['observation'] == FAULTS[name][3]
        assert payload['intent_ref'] == initial['fact']['intent_ref']
        assert payload['action_id'] == initial['fact']['action_id'] and payload['action_digest'] == initial['fact']['action_digest']
        if name == 'U1':
            assert observation['scope_complete'] and observation['relevant_scope_completeness'] and payload['observed_snapshot_ref'] is not None
        else:
            assert payload['observed_snapshot_ref'] is None
        if name == 'U2':
            questions = observation['view']['target']['questions']
            ids = [q['platform_question_id'] for q in questions]
            assert len(ids) == 2 and len(set(ids)) == 1
            assert len(state(after)['target']['questions']) == 1
        if name in ('U1', 'U2', 'U3'):
            assert observation['scope_complete'] and observation['relevant_scope_completeness']
        if name in ('U4', 'U5'):
            assert not observation['scope_complete'] and not observation['relevant_scope_completeness']
        if name == 'U5':
            for key in ('view', 'state', 'read_sequence', 'target_state_hash', 'target_state_version'):
                assert observation[key] is None
        else:
            execution = json.loads((case / 'execution.json').read_bytes())
            last_sequence = execution['observation']['read_sequence'] or execution['prepared']['observation']['read_sequence']
            assert observation['read_sequence'] > last_sequence
        assert final['status']['owner_id'] is None and final['status']['owner_phase'] == 'RELEASED'
        write(case / 'reconcile-proof.json', {'initial': initial, 'final': final, 'resolution': artifact,
            'actual_observation': observation, 'new_effects': 0, 'original_action_intent_permit_fact_unchanged': True,
            'target_business_digest_unchanged': True, 'normal_reconcile_owner_release': True})
    except BaseException:
        capture(case, 'reconcile-first-failure', store=store)
        raise


if __name__ == '__main__':
    name, phase, root_arg = sys.argv[1:]
    root = Path(root_arg).resolve()
    case = root / 'cases' / name
    check_frozen()
    try:
        (execute if phase == 'execute' else recover)(case, name)
    finally:
        write(root / 'imports' / (name + '-' + phase + '.json'), imports())
