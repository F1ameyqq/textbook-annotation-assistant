"""Bounded C12/H1 driver; inherited assertions, accepted capture, real APIs."""
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples/a03/T2-history'))
from t2_support import BOUNDARIES, accepted, capture, configure, frozen, inherited, write


def execute(root):
    old = inherited()
    from annotation.delivery.mock import compare_action
    from annotation.runtime.storage.common import plain, reference, unique
    case = root / 'cases/H1'
    store = claim = boundary = None
    try:
        store, observer, claim, keeper, plan, config = old.setup_native(case)
        boundary = accepted.LeaseBoundary(keeper)
        BOUNDARIES[str(case.resolve())] = boundary
        reg = store.registration()
        action, = plan['payload']['actions']
        assert action['operation'] == 'CREATE_FRAMES' and len(json.loads(action['expected_after']['frames'])) == 2
        store.accept_plan(reg['id'], reference(plan), owner_id=claim.owner_id, generation=claim.generation)
        context = store.load_book_context(store.target_key(reg['id']), owner_id=claim.owner_id, generation=claim.generation)
        observer.import_book_context(context, authority=store)
        bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
        before = capture(case, 'before-build')
        assert not before['runtime']['tables']['intents'] and not before['target']['tables']['effects']
        prepared = observer.prepare_action(bundle, reference(plan), action['action_id'], config,
            current_snapshot_ref=plan['payload']['snapshot'], asset_root=reg['package_root'], bridge_context=bundle.bridge_context)
        intent = store.commit_intent(prepared, owner_id=claim.owner_id, generation=claim.generation)
        permit = store.issue_first_dispatch(intent['intent_ref'], owner_id=claim.owner_id, generation=claim.generation,
            plan_ref=reference(plan), action_id=action['action_id'], observation_binding=prepared['observation_binding'])
        dispatched = observer.dispatch_action(prepared, committed_intent=intent, dispatch_permit=permit,
            authority=store, effect_fault=None)
        observed = observer.observe_target(store.target_key(reg['id']), observation_id=unique('t2-H1-execution'), read_fault='unavailable')
        comparison = compare_action(prepared['action'], prepared['observation'], observed)
        result = store.commit_action_result(intent, prepared, observed, comparison, owner_id=claim.owner_id, generation=claim.generation)
        write(case / 'execution.json', {'prepared': plain(prepared), 'intent': plain(intent), 'dispatch': plain(dispatched),
            'observation': plain(observed), 'comparison': plain(comparison), 'result': plain(result)})
        values = capture(case, 'unknown-established')
        proof = old.assert_unknown(store, values, True)
        write(case / 'unknown-proof.json', proof)
        target = json.loads(next(r['value'] for r in values['target']['tables']['meta'] if r['key'] == 'state'))
        assert len(target['target']['questions']) == 1 and len(target['target']['frames']) == 2
    except BaseException:
        write(root / 'H1-execute-first-error.txt', traceback.format_exc().encode('utf-8'))
        if store is not None:
            try:
                capture(case, 'first-failure')
            except BaseException:
                write(root / 'H1-execute-capture-error.txt', traceback.format_exc().encode('utf-8'))
        raise
    finally:
        if boundary is not None:
            boundary.stop()
            store.release(store.target_key(store.registration()['id']), owner_id=claim.owner_id, generation=claim.generation)
            del BOUNDARIES[str(case.resolve())]
            write(case / 'owner-release.json', {'pid': os.getpid(), 'owner': claim.owner_id, 'generation': claim.generation,
                'normal_release': True, 'current_boundary_stopped': True, 'keepers': boundary.snapshot()})
            values = capture(case, 'after-release')
            assert values['runtime']['tables']['books'][0]['owner'] is None


def open_case(case):
    configure()
    from annotation.runtime.storage.native import open_native_state
    return open_native_state(case / 'anchor.json', expected_ledger_id='ledger-r8-r3-H1',
                             expected_target_store_id='target-store-r8-r3-H1')


def recover(root):
    old = inherited()
    from annotation.runtime.recovery import reconcile
    case = root / 'cases/H1'
    store = open_case(case)
    before = capture(case, 'before-reconcile')
    initial = old.assert_unknown(store, before, True)
    assert initial['status']['owner_id'] is None and initial['status']['owner_phase'] == 'RELEASED'
    write(case / 'reopened-status.json', initial['status'])
    try:
        result = reconcile(store, read_fault=None, max_attempts=1, call_id='recovery-a03-t2-H1')
        write(case / 'reconcile-result.json', result)
        after = capture(case, 'after-reconcile')
        assert result['attempt_count'] == 1 and result['pending_count'] == 0 and not result['paused']
        resolution, = result['resolutions']
        assert resolution['status'] == 'RESOLVED_APPLIED' and resolution['classification'] == 'MATCH'
        assert after['runtime']['tables']['books'][0]['owner'] is None
        assert before['target']['tables']['effects'] == after['target']['tables']['effects']
        assert not after['runtime']['tables']['native_report_reads']
        write(case / 'reconcile-release.json', {'pid': os.getpid(), 'normal_reconcile_return': True,
            'owner': after['runtime']['tables']['books'][0], 'new_target_effects': 0})
    except BaseException:
        write(root / 'H1-recover-first-error.txt', traceback.format_exc().encode('utf-8'))
        try:
            capture(case, 'reconcile-first-failure')
        except BaseException:
            write(root / 'H1-recover-capture-error.txt', traceback.format_exc().encode('utf-8'))
        raise


def report(root):
    old = inherited()
    case = root / 'cases/H1'
    store = open_case(case)
    before = json.loads((case / 'captures/before-reconcile/SQL.json').read_bytes())
    after = json.loads((case / 'captures/after-reconcile/SQL.json').read_bytes())
    initial = json.loads((case / 'unknown-proof.json').read_bytes())
    result = json.loads((case / 'reconcile-result.json').read_bytes())
    try:
        # The original exact assertions include history validation and the sole explicit publish_quality call.
        old.history_report(store, case, before, after, initial, result)
    except BaseException:
        write(root / 'H1-report-first-error.txt', traceback.format_exc().encode('utf-8'))
        try:
            capture(case, 'report-first-failure')
        except BaseException:
            write(root / 'H1-report-capture-error.txt', traceback.format_exc().encode('utf-8'))
        raise


if __name__ == '__main__':
    phase, output = sys.argv[1:]
    frozen()
    configure()
    root = Path(output).resolve()
    if phase == 'contracts':
        inherited().contracts(root)
    else:
        {'execute': execute, 'recover': recover, 'report': report}[phase](root)
