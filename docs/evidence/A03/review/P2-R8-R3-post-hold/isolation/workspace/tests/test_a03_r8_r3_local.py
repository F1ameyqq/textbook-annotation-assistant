"""R3 local negative controls via normal native APIs, without target effects."""
import json
import unittest

from test_a03_r8_r3_post_hold import EVIDENCE, setup_pre, write


def refusal(test, expected, operation, records, label):
    try:
        operation()
    except Exception as error:
        code = getattr(error, 'code', None)
        if code is None and getattr(error, 'issues', None):
            code = error.issues[0].get('code')
        record = {'control': label, 'expected_code': expected, 'actual_code': code,
                  'exception_type': type(error).__name__, 'message': str(error)}
        records.append(record)
        print(json.dumps(record, sort_keys=True), flush=True)
        test.assertEqual(code, expected)
    else:
        test.fail('control unexpectedly allowed: ' + label)


class R8R3LocalControls(unittest.TestCase):
    def test_no_hold_owner_and_pending(self):
        from annotation.contracts import artifact_ref, policy_ref
        from annotation.delivery.planner import create_plan
        from annotation.quality.targetcheck import check_target
        from annotation.runtime.storage.common import now
        state = setup_pre(EVIDENCE / 'cases/local-pending')
        store, observer, claim, keeper, bundle, pre_ref, actual, proof, config = state
        reg = store.registration()
        codes = []
        try:
            refusal(self, 'NATIVE_PRE_CONTEXT_INVALID', lambda: store.begin_native_pre(reg['id'],
                owner_id=claim.owner_id, generation=claim.generation, observer=observer, kind='POST_HOLD'), codes, 'POST_HOLD_without_hold')
            refusal(self, 'OWNER_GENERATION_STALE', lambda: store.begin_native_pre(reg['id'],
                owner_id=claim.owner_id, generation=claim.generation + 1, observer=observer, kind='POST_HOLD'), codes, 'stale_generation')
            graph = next(a for a in bundle.artifacts if a.kind == 'QuestionGraph')
            bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref,
                policy_ref(bundle.policies[0]), config, artifact_id='local-r3-target', created_at=now(), bridge_context=bundle.bridge_context)
            bundle = create_plan(bundle, artifact_ref(graph), pre_ref, artifact_ref(bundle.artifacts[-1]), actual.snapshot_ref,
                actual.snapshot_ref, policy_ref(bundle.policies[0]), config, artifact_id='local-r3-plan', created_at=now(), bridge_context=bundle.bridge_context)
            plan = bundle.artifacts[-1]
            store.record_native_plan(reg['id'], bundle, artifact_ref(plan), config, owner_id=claim.owner_id, generation=claim.generation)
            store.accept_plan(reg['id'], artifact_ref(plan), owner_id=claim.owner_id, generation=claim.generation)
            bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
            prepared = observer.prepare_action(bundle, artifact_ref(plan), plan.payload.actions[0].action_id, config,
                current_snapshot_ref=actual.snapshot_ref, asset_root=reg['package_root'], bridge_context=bundle.bridge_context)
            intent = store.commit_intent(prepared, owner_id=claim.owner_id, generation=claim.generation)
            refusal(self, 'BOOK_WRITE_PAUSED', lambda: store.begin_native_pre(reg['id'],
                owner_id=claim.owner_id, generation=claim.generation, observer=observer, kind='POST_HOLD'), codes, 'real_pending_intent')
            with store.connect() as db:
                pending = db.execute("SELECT count(*) FROM intents WHERE state='PENDING'").fetchone()[0]
                permits = db.execute('SELECT count(*) FROM permits').fetchone()[0]
            with observer._connect() as db:
                effects = db.execute('SELECT count(*) FROM effects').fetchone()[0]
            self.assertEqual((pending, permits, effects), (1, 0, 0))
            write(EVIDENCE / 'local-result.json', {'controls': codes, 'pending': pending, 'permits': permits,
                'target_effects': effects, 'intent_ref': intent['intent_ref'], 'SQL_fabrication': False})
        finally:
            keeper.stop()
            store.release(observer.target_key, owner_id=claim.owner_id, generation=claim.generation)


if __name__ == '__main__':
    unittest.main(failfast=True)
