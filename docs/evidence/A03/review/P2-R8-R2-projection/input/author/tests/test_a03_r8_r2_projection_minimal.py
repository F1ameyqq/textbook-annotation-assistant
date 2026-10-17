"""Pure-value projection source checks. No SQL admission or target effects."""
import copy
import json
import unittest

from annotation.runtime.storage import RuntimeStore
from annotation.runtime.storage.common import RuntimeFailure


class R8R2ProjectionSourceTests(unittest.TestCase):
    def test_material_provenance_fallback_and_identity(self):
        plan_ref = {'artifact_id': 'pure-plan-r2', 'revision': 1, 'kind': 'ApplyPlan', 'content_hash': '1' * 64}
        intent_ref = {'artifact_id': 'pure-intent-r2', 'revision': 1, 'kind': 'WriteIntent', 'content_hash': '2' * 64}
        evidence = [{'path': 'pure-fixture/attempt.json', 'sha256': '3' * 64, 'media_type': 'application/json', 'origin': 'SYNTHETIC'}]
        row = {'id': 'pure-action-r2', 'digest': '4' * 64, 'state': 'APPLIED', 'fact': 'pure-value-only'}
        fact = {'plan_ref': plan_ref, 'action_id': row['id'], 'action_digest': row['digest'], 'intent_ref': intent_ref,
            'result': {'action_id': row['id'], 'intent_ref': intent_ref, 'attempt_fact': 'MAY_HAVE_BEEN_ATTEMPTED',
                       'attempt_evidence_refs': evidence}}
        frozen = copy.deepcopy(fact)
        attempt, proof = RuntimeStore._progress_attempt(row, intent_ref, plan_ref, fact)
        self.assertEqual(attempt, 'MAY_HAVE_BEEN_ATTEMPTED')
        self.assertEqual(proof, evidence)
        proof[0]['path'] = 'caller-mutation'
        self.assertEqual(fact, frozen)
        missing = dict(row, state='INTENT', fact=None)
        self.assertEqual(RuntimeStore._progress_attempt(missing, intent_ref, plan_ref, None), ('MAY_HAVE_BEEN_ATTEMPTED', []))
        self.assertEqual(RuntimeStore._progress_attempt(dict(missing, state='RESERVED'), None, plan_ref, None), ('NOT_ATTEMPTED', []))
        foreign = copy.deepcopy(fact)
        foreign['intent_ref']['content_hash'] = '5' * 64
        with self.assertRaises(RuntimeFailure) as refused:
            RuntimeStore._progress_attempt(row, intent_ref, plan_ref, foreign)
        self.assertEqual(refused.exception.code, 'RECOVERY_CHAIN_INVALID')
        print(json.dumps({'with_fact': attempt, 'attempt_evidence_copied': True,
            'no_fact_pending': 'MAY_HAVE_BEEN_ATTEMPTED', 'no_fact_reserved': 'NOT_ATTEMPTED',
            'foreign_intent': 'RECOVERY_CHAIN_INVALID', 'SQL_rows_or_effects_created': 0}))


if __name__ == '__main__':
    unittest.main(failfast=True)
