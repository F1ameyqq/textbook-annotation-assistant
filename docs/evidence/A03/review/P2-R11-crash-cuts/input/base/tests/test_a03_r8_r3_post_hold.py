"""Bounded R8 groups. Drivers arrange inputs/faults; product owns business rows."""
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/a03/P2-R8-R3-post-hold'
BASE_EVIDENCE = ROOT / 'docs/evidence/A03/execution/P2-R8-R3-post-hold'
EVIDENCE = BASE_EVIDENCE / 'validation' / os.environ.get('A03_R8_R3_RUN_ID', 'native-r3-01')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def open_case(path):
    from annotation.runtime.storage.native import open_native_state
    return open_native_state(path / 'anchor.json', expected_ledger_id='ledger-r8-r3-' + path.name,
        expected_target_store_id='target-store-r8-r3-' + path.name)


def setup_pre(path):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.delivery.mock.persistent import PersistentMockSession
    from annotation.quality.targetcheck import SimulationConfig
    from annotation.runtime.storage.native import init_native_state
    from annotation.runtime.recovery.lease import LeaseKeeper
    from annotation.quality.synthetic_precheck import produce_a03_pre_run, admit_a03_pre_run
    from annotation.runtime.storage.common import now
    path.mkdir(parents=True, exist_ok=False)
    source_root = path / 'input'
    shutil.copytree(FIXTURE, source_root)
    raw = json.loads((source_root / 'initial.json').read_bytes())
    store = init_native_state(path / 'anchor.json', path / 'runtime',
        expected_ledger_id='ledger-r8-r3-' + path.name, expected_target_store_id='target-store-r8-r3-' + path.name)
    context = store.bridge_for(raw, source_root)
    from annotation.contracts import validate_bundle
    bundle = validate_bundle(raw, asset_root=source_root, bridge_context=context)
    source, evidence, graph, snapshot = bundle.artifacts
    target_key = {'platform_namespace': 'a03-r8-r3-native', 'target_id': snapshot.payload.target_id, 'book_id': source.book_id}
    config = SimulationConfig(source.book_id, snapshot.payload.target_id, source.scope_id, {'directory-r8-r3': 'platform-r8-r3'})
    reg = store.register_book(bundle, target_key=target_key, target_dir=path / 'target', target_session_id='target-session-r8-r3-' + path.name,
        source_ref=artifact_ref(source), asset_root=source_root, config=vars(config), registration_id='registration-r8-r3-' + path.name)
    registration = store.registration(reg.registration_id)
    package_root = Path(reg.package_root)
    context = store.bridge_for(store.bundle(reg.registration_id), package_root)
    observer = PersistentMockSession.create(path / 'target', bundle, artifact_ref(snapshot), platform_namespace='a03-r8-r3-native',
        source_ref=artifact_ref(source), asset_root=package_root, expected_store_id=store.target_store_id,
        target_session_id=registration['session'], bridge_context=context)
    claim = store.claim(target_key, observer=observer)
    keeper = LeaseKeeper(store, target_key, claim.owner_id, claim.generation).start()
    try:
        actual = store.begin_native_pre(reg.registration_id, owner_id=claim.owner_id, generation=claim.generation, observer=observer)
        bundle, pre_ref = produce_a03_pre_run(actual.bundle, artifact_ref(source), artifact_ref(evidence), artifact_ref(graph), policy_ref(bundle.policies[0]),
            bridge_context=actual.bundle.bridge_context, registered_run_handle=actual.handle,
            actual_snapshot_ref=actual.snapshot_ref, actual_observation=actual.observation, asset_root=package_root,
            artifact_id='pre-r8-r3-' + path.name, created_at=now())
        admitted = admit_a03_pre_run(bundle, pre_ref, bridge_context=bundle.bridge_context,
            registered_run_handle=actual.handle, actual_snapshot_ref=actual.snapshot_ref, asset_root=package_root)
        return store, observer, claim, keeper, bundle, pre_ref, actual, admitted, config
    except BaseException:
        keeper.stop()
        raise


