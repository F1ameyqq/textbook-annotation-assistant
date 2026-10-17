"""Compare saved case identities and the frozen progress branch; no product run."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R1-producer'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    raw = (OUT / 'database-readback.json').read_bytes()
    saved = json.loads(raw)
    action = saved['runtime']['actions'][0]
    intent = saved['runtime']['intents'][0]
    plan = saved['runtime']['plans'][0]
    fact = saved['late_material_fact']['data']
    # This branch evaluation is an explanation of stored values and source,
    # not a reconstructed/resealed progress Artifact or product execution.
    inferred_attempt = ('NOT_ATTEMPTED' if not action['intent'] else
        'MAY_HAVE_BEEN_ATTEMPTED' if action['state'] in ('INTENT', 'UNKNOWN') else 'ATTEMPTED')
    projected = {'plan_ref': json.loads(plan['ref']), 'action_id': action['id'],
        'intent_ref': json.loads(intent['ref']), 'attempt_fact': inferred_attempt}
    material = {'plan_ref': fact['plan_ref'], 'action_id': fact['action_id'],
        'intent_ref': fact['intent_ref'], 'attempt_fact': fact['result']['attempt_fact']}
    differs = {key: projected[key] != material[key] for key in projected}
    if differs != {'plan_ref': False, 'action_id': False, 'intent_ref': False, 'attempt_fact': True}:
        raise RuntimeError('saved case does not isolate the stated mismatch')
    storage_path = ROOT / 'src/annotation/runtime/storage/__init__.py'
    native_path = ROOT / 'src/annotation/runtime/storage/native.py'
    contract_path = ROOT / 'src/annotation/contracts/recovery.py'
    snapshot = OUT / 'runs/N1/product-snapshot/src/annotation/runtime/storage/__init__.py'
    if sha(storage_path.read_bytes()) != sha(snapshot.read_bytes()):
        raise RuntimeError('explanatory source differs from actually executed snapshot')
    if 'else "ATTEMPTED"' not in storage_path.read_text(encoding='utf-8').splitlines()[798]:
        raise RuntimeError('frozen branch line mismatch')
    result = {'status': 'CONFIRMED_SAVED_CASE_IDENTITY_AND_STATIC_BRANCH',
        'input_readback_sha256': sha(raw), 'source_sha256': {
            'runtime/storage/__init__.py': sha(storage_path.read_bytes()),
            'runtime/storage/native.py': sha(native_path.read_bytes()),
            'contracts/recovery.py': sha(contract_path.read_bytes())},
        'actual_trace': 'runs/N1/stderr.txt', 'actual_guard_line': 'contracts/recovery.py:663',
        'projection_branch_line': 'runtime/storage/__init__.py:799',
        'late_fact_line': 'runtime/storage/native.py:273',
        'action_state_update_lines': 'runtime/storage/native.py:283-284',
        'database_plan_id': plan['id'], 'database_intent_id': intent['id'], 'database_action_state': action['state'],
        'action_row_intent_equals_intent_row_id': action['intent'] == intent['id'],
        'action_row_plan_equals_plan_row_id': action['plan'] == plan['id'],
        'late_material_fact_values': material, 'failed_projection_values_from_saved_row_and_frozen_branch': projected,
        'guard_inequality_terms': differs, 'failing_progress_persisted': False,
        'interpretation': 'Rejected progress is not a durable Artifact; ATTEMPTED is uniquely inferred from saved APPLIED row and executed frozen source. The raw actual trace fails at the same four-term guard.',
        'persisted_progress': saved['current_bundle']['progress'], 'product_tests_executed': 0}
    with (OUT / 'attempt-field-binding.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'confirmed_case': True, 'only_mismatched_term': 'attempt_fact',
        'material': material['attempt_fact'], 'frozen_branch_inference': inferred_attempt, 'product_execution': False}))


if __name__ == '__main__':
    main()
