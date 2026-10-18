"""T1 scene orchestration: use frozen setup/assertion helpers, product owns rules."""
import importlib.util
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'examples/a03/T1-capture'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(HERE))
from capture import capture, LeaseBoundary, write
from support_t1 import FAULTS, check_frozen, imports
prior_path = list(sys.path)
spec = importlib.util.spec_from_file_location('r12_fixed_helper', ROOT / 'tests/test_a03_p2_r12_r2_issue_ownership.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
sys.modules[spec.name] = helper
sys.path[:] = prior_path
sys.path.insert(0, str(HERE / 'runtime-view/src'))
setup_legacy, setup_native, assert_unknown = helper.setup_legacy, helper.setup_native, helper.assert_unknown


def execute(case, name):
    from annotation.delivery.mock import compare_action
    from annotation.runtime.storage.common import plain, reference, unique
    store = claim = keeper = boundary = None
    try:
        store, observer, claim, keeper, plan, config = (setup_legacy if name == 'L1' else setup_native)(case)
        boundary = LeaseBoundary(keeper)
        reg = store.registration()
        action, = plan['payload']['actions']
        assert action['operation'] == 'CREATE_FRAMES'
        store.accept_plan(reg['id'], reference(plan), owner_id=claim.owner_id, generation=claim.generation)
        context = store.load_book_context(store.target_key(reg['id']), owner_id=claim.owner_id, generation=claim.generation)
        observer.import_book_context(context, authority=store)
        bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
        before = capture(case, 'before-build', boundary=boundary)
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
        observed = observer.observe_target(store.target_key(reg['id']), observation_id=unique('r12-r2-execution'), read_fault=read_fault)
        comparison = compare_action(prepared['action'], prepared['observation'], observed)
        result = store.commit_action_result(intent, prepared, observed, comparison, owner_id=claim.owner_id, generation=claim.generation)
        write(case / 'execution.json', {'prepared': plain(prepared), 'intent': plain(intent),
            'dispatch': plain(dispatched), 'observation': plain(observed), 'comparison': plain(comparison), 'result': plain(result)})
        actual = capture(case, 'unknown-established', boundary=boundary)
        proof = assert_unknown(store, actual, name != 'L1')
        write(case / 'unknown-proof.json', proof)
        target = json.loads(next(r['value'] for r in actual['target']['tables']['meta'] if r['key'] == 'state'))
        expected_frames = 1 if name in ('L1', 'U1') else 2
        assert len(target['target']['questions']) == 1 and len(target['target']['frames']) == expected_frames
        assert len(json.loads(action['expected_after']['frames'])) == 2
    except BaseException:
        if store is not None:
            capture(case, 'first-failure', boundary=boundary)
        raise
    finally:
        if keeper is not None:
            boundary.stop()
            store.release(store.target_key(store.registration()['id']), owner_id=claim.owner_id, generation=claim.generation)
            write(case / 'owner-release.json', {'pid': os.getpid(), 'owner': claim.owner_id,
                'generation': claim.generation, 'keeper_alive': boundary.keeper.thread.is_alive(), 'normal_release': True,
                'lifecycle': boundary.snapshot(), 'capture_events': boundary.events})
            released = capture(case, 'after-release')
            write(case / 'released-status.json', store.status())
            assert released['runtime']['tables']['books'][0]['owner'] is None


def recover(case, name):
    from annotation.runtime.storage.native import open_native_state
    from annotation.runtime.recovery import reconcile
    store = open_native_state(case / 'anchor.json', expected_ledger_id='ledger-r8-r3-' + name,
        expected_target_store_id='target-store-r8-r3-' + name)
    before = capture(case, 'before-reconcile')
    initial = assert_unknown(store, before, True)
    assert initial['status']['owner_id'] is None and initial['status']['owner_phase'] == 'RELEASED'
    write(case / 'reopened-status.json', initial['status'])
    try:
        result = reconcile(store, read_fault=FAULTS[name][2], max_attempts=1, call_id='recovery-r12-r2-' + name)
        write(case / 'reconcile-result.json', result)
        after = capture(case, 'after-reconcile')
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
        capture(case, 'reconcile-first-failure')
        raise


if __name__ == '__main__':
    name, phase, output = sys.argv[1:]
    assert name in FAULTS and phase in ('execute', 'recover')
    check_frozen()
    root = Path(output).resolve()
    try:
        (execute if phase == 'execute' else recover)(root / 'cases' / name, name)
    finally:
        write(root / 'imports' / (name + '-' + phase + '.json'), imports())
