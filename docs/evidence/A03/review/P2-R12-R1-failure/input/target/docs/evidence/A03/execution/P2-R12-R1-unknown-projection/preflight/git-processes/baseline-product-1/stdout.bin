"""Fresh native runtime store and process-private actual PRE registry.

All persistent writes, owner/currentness checks and proof issuance live here.
The ordinary intent, fence, permit and effect implementations remain in base.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from annotation.contracts import artifact_ref, content_digest
from annotation.contracts.a03_native import (EXCHANGE, _attach_registry, _issue_context,
    require_context, select_native_codec, validate_native_bundle)
from . import RuntimeStore, SQL, CURRENT, exclusive_bytes
from .common import Handle, canonical, digest, fail, now, plain, reference, unique

NATIVE_SQL = '''
CREATE TABLE native_pre_runs(id TEXT PRIMARY KEY, registration TEXT NOT NULL,
    binding TEXT NOT NULL, head_sequence INTEGER NOT NULL, head_hash TEXT NOT NULL,
    created REAL NOT NULL, reads INTEGER NOT NULL, status TEXT NOT NULL,
    snapshot TEXT, observation TEXT, input_sha TEXT, input_manifest TEXT,
    pre_ref TEXT, run_sha TEXT, accepted_plan TEXT,
    UNIQUE(registration,head_sequence,head_hash));
CREATE TABLE native_creation_anchors(plan_artifact_id TEXT PRIMARY KEY,
    input_path TEXT NOT NULL,input_sha TEXT NOT NULL,manifest TEXT NOT NULL,
    config TEXT NOT NULL,created_at TEXT NOT NULL,run_id TEXT NOT NULL);
CREATE TABLE native_report_reads(plan_id TEXT PRIMARY KEY,created REAL NOT NULL,reads INTEGER NOT NULL);
'''


class RegisteredRunHandle:
    __slots__ = ('run_id', '_registry', '_pid')

    def __init__(self, run_id, registry):
        import os
        self.run_id, self._registry, self._pid = run_id, registry, os.getpid()


class AdmittedPreRun:
    __slots__ = ('run_id', 'pre_ref', 'input_sha256', 'snapshot_ref', '_registry', '_token')

    def __init__(self, run, registry, token):
        self.run_id, self.pre_ref = run['id'], json.loads(run['pre_ref'])
        self.input_sha256, self.snapshot_ref = run['input_sha'], json.loads(run['snapshot'])
        self._registry, self._token = registry, token


class NativeRegistry:
    def __init__(self, store):
        self.store, self.registry_id = store, unique('native-registry')
        self.handles, self.admitted, self.roots = {}, {}, set()
        self._callback = self._dispatch
        _attach_registry(self, self._callback)

    def context(self, bundle, root, *, binding='', historical=False):
        root = Path(root).resolve(strict=True)
        self.roots.add(root)
        return _issue_context(self, bundle, root, binding=binding, historical=historical)

    def _handle(self, handle):
        import os
        if (type(handle) is not RegisteredRunHandle or self.handles.get(id(handle)) is not handle
                or handle._registry is not self or handle._pid != os.getpid()):
            fail('NATIVE_RUN_HANDLE_REQUIRED', 'serialized or foreign PRE run handle rejected')
        with self.store.connect() as connection:
            row = connection.execute('SELECT * FROM native_pre_runs WHERE id=?', (handle.run_id,)).fetchone()
        if row is None:
            fail('NATIVE_RUN_MISSING')
        return dict(row)

    def _current(self, row, *, accepted=False):
        reg = self.store.registration(row['registration'])
        binding = json.loads(row['binding'])
        with self.store.connect() as connection:
            context = binding['context']
            head = (row['head_sequence'], row['head_hash']) if not accepted or context['kind'] == 'POST_HOLD' else None
            book = self.store._pre_lease(connection, reg, binding['owner_id'], binding['generation'],
                kind=context['kind'], context=context, expected_head=head, accepted=accepted)
            if not accepted and (book['head_sequence'], book['head_hash']) != (row['head_sequence'], row['head_hash']):
                fail('NATIVE_RUN_STALE_HEAD', 'whole-book head progressed after actual PRE')
            expected = binding['context']['hold_id']
            if book['hold'] != expected or (not accepted and self.store._pending(connection, reg['book'])):
                fail('NATIVE_RUN_CURRENTNESS', 'current hold/pending differs from actual run')
        if time.time() > row['created'] + 60:
            fail('NATIVE_PRE_DEADLINE_EXCEEDED', 'durable PRE window expired; reopen does not refresh it')
        observer = self.store._observers.get(reg['book'])
        if observer is None:
            fail('NATIVE_PRE_OBSERVER_REQUIRED')
        self.store._hold_fence(observer, self.store.target_key(reg['id']), binding['owner_id'], binding['generation'])
        if row['observation']:
            body = json.loads(row['observation'])
            self.store._hold_native(reg, observer, body['resource'], json.loads(row['snapshot']))
        return reg, binding

    def _dispatch(self, operation, context, **kwargs):
        if context._registry is not self:
            fail('NATIVE_CONTEXT_FOREIGN')
        if operation == 'derive_context':
            root = Path(kwargs['asset_root']).resolve(strict=True)
            if root not in self.roots:
                fail('NATIVE_CONTEXT_ROOT_FOREIGN')
            return self.context(kwargs['bundle'], root, binding=context._binding, historical=context._historical)
        if operation == 'producer_binding':
            row = self._handle(kwargs['handle'])
            reg, binding = self._current(row)
            if (json.loads(row['snapshot']) != plain(kwargs['snapshot_ref'])
                    or json.loads(row['observation']) != plain(kwargs['observation'])):
                fail('NATIVE_PRE_OBSERVATION_FOREIGN')
            return {'run_id': row['id'], 'context': binding['context'],
                'input_manifest': self.store.resource_manifest(kwargs.get('bundle') or self.store.bundle(reg['id']), reg['package_root']),
                'native_binding': {key: binding[key] for key in
                    ('registry_id', 'registration_id', 'owner_id', 'generation', 'target_store_id', 'target_session_id')}}
        if operation == 'admit_pre':
            row = self._handle(kwargs['handle'])
            reg, binding = self._current(row)
            bundle = kwargs['bundle']
            pre = next((a for a in bundle.artifacts if artifact_ref(a) == plain(kwargs['pre_ref'])), None)
            if pre is None or pre.kind != 'CheckReport' or pre.payload.stage != 'PRE_APPLY' or pre.payload.decision != 'PASS':
                fail('NATIVE_PRE_FAILED')
            run = self.store.read_resource(plain(pre.payload.synthetic_run_ref), reg['id'])
            expected_binding = {key: binding[key] for key in
                ('registry_id', 'registration_id', 'owner_id', 'generation', 'target_store_id', 'target_session_id')}
            if (run['run_id'] != row['id'] or run['native_binding'] != expected_binding
                    or run['context'] != binding['context'] or run['snapshot_ref'] != json.loads(row['snapshot'])
                    or run['snapshot_ref'] != plain(kwargs['snapshot_ref'])
                    or run['actual_observation'] != json.loads(row['observation'])['resource']
                    or run['input_raw_sha256'] != row['input_sha'] or run['input_manifest'] != json.loads(row['input_manifest'])):
                fail('NATIVE_PRE_BINDING_MISMATCH')
            from annotation.quality.synthetic_precheck import compare_synthetic_inputs, CHECKS
            checks = compare_synthetic_inputs(bundle, run['source_ref'], run['evidence_ref'], run['graph_ref'], run['policy_ref'], asset_root=reg['package_root'])
            if checks != run['checks'] or set(checks) != set(CHECKS) or any(v != 'PASS' for v in checks.values()):
                fail('NATIVE_PRE_FAILED', 'actual comparison does not support self-reported PASS')
            original = self.store.bundle(reg['id'])
            incoming = plain(bundle)
            if incoming['artifacts'] != original['artifacts'] + [plain(pre)] or incoming['evidence'][:-1] != original['evidence']:
                fail('NATIVE_PRE_INPUT_EXTENSION', 'admission only appends the produced PRE and its actual run evidence')
            with self.store.transaction() as connection:
                # Recheck the row and head under the committing transaction.
                book = self.store._pre_lease(connection, reg, binding['owner_id'], binding['generation'],
                    kind=binding['context']['kind'], context=binding['context'],
                    expected_head=(row['head_sequence'], row['head_hash']))
                if (book['head_sequence'], book['head_hash']) != (row['head_sequence'], row['head_hash']):
                    fail('NATIVE_RUN_STALE_HEAD')
                if connection.execute('SELECT status FROM native_pre_runs WHERE id=?', (row['id'],)).fetchone()[0] != 'OBSERVED':
                    fail('NATIVE_PRE_REPLAY')
                connection.execute('UPDATE native_pre_runs SET status=?,pre_ref=?,run_sha=? WHERE id=?',
                    ('ADMITTED', canonical(kwargs['pre_ref']).decode(), pre.payload.synthetic_run_ref.sha256, row['id']))
                for resource in self.store.resource_manifest(incoming, reg['package_root']):
                    path = Path(reg['package_root']) / resource['path']
                    self.store._file(path, path.read_bytes(), connection)
                self.store._artifact(connection, plain(pre))
                self.store._save_bundle(connection, reg['id'], incoming)
            with self.store.connect() as connection:
                actual = dict(connection.execute('SELECT * FROM native_pre_runs WHERE id=?', (row['id'],)).fetchone())
            token = object()
            proof = AdmittedPreRun(actual, self, token)
            self.admitted[digest(kwargs['pre_ref'])] = (proof, token)
            return proof
        if operation == 'assert_pre':
            entry = self.admitted.get(digest(kwargs['pre_ref']))
            if not entry or type(entry[0]) is not AdmittedPreRun or entry[0]._token is not entry[1]:
                fail('NATIVE_ADMITTED_RUN_REQUIRED', 'PASS bytes or reopened registry cannot recreate process-private proof')
            with self.store.connect() as connection:
                row = dict(connection.execute('SELECT * FROM native_pre_runs WHERE id=?', (entry[0].run_id,)).fetchone())
            if json.loads(row['pre_ref']) != plain(kwargs['pre_ref']) or json.loads(row['snapshot']) != plain(kwargs['snapshot_ref']):
                fail('NATIVE_PRE_BINDING_MISMATCH')
            self._current(row, accepted=bool(row['accepted_plan']))
            if row['accepted_plan']:
                with self.store.connect() as connection:
                    plan = connection.execute('SELECT * FROM plans WHERE id=?', (row['accepted_plan'],)).fetchone()
                    if not plan or plan['status'] != 'RUNNING':
                        fail('NATIVE_ACCEPTED_PLAN_NOT_CURRENT')
            return entry[0]
        if operation == 'creation_anchor':
            if context._historical:
                return None
            raw = canonical(plain(kwargs['bundle']))
            path = self.store.object(plain(kwargs['bundle']))
            values = (kwargs['artifact_id'], str(path), hashlib.sha256(raw).hexdigest(),
                canonical(self.store.resource_manifest(kwargs['bundle'], context.asset_root)).decode(),
                canonical(vars(kwargs['config'])).decode(), kwargs['created_at'], kwargs['run_id'])
            with self.store.transaction() as connection:
                if connection.execute('SELECT 1 FROM native_creation_anchors WHERE plan_artifact_id=?', (kwargs['artifact_id'],)).fetchone():
                    fail('NATIVE_CREATION_ANCHOR_EXISTS')
                connection.execute('INSERT INTO native_creation_anchors VALUES(?,?,?,?,?,?,?)', values)
            return None
        if operation == 'verify_creation_anchor':
            from annotation.delivery.planner import create_plan
            from annotation.runtime.recovery import configuration
            plan = kwargs['plan']
            with self.store.connect() as connection:
                row = connection.execute('SELECT * FROM native_creation_anchors WHERE plan_artifact_id=?', (plan.artifact_id,)).fetchone()
            if not row:
                fail('NATIVE_CREATION_ANCHOR_MISSING')
            raw = Path(row['input_path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['input_sha']:
                fail('NATIVE_CREATION_ANCHOR_HASH')
            original = json.loads(raw)
            if self.store.resource_manifest(original, context.asset_root) != json.loads(row['manifest']):
                fail('NATIVE_CREATION_MANIFEST_CHANGED')
            if canonical(vars(kwargs['config'])).decode() != row['config']:
                fail('NATIVE_CREATION_CONFIG_CHANGED')
            historical = self.context(original, context.asset_root, binding=context._binding, historical=True)
            payload = plan.payload
            generated = create_plan(original, payload.graph, payload.precheck, payload.targetcheck,
                payload.snapshot, payload.snapshot, payload.policy, kwargs['config'], artifact_id=plan.artifact_id,
                created_at=plan.created_at, run_id=plan.run_id, bridge_context=historical)
            if generated.artifacts[-1] != plan:
                fail('PLAN_CHANGED')
            binding = kwargs.get('observation_binding')
            if binding is not None and (plain(binding).get('plan_ref') != artifact_ref(plan)
                    or plain(binding).get('observed_snapshot_ref') != plain(kwargs['current_ref'])):
                fail('OBSERVATION_BINDING_MISMATCH')
            return None
        fail('NATIVE_REGISTRY_OPERATION_UNSUPPORTED', operation)


class NativeRuntimeStore(RuntimeStore):
    _db_version = 'a03-native-runtime-db-1'
    _application_id = 0x41303452
    _user_version = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.native_registry = NativeRegistry(self)

    def _expected_meta(self):
        result = super()._expected_meta()
        selection = select_native_codec()
        result.update(profile=selection.profile_id, profile_sha256=selection.profile_sha256,
            adoption_sha256=selection.adoption_sha256, initialization='COMPLETE', migration='NOT_IMPLEMENTED_BLOCKED')
        return result

    def bridge_for(self, bundle, root=None):
        return self.native_registry.context(bundle, root or getattr(bundle, 'asset_root', None))

    def _post_hold_event(self, connection, reg, book):
        """Read the immutable hold for this fixed registration, not writer authority."""
        for row in connection.execute('SELECT body FROM events WHERE book=? ORDER BY sequence DESC', (reg['book'],)):
            event = json.loads(row['body'])
            if event['event'] != 'TARGET_DRIFT_HOLD' or event['payload'].get('hold_id') != book['hold']:
                continue
            payload = event['payload']
            if (event['target_key'] != json.loads(book['target_key'])
                    or payload.get('registration_id') != reg['id'] or payload.get('scope_id') != reg['scope']
                    or payload.get('source_ref') != json.loads(reg['source'])
                    or payload.get('target_store_id') != self.target_store_id
                    or payload.get('target_session_id') != reg['session']):
                fail('HOLD_EVIDENCE_INVALID', 'active hold differs from exact registered source/target/session')
            return event
        fail('HOLD_EVIDENCE_INVALID', 'active hold lacks its exact immutable event')

    def _pre_lease(self, connection, reg, owner_id, generation, *, kind, context=None,
                   expected_head=None, accepted=False):
        """POST_HOLD read-only PRE exception with explicit pending/hold/head checks.

        Shared _lease still proves ACTIVE owner/generation/PID/instance. Its
        ordinary and INITIAL hold prohibition is unchanged. This helper neither
        clears a hold nor grants a plan/intent/permit or target effect.
        """
        if kind not in ('INITIAL', 'POST_HOLD'):
            fail('NATIVE_PRE_CONTEXT_INVALID')
        post_hold = kind == 'POST_HOLD'
        book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=accepted or post_hold)
        if post_hold:
            if self._pending(connection, reg['book']):
                fail('BOOK_WRITE_PAUSED', 'POST_HOLD PRE cannot bypass unresolved book obligations', 3)
            if not book['hold']:
                fail('NATIVE_RUN_CURRENTNESS' if context else 'NATIVE_PRE_CONTEXT_INVALID', 'POST_HOLD needs the actual current hold')
            event = self._post_hold_event(connection, reg, book)
            if context is not None:
                if context['hold_id'] != book['hold']:
                    fail('NATIVE_RUN_CURRENTNESS', 'POST_HOLD run belongs to another hold')
                if (expected_head is None or context['hold_head'] != {'sequence': expected_head[0], 'hash': expected_head[1]}):
                    fail('NATIVE_RUN_STALE_HEAD', 'POST_HOLD context does not bind its registered head')
                if self.read_resource(context['hold_ref'], reg['id']) != event:
                    fail('NATIVE_RUN_CURRENTNESS', 'POST_HOLD resource is not the exact current hold event')
        if expected_head is not None and (book['head_sequence'], book['head_hash']) != expected_head:
            fail('NATIVE_RUN_STALE_HEAD', 'whole-book head progressed after actual PRE')
        return book

    def verify_integrity(self):
        super().verify_integrity()
        with self.connect() as connection:
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'native_pre_runs', 'native_creation_anchors', 'native_report_reads'} <= names:
                fail('NATIVE_INITIALIZATION_INCOMPLETE', 'native tables missing; no automatic completion', 5)
        return True

    def _append(self, connection, registration_id, *artifacts):
        row = connection.execute('SELECT * FROM registrations WHERE id=?', (registration_id,)).fetchone()
        bundle = json.loads(Path(row['bundle_path']).read_bytes())
        for artifact in artifacts:
            if not any(reference(a) == reference(artifact) for a in bundle['artifacts']):
                bundle['artifacts'].append(plain(artifact))
        self._validate(bundle, asset_root=row['package_root'])
        return super()._append(connection, registration_id, *artifacts)

    def commit_reconciliation(self, result, *, owner_id, generation):
        committed = super().commit_reconciliation(result, owner_id=owner_id, generation=generation)
        payload = plain(result)['payload']
        if payload['resolution'] == 'STILL_UNKNOWN':
            return committed
        # A late material fact belongs to the existing intent and terminal head.
        # Keep the original intent/progress/UNKNOWN and null original receipt.
        registration_id = self._observations[payload['observation_id']][2]
        target_key = self.target_key(registration_id)
        with self.effect_gate(target_key).acquire(), self.transaction() as connection:
            intent = connection.execute('SELECT * FROM intents WHERE ref=?', (canonical(payload['intent_ref']).decode(),)).fetchone()
            plan_row = connection.execute('SELECT * FROM plans WHERE id=?', (intent['plan'],)).fetchone()
            reg = self.registration(plan_row['registration'])
            self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
            plan = self._plan(reg['id'], intent['plan'])
            stored = json.loads(Path(intent['prepared']).read_bytes())
            outcome = 'APPLIED' if payload['resolution'] == 'RESOLVED_APPLIED' else 'NOT_APPLIED'
            before_id = self._evidence(connection, reg['id'], stored['intent']['payload']['prepared_before'])
            after_id = self._evidence(connection, reg['id'], payload['readback'])
            result_value = {'action_id': intent['action'], 'outcome': outcome, 'platform_ids': payload['platform_ids'],
                'before_evidence_refs': [before_id], 'after_evidence_refs': [after_id], 'readback': payload['readback'],
                'effect_match': payload['observation'], 'next_step': 'POSTCHECK' if outcome == 'APPLIED' else 'RECHECK_TARGET',
                'replay_allowed': False, 'reason': 'Late fact from exact committed read-only terminal head',
                'attempt_fact': 'MAY_HAVE_BEEN_ATTEMPTED', 'attempt_evidence_refs': [payload['readback']], 'intent_ref': payload['intent_ref']}
            book = connection.execute('SELECT * FROM books WHERE key=?', (reg['book'],)).fetchone()
            fact = {'format_version': 'a03-action-fact-3', 'design_only': False, 'origin_phase': 'RECOVERY',
                'resolution_ref': reference(result), 'plan_ref': reference(plan), 'intent_ref': payload['intent_ref'],
                'obligation_id': payload['obligation_id'], 'action_id': intent['action'], 'action_digest': payload['action_digest'],
                'prepared_before': stored['intent']['payload']['prepared_before'],
                'observed_snapshot_ref': payload['observed_snapshot_ref'], 'readback': payload['readback'],
                'comparator_version': 'a02-facts-1', 'result': result_value, 'journal_sequence': book['head_sequence'],
                'predecessor_hash': payload.get('journal_head_hash', book['head_hash']), 'unattempted_basis': None}
            resource = self.resource(fact, reg['id'], connection)
            connection.execute('UPDATE actions SET fact=?,state=? WHERE book=? AND id=?',
                (canonical(resource).decode(), outcome, reg['book'], intent['action']))
        self.project_plan(reg['id'], plan)
        return committed

    @staticmethod
    def resource_manifest(bundle, root):
        from annotation.contracts.a03_bridge._resources import ResourceReader
        root = Path(root).resolve()
        reader, found = ResourceReader(root), {}

        def walk(value):
            if isinstance(value, dict):
                if {'path', 'sha256', 'media_type'} <= set(value):
                    token = (value['path'], value['sha256'], value['media_type'])
                    if token in found:
                        return
                    found[token] = {key: value[key] for key in ('path', 'sha256', 'media_type', 'origin')}
                    walk(reader.read(value))
                else:
                    for child in value.values():
                        walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(plain(bundle))
        return [found[key] for key in sorted(found)]

    def begin_native_pre(self, registration_id, *, owner_id, generation, observer, kind='INITIAL'):
        from annotation.runtime.recovery.observation import observe_bounded
        reg = self.registration(registration_id)
        self._hold_observer(reg, observer)
        self._observers[reg['book']] = observer
        with self.effect_gate(self.target_key(reg['id'])).acquire():
            with self.transaction() as connection:
                book = self._pre_lease(connection, reg, owner_id, generation, kind=kind)
                if (kind == 'INITIAL' and book['hold']) or (kind == 'POST_HOLD' and not book['hold']) or kind not in ('INITIAL', 'POST_HOLD'):
                    fail('NATIVE_PRE_CONTEXT_INVALID')
                hold = None
                if book['hold']:
                    hold = self._post_hold_event(connection, reg, book)
                context = {'kind': kind, 'hold_id': book['hold'],
                    'hold_head': {'sequence': book['head_sequence'], 'hash': book['head_hash']} if hold else None,
                    'hold_ref': self.resource(hold, reg['id'], connection) if hold else None}
                binding = {'registry_id': self.native_registry.registry_id, 'registration_id': reg['id'],
                    'owner_id': owner_id, 'generation': generation, 'target_store_id': self.target_store_id,
                    'target_session_id': reg['session'], 'context': context}
                run_id = unique('native-pre')
                # Count before the independent read. Unique head window and the
                # persisted created time prevent retry/reopen budget refresh.
                connection.execute('INSERT INTO native_pre_runs VALUES(?,?,?,?,?,?,1,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL)',
                    (run_id, reg['id'], canonical(binding).decode(), book['head_sequence'], book['head_hash'], time.time(), 'READ_STARTED'))
            actual = observe_bounded(observer, timeout=2)
            if not actual.get('ok') or not actual.get('process_reaped') or actual['read_elapsed_seconds'] > 2:
                fail('NATIVE_PRE_READ_FAILED', 'actual read failed; the durable read is consumed')
            captured, snapshot = self.capture_observation(actual['observation'], observer, reg['id'])
            if snapshot is None:
                fail('NATIVE_PRE_READ_INCOMPLETE')
            bundle = self.bundle(reg['id'])
            bundle['artifacts'].append(snapshot)
            manifest = self.resource_manifest(bundle, reg['package_root'])
            with self.transaction() as connection:
                self._append(connection, reg['id'], snapshot)
                connection.execute('UPDATE native_pre_runs SET status=?,snapshot=?,observation=?,input_sha=?,input_manifest=? WHERE id=?',
                    ('OBSERVED', canonical(reference(snapshot)).decode(), canonical(captured).decode(), digest(bundle), canonical(manifest).decode(), run_id))
            handle = RegisteredRunHandle(run_id, self.native_registry)
            self.native_registry.handles[id(handle)] = handle
            return Handle(handle=handle, observation=captured, snapshot_ref=reference(snapshot),
                bundle=self._validate(self.bundle(reg['id']), asset_root=reg['package_root']))

    def accept_plan(self, registration_id, plan_ref, *, owner_id, generation):
        result = super().accept_plan(registration_id, plan_ref, owner_id=owner_id, generation=generation)
        plan = self._plan(registration_id)
        with self.transaction() as connection:
            connection.execute('UPDATE native_pre_runs SET accepted_plan=? WHERE pre_ref=? AND status=?',
                (digest(plan_ref), canonical(plan['payload']['precheck']).decode(), 'ADMITTED'))
        return result

    def record_native_plan(self, registration_id, bundle, plan_ref, config, *, owner_id, generation):
        from annotation.contracts import assert_plan_ready
        from annotation.delivery.planner import verify_generated_plan
        from annotation.quality.targetcheck import resolve_artifact
        reg = self.registration(registration_id)
        context = self.bridge_for(bundle, reg['package_root'])
        validated = validate_native_bundle(bundle, bridge_context=context)
        plan = resolve_artifact(validated, plan_ref, 'ApplyPlan')
        assert_plan_ready(validated, plan_ref, plan.payload.snapshot, bridge_context=context)
        verify_generated_plan(validated, plan, plan.payload.snapshot, config, bridge_context=context)
        with self.effect_gate(self.target_key(reg['id'])).acquire(), self.transaction() as connection:
            self._lease(connection, reg['book'], owner_id, generation)
            original = self.bundle(reg['id'])
            incoming = plain(validated)
            if incoming['artifacts'][:len(original['artifacts'])] != original['artifacts'] or incoming['evidence'] != original['evidence']:
                fail('NATIVE_PLAN_HISTORY_CHANGED')
            self._append(connection, reg['id'], *incoming['artifacts'][len(original['artifacts']):])
        return plan_ref


def init_native_state(anchor_path, state_dir, *, expected_ledger_id, expected_target_store_id, before_completion=None):
    anchor, directory = Path(anchor_path).resolve(), Path(state_dir).resolve()
    if anchor.exists() or directory.exists():
        fail('STATE_INIT_TARGET_EXISTS', 'native init requires two fresh paths', 5)
    directory.mkdir(parents=True)
    selection = select_native_codec()
    metadata = {'version': NativeRuntimeStore._db_version, 'ledger_id': expected_ledger_id,
        'target_store_id': expected_target_store_id, 'state_dir': str(directory), 'profile': selection.profile_id,
        'profile_sha256': selection.profile_sha256, 'adoption_sha256': selection.adoption_sha256,
        'initialization': 'COMPLETE', 'migration': 'NOT_IMPLEMENTED_BLOCKED'}
    with sqlite3.connect(str(directory / 'runtime.sqlite3')) as connection:
        connection.execute('PRAGMA application_id=' + str(NativeRuntimeStore._application_id))
        connection.execute('PRAGMA user_version=4')
        connection.executescript(SQL + NATIVE_SQL)
        if before_completion is not None:
            before_completion()
        connection.executemany('INSERT INTO meta VALUES(?,?)', metadata.items())
    descriptor = {'format_version': 'a03-native-runtime-anchor-1', 'state_dir': str(directory),
        'anchor_path': str(anchor), 'ledger_id': expected_ledger_id,
        'target_store_id': expected_target_store_id, 'db_version': NativeRuntimeStore._db_version}
    exclusive_bytes(anchor, canonical(descriptor))
    return open_native_state(anchor, expected_ledger_id=expected_ledger_id, expected_target_store_id=expected_target_store_id)


def open_native_state(anchor_path, *, expected_ledger_id, expected_target_store_id):
    store = NativeRuntimeStore(anchor_path, expected_ledger_id=expected_ledger_id,
        expected_target_store_id=expected_target_store_id)
    CURRENT.set(store)
    return store