def n1_child(path):
    from annotation.contracts import artifact_ref, policy_ref
    from annotation.quality.targetcheck import check_target
    from annotation.delivery.planner import create_plan
    from annotation.runtime.storage.common import now
    from annotation.runtime.recovery import run_plan
    store, observer, claim, keeper, bundle, pre_ref, actual, admitted, config = setup_pre(path)
    reg = store.registration()
    graph = next(a for a in bundle.artifacts if a.kind == 'QuestionGraph')
    bundle = check_target(bundle, artifact_ref(graph), actual.snapshot_ref, actual.snapshot_ref, policy_ref(bundle.policies[0]), config,
        artifact_id='target-r8-r3-n1', created_at=now(), bridge_context=bundle.bridge_context)
    target_ref = artifact_ref(bundle.artifacts[-1])
    bundle = create_plan(bundle, artifact_ref(graph), pre_ref, target_ref, actual.snapshot_ref, actual.snapshot_ref,
        policy_ref(bundle.policies[0]), config, artifact_id='plan-r8-r3-n1', created_at=now(), bridge_context=bundle.bridge_context)
    plan = bundle.artifacts[-1]
    if len(plan.payload.actions) != 1 or plan.payload.actions[0].operation != 'CREATE_FRAMES':
        raise AssertionError('actual planner did not generate singleton CREATE_FRAMES')
    store.record_native_plan(reg['id'], bundle, artifact_ref(plan), config, owner_id=claim.owner_id, generation=claim.generation)
    write(path / 'before-dispatch.json', {'registration_id': reg['id'], 'pre_ref': pre_ref, 'plan_ref': artifact_ref(plan),
        'snapshot_ref': actual.snapshot_ref, 'run_id': admitted.run_id, 'product_import': __import__('annotation').__path__[0]})
    run_plan(store, reg['id'], owner_id=claim.owner_id, generation=claim.generation, config=vars(config),
        fault={'point': 'after_effect', 'mode': 'barrier', 'marker': str(path / 'effect-committed.barrier.json'), 'release': str(path / 'release.barrier')},
        effect_fault='after_effect_exit')
    raise AssertionError('expected actual child exit after effect')


