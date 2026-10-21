"""Fresh native runtime store and process-private actual PRE registry.

All persistent writes, owner/currentness checks and proof issuance live here.
The ordinary intent, fence, permit and effect implementations remain in base.
"""
import hashlib
from collections import OrderedDict
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sqlite3
import time

from annotation.contracts import artifact_ref, content_digest
from annotation.contracts.a03_native import (EXCHANGE, _attach_registry, _issue_context,
    _validate_native_for_registry, require_context, select_native_codec, validate_native_bundle)
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
CREATE TABLE native_hold_candidates(plan_id TEXT PRIMARY KEY,registration TEXT NOT NULL,
    hold_id TEXT NOT NULL,head_sequence INTEGER NOT NULL,head_hash TEXT NOT NULL,
    pre_ref TEXT NOT NULL,cleared_event TEXT);
CREATE TABLE native_readonly_entries(id TEXT PRIMARY KEY,book TEXT NOT NULL,registration TEXT NOT NULL,
    plan_id TEXT NOT NULL,action_id TEXT NOT NULL,binding TEXT NOT NULL,
    started REAL NOT NULL,deadline REAL NOT NULL,parent_deadline REAL NOT NULL,
    state TEXT NOT NULL,used_count INTEGER NOT NULL DEFAULT 0,initial_head TEXT NOT NULL,
    result TEXT,UNIQUE(book,plan_id,action_id));
