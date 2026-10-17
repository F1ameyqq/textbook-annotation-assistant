"""Native independent report read and typed POST/Batch production."""
import json
import time

from annotation.contracts import artifact_ref
from annotation.delivery.planner import compare_action_effect
from annotation.quality.targetcheck import append_artifacts, make_artifact, resolve_artifact
from annotation.runtime.storage.common import Handle, canonical, digest, fail, now, plain, reference, unique
from .observation import observe_bounded


def publish_native_quality(store, registration_id, projection=None, *, owner_id=None, generation=None):
    from . import open_observer, claim_current
    reg = store.registration(registration_id)
    key = store.target_key(registration_id)
    borrowed = owner_id is not None or generation is not None
    if borrowed:
        if owner_id is None or generation is None:
            fail('OWNER_GENERATION_STALE', 'report owner_id and generation must be supplied together', 4)
        # Use the existing instance/PID/ACTIVE/owner/generation/expiry guard.
        # Validate before projecting or consuming the durable report read.
        with store.connect() as connection:
            store._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
    plan = store._plan(registration_id)
    projection = projection or store.project_plan(registration_id, plan)
    if projection.get('receipt_ref') is None:
        return Handle(status='NO_COMPLETE_RECEIPT', content_check_status='PENDING', submission_status='NOT_SUBMITTED')
    observer = open_observer(store, registration_id)
    claim = Handle(owner_id=owner_id, generation=generation) if borrowed else claim_current(store, observer, key)
    try:
        with store.transaction() as connection:
            store._lease(connection, reg['book'], claim['owner_id'], claim['generation'], pending_ok=True)
            connection.execute('INSERT INTO native_report_reads VALUES(?,?,1)', (digest(reference(plan)), time.time()))
        actual = observe_bounded(observer, timeout=2)
        if not actual.get('ok') or actual['read_elapsed_seconds'] > 2:
            fail('NATIVE_REPORT_READ_FAILED', 'durable report read consumed; no implicit retry')
        captured, snapshot = store.capture_observation(actual['observation'], observer, registration_id)
        if snapshot is None:
            fail('NATIVE_REPORT_READ_INCOMPLETE')
        with store.transaction() as connection:
            store._lease(connection, reg['book'], claim['owner_id'], claim['generation'], pending_ok=True)
            store._append(connection, registration_id, snapshot)
        bundle = store._validate(store.bundle(registration_id), asset_root=reg['package_root'])
        receipt = resolve_artifact(bundle, projection['receipt_ref'], 'ExecutionReceipt')
        graph = resolve_artifact(bundle, plan['payload']['graph'], 'QuestionGraph')
        bindings, heads, comparisons = [], [], []
        for action, resource in zip(plan['payload']['actions'], receipt.payload.action_fact_refs):
            fact = store.read_resource(plain(resource), registration_id)
            before = store.read_resource(fact['prepared_before'], registration_id)
            comparison = compare_action_effect(action, before, actual['observation'])
            comparisons.append(comparison)
            head = resolve_artifact(bundle, fact['resolution_ref'], 'ReconciliationResult') if fact['resolution_ref'] else None
            if head:
                heads.append(artifact_ref(head))
            bindings.append({'action_id': action['action_id'], 'action_digest': digest(action),
                'intent_ref': fact['intent_ref'], 'fact_ref': plain(resource),
                'resolution_head_ref': artifact_ref(head) if head else None,
                'head_original_receipt_ref': plain(head.payload.original_receipt_ref) if head else None,
                'observed_snapshot_ref': fact['observed_snapshot_ref'], 'effective_outcome': fact['result']['outcome']})
        frame_pass = all(c['effect_match'] == 'MATCH' for c in comparisons)
        payload = {'stage': 'POST_APPLY', 'subject': artifact_ref(receipt), 'graph': plan['payload']['graph'],
            'policy': plan['payload']['policy'], 'receipt': artifact_ref(receipt), 'report_snapshot_ref': reference(snapshot),
            'report_observation': captured['resource'], 'action_bindings': bindings, 'recovery_refs': heads,
            'frame_structure': 'PASS' if frame_pass else 'FAIL', 'content_check_status': 'PENDING',
            'submission_status': 'NOT_SUBMITTED', 'decision': 'HOLD', 'issues': ['CONTENT_REVIEW_PENDING']}
        post = make_artifact('CheckReport', unique('native-post'), graph, payload, list(bundle.artifacts),
            graph.producer.config_version, 'a03-native-independent-report', now(), bridge_context=bundle.bridge_context)
        bundle = append_artifacts(bundle, post, bridge_context=bundle.bridge_context)
        source = resolve_artifact(bundle, graph.payload.source, 'SourceBundle')
        batch_payload = {'source': artifact_ref(source), 'graph': artifact_ref(graph), 'receipt': artifact_ref(receipt),
            'postcheck': artifact_ref(post), 'report_snapshot_ref': reference(snapshot), 'recovery_refs': heads,
            'scope_manifest': list(source.payload.scope_manifest), 'total_expected': len(source.payload.scope_manifest),
            'questions': [{'question_id': q, 'state': 'PENDING'} for q in source.payload.scope_manifest],
            'state': 'CONTENT_PENDING', 'content_check_status': 'PENDING', 'submission_status': 'NOT_SUBMITTED'}
        batch = make_artifact('BatchReport', unique('native-batch'), graph, batch_payload, list(bundle.artifacts),
            graph.producer.config_version, 'a03-native-independent-report', now(), bridge_context=bundle.bridge_context)
        bundle = append_artifacts(bundle, batch, bridge_context=bundle.bridge_context)
        with store.effect_gate(key).acquire(), store.transaction() as connection:
            store._lease(connection, reg['book'], claim['owner_id'], claim['generation'], pending_ok=True)
            store._append(connection, registration_id, post, batch)
        return Handle(postcheck_ref=artifact_ref(post), batch_ref=artifact_ref(batch), frame_structure=payload['frame_structure'],
            content_check_status='PENDING', submission_status='NOT_SUBMITTED')
    finally:
        if not borrowed:
            store.release(key, owner_id=claim['owner_id'], generation=claim['generation'])