class R8R3NativeBridgeTests(unittest.TestCase):
    def test_N1(self):
        from annotation.runtime.recovery import reconcile, publish_quality
        from annotation.runtime.storage.common import reference
        case = EVIDENCE / 'cases/N1'
        audit = EVIDENCE / 'processes/n1-child'
        audit.mkdir(parents=True, exist_ok=False)
        argv = [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()), '--n1-child', str(case)]
        write(audit / 'preregistered.json', {'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 45,
            'script_sha256': sha(Path(__file__).read_bytes()), 'fixture_sha256': sha((FIXTURE / 'initial.json').read_bytes()),
            'input_index_sha256': sha((BASE_EVIDENCE / 'inputs.json').read_bytes())})
        with (audit / 'script-snapshot.py').open('xb') as stream:
            stream.write(Path(__file__).read_bytes())
        with (audit / 'stdout.txt').open('xb') as stdout, (audit / 'stderr.txt').open('xb') as stderr:
            process = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr)
            write(audit / 'started.json', {'pid': process.pid, 'parent_pid': os.getpid()})
            started = time.monotonic()
            released = False
            while process.poll() is None and time.monotonic() - started < 45:
                if (case / 'effect-committed.barrier.json').is_file() and not released:
                    # Observe the committed independent target while the child is
                    # held after SQLite commit and before deliberate process exit.
                    with sqlite3.connect((case / 'target/target.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
                        self.assertEqual(db.execute('SELECT count(*) FROM effects').fetchone()[0], 1)
                    (case / 'release.barrier').write_bytes(b'release after independent effect count\n')
                    released = True
                time.sleep(.01)
            timed_out = process.poll() is None
            if timed_out:
                process.kill()
            code = process.wait(timeout=5)
        write(audit / 'completed.json', {'pid': process.pid, 'exit_code': code, 'alive': process.poll() is None,
            'timed_out': timed_out, 'barrier_released': released, 'stdout_sha256': sha((audit / 'stdout.txt').read_bytes()),
            'stderr_sha256': sha((audit / 'stderr.txt').read_bytes())})
        self.assertEqual(code, 87, (audit / 'stderr.txt').read_text(encoding='utf-8'))
        self.assertTrue(released)
        store = open_case(case)
        reg = store.registration()
        pending = store.status(reg['id'])
        self.assertEqual(pending['pending_count'], 1)
        with store.connect() as db:
            self.assertIsNone(db.execute('SELECT receipt FROM intents').fetchone()[0])
        projection = store.project_plan(reg['id'])
        self.assertIsNone(projection['receipt_ref'])
        self.assertEqual(projection['actions'][0]['effective_outcome'], 'UNKNOWN')
        restored = reconcile(store, reg['id'], call_id='call-r8-r3-n1', max_attempts=1)
        self.assertEqual(restored['resolutions'][0]['status'], 'RESOLVED_APPLIED')
        bundle = store.bundle(reg['id'])
        heads = [a for a in bundle['artifacts'] if a['kind'] == 'ReconciliationResult']
        self.assertEqual(len(heads), 1)
        self.assertIsNone(heads[0]['payload']['original_receipt_ref'])
        receipts = [a for a in bundle['artifacts'] if a['kind'] == 'ExecutionReceipt']
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]['payload']['results'][0]['intent_ref'], heads[0]['payload']['intent_ref'])
        formal_receipt_ref = reference(receipts[0])
        with store.connect() as db:
            formal_refs = [json.loads(row[0]) for row in db.execute('SELECT ref FROM artifacts')]
            intent_receipt = json.loads(db.execute('SELECT receipt FROM intents').fetchone()[0])
            material_resource = json.loads(db.execute('SELECT fact FROM actions').fetchone()[0])
        self.assertIn(formal_receipt_ref, formal_refs)
        self.assertEqual(intent_receipt, formal_receipt_ref)
        material = store.read_resource(material_resource, reg['id'])
        material_progress = next(a for a in reversed(bundle['artifacts']) if a['kind'] == 'ExecutionProgress')['payload']
        projected = material_progress['actions'][0]
        self.assertEqual(material_progress['plan_ref'], material['plan_ref'])
        self.assertEqual(projected['action_id'], material['action_id'])
        self.assertEqual(projected['intent_ref'], material['intent_ref'])
        self.assertEqual(projected['attempt_fact'], material['result']['attempt_fact'])
        self.assertEqual(projected['attempt_evidence_refs'], material['result']['attempt_evidence_refs'])
        self.assertEqual(projected['result_fact'], material_resource)
        self.assertEqual(projected['receipt_ref'], formal_receipt_ref)
        self.assertEqual(projected['attempt_fact'], 'MAY_HAVE_BEEN_ATTEMPTED')
        report = publish_quality(store, reg['id'])
        self.assertEqual(report['content_check_status'], 'PENDING')
        self.assertEqual(report['submission_status'], 'NOT_SUBMITTED')
        current = store.bundle(reg['id'])
        with store.connect() as db:
            formal_refs = [json.loads(row[0]) for row in db.execute('SELECT ref FROM artifacts')]
        for report_ref in (report['postcheck_ref'], report['batch_ref']):
            self.assertIn(report_ref, formal_refs)
            self.assertTrue(any(reference(a) == report_ref for a in current['artifacts']))
        self.assertTrue(any(reference(a) == projection['progress_ref'] for a in current['artifacts']))
        self.assertIsNone(next(a for a in current['artifacts'] if a['kind'] == 'ReconciliationResult')['payload']['original_receipt_ref'])
        with sqlite3.connect((case / 'target/target.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
            effect_count = db.execute('SELECT count(*) FROM effects').fetchone()[0]
        self.assertEqual(effect_count, 1)
        write(EVIDENCE / 'N1-result.json', {'status': 'REVIEW', 'effect_count': effect_count,
            'original_receipt_ref': None, 'terminal_head': reference(heads[0]), 'quality': report,
            'formal_receipt_ref': formal_receipt_ref, 'SQL_artifacts_current_bundle_intent_receipt_agree': True,
            'material_progress_plan_action_intent_attempt_agree': True, 'attempt_evidence_matches_original_fact': True,
            'UNKNOWN_retained': any(a['kind'] == 'ExecutionProgress' and any(r['effective_outcome'] == 'UNKNOWN' for r in a['payload']['actions']) for a in store.bundle(reg['id'])['artifacts'])})

    def test_N2(self):
        from annotation.runtime.recovery import open_observer, claim_current
        from annotation.runtime.recovery.lease import LeaseKeeper
        from annotation.quality.synthetic_precheck import produce_a03_pre_run, admit_a03_pre_run
        from annotation.contracts import artifact_ref, policy_ref
        from annotation.runtime.storage.common import now, reference
        from test_a03_r8_r3_local import refusal
        case = EVIDENCE / 'cases/N1'
        store = open_case(case)
        reg = store.registration()
        observer = open_observer(store, reg['id'])
        key = store.target_key(reg['id'])
        observer.synthetic_external_add_directory('synthetic-external-N2')
        claim = claim_current(store, observer, key)
        keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()
        records = []
        produced = []
        try:
            hold = store.detect_target_drift(key, owner_id=claim.owner_id, generation=claim.generation, observer=observer)
            with store.connect() as db:
                self.assertIsNotNone(db.execute('SELECT hold FROM books').fetchone()[0])
            old = json.loads((case / 'before-dispatch.json').read_bytes())
            refusal(self, 'NATIVE_ADMITTED_RUN_REQUIRED', lambda: store.native_registry._dispatch('assert_pre',
                store.bridge_for(store.bundle(reg['id']), reg['package_root']), pre_ref=old['pre_ref'],
                snapshot_ref=old['snapshot_ref']), records, 'old_INITIAL_after_registry_reopen')
            refusal(self, 'TARGET_DRIFT_HOLD', lambda: store.begin_native_pre(reg['id'], owner_id=claim.owner_id,
                generation=claim.generation, observer=observer, kind='INITIAL'), records, 'INITIAL_while_held')
            refusal(self, 'TARGET_DRIFT_HOLD', lambda: store.accept_plan(reg['id'], old['plan_ref'],
                owner_id=claim.owner_id, generation=claim.generation), records, 'ordinary_plan_accept_while_held')

            def produce_post(identity):
                actual = store.begin_native_pre(reg['id'], owner_id=claim.owner_id, generation=claim.generation, observer=observer, kind='POST_HOLD')
                source = next(a for a in actual.bundle.artifacts if a.kind == 'SourceBundle')
                evidence = next(a for a in actual.bundle.artifacts if a.kind == 'EvidenceBundle')
                graph = next(a for a in actual.bundle.artifacts if a.kind == 'QuestionGraph')
                bundle, pre_ref = produce_a03_pre_run(actual.bundle, artifact_ref(source), artifact_ref(evidence), artifact_ref(graph), policy_ref(actual.bundle.policies[0]),
                    bridge_context=actual.bundle.bridge_context, registered_run_handle=actual.handle, actual_snapshot_ref=actual.snapshot_ref,
                    actual_observation=actual.observation, asset_root=reg['package_root'], artifact_id=identity, created_at=now())
                proof = admit_a03_pre_run(bundle, pre_ref, bridge_context=bundle.bridge_context,
                    registered_run_handle=actual.handle, actual_snapshot_ref=actual.snapshot_ref, asset_root=reg['package_root'])
                self.assertEqual(proof.pre_ref, pre_ref)
                with store.connect() as db:
                    row = dict(db.execute('SELECT * FROM native_pre_runs WHERE id=?', (proof.run_id,)).fetchone())
                    book = dict(db.execute('SELECT * FROM books WHERE key=?', (reg['book'],)).fetchone())
                binding = json.loads(row['binding'])
                self.assertEqual(row['status'], 'ADMITTED')
                self.assertEqual(binding['context']['hold_id'], hold['hold_id'])
                self.assertEqual(binding['context']['hold_head'], {'sequence': row['head_sequence'], 'hash': row['head_hash']})
                self.assertEqual((book['head_sequence'], book['head_hash']), (row['head_sequence'], row['head_hash']))
                self.assertEqual(json.loads(row['snapshot']), actual.snapshot_ref)
                hold_body = store.read_resource(binding['context']['hold_ref'], reg['id'])
                self.assertEqual(hold_body['payload']['hold_id'], hold['hold_id'])
                produced.append({'run_id': proof.run_id, 'pre_ref': pre_ref, 'snapshot_ref': actual.snapshot_ref,
                    'hold_context': binding['context'], 'owner_id': claim.owner_id, 'generation': claim.generation,
                    'created': row['created'], 'observation_id': actual.observation['observation_id'],
                    'read_sequence': actual.observation['read_sequence']})
                print(json.dumps({'POST_HOLD_admitted': produced[-1]}, sort_keys=True), flush=True)
                return bundle, pre_ref, actual, proof, row

            first = produce_post('pre-r8-r3-post-hold-1')
            keeper.stop()
            store.release(key, owner_id=claim.owner_id, generation=claim.generation)
            claim = claim_current(store, observer, key)
            keeper = LeaseKeeper(store, key, claim.owner_id, claim.generation).start()
            refusal(self, 'OWNER_GENERATION_STALE', lambda: store.native_registry._dispatch('assert_pre',
                first[0].bridge_context, pre_ref=first[1], snapshot_ref=first[2].snapshot_ref), records, 'old_hold_run_after_normal_owner_head_progress')
            second = produce_post('pre-r8-r3-post-hold-2')
            self.assertGreater(second[2].observation['read_sequence'], first[2].observation['read_sequence'])
            refusal(self, 'TARGET_DRIFT_HOLD', lambda: store.accept_plan(reg['id'], old['plan_ref'],
                owner_id=claim.owner_id, generation=claim.generation), records, 'ordinary_write_still_blocked_after_POST_HOLD_admission')
            deadline = second[4]['created'] + 60.1
            print(json.dumps({'real_deadline_wait_until_epoch': deadline, 'clock_or_database_override': False}), flush=True)
            while time.time() < deadline:
                keeper.check()
                time.sleep(min(.25, max(.01, deadline - time.time())))
            refusal(self, 'NATIVE_PRE_DEADLINE_EXCEEDED', lambda: store.native_registry._dispatch('assert_pre',
                second[0].bridge_context, pre_ref=second[1], snapshot_ref=second[2].snapshot_ref), records, 'expired_current_hold_proof')
            with store.connect() as db:
                final_hold = db.execute('SELECT hold FROM books WHERE key=?', (reg['book'],)).fetchone()[0]
                permits = db.execute('SELECT count(*) FROM permits').fetchone()[0]
            with observer._connect() as db:
                effects = db.execute('SELECT count(*) FROM effects').fetchone()[0]
            self.assertEqual(final_hold, hold['hold_id'])
            self.assertEqual((permits, effects), (1, 1))
            write(EVIDENCE / 'N2-result.json', {'status': 'REVIEW', 'same_current_hold_preserved': final_hold,
                'POST_HOLD_runs': produced, 'refusals': records, 'permit_count': permits, 'target_effect_count': effects,
                'hold_clear_calls': 0, 'old_hold_control': 'same hold; old owner/generation and exact whole-book head after normal release/claim',
                'real_expiry_wait': True, 'clock_or_SQL_fabrication': False})
        finally:
            keeper.stop()
            store.release(key, owner_id=claim.owner_id, generation=claim.generation)

    def test_N3(self):
        from annotation.contracts.a03_native import NativeSchemas
        from annotation.contracts.recovery import _node
        from annotation.quality.synthetic_precheck import compare_synthetic_inputs, CHECKS
        from annotation.runtime.storage.common import digest, reference
        original = json.loads((FIXTURE / 'initial.json').read_bytes())
        results = []
        for index, check in enumerate(CHECKS):
            folder = EVIDENCE / 'cases' / ('N3-' + check)
            shutil.copytree(FIXTURE, folder)
            data = copy.deepcopy(original)
            source, evidence, graph, snapshot = data['artifacts']
            if check == 'source_integrity':
                path = folder / 'assets/page.pgm'
                raw = path.read_bytes().replace(b'255 255 255', b'254 255 255', 1)
                path.write_bytes(raw)
                new_sha = sha(raw)
                def images(value):
                    if isinstance(value, dict):
                        if value.get('asset_id') == 'page-r8-r3' and 'sha256' in value:
                            value['sha256'] = new_sha
                        for child in value.values():
                            images(child)
                    elif isinstance(value, list):
                        for child in value:
                            images(child)
                images(data)
            elif check == 'structure':
                evidence['payload']['regions'][0]['box']['bbox'][0] = 5
            elif check == 'answer_matching':
                graph['payload']['answer_relations'][0]['candidate_fragment_ids'].append('fragment-stem-r8-r3')
            elif check == 'coverage':
                clue = copy.deepcopy(evidence['payload']['coverage_clues'][0])
                clue['clue_id'] = 'clue-r8-r3-extra'
                evidence['payload']['coverage_clues'].append(clue)
            else:
                data['policies'][0]['role_mapping']['option'] = 'Q'
            policy = data['policies'][0]
            policy['content_hash'] = digest({k: v for k, v in policy.items() if k != 'content_hash'})
            policy_ref = {k: policy[k] for k in ('policy_id', 'revision', 'content_hash')}
            rewritten = {}
            def refs(value):
                if isinstance(value, dict):
                    if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                        return reference(rewritten[value['kind']])
                    return {k: refs(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [refs(v) for v in value]
                return value
            for artifact in data['artifacts']:
                artifact.update(refs(artifact))
                artifact['producer']['policy_versions'] = [policy_ref]
                artifact['content_hash'] = digest({k: v for k, v in artifact.items() if k != 'content_hash'})
                rewritten[artifact['kind']] = artifact
            NativeSchemas().check(data)
            actual = compare_synthetic_inputs(_node(data), reference(data['artifacts'][0]), reference(data['artifacts'][1]), reference(data['artifacts'][2]), policy_ref, asset_root=folder)
            self.assertEqual(actual[check], 'FAIL')
            self.assertEqual([k for k, v in actual.items() if v == 'FAIL'], [check])
            results.append({'control': check, 'comparison': actual, 'admitted': False, 'effects': 0})
        write(EVIDENCE / 'N3-result.json', results)

    def test_N4(self):
        from annotation.quality.synthetic_precheck import admit_a03_pre_run
        from test_a03_r8_r3_local import refusal
        states = [setup_pre(EVIDENCE / 'cases' / name) for name in ('N4-a', 'N4-b')]
        codes = []
        try:
            a, b = states
            store, observer, claim, keeper, bundle, pre_ref, actual, proof, config = a
            for label, handle in (('missing_run', {}), ('serialized_run', {'run_id': proof.run_id}), ('foreign_run', b[6].handle)):
                refusal(self, 'NATIVE_RUN_HANDLE_REQUIRED', lambda handle=handle: admit_a03_pre_run(bundle, pre_ref,
                    bridge_context=bundle.bridge_context, registered_run_handle=handle,
                    actual_snapshot_ref=actual.snapshot_ref, asset_root=observer.asset_root), codes, label)
            refusal(self, 'NATIVE_PRE_OBSERVATION_FOREIGN', lambda: store.native_registry._dispatch('producer_binding',
                bundle.bridge_context, handle=actual.handle, snapshot_ref=actual.snapshot_ref, observation=b[6].observation), codes, 'foreign_observation')
            for state in states:
                with state[0].connect() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM permits').fetchone()[0], 0)
                with state[1]._connect() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM effects').fetchone()[0], 0)
            write(EVIDENCE / 'N4-result.json', {'refusals': codes, 'permit_count': 0, 'effect_count': 0})
        finally:
            for store, observer, claim, keeper, *_ in states:
                keeper.stop()
                store.release(observer.target_key, owner_id=claim.owner_id, generation=claim.generation)

    def test_N5(self):
        from annotation.contracts import validate_bundle
        from annotation.contracts.a03_native import BridgeContext, require_context, select_native_codec
        from annotation.contracts.a03_bridge import select_static_codec, open_static_context, validate_static_bundle
        from test_a03_r8_r3_local import refusal
        codes = []
        initial = json.loads((FIXTURE / 'initial.json').read_bytes())
        refusal(self, 'NATIVE_CONTEXT_REQUIRED', lambda: validate_bundle(initial, asset_root=FIXTURE), codes, 'native_without_context')
        selection = select_native_codec()
        refusal(self, 'NATIVE_CONTEXT_REQUIRED', lambda: require_context(BridgeContext(replace(selection, api_sha256='0' * 64), FIXTURE, sha(b''), (), {}, '')), codes, 'unknown_pins_unissued_context')
        refusal(self, 'NATIVE_CONTEXT_REQUIRED', lambda: require_context(select_static_codec()), codes, 'R7_selection_is_not_native_authority')
        static_root = ROOT / 'examples/a03/P2-R2-proposal/candidate-final'
        static = validate_static_bundle(json.loads((static_root / 'converted-initial.json').read_bytes()), context=open_static_context(asset_root=static_root))
        refusal(self, 'NATIVE_CONTEXT_REQUIRED', lambda: require_context(static), codes, 'R7_validated_static_object_is_not_native_authority')
        legacy_raw = (static_root / 'original/new-authored-initial-a.json').read_bytes()
        legacy_history = json.loads(legacy_raw)
        self.assertEqual(legacy_history['format_version'], 'a03-exchange-1')
        refusal(self, 'NATIVE_CONTEXT_REQUIRED', lambda: require_context(legacy_history), codes, 'actual_1_1_historical_JSON_is_not_native_authority')
        for version in ('a03-exchange-1', 'a03-exchange-3-proposal'):
            old = {'format_version': version, 'role': 'STATIC_INSPECTION'}
            refusal(self, 'NATIVE_CONTEXT_REQUIRED', lambda old=old: require_context(old), codes, 'old_role_descriptor_' + version)
        write(EVIDENCE / 'N5-result.json', {'refusals': codes, 'legacy_1_1_read_sha256': sha(legacy_raw),
            'R7_static_validated': True, 'legacy_1_1_archive_validator_acceptance_claim': False})

    def test_N6(self):
        from annotation.contracts.recovery import _node
        from annotation.delivery.planner import verify_generated_plan
        from annotation.runtime.recovery import configuration
        from test_a03_r8_r3_local import refusal
        codes = []
        store = open_case(EVIDENCE / 'cases/N1')
        reg = store.registration()
        bundle = store._validate(store.bundle(reg['id']), asset_root=reg['package_root'])
        plan = next(a for a in bundle.artifacts if a.kind == 'ApplyPlan')
        verify_generated_plan(bundle, plan, plan.payload.snapshot, configuration(json.loads(reg['config'])), bridge_context=bundle.bridge_context)
        self.assertTrue(any(a.kind == 'ExecutionProgress' and any(r.effective_outcome == 'UNKNOWN' for r in a.payload.actions) for a in bundle.artifacts))
        with store.connect() as db:
            anchor = db.execute('SELECT * FROM native_creation_anchors').fetchone()
        missing = json.loads(Path(anchor['input_path']).read_bytes())
        missing['evidence'] = missing['evidence'][:-1]
        refusal(self, 'EVIDENCE_ID_MISSING', lambda: store.native_registry.context(missing, reg['package_root'], historical=True), codes, 'anchor_missing_formal_PRE_run_evidence')
        write(EVIDENCE / 'N6-result.json', {'same_plan_recomputed_from_creation_anchor': True,
            'full_current_history_keeps_UNKNOWN': True, 'refusals': codes})

    def test_N7(self):
        from annotation.runtime.storage import open_state
        from annotation.runtime.storage.native import init_native_state, open_native_state
        from annotation.delivery.mock.persistent import PersistentMockSession
        from annotation.runtime.storage.native_target import NativeTargetSession
        from annotation.runtime.recovery import open_observer
        from test_a03_r8_r3_local import refusal
        codes = []
        path = EVIDENCE / 'cases/N7'
        path.mkdir(parents=True, exist_ok=False)
        store = init_native_state(path / 'anchor.json', path / 'runtime', expected_ledger_id='ledger-N7', expected_target_store_id='store-N7')
        reopened = open_native_state(path / 'anchor.json', expected_ledger_id='ledger-N7', expected_target_store_id='store-N7')
        self.assertEqual(store.anchor, reopened.anchor)
        refusal(self, 'STATE_DIRECTORY_IDENTITY_MISMATCH', lambda: open_state(path / 'anchor.json',
            expected_ledger_id='ledger-N7', expected_target_store_id='store-N7'), codes, 'old_runtime_entry_rejects_native_database')
        n1_store = open_case(EVIDENCE / 'cases/N1')
        n1_reg = n1_store.registration()
        target = open_observer(n1_store, n1_reg['id'])
        self.assertEqual(target.native_metadata(), target.descriptor['native_adoption'])
        refusal(self, 'TARGET_STORE_VERSION_UNSUPPORTED', lambda: PersistentMockSession.open(n1_reg['target_dir'],
            expected_store_id=n1_store.target_store_id, expected_target_session_id=n1_reg['session'],
            expected_target_key=n1_store.target_key(n1_reg['id']), expected_scope_id=n1_reg['scope'],
            expected_source_ref=json.loads(n1_reg['source'])), codes, 'old_target_entry_rejects_native_database')
        incomplete = EVIDENCE / 'cases/N7-incomplete'
        incomplete.mkdir(parents=True, exist_ok=False)
        def stop_before_completion():
            raise RuntimeError('controlled interruption before native formal completion')
        with self.assertRaises(RuntimeError):
            init_native_state(incomplete / 'anchor.json', incomplete / 'runtime', expected_ledger_id='incomplete', expected_target_store_id='incomplete', before_completion=stop_before_completion)
        refusal(self, 'STATE_DIRECTORY_IDENTITY_MISMATCH', lambda: open_native_state(incomplete / 'anchor.json',
            expected_ledger_id='incomplete', expected_target_store_id='incomplete'), codes, 'incomplete_native_initialization_rejected')
        write(EVIDENCE / 'N7-result.json', {'runtime_reopened_same_identity': True, 'target_reopened_same_adoption': True,
            'old_database_migration': 'NOT_IMPLEMENTED_BLOCKED', 'refusals': codes})


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--n1-child':
        n1_child(Path(sys.argv[2]))
    else:
        unittest.main(failfast=True)