CREATE TABLE native_readonly_reads(entry_id TEXT NOT NULL,ordinal INTEGER NOT NULL,
    state TEXT NOT NULL,resource TEXT,PRIMARY KEY(entry_id,ordinal));
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
        self._validation_values = OrderedDict()
        self.validation_counts = dict(entries=0, complete=0, reuse=0, resource_reads=0)
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

    def _project_unknown_diagnostic_post(self):
        # Native reports require their own fresh observation and explicit publisher.
        return False

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

    def _validate(self, bundle, *, asset_root):
        root = Path(asset_root).resolve(strict=True)
        self.native_registry.roots.add(root)
        return _validate_native_for_registry(self.native_registry, bundle, root)

    def _m_event(self, connection, key, name, payload):
        """Append the actual global event once, with the adopted M payload version."""
        book = connection.execute('SELECT * FROM books WHERE key=?', (key,)).fetchone()
        event = dict(sequence=book['head_sequence'] + 1, event=name, journal_id=book['journal'],
            target_key=json.loads(book['target_key']), plan_ref=payload['binding']['plan_ref'],
            owner_id=book['owner'], generation=book['generation'], recorded_at=now(),
            payload=plain(payload), previous_hash=book['head_hash'], event_version='a03-M-event-1')
        event['event_hash'] = digest(event)
        connection.execute('INSERT INTO events VALUES(?,?,?)', (key, event['sequence'], canonical(event).decode()))
        connection.execute('UPDATE books SET head_sequence=?,head_hash=? WHERE key=?',
            (event['sequence'], event['event_hash'], key))
        return event

    def _check_readonly_entry(self, connection, key, *, operation):
        rows = connection.execute("SELECT * FROM native_readonly_entries WHERE book=? AND state='ACTIVE'", (key,)).fetchall()
        for row in rows:
            binding = json.loads(row['binding'])
            book = connection.execute('SELECT * FROM books WHERE key=?', (key,)).fetchone()
            alive = (book['owner'] == binding['owner_id'] and book['generation'] == binding['generation']
                and book['lease'] > time.time() and self._pid_alive(book['pid']))
            if row['deadline'] > time.time() and alive:
                fail('READONLY_SESSION_ACTIVE', 'controlled ' + operation + ' cannot cross an active readonly entry', 3)
            connection.execute("UPDATE native_readonly_entries SET state='ABORTED' WHERE id=? AND state='ACTIVE'", (row['id'],))
            self._m_event(connection, key, 'M_READONLY_ABORTED',
                {'binding': binding, 'used_count': row['used_count'], 'reason': 'DEAD_OR_EXPIRED'})

    def _pending(self, connection, key, except_intent=None):
        pending = super()._pending(connection, key, except_intent)
        for entry in connection.execute("SELECT e.id,e.registration,e.action_id,e.binding FROM native_readonly_entries e JOIN actions a ON a.book=e.book AND a.id=e.action_id WHERE e.book=? AND e.state='ABORTED' AND a.fact IS NULL AND a.intent IS NULL", (key,)):
            pending.append({'id': entry['id'], 'registration': entry['registration'],
                'action': entry['action_id'], 'classification': 'UNATTEMPTED_ABSENCE_INCONCLUSIVE',
                'intent_ref': None, 'binding': json.loads(entry['binding'])})
        return pending

    def _m_prefix(self, connection, reg, plan, head):
        from annotation.contracts.recovery import REF_FIELDS
        frames = []
        artifacts = self.bundle(reg['id'])['artifacts']
        byref = {canonical(reference(a)): a for a in artifacts}
        accepted = None
        for row in connection.execute('SELECT body FROM events WHERE book=? ORDER BY sequence', (reg['book'],)):
            event = json.loads(row['body'])
            if event['sequence'] > head['sequence']:
                break
            refs, visited = {}, set()
            def walk(value):
                if isinstance(value, list):
                    for member in value:
                        walk(member)
                elif isinstance(value, dict):
                    if set(value) == REF_FIELDS:
                        refs[canonical(value)] = value
                    elif {'path', 'sha256', 'media_type'} <= set(value):
                        token = (value['path'], value['sha256'])
                        if value['media_type'] == 'application/json' and token not in visited:
                            visited.add(token)
                            walk(self.read_resource(value, reg['id']))
                    else:
                        for member in value.values():
                            walk(member)
            walk(event)
            scope = byref[canonical(event['plan_ref'])]['scope_id'] if event['plan_ref'] is not None else None
            if event['plan_ref'] is None and event['event'] == 'TARGET_DRIFT_HOLD':
                scope = reg['scope']
            frames.append({'frame_version': 'a03-journal-consumer-frame-2', 'consumer_scope_id': scope,
                'input_refs': list(refs.values()), 'event': event})
            if event['event'] == 'PLAN_ACCEPTED' and event['plan_ref'] == reference(plan):
                accepted = {'sequence': event['sequence'], 'hash': event['event_hash']}
        if accepted is None:
            fail('UNATTEMPTED_ENTRY_INVALID', 'no exact accepted plan anchor')
        book = connection.execute('SELECT * FROM books WHERE key=?', (reg['book'],)).fetchone()
        return {'format_version': 'a03-runtime-event-prefix-2', 'profile_id': 'a03-p2-r2-static-2-PROPOSAL',
            'journal_id': book['journal'], 'target_key': self.target_key(reg['id']), 'from_sequence': 1,
            'predecessor': {'sequence': 0, 'hash': '0' * 64}, 'subject_plan_ref': reference(plan),
            'accepted_anchor': accepted, 'expected_book_head': head, 'frames': frames}

    def commit_unattempted_absence(self, bundle, request, *, owner_id, generation, asset_root, observer):
        """At most three real reads, never a dispatch/intent or old-tail continuation."""
        from annotation.runtime.recovery.observation import observe_bounded
        from annotation.delivery.reconciler import reconcile_action
        reg = self.registration(request['registration_id'])
        plan = self._plan(reg['id'], digest(request['plan_ref']))
        self._validate(bundle, asset_root=asset_root)
        action = next((a for a in plan['payload']['actions'] if a['action_id'] == request['action_id']), None)
        if action is None or digest(action) != request['action_digest'] or reference(plan) != plain(request['plan_ref']):
            fail('ACTION_DIGEST_MISMATCH')
        key = self.target_key(reg['id'])
        observer = self._hold_observer(reg, observer)
        entry_id = request['entry_id']
        stamp = time.time()
        parent_deadline = stamp + 60
        deadline = min(parent_deadline, stamp + 8)
        with self.effect_gate(key).acquire(), self.transaction() as connection:
            self._check_readonly_entry(connection, reg['book'], operation='readonly-entry')
            book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
            prior = connection.execute('SELECT id,state FROM native_readonly_entries WHERE book=? AND plan_id=? AND action_id=?',
                (reg['book'], digest(reference(plan)), action['action_id'])).fetchone()
            if prior:
                fail('READONLY_ENTRY_CONSUMED', 'same action cannot reset its entry or read budget', 3)
            row = connection.execute('SELECT * FROM actions WHERE book=? AND id=?', (reg['book'], action['action_id'])).fetchone()
            state = connection.execute('SELECT status FROM plans WHERE id=?', (digest(reference(plan)),)).fetchone()
            if (row is None or row['plan'] != digest(reference(plan)) or row['digest'] != digest(action)
                    or row['state'] != 'RESERVED' or row['intent'] is not None or row['fact'] is not None
                    or state is None or state['status'] != 'INTERRUPTED' or book['hold']):
                fail('UNATTEMPTED_ENTRY_INVALID', 'only an exact interrupted, reserved, intent-free tail')
            head = {'sequence': book['head_sequence'], 'hash': book['head_hash']}
            if head != request['expected_event_head']:
                fail('EVENT_HEAD_CAS_MISMATCH')
            binding = {'ledger_id': self.ledger_id, 'readonly_session_id': entry_id,
                'entry_id': entry_id, 'parent_call_id': request['parent_call_id'],
                'owner_id': owner_id, 'generation': generation, 'registration_id': reg['id'],
                'target_store_id': self.target_store_id, 'target_session_id': reg['session'],
                'target_key': key, 'plan_ref': reference(plan), 'scope_id': reg['scope'],
                'source_ref': json.loads(reg['source']), 'action_id': action['action_id'],
                'action_digest': digest(action), 'fence_token': digest({'owner': owner_id, 'generation': generation, 'store': self.target_store_id})}
            connection.execute('INSERT INTO native_readonly_entries VALUES(?,?,?,?,?,?,?,?,?,\'ACTIVE\',0,?,NULL)',
                (entry_id, reg['book'], reg['id'], digest(reference(plan)), action['action_id'], canonical(binding).decode(),
                 stamp, deadline, parent_deadline, canonical(head).decode()))
            self._m_event(connection, reg['book'], 'M_READONLY_STARTED', {'binding': binding, 'initial_event_head': head})
        observations, resources, snapshots, comparisons = [], [], [], []
        processes = []
        try:
            for ordinal in (1, 2, 3):
                gate = self.effect_gate(key).acquire() if ordinal == 3 else nullcontext()
                with gate:
                    with self.transaction() as connection:
                        book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
                        current = connection.execute('SELECT * FROM native_readonly_entries WHERE id=?', (entry_id,)).fetchone()
                        if current['state'] != 'ACTIVE' or current['used_count'] != ordinal - 1 or time.time() >= deadline:
                            fail('READONLY_ENTRY_EXHAUSTED', 'entry lifetime and persistent read count cannot be refreshed', 3)
                        connection.execute('UPDATE native_readonly_entries SET used_count=? WHERE id=?', (ordinal, entry_id))
                        connection.execute("INSERT INTO native_readonly_reads VALUES(?,?,'STARTED',NULL)", (entry_id, ordinal))
                        self._m_event(connection, reg['book'], 'M_READONLY_READ_STARTED',
                            {'binding': binding, 'ordinal': ordinal, 'in_final_gate': ordinal == 3})
                    result = observe_bounded(observer, timeout=min(2, max(0, deadline-time.time())),
                        read_fault=request.get('read_fault') if ordinal == 2 else None)
                    processes.append(result)
                    if not result.get('ok') or not result.get('process_reaped') or result['read_elapsed_seconds'] > 2 or time.time() >= deadline:
                        fail('READONLY_READ_FAILED', 'read consumed its durable slot', 3)
                    captured, snapshot = self.capture_observation(result['observation'], observer, reg['id'])
                    observation = self.read_resource(captured['resource'], reg['id'])
                    observations.append(observation)
                    resources.append(captured['resource'])
                    snapshots.append(snapshot)
                    with self.transaction() as connection:
                        self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
                        connection.execute("UPDATE native_readonly_reads SET state='OBSERVED',resource=? WHERE entry_id=? AND ordinal=?",
                            (canonical(captured['resource']).decode(), entry_id, ordinal))
                        self._m_event(connection, reg['book'], 'M_READONLY_READ_FINISHED',
                            {'binding': binding, 'ordinal': ordinal, 'observation': captured['resource']})
                        if snapshot is not None:
                            self._append(connection, reg['id'], snapshot)
                    if ordinal >= 2:
                        comparison = plain(reconcile_action(action, observations[0], observation))
                        comparisons.append(comparison)
                        if comparison['effect_match'] != 'ABSENT' or snapshot is None:
                            fail('UNATTEMPTED_ABSENCE_INCONCLUSIVE', 'insufficient observation; progress only', 3)
                    if ordinal == 3:
                        with self.transaction() as connection:
                            book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
                            current = connection.execute('SELECT * FROM native_readonly_entries WHERE id=?', (entry_id,)).fetchone()
                            row = connection.execute('SELECT * FROM actions WHERE book=? AND id=?', (reg['book'], action['action_id'])).fetchone()
                            if (current['state'] != 'ACTIVE' or current['used_count'] != 3 or time.time() >= deadline
                                    or row['intent'] is not None or row['fact'] is not None or row['state'] != 'RESERVED' or book['hold']):
                                fail('UNATTEMPTED_ENTRY_INVALID', 'final local CAS failed')
                            final_head = {'sequence': book['head_sequence'], 'hash': book['head_hash']}
                            prefix = self.resource(self._m_prefix(connection, reg, plan, final_head), reg['id'], connection)
                            basis = {'format_version': 'a03-unattempted-basis-M1', 'binding': binding,
                                'readonly_session_id': entry_id, 'gate_binding': binding, 'initial_event_head': head,
                                'expected_event_head': final_head, 'complete_uncalled_prefix': prefix,
                                'readonly_prepared_ref': resources[0], 'observations': resources,
                                'observer_calls': 2, 'total_read_calls': 3, 'used_count': 3, 'retries': 0,
                                'single_read_seconds': 2, 'entry_seconds': 8, 'parent_seconds': 60,
                                'busy_seconds': 1, 'gate_seconds': 5, 'lease_seconds': 10, 'renew_seconds': 2,
                                'parent_deadline': parent_deadline, 'entry_deadline': deadline,
                                'fact_key': digest({'book': reg['book'], 'plan': reference(plan), 'action': action['action_id']}),
                                'plan_status': 'INTERRUPTED', 'comparison': 'ABSENT'}
                            basis_resource = self.resource(basis, reg['id'], connection)
                            before_id = self._evidence(connection, reg['id'], resources[0])
                            after_id = self._evidence(connection, reg['id'], resources[-1])
                            result_value = {'action_id': action['action_id'], 'outcome': 'NOT_APPLIED', 'platform_ids': [],
                                'before_evidence_refs': [before_id], 'after_evidence_refs': [after_id],
                                'readback': resources[-1], 'effect_match': 'ABSENT', 'next_step': 'RECHECK_TARGET',
                                'replay_allowed': False, 'reason': 'Three real reads and exact uncalled prefix; old tail remains interrupted',
                                'attempt_fact': 'NOT_ATTEMPTED', 'attempt_evidence_refs': [basis_resource], 'intent_ref': None}
                            fact, fact_resource = self._fact(connection, reg, plan, action['action_id'], result_value,
                                prepared=resources[0], snapshot_ref=reference(snapshot), readback=resources[-1], basis=basis_resource)
                            event = self._m_event(connection, reg['book'], 'M_UNATTEMPTED_COMMITTED',
                                {'binding': binding, 'fact': fact_resource, 'expected_event_head': final_head})
                            assert event['sequence'] == fact['journal_sequence'] and event['previous_hash'] == fact['predecessor_hash']
                            connection.execute("UPDATE actions SET state='NOT_APPLIED',fact=? WHERE book=? AND id=? AND intent IS NULL AND fact IS NULL",
                                (canonical(fact_resource).decode(), reg['book'], action['action_id']))
                            connection.execute("UPDATE native_readonly_entries SET state='COMMITTED',result=? WHERE id=?",
                                (canonical(fact_resource).decode(), entry_id))
            projection = self.project_plan(reg['id'], plan)
            return Handle(status='NOT_APPLIED', entry_id=entry_id, read_count=3,
                processes=processes, fact_ref=fact_resource, projection=projection, target_effects=0)
        except BaseException as error:
            with self.effect_gate(key).acquire(), self.transaction() as connection:
                current = connection.execute('SELECT * FROM native_readonly_entries WHERE id=?', (entry_id,)).fetchone()
                if current and current['state'] == 'ACTIVE':
                    self._m_event(connection, reg['book'], 'M_READONLY_ABORTED',
                        {'binding': binding, 'used_count': current['used_count'], 'reason': getattr(error, 'code', type(error).__name__)})
                    connection.execute("UPDATE native_readonly_entries SET state='ABORTED' WHERE id=?", (entry_id,))
            if getattr(error, 'code', None) in ('READONLY_READ_FAILED', 'UNATTEMPTED_ABSENCE_INCONCLUSIVE', 'READONLY_ENTRY_EXHAUSTED'):
                return Handle(status='INCONCLUSIVE', entry_id=entry_id, read_count=len(processes),
                    processes=processes, code=error.code, projection=self.project_plan(reg['id'], plan), target_effects=0)
            raise

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
        self._check_readonly_entry(connection, reg['book'], operation='PRE')
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
            if not {'native_pre_runs', 'native_creation_anchors', 'native_report_reads',
                    'native_hold_candidates', 'native_readonly_entries', 'native_readonly_reads'} <= names:
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

    def record_hold_candidate(self, registration_id, bundle, plan_ref, config, *, hold_id,
                              owner_id, generation, expected_head):
        """Index only a genuine POST_HOLD candidate; no action reservation or head change."""
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
            pre = next(a for a in plain(validated)['artifacts'] if reference(a) == plain(plan.payload.precheck))
            run = pre['payload']['verification_context']
            if run['kind'] != 'POST_HOLD' or run['hold_id'] != hold_id:
                fail('HOLD_EVIDENCE_INVALID', 'candidate requires its exact actual POST_HOLD proof')
            book = self._pre_lease(connection, reg, owner_id, generation, kind='POST_HOLD',
                context=run, expected_head=(expected_head['sequence'], expected_head['hash']))
            original, incoming = self.bundle(reg['id']), plain(validated)
            if incoming['artifacts'][:len(original['artifacts'])] != original['artifacts'] or incoming['evidence'] != original['evidence']:
                fail('NATIVE_PLAN_HISTORY_CHANGED')
            self._append(connection, reg['id'], *incoming['artifacts'][len(original['artifacts']):])
            connection.execute('INSERT INTO native_hold_candidates VALUES(?,?,?,?,?,?,NULL)',
                (digest(plan_ref), reg['id'], hold_id, book['head_sequence'], book['head_hash'], canonical(plan.payload.precheck).decode()))
        return Handle(plan_ref=plain(plan_ref), readonly=True, hold_id=hold_id, head=plain(expected_head), target_effects=0)

    def _check_hold_candidate(self, connection, reg, candidate_plan_ref, hold_id, expected_head):
        row = connection.execute('SELECT * FROM native_hold_candidates WHERE plan_id=?', (digest(candidate_plan_ref),)).fetchone()
        if (row is None or row['registration'] != reg['id'] or row['hold_id'] != hold_id
                or row['cleared_event'] is not None or (row['head_sequence'], row['head_hash']) != expected_head):
            fail('HOLD_EVIDENCE_INVALID', 'clear requires its formally indexed readonly candidate at the exact head')

    def _record_hold_clear(self, connection, candidate_plan_ref, event):
        connection.execute('UPDATE native_hold_candidates SET cleared_event=? WHERE plan_id=? AND cleared_event IS NULL',
            (canonical(event).decode(), digest(candidate_plan_ref)))


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
