"""Current target drift holds, separate from immutable resolution histories.

This mixin uses RuntimeStore's controlled files, book gate and transactions.
Observations are verified again by the independent target's persisted registry;
neither caller hashes nor a serialized completeness flag grant clearance.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sqlite3
import time

from .common import Handle, canonical, digest, fail, plain, reference, unique


def _time(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError('timezone required')
        return result
    except (ValueError, AttributeError):
        fail('HOLD_EVIDENCE_INVALID', 'invalid evidence timestamp')


class HoldSupport:
    def _hold_registration(self, target_key):
        key = self.book_id(plain(target_key))
        with self.connect() as connection:
            rows = connection.execute('SELECT * FROM registrations WHERE book=?', (key,)).fetchall()
        if len(rows) != 1:
            fail('REGISTRATION_BINDING_MISMATCH', 'one fixed target registration is required')
        return dict(rows[0])

    def _hold_observer(self, reg, observer=None):
        from annotation.delivery.mock.persistent import PersistentMockSession
        key = self.target_key(reg['id'])
        observer = observer or self._observers.get(reg['book'])
        if observer is None:
            observer = PersistentMockSession.open(reg['target_dir'], expected_store_id=self.target_store_id,
                expected_target_session_id=reg['session'], expected_target_key=key,
                expected_scope_id=reg['scope'], expected_source_ref=json.loads(reg['source']))
        if not isinstance(observer, PersistentMockSession):
            fail('HOLD_EVIDENCE_INVALID', 'only the registered controlled target observer is supported')
        descriptor = plain(observer.descriptor)
        expected = {'store_id': self.target_store_id, 'target_session_id': reg['session'],
                    'target_key': key, 'fixed_scope_id': reg['scope'],
                    'fixed_source_ref': json.loads(reg['source'])}
        if (any(descriptor.get(k) != v for k, v in expected.items()) or
                Path(observer.directory).resolve() != Path(reg['target_dir']).resolve() or
                Path(observer.asset_root).resolve() != Path(reg['package_root']).resolve()):
            fail('HOLD_EVIDENCE_INVALID', 'observer store/session/source/scope/root differs from registration')
        return observer

    def _hold_fence(self, observer, target_key, owner_id, generation):
        context = plain(observer.export_book_context(target_key))
        if (context.get('fence_generation') != generation or context.get('fence_owner_id') != owner_id or
                context.get('target_store_id') != self.target_store_id or context.get('target_key') != target_key):
            fail('OWNER_GENERATION_STALE', 'current independent target fence differs', 4)
        return context

    def _hold_artifact(self, connection, ref, reg, kind=None):
        from annotation.contracts import content_digest
        ref = plain(ref)
        if not isinstance(ref, dict) or set(ref) != {'artifact_id', 'revision', 'kind', 'content_hash'}:
            fail('HOLD_EVIDENCE_INVALID', 'exact four-field artifact reference required')
        rows = connection.execute('SELECT path FROM artifacts WHERE ref=? AND book=? AND scope=?',
            (canonical(ref).decode(), self.target_key(reg['id'])['book_id'], reg['scope'])).fetchall()
        if len(rows) != 1:
            fail('HOLD_EVIDENCE_INVALID', 'artifact is not indexed in the exact registered book/scope')
        artifact = json.loads(Path(rows[0]['path']).read_bytes())
        if reference(artifact) != ref or content_digest(artifact) != ref['content_hash'] or (kind and artifact['kind'] != kind):
            fail('HOLD_EVIDENCE_INVALID', 'indexed artifact identity or bytes differ')
        return artifact

    def _hold_native(self, reg, observer, resource, snapshot_ref=None):
        """Revalidate an old observation against target.sqlite3, across processes."""
        body = self.read_resource(plain(resource), reg['id'])
        if (body.get('format_version') != 'a03-target-observation-1' or
                body.get('target_key') != self.target_key(reg['id']) or
                body.get('target_session_id') != reg['session'] or
                body.get('source_ref') != json.loads(reg['source']) or body.get('scope_id') != reg['scope'] or
                body.get('store_id') != self.target_store_id or body.get('scope_complete') is not True):
            fail('HOLD_EVIDENCE_INVALID', 'native observation bindings are incomplete or foreign')
        # Runtime capture normalizes nested Resource paths and removes asset_root.
        # Verify the original target evidence first, then reproduce that portable
        # projection without writing files or trusting normalized caller fields.
        target = sqlite3.connect(observer.path.as_uri() + '?mode=ro', uri=True, timeout=1)
        try:
            row = target.execute('SELECT body FROM observations WHERE observation_id=?',
                                 (body.get('observation_id'),)).fetchone()
        finally:
            target.close()
        if row is None:
            fail('HOLD_EVIDENCE_INVALID', 'native persisted observation is missing')
        original = json.loads(row[0])
        raw = (json.dumps(original, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
        original_resource = {'path': 'assets/a03-target/' + hashlib.sha256(raw).hexdigest() + '.json',
                             'sha256': hashlib.sha256(raw).hexdigest(), 'media_type': 'application/json', 'origin': 'SYNTHETIC'}
        root = Path(observer.asset_root).resolve()
        visiting = set()
        normalized_resources = {}

        def normalize_resource(ref):
            key = canonical(ref)
            if key in normalized_resources:
                return normalized_resources[key]
            path = (root / ref['path']).resolve()
            if root not in path.parents or path.is_symlink() or not path.is_file() or path in visiting:
                fail('HOLD_EVIDENCE_INVALID', 'native resource is missing, unsafe or cyclic')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != ref['sha256'] or ref.get('media_type') != 'application/json':
                fail('HOLD_EVIDENCE_INVALID', 'native JSON resource digest or type differs')
            visiting.add(path)
            normalized = normalize(json.loads(raw))
            visiting.remove(path)
            sha = hashlib.sha256(canonical(normalized)).hexdigest()
            result = ({'path': 'assets/runtime/' + sha + '.json', 'sha256': sha,
                       'media_type': 'application/json', 'origin': 'SYNTHETIC'}, normalized)
            normalized_resources[key] = result
            return result

        def normalize(value):
            if isinstance(value, dict):
                if {'path', 'sha256', 'media_type'} <= set(value):
                    return normalize_resource(value)[0]
                return {name: normalize(member) for name, member in value.items() if name != 'asset_root'}
            if isinstance(value, list):
                return [normalize(member) for member in value]
            return value

        # This public target method reads its independent persisted observation
        # registry and verifies exact resource bytes before deriving the snapshot.
        snapshot = plain(observer.snapshot_from_observation(dict(original, resource=original_resource, readback=original_resource)))
        expected_resource, expected_body = normalize_resource(original_resource)
        if plain(resource) != expected_resource or body != expected_body:
            fail('HOLD_EVIDENCE_INVALID', 'runtime observation differs from the exact normalized native read')
        if snapshot_ref is not None and reference(snapshot) != plain(snapshot_ref):
            fail('HOLD_EVIDENCE_INVALID', 'snapshot is not derived from the exact persisted native observation')
        return original, snapshot

    def _hold_native_for_snapshot(self, connection, reg, observer, snapshot_ref):
        root = Path(reg['package_root']).resolve()
        snapshot = self._hold_artifact(connection, snapshot_ref, reg, 'PlatformSnapshot')
        for row in connection.execute('SELECT path,sha FROM files ORDER BY path'):
            path = (self.directory / row['path']).resolve()
            if root not in path.parents or path.suffix.lower() != '.json':
                continue
            try:
                value = json.loads(path.read_bytes())
            except (OSError, ValueError):
                fail('HOLD_EVIDENCE_INVALID', 'indexed JSON evidence is unreadable')
            if (not isinstance(value, dict) or value.get('format_version') != 'a03-target-observation-1' or
                    value.get('observed_at') != snapshot['payload']['observed_at']):
                continue
            resource = {'path': path.relative_to(root).as_posix(), 'sha256': row['sha'],
                        'media_type': 'application/json', 'origin': 'SYNTHETIC'}
            body, actual = self._hold_native(reg, observer, resource)
            if reference(actual) == plain(snapshot_ref):
                return body, actual, resource
        fail('HOLD_EVIDENCE_INVALID', 'snapshot has no persisted runtime/target native observation binding')

    def _hold_baseline(self, connection, reg, observer):
        terminal_seen, expected = False, None
        for row in connection.execute('SELECT body FROM events WHERE book=? ORDER BY sequence', (reg['book'],)):
            event = json.loads(row['body'])
            payload = event['payload']
            resource, snapshot_ref, ref = None, None, None
            if event['event'] == 'RECONCILIATION_COMMITTED' and payload.get('resolution') in ('RESOLVED_APPLIED', 'RESOLVED_NOT_APPLIED'):
                resolution = self._hold_artifact(connection, payload['resolution_ref'], reg, 'ReconciliationResult')
                rp = resolution['payload']
                if rp['resolution'] != payload['resolution']:
                    fail('HOLD_EVIDENCE_INVALID', 'terminal event differs from immutable resolution')
                terminal_seen = True
                resource, snapshot_ref, ref = rp['readback'], rp['observed_snapshot_ref'], reference(resolution)
            elif terminal_seen and event['event'] == 'ACTION_RESULT_COMMITTED' and payload.get('outcome') == 'APPLIED':
                fact = self.read_resource(payload['fact'], reg['id'])
                if (fact['action_id'] != payload['action_id'] or fact['action_digest'] != payload['action_digest'] or
                        fact['result']['outcome'] != 'APPLIED' or fact['journal_sequence'] != event['sequence'] or
                        fact['predecessor_hash'] != event['previous_hash']):
                    fail('HOLD_EVIDENCE_INVALID', 'applied event differs from immutable fact')
                resource, snapshot_ref, ref = fact['readback'], fact['observed_snapshot_ref'], payload['fact']
            elif terminal_seen and event['event'] == 'HOLD_CLEARED':
                resource, snapshot_ref, ref = payload['verification_observation'], payload['verification_snapshot_ref'], payload['candidate_plan_ref']
            if resource is not None:
                expected = {'event_sequence': event['sequence'], 'event_hash': event['event_hash'],
                    'event': event['event'], 'binding': ref, 'plan_ref': payload.get('plan_ref'),
                    '_resource': resource, '_snapshot_ref': snapshot_ref}
        if expected is not None:
            body, _ = self._hold_native(reg, observer, expected.pop('_resource'), expected.pop('_snapshot_ref'))
            expected.update(target_state_hash=body['target_state_hash'], target_state_version=body['target_state_version'],
                            read_sequence=body['read_sequence'], observed_at=body['observed_at'])
        return expected if terminal_seen else None

    def _hold_read(self, reg, observer, deadline, *, capture=True):
        from annotation.runtime.recovery.observation import observe_bounded
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail('RECOVERY_DEADLINE_EXCEEDED', 'hold operation deadline exhausted', 6)
        result = observe_bounded(observer, timeout=min(2, remaining))
        if not result.get('ok') or not result.get('process_reaped') or result['read_elapsed_seconds'] > 2:
            fail(result.get('code', 'TARGET_READ_TIMEOUT'), 'hold observation failed within its bounded process', 6)
        original = result['observation']
        if not capture:
            snapshot = plain(observer.snapshot_from_observation(original))
            if (original.get('target_key') != self.target_key(reg['id']) or
                    original.get('target_session_id') != reg['session'] or original.get('scope_id') != reg['scope'] or
                    original.get('source_ref') != json.loads(reg['source']) or original.get('store_id') != self.target_store_id):
                fail('HOLD_EVIDENCE_INVALID', 'current native observation differs from registration')
            return original, snapshot, original
        captured, snapshot = self.capture_observation(original, observer, reg['id'])
        if snapshot is None:
            fail('HOLD_EVIDENCE_INVALID', 'hold requires a complete fresh native observation')
        body, actual = self._hold_native(reg, observer, captured['resource'], reference(snapshot))
        return captured, actual, body

    def _hold_assert_head(self, book, expected):
        if (book['head_sequence'], book['head_hash']) != expected:
            fail('EVENT_HEAD_CAS_MISMATCH', 'book event head changed during hold operation', 4)

    def _hold_current(self, observer, target_key, owner_id, generation, actual):
        from annotation.contracts import target_state_digest
        current = self._hold_fence(observer, target_key, owner_id, generation)
        live = plain(observer.read_target(target_key['book_id']))
        if (current['target_state_hash'] != actual['target_state_hash'] or
                (target_state_digest(live), 'a03-target-epoch-' + str(live['epoch'])) !=
                (actual['target_state_hash'], actual['target_state_version'])):
            fail('TARGET_CHANGED', 'target changed during final hold transaction', 3)

    def detect_target_drift(self, target_key, *, owner_id, generation, observer=None):
        target_key = plain(target_key)
        reg = self._hold_registration(target_key)
        observer = self._hold_observer(reg, observer)
        deadline = time.monotonic() + 60
        with self.effect_gate(target_key).acquire():
            self.verify_integrity()
            with self.connect() as connection:
                book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
                if book['hold']:
                    return Handle(status='TARGET_DRIFT_HOLD', hold_id=book['hold'], created=False)
                expected_head = (book['head_sequence'], book['head_hash'])
                baseline = self._hold_baseline(connection, reg, observer)
            if baseline is None:
                return Handle(status='NO_TERMINAL_BASELINE', hold_id=None, created=False)
            self._hold_fence(observer, target_key, owner_id, generation)
            captured, snapshot, actual = self._hold_read(reg, observer, deadline, capture=False)
            matches = (actual['target_state_hash'], actual['target_state_version']) == (baseline['target_state_hash'], baseline['target_state_version'])
            if not matches:
                captured, snapshot = self.capture_observation(captured, observer, reg['id'])
                if snapshot is None:
                    fail('HOLD_EVIDENCE_INVALID', 'hold requires a complete valid native snapshot')
                actual, snapshot = self._hold_native(reg, observer, captured['resource'], reference(snapshot))
            with self.transaction() as connection:
                book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
                self._hold_assert_head(book, expected_head)
                self._hold_current(observer, target_key, owner_id, generation, actual)
                if time.monotonic() >= deadline:
                    fail('RECOVERY_DEADLINE_EXCEEDED', 'hold operation deadline exhausted', 6)
                if matches:
                    return Handle(status='NO_DRIFT', hold_id=None, created=False,
                                  target_state_hash=actual['target_state_hash'], target_state_version=actual['target_state_version'],
                                  read_sequence=actual['read_sequence'])
                self._append(connection, reg['id'], snapshot)
                hold_id = unique('target-drift-hold')
                prior_prechecks = []
                bundle = self.bundle(reg['id'])
                for artifact in bundle['artifacts']:
                    if artifact['kind'] == 'ApplyPlan':
                        ref = artifact['payload']['precheck']
                        if ref not in prior_prechecks:
                            prior_prechecks.append(ref)
                payload = {'hold_id': hold_id, 'registration_id': reg['id'], 'plan_ref': baseline['plan_ref'],
                    'baseline': baseline, 'observation': captured['resource'], 'snapshot_ref': reference(snapshot),
                    'observation_id': actual['observation_id'], 'observed_at': actual['observed_at'],
                    'read_sequence': actual['read_sequence'], 'target_state_hash': actual['target_state_hash'],
                    'target_state_version': actual['target_state_version'], 'target_store_id': self.target_store_id,
                    'target_session_id': reg['session'], 'source_ref': json.loads(reg['source']), 'scope_id': reg['scope'],
                    'prior_precheck_refs': prior_prechecks}
                event = self._event(connection, reg['book'], 'TARGET_DRIFT_HOLD', payload)
                connection.execute('UPDATE books SET hold=? WHERE key=?', (hold_id, reg['book']))
            return Handle(status='TARGET_DRIFT_HOLD', hold_id=hold_id, created=True, event=event,
                          snapshot_ref=reference(snapshot), observation=captured['resource'])

    def clear_target_drift_hold(self, hold_id, snapshot_ref, precheck_ref, targetcheck_ref,
                               candidate_plan_ref, *, owner_id, generation):
        from annotation.contracts import (ContractError, assert_recovery_plan_ready, validate_recovery_bundle)
        from annotation.delivery.planner import verify_generated_plan
        from annotation.runtime.recovery import configuration
        deadline = time.monotonic() + 60
        with self.connect() as connection:
            rows = connection.execute('SELECT key FROM books WHERE hold=?', (hold_id,)).fetchall()
            if len(rows) != 1:
                fail('HOLD_EVIDENCE_INVALID', 'exact active hold does not exist')
            target_key = json.loads(connection.execute('SELECT target_key FROM books WHERE key=?', (rows[0]['key'],)).fetchone()[0])
        reg = self._hold_registration(target_key)
        observer = self._hold_observer(reg)
        with self.effect_gate(target_key).acquire():
            self.verify_integrity()
            with self.connect() as connection:
                book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
                if book['hold'] != hold_id:
                    fail('HOLD_EVIDENCE_INVALID', 'active hold changed')
                if self._pending(connection, reg['book']):
                    fail('BOOK_WRITE_PAUSED', 'all book scopes must have no unresolved save obligation', 3)
                expected_head = (book['head_sequence'], book['head_hash'])
                hold = None
                for row in connection.execute('SELECT body FROM events WHERE book=? ORDER BY sequence DESC', (reg['book'],)):
                    event = json.loads(row['body'])
                    if event['event'] == 'TARGET_DRIFT_HOLD' and event['payload'].get('hold_id') == hold_id:
                        hold = event
                        break
                if hold is None:
                    fail('HOLD_EVIDENCE_INVALID', 'active hold lacks its immutable event')
                refs = [(snapshot_ref, 'PlatformSnapshot'), (precheck_ref, 'CheckReport'),
                        (targetcheck_ref, 'CheckReport'), (candidate_plan_ref, 'ApplyPlan')]
                snapshot, precheck, targetcheck, plan = [self._hold_artifact(connection, ref, reg, kind) for ref, kind in refs]
                native, _, native_resource = self._hold_native_for_snapshot(connection, reg, observer, snapshot_ref)
            self._hold_fence(observer, target_key, owner_id, generation)
            hp = hold['payload']
            if (_time(native['observed_at']) <= max(_time(hp['observed_at']), _time(hold['recorded_at'])) or
                    native['read_sequence'] <= hp['read_sequence']):
                fail('OBSERVATION_NOT_FRESH', 'candidate snapshot must be a new actual observation after the hold')
            if (plain(precheck_ref) in hp['prior_precheck_refs'] or _time(precheck['created_at']) <= _time(hold['recorded_at']) or
                    precheck['payload']['stage'] != 'PRE_APPLY' or precheck['payload']['decision'] != 'PASS'):
                fail('HOLD_EVIDENCE_INVALID', 'a genuinely new post-hold PRE_APPLY is required; old PRE cannot be relabeled by this runtime')
            pp = plan['payload']
            if (pp['snapshot'] != plain(snapshot_ref) or pp['precheck'] != plain(precheck_ref) or
                    pp['targetcheck'] != plain(targetcheck_ref) or targetcheck['payload']['stage'] != 'TARGET' or
                    targetcheck['payload']['snapshot'] != plain(snapshot_ref) or targetcheck['payload']['subject'] != plain(snapshot_ref) or
                    targetcheck['payload']['decision'] != 'PASS' or _time(targetcheck['created_at']) < _time(native['observed_at']) or
                    _time(plan['created_at']) < max(_time(native['observed_at']), _time(precheck['created_at']), _time(targetcheck['created_at']))):
                fail('HOLD_EVIDENCE_INVALID', 'candidate plan/new PRE/new TARGET/current snapshot bindings differ')
            try:
                bundle = self._validate(self.bundle(reg['id']), asset_root=reg['package_root'])
                selected = assert_recovery_plan_ready(bundle, candidate_plan_ref, snapshot_ref, bridge_context=getattr(bundle, "bridge_context", None))
                verify_generated_plan(bundle, selected, snapshot_ref, configuration(json.loads(reg['config'])), bridge_context=getattr(bundle, "bridge_context", None))
            except ContractError as error:
                code = error.issues[0]['code'] if error.issues else 'HOLD_EVIDENCE_INVALID'
                fail(code if code in ('TARGET_CHANGED', 'OBSERVATION_NOT_FRESH', 'BOOK_WRITE_PAUSED') else 'HOLD_EVIDENCE_INVALID', str(error))
            # Retain the same book gate while the independent target is read.
            # No dispatch permit is issued or consumed by this route.
            self.renew(target_key, owner_id=owner_id, generation=generation)
            captured, verified_snapshot, actual = self._hold_read(reg, observer, deadline)
            if (actual['target_state_hash'], actual['target_state_version']) != (native['target_state_hash'], native['target_state_version']):
                fail('TARGET_CHANGED', 'target changed after candidate planning; hold remains', 3)
            self.fault('BEFORE_HOLD_CLEAR_COMMIT')
            with self.transaction() as connection:
                book = self._lease(connection, reg['book'], owner_id, generation, pending_ok=True)
                self._hold_assert_head(book, expected_head)
                if book['hold'] != hold_id or self._pending(connection, reg['book']):
                    fail('BOOK_WRITE_PAUSED', 'hold or full-book unresolved set changed', 3)
                self._hold_current(observer, target_key, owner_id, generation, actual)
                if time.monotonic() >= deadline:
                    fail('RECOVERY_DEADLINE_EXCEEDED', 'hold clearance deadline exhausted', 6)
                self._append(connection, reg['id'], verified_snapshot)
                payload = {'hold_id': hold_id, 'hold_event_hash': hold['event_hash'], 'registration_id': reg['id'],
                    'plan_ref': plain(candidate_plan_ref), 'candidate_plan_ref': plain(candidate_plan_ref),
                    'snapshot_ref': plain(snapshot_ref), 'precheck_ref': plain(precheck_ref), 'targetcheck_ref': plain(targetcheck_ref),
                    'candidate_observation': native_resource, 'verification_observation': captured['resource'],
                    'verification_snapshot_ref': reference(verified_snapshot), 'target_state_hash': actual['target_state_hash'],
                    'target_state_version': actual['target_state_version'], 'read_sequence': actual['read_sequence']}
                event = self._event(connection, reg['book'], 'HOLD_CLEARED', payload)
                connection.execute('UPDATE books SET hold=NULL WHERE key=? AND hold=?', (reg['book'], hold_id))
            return Handle(cleared=True, hold_id=hold_id, event_head={'sequence': event['sequence'], 'hash': event['event_hash']},
                          event=event, target_effects=0)
