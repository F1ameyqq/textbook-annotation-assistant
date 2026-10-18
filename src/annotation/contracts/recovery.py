"""Approved A03 recovery contracts. No store authority or target effects live here.

The serialized contract proves shape, bytes and exact dependencies. Runtime must
independently prove current owner, original durable intent and the whole book.
Legacy C01 inputs keep their separate, unchanged validator and archive semantics.
"""
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

from .integrity import artifact_ref, content_digest, file_digest, read_json
from .models import relative_path
from .recovery_schema import FrozenSchemas
from .validation import fail, image_size

RECOVERY_SCHEMA_VERSION = '1.1.0-a-recovery-proposal'
RECOVERY_EXCHANGE_VERSION = 'a03-exchange-1'
RECOVERY_PROFILE = 'A03-P1-R2'
REF_FIELDS = {'artifact_id', 'revision', 'kind', 'content_hash'}
RESOURCE_FIELDS = {'path', 'sha256', 'media_type', 'origin'}
EVIDENCE_FIELDS = {'evidence_refs', 'before_evidence_refs', 'after_evidence_refs', 'submission_evidence_refs'}
NEW_KINDS = {'WriteIntent', 'ExecutionProgress', 'ReconciliationResult'}


class Node(dict):
    """JSON value with the attribute/model_dump interface used by A02 helpers."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as error:
            raise AttributeError(key) from error

    def model_dump(self, mode='json', **kwargs):
        return json.loads(json.dumps(self, ensure_ascii=False, allow_nan=False))


def _node(value):
    if isinstance(value, dict):
        return Node({k: _node(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_node(v) for v in value]
    return value


class RecoveryExchangeBundle(Node):
    """Validated value plus explicit resource root; still no execution permission."""
    def __init__(self, value, asset_root):
        super().__init__(_node(value))
        self.asset_root = Path(asset_root).resolve()
        self.profile = RECOVERY_PROFILE


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def target_state_digest(state):
    """Business state only; observation metadata, fencing and logs are excluded."""
    value = _data(state)
    target = value.get('target', value)
    result = {k: value[k] for k in ('target_key', 'source_ref', 'scope_id')}
    result.update({k: target[k] for k in ('platform_version', 'capabilities', 'directories', 'questions', 'frames')})
    result.update({k: value[k] for k in ('internal_bindings', 'frame_projections')})
    return canonical_hash(result)


def _data(value):
    return value.model_dump(mode='json') if hasattr(value, 'model_dump') else copy.deepcopy(value)


def _walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _is_ref(value):
    return isinstance(value, dict) and set(value) == REF_FIELDS


def _is_resource(value):
    return isinstance(value, dict) and {'path', 'sha256', 'media_type'} <= set(value)


def _identity(artifact):
    return artifact['book_id'], artifact['scope_id'], artifact['artifact_id'], artifact['revision']


def _artifact_node(artifact):
    return ('a',) + _identity(artifact)


def recovery_artifact_ref(artifact):
    return artifact_ref(_data(artifact))


def seal_recovery_artifact(data):
    value = _data(data)
    value['content_hash'] = '0' * 64
    FrozenSchemas().check(value, definition=value.get('kind'))
    value['content_hash'] = content_digest(value)
    return value


def recovery_schema():
    return copy.deepcopy(FrozenSchemas().documents['recovery-exchange.schema.json'])


class _Closure:
    def __init__(self, bundle, root, synthetic=True, *, schema_version=RECOVERY_SCHEMA_VERSION, schemas=None):
        self.bundle, self.root, self.synthetic = bundle, Path(root).resolve(), synthetic
        self.artifacts, self.evidence, self.graph, self.decoded = {}, {}, {}, {}
        self.schemas = FrozenSchemas() if schemas is None else schemas
        for artifact in bundle['artifacts']:
            key = _identity(artifact)
            if key in self.artifacts:
                fail('$.artifacts', 'ARTIFACT_IDENTITY_CONFLICT', 'immutable identity appears twice')
            if artifact['schema_version'] != schema_version:
                fail('$.artifacts', 'CROSS_VERSION_REFERENCE', 'mixed artifact namespace')
            if content_digest(artifact) != artifact['content_hash']:
                fail('$.artifacts', 'REFERENCE_HASH_MISMATCH', 'artifact canonical digest differs')
            self.artifacts[key] = artifact
        for record in bundle['evidence']:
            if record['evidence_id'] in self.evidence:
                fail('$.evidence', 'DUPLICATE_EVIDENCE_ID', 'evidence IDs must be unique')
            self.evidence[record['evidence_id']] = record
            if synthetic and record['mode'] != 'SYNTHETIC':
                fail('$.evidence', 'SYNTHETIC_ONLY', 'observed evidence is not simulated input')
        policies = set()
        for policy in bundle['policies']:
            key = (policy['policy_id'], policy['revision'])
            if key in policies or content_digest(policy) != policy['content_hash']:
                fail('$.policies', 'POLICY_CONFLICT', 'duplicate or incorrect policy binding')
            policies.add(key)

    def resolve(self, ref, consumer=None, kind=None):
        if not _is_ref(ref):
            fail('$.reference', 'SCHEMA', 'ordinary reference must be exact four-tuple')
        values = [a for a in self.artifacts.values() if (a['artifact_id'], a['revision']) == (ref['artifact_id'], ref['revision'])]
        if consumer:
            local = [a for a in values if (a['book_id'], a['scope_id']) == (consumer['book_id'], consumer['scope_id'])]
            if values and not local:
                fail('$.reference', 'REFERENCE_SCOPE_MISMATCH', 'ordinary dependency crosses book or scope')
            values = local
        if not values:
            fail('$.reference', 'MISSING_REFERENCE', 'exact artifact identity is absent')
        matches = [a for a in values if a['content_hash'] == ref['content_hash'] and a['kind'] == ref['kind']]
        if not matches:
            fail('$.reference', 'REFERENCE_HASH_MISMATCH', 'artifact kind/digest differs')
        if len(matches) != 1:
            fail('$.reference', 'REFERENCE_SCOPE_MISMATCH', 'reference requires an unambiguous owning scope')
        value = matches[0]
        if kind and value['kind'] != kind:
            fail('$.reference', 'RECOVERY_CHAIN_INVALID', 'unexpected dependency kind')
        if consumer and (value['book_id'], value['scope_id']) != (consumer['book_id'], consumer['scope_id']):
            fail('$.reference', 'REFERENCE_SCOPE_MISMATCH', 'ordinary dependency crosses book or scope')
        return value

    def resource(self, resource):
        if not RESOURCE_FIELDS <= set(resource):
            fail('$.resource', 'SCHEMA', 'recovery resource requires origin')
        if self.synthetic and resource['origin'] != 'SYNTHETIC':
            fail('$.resource', 'SYNTHETIC_ONLY', 'resource origin is not synthetic')
        try:
            relative_path(resource['path'])
        except ValueError as error:
            fail('$.resource.path', 'PATH_ESCAPE', str(error))
        target = (self.root / resource['path']).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            fail('$.resource.path', 'PATH_ESCAPE', 'resource escapes asset root')
        if not target.is_file():
            fail('$.resource', 'RESOURCE_MISSING', resource['path'])
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != resource['sha256']:
            fail('$.resource', 'RESOURCE_HASH_MISMATCH', resource['path'])
        if 'asset_id' in resource:
            try:
                size = image_size(target, resource['media_type'])
            except (OSError, ValueError) as error:
                fail('$.resource', 'IMAGE_HEADER', str(error))
            if size != (resource['width'], resource['height']):
                fail('$.resource', 'IMAGE_DIMENSIONS', 'declared image size differs')
        key = ('r', resource['path'], resource['sha256'], resource['media_type'])
        if key not in self.decoded:
            try:
                self.decoded[key] = read_json(target) if resource['media_type'] == 'application/json' else None
            except (OSError, ValueError) as error:
                fail('$.resource', 'JSON_INPUT', str(error))
        return key, self.decoded[key]

    def check(self):
        # Every consumer has its own traversal and declaration test. Parsed-byte
        # caching never inherits another artifact's declarations or scope.
        for artifact in self.artifacts.values():
            parent = _artifact_node(artifact)
            declared = [canonical_hash(ref) for ref in artifact['input_refs']]
            if len(set(declared)) != len(declared):
                fail('$.input_refs', 'DUPLICATE_ID', 'duplicate ordinary declaration')
            self.graph.setdefault(parent, set())
            seen = set()

            def visit(value, node, active, envelope=False):
                if (getattr(self, 'native', False) and isinstance(value, dict)
                        and value.get('format_version') == 'a03-runtime-event-prefix-2'):
                    # Native StaticPackage already validates the raw prefix and
                    # each typed frame's own exact declarations/book/scope/DAG.
                    # Reinterpreting every frame as this outer consumer would
                    # incorrectly widen ordinary scope or reject real history.
                    from .a03_native._closure import audit_prefix_resources
                    audit_prefix_resources(self, value)
                    return
                if _is_ref(value):
                    dep = self.resolve(value, artifact)
                    if canonical_hash(value) not in declared:
                        fail('$.input_refs', 'UNDECLARED_RESOURCE_REFERENCE', 'consumer must declare exact nested ordinary ref')
                    self.graph.setdefault(node, set()).add(_artifact_node(dep))
                    return
                # Malformed would-be ordinary refs may not hide as arbitrary JSON.
                if isinstance(value, dict) and REF_FIELDS <= set(value) and not envelope:
                    fail('$.reference', 'SCHEMA', 'ordinary reference has extra fields')
                if _is_resource(value):
                    resource_node, body = self.resource(value)
                    self.graph.setdefault(node, set()).add(resource_node)
                    self.graph.setdefault(resource_node, set())
                    if resource_node in active:
                        fail('$.resource', 'RESOURCE_REFERENCE_CYCLE', 'recursive resource cycle')
                    if resource_node not in seen:
                        seen.add(resource_node)
                        visit(body, resource_node, active | {resource_node})
                    return
                if isinstance(value, dict):
                    if self.synthetic:
                        if value.get('origin', 'SYNTHETIC') != 'SYNTHETIC' or value.get('provenance', 'SYNTHETIC') != 'SYNTHETIC':
                            fail('$.origin', 'SYNTHETIC_ONLY', 'nested real origin cannot be relabeled')
                        if value.get('evidence_mode', 'SYNTHETIC') != 'SYNTHETIC':
                            fail('$.producer', 'SYNTHETIC_ONLY', 'observed producer')
                        if 'region_id' in value and value.get('source', 'SYNTHETIC') != 'SYNTHETIC':
                            fail('$.source', 'SYNTHETIC_ONLY', 'region source is not synthetic')
                        if 'clue_id' in value and value.get('source', 'SYNTHETIC') != 'SYNTHETIC':
                            fail('$.source', 'SYNTHETIC_ONLY', 'coverage source is not synthetic')
                        if value.get('execution_mode', 'SIMULATED') not in ('SIMULATED', 'NOT_EXECUTED'):
                            fail('$.execution_mode', 'SYNTHETIC_ONLY', 'real execution mode')
                    for field, child in value.items():
                        if envelope and field == 'content_hash':
                            continue
                        if field in EVIDENCE_FIELDS and isinstance(child, list):
                            for evidence_id in child:
                                if isinstance(evidence_id, str):
                                    if evidence_id not in self.evidence:
                                        fail('$.evidence_refs', 'MISSING_REFERENCE', 'formal evidence ID is absent')
                                    visit(self.evidence[evidence_id]['resource'], node, active)
                        visit(child, node, active)
                elif isinstance(value, list):
                    for child in value:
                        visit(child, node, active)
            visit(artifact, parent, set(), envelope=True)
        # Unused evidence is still part of the all-synthetic input package.
        # Recurse for byte/origin/shape checks without inventing an Artifact
        # consumer or inheriting a different consumer's declaration closure.
        checked_evidence_resources = set()
        def audit_evidence(value, parent=None, active=frozenset()):
            if _is_resource(value):
                node, body = self.resource(value)
                if parent:
                    self.graph.setdefault(parent, set()).add(node)
                self.graph.setdefault(node, set())
                if node in active:
                    fail('$.evidence', 'RESOURCE_REFERENCE_CYCLE', 'nested evidence resource cycle')
                if node not in checked_evidence_resources:
                    checked_evidence_resources.add(node)
                    audit_evidence(body, node, active | {node})
                return
            if _is_ref(value):
                dependency = self.resolve(value)
                if parent:
                    self.graph.setdefault(parent, set()).add(_artifact_node(dependency))
                return
            if isinstance(value, dict):
                if REF_FIELDS <= set(value):
                    fail('$.evidence', 'SCHEMA', 'nested ordinary ref must have exactly four fields')
                if self.synthetic and (value.get('origin', 'SYNTHETIC') != 'SYNTHETIC' or
                        value.get('provenance', 'SYNTHETIC') != 'SYNTHETIC' or
                        value.get('evidence_mode', 'SYNTHETIC') != 'SYNTHETIC' or
                        ('region_id' in value and value.get('source', 'SYNTHETIC') != 'SYNTHETIC') or
                        ('clue_id' in value and value.get('source', 'SYNTHETIC') != 'SYNTHETIC') or
                        value.get('execution_mode', 'SIMULATED') not in ('SIMULATED', 'NOT_EXECUTED')):
                    fail('$.evidence', 'SYNTHETIC_ONLY', 'unused nested evidence has real provenance')
                for child in value.values():
                    audit_evidence(child, parent, active)
            elif isinstance(value, list):
                for child in value:
                    audit_evidence(child, parent, active)
        for record in self.evidence.values():
            audit_evidence(record['resource'])
        active, done = [], set()

        def dag(node):
            if node in active:
                cycle = active[active.index(node):]
                code = 'RESOURCE_REFERENCE_CYCLE' if any(n[0] == 'r' for n in cycle) else 'REFERENCE_CYCLE'
                fail('$.dependencies', code, 'dependency cycle')
            if node not in done:
                active.append(node)
                for dependency in self.graph.get(node, set()):
                    dag(dependency)
                active.pop()
                done.add(node)
        for node in self.graph:
            dag(node)


def _timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        fail('$.time', 'SCHEMA', 'expected timezone timestamp')
    if stamp.tzinfo is None:
        fail('$.time', 'SCHEMA', 'timestamp requires timezone')
    return stamp


def _snapshot_business_equal(first, second):
    if not isinstance(first, dict) or not isinstance(second, dict):
        return False
    metadata = {'observed_at', 'observed_version', 'observed_hash'}
    return {k: v for k, v in first.items() if k not in metadata} == {k: v for k, v in second.items() if k not in metadata}


def _scope(ctx):
    for source in ctx.artifacts.values():
        if source['kind'] != 'SourceBundle':
            continue
        p = source['payload']
        integrity = p['scope_integrity']
        if integrity['status'] != 'SYNTHETIC_COMPLETE' or integrity['basis'] != 'FIXTURE' or integrity['proof'] is None:
            fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'A03 requires explicit complete synthetic fixture proof')
        _, proof = ctx.resource(integrity['proof'])
        if not isinstance(proof, dict):
            fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'proof must be JSON')
        required = {'book_id': source['book_id'], 'scope_id': source['scope_id'],
                    'pages_expected': p['pages_expected'], 'pages_acquired': p['pages_acquired'],
                    'scope_manifest': p['scope_manifest']}
        if proof.get('origin') != 'SYNTHETIC' or proof.get('basis') != 'FIXTURE' or proof.get('complete') is not True:
            fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'proof fixture binding absent')
        if any(proof.get(k) != v for k, v in required.items()) or p['scope_manifest'] is None:
            fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'proof book/scope/page/question manifest differs')
        assets = [{k: a[k] for k in ('asset_id', 'path', 'sha256', 'width', 'height')} for a in p['assets']]
        if proof.get('assets') != assets or set(p['pages_expected']) != set(p['pages_acquired']):
            fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'proof assets/pages differ')
        rows = proof.get('per_page_questions', [])
        if {r.get('asset_id') for r in rows} != set(p['pages_expected']) or len(rows) != len(p['pages_expected']):
            fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'one independent enumeration per fixture page required')
        questions = set()
        for row in rows:
            if row.get('enumeration_complete') is not True or not isinstance(row.get('question_ids'), list):
                fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'incomplete page enumeration')
            if len(row['question_ids']) != len(set(row['question_ids'])):
                fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'duplicate page question')
            questions.update(row['question_ids'])
        if questions != set(p['scope_manifest']) or len(set(p['scope_manifest'])) != len(p['scope_manifest']):
            fail('$.scope_integrity', 'SYNTHETIC_COMPLETE_REQUIRED', 'page enumeration differs from full scope')


def _plan_action(ctx, plan_ref, action_id, consumer):
    plan = ctx.resolve(plan_ref, consumer, 'ApplyPlan')
    actions = [a for a in plan['payload']['actions'] if a['action_id'] == action_id]
    if len(actions) != 1:
        fail('$.action_id', 'RECOVERY_CHAIN_INVALID', 'action absent or duplicate in exact plan')
    return plan, actions[0]


def obligation_id(intent):
    p = _data(intent)['payload']
    return 'obl-' + canonical_hash({'journal_id': p['journal_id'], 'target_key': p['target_key'],
                                    'intent_ref': recovery_artifact_ref(intent),
                                    'journal_sequence': p['journal_sequence'],
                                    'journal_head_hash': p['journal_head_hash']})


def plan_dependency_digest(plan, source_ref, target_session_id, prepared_before):
    p = _data(plan)['payload']
    dependencies = {k: p[k] for k in ('graph', 'precheck', 'targetcheck', 'snapshot', 'policy',
                                     'execution_mode', 'session_mode', 'required_capabilities')}
    return canonical_hash({'plan_dependencies_digest': canonical_hash(dependencies), 'source_ref': _data(source_ref),
                           'target_session_id': target_session_id, 'comparator_version': 'a02-facts-1',
                           'prepared_before_sha256': _data(prepared_before)['sha256']})


def _intents(ctx):
    seen = set()
    for intent in ctx.artifacts.values():
        if intent['kind'] != 'WriteIntent':
            continue
        p = intent['payload']
        plan, action = _plan_action(ctx, p['plan_ref'], p['action_id'], intent)
        if p['action_digest'] != canonical_hash(action):
            fail('$.action_digest', 'ACTION_DIGEST_MISMATCH', 'intent complete action digest differs')
        graph = ctx.resolve(plan['payload']['graph'], intent, 'QuestionGraph')
        if p['source_ref'] != graph['payload']['source'] or p['before_snapshot_ref'] != plan['payload']['snapshot']:
            fail('$.intent', 'RECOVERY_CHAIN_INVALID', 'intent source/initial snapshot differs')
        if p['question_id'] != action['target']['question_id'] or p['source_entity_ids'] != action['source_entity_ids']:
            fail('$.intent', 'ACTION_DIGEST_MISMATCH', 'intent question/entities differ')
        if p['target_key']['book_id'] != intent['book_id'] or p['target_key']['target_id'] != action['target']['target_id']:
            fail('$.target_key', 'TARGET_IDENTITY_MISMATCH', 'intent target differs')
        key = canonical_hash([p['target_key'], p['plan_ref'], p['action_id']])
        if key in seen:
            fail('$.intent', 'INTENT_CONFLICT', 'duplicate plan/action intent')
        seen.add(key)
        _, prepared = ctx.resource(p['prepared_before'])
        if not isinstance(prepared, dict) or prepared.get('action_id') != p['action_id']:
            fail('$.prepared_before', 'OBSERVATION_BINDING_MISMATCH', 'prepare does not bind action')
        if prepared.get('source_ref') != p['source_ref'] or prepared.get('target_session_id') != p['target_session_id']:
            fail('$.prepared_before', 'OBSERVATION_BINDING_MISMATCH', 'prepare source/session differs')
        if p['plan_dependency_digest'] != plan_dependency_digest(plan, p['source_ref'], p['target_session_id'], p['prepared_before']):
            fail('$.plan_dependency_digest', 'ACTION_DIGEST_MISMATCH', 'exact plan dependency digest differs')
        if _timestamp(prepared.get('observed_at')) > _timestamp(p['intent_committed_at']):
            fail('$.intent', 'OBSERVATION_NOT_FRESH', 'prepare occurs after intent')


def _observation_binding(ctx, resolution, intent):
    p, ip = resolution['payload'], intent['payload']
    fields = ('observed_snapshot_ref', 'readback', 'read_sequence', 'target_state_version', 'target_state_hash')
    if p['observation'] in ('MATCH', 'ABSENT') and any(p[k] is None for k in fields):
        fail('$.resolution', 'OBSERVATION_BINDING_MISMATCH', 'decisive observation requires complete actual read bindings')
    if _timestamp(p['observed_at']) <= _timestamp(ip['intent_committed_at']):
        fail('$.resolution', 'OBSERVATION_NOT_FRESH', 'observation must follow original intent')
    _, prepared = ctx.resource(ip['prepared_before'])
    if p['read_sequence'] is not None:
        if type(prepared.get('read_sequence')) is not int or prepared['read_sequence'] >= p['read_sequence']:
            fail('$.resolution', 'OBSERVATION_NOT_FRESH', 'read sequence must follow the original actual prepare read')
    if p['readback'] is None:
        if p['observation'] != 'INDETERMINATE' or p['resolution'] != 'STILL_UNKNOWN':
            fail('$.resolution', 'OBSERVATION_BINDING_MISMATCH', 'failed read cannot decide outcome')
        return
    _, readback = ctx.resource(p['readback'])
    if not isinstance(readback, dict):
        fail('$.readback', 'OBSERVATION_BINDING_MISMATCH', 'readback must be complete JSON observation')
    required = {'observation_id': p['observation_id'], 'observed_at': p['observed_at'],
                'read_sequence': p['read_sequence'], 'target_state_version': p['target_state_version'],
                'target_state_hash': p['target_state_hash'], 'target_key': ip['target_key'],
                'source_ref': ip['source_ref'], 'scope_id': intent['scope_id'],
                'target_session_id': ip['target_session_id']}
    if any(readback.get(k) != v for k, v in required.items()):
        fail('$.readback', 'OBSERVATION_BINDING_MISMATCH', 'observation identity/state differs')
    if p['observed_snapshot_ref'] is not None:
        snapshot = ctx.resolve(p['observed_snapshot_ref'], resolution, 'PlatformSnapshot')['payload']
        if (snapshot['observed_at'], snapshot['observed_version'], snapshot['observed_hash']) != (p['observed_at'], p['target_state_version'], p['target_state_hash']):
            fail('$.snapshot', 'OBSERVATION_BINDING_MISMATCH', 'snapshot observation differs')
        view = readback.get('view')
        if not isinstance(view, dict) or not _snapshot_business_equal(view.get('target'), snapshot):
            fail('$.readback', 'OBSERVATION_BINDING_MISMATCH', 'readback view differs from exact snapshot')
        digest_input = dict(view, target_key=ip['target_key'], source_ref=ip['source_ref'], scope_id=intent['scope_id'])
        if target_state_digest(digest_input) != p['target_state_hash']:
            fail('$.readback', 'OBSERVATION_BINDING_MISMATCH', 'business state digest differs')
    if p['observation'] in ('MATCH', 'ABSENT'):
        if readback.get('scope_complete') is not True or not p['evidence_refs']:
            fail('$.readback', 'OBSERVATION_BINDING_MISMATCH', 'decisive read needs complete scope and evidence')
        ids = readback.get('action_ids')
        if ids is not None and p['action_id'] not in ids:
            fail('$.readback', 'OBSERVATION_BINDING_MISMATCH', 'action is outside observed relevant scope')


def _resolutions(ctx):
    successors, heads, observations, attempts = {}, {}, set(), set()
    resolutions = [a for a in ctx.artifacts.values() if a['kind'] == 'ReconciliationResult']
    for resolution in resolutions:
        p = resolution['payload']
        intent = ctx.resolve(p['intent_ref'], resolution, 'WriteIntent')
        ip = intent['payload']
        if (p['plan_ref'], p['action_id'], p['action_digest']) != (ip['plan_ref'], ip['action_id'], ip['action_digest']):
            fail('$.resolution', 'RECOVERY_CHAIN_INVALID', 'resolution plan/action differs from intent')
        if p['obligation_id'] != obligation_id(intent):
            fail('$.obligation_id', 'RECOVERY_CHAIN_INVALID', 'obligation must derive from exact original intent')
        expected = {'MATCH': 'RESOLVED_APPLIED', 'ABSENT': 'RESOLVED_NOT_APPLIED',
                    'CONFLICT': 'STILL_UNKNOWN', 'INDETERMINATE': 'STILL_UNKNOWN'}[p['observation']]
        if p['resolution'] != expected or (p['observation'] == 'MATCH' and not p['platform_ids']):
            fail('$.resolution', 'RECOVERY_CHAIN_INVALID', 'observation/outcome/IDs inconsistent')
        if p['observation'] == 'ABSENT' and p['platform_ids']:
            fail('$.resolution', 'RECOVERY_CHAIN_INVALID', 'ABSENT cannot claim applied platform IDs')
        if p['observation_id'] in observations:
            fail('$.observation_id', 'OBSERVATION_NOT_FRESH', 'observation identity reused')
        observations.add(p['observation_id'])
        attempt = (p['recovery_call_id'], canonical_hash(p['intent_ref']), p['attempt_index'])
        if attempt in attempts:
            fail('$.attempt_index', 'RECOVERY_CHAIN_INVALID', 'recovery attempt reused')
        attempts.add(attempt)
        previous = p['previous_resolution_ref']
        chain_key = canonical_hash(p['intent_ref'])
        previous_key = canonical_hash(previous) if previous else ('ROOT:' + chain_key)
        if previous_key in successors:
            fail('$.previous_resolution_ref', 'RESOLUTION_FORK', 'one unique successor required')
        successors[previous_key] = resolution
        if previous:
            prior = ctx.resolve(previous, resolution, 'ReconciliationResult')['payload']
            if prior['resolution'] != 'STILL_UNKNOWN':
                fail('$.previous_resolution_ref', 'RESOLUTION_TERMINAL', 'terminal resolution has no successor')
            for field in ('intent_ref', 'plan_ref', 'action_id', 'action_digest', 'obligation_id', 'original_receipt_ref'):
                if prior[field] != p[field]:
                    fail('$.previous_resolution_ref', 'RECOVERY_CHAIN_INVALID', 'resolution chain changes binding')
            if (_timestamp(p['observed_at']) <= _timestamp(prior['observed_at']) or
                    (p['read_sequence'] is not None and prior['read_sequence'] is not None and p['read_sequence'] <= prior['read_sequence'])):
                fail('$.resolution', 'OBSERVATION_NOT_FRESH', 'chain must use a new increasing actual observation')
            if p['recovery_call_id'] == prior['recovery_call_id'] and p['attempt_index'] != prior['attempt_index'] + 1:
                fail('$.attempt_index', 'RECOVERY_CHAIN_INVALID', 'same invocation attempt index must increase once')
        elif p['attempt_index'] != 1:
            fail('$.attempt_index', 'RECOVERY_CHAIN_INVALID', 'new chain starts at first attempt')
        if p['original_receipt_ref'] is not None:
            receipt = ctx.resolve(p['original_receipt_ref'], resolution, 'ExecutionReceipt')
            results = [r for r in receipt['payload']['results'] if r['action_id'] == p['action_id']]
            if receipt['payload']['plan'] != p['plan_ref'] or len(results) != 1 or results[0]['outcome'] != 'UNKNOWN' or results[0]['intent_ref'] != p['intent_ref']:
                fail('$.original_receipt_ref', 'RECOVERY_CHAIN_INVALID', 'resolution requires exact original UNKNOWN intent result')
        _observation_binding(ctx, resolution, intent)
    for resolution in resolutions:
        if canonical_hash(recovery_artifact_ref(resolution)) not in successors:
            heads[canonical_hash(resolution['payload']['intent_ref'])] = resolution
    return heads


def _unattempted(ctx, fact, consumer, plan, action):
    if getattr(ctx, 'native', False):
        from .a03_native._closure import validate_unattempted_basis
        return validate_unattempted_basis(ctx, fact, consumer, plan, action)
    from .prefix_validation import validate_prefix
    basis_ref = fact['unattempted_basis']
    if basis_ref is None:
        fail('$.fact', 'NOT_ATTEMPTED_WITHOUT_ABSENT', 'never-called result requires its dedicated basis')
    _, basis = ctx.resource(basis_ref)
    ctx.schemas.check(basis, 'unattempted-basis.schema.json')
    required = {'plan_ref': fact['plan_ref'], 'action_id': fact['action_id'],
                'action_digest': fact['action_digest'], 'scope_id': consumer['scope_id']}
    if any(basis.get(k) != v for k, v in required.items()) or basis['comparison'] != 'ABSENT':
        fail('$.unattempted_basis', 'NOT_ATTEMPTED_WITHOUT_ABSENT', 'basis does not prove this exact tail action absent')
    if fact['intent_ref'] is not None or fact['obligation_id'] is not None or fact['resolution_ref'] is not None or fact['result']['intent_ref'] is not None:
        fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'unattempted fact cannot fabricate an intent or obligation')
    _, prefix = ctx.resource(basis['complete_uncalled_prefix'])
    errors = validate_prefix(prefix, plan, basis['expected_event_head'], fact['action_id'])
    if errors:
        fail('$.unattempted_basis', errors[0], 'invalid complete accepted-plan-to-head prefix')
    if (fact['journal_sequence'], fact['predecessor_hash']) != (basis['expected_event_head']['sequence'] + 1, basis['expected_event_head']['hash']):
        fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'tail result does not bind exact CAS predecessor')
    if fact['prepared_before'] != basis['readonly_prepared_ref'] or fact['readback'] != basis['second_observation_ref']:
        fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'fact must consume both dedicated actual reads')
    _, first = ctx.resource(basis['first_observation_ref'])
    _, second = ctx.resource(basis['second_observation_ref'])
    _, prepared = ctx.resource(basis['readonly_prepared_ref'])
    if not all(isinstance(item, dict) for item in (first, second, prepared)):
        fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'readonly observations must be JSON')
    for item in (first, second):
        expected = {'target_key': basis['target_key'], 'target_session_id': basis['target_session_id'],
                    'source_ref': basis['source_ref'], 'scope_id': basis['scope_id']}
        if any(item.get(k) != v for k, v in expected.items()) or item.get('scope_complete') is not True:
            fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'tail reads require exact full relevant scope')
    if (first.get('observation_id') == second.get('observation_id') or
            type(first.get('read_sequence')) is not int or type(second.get('read_sequence')) is not int or
            first['read_sequence'] >= second['read_sequence'] or
            _timestamp(first.get('observed_at')) >= _timestamp(second.get('observed_at'))):
        fail('$.fact', 'OBSERVATION_NOT_FRESH', 'two distinct increasing reads are required')
    if prepared.get('observation_id') != first.get('observation_id') or prepared.get('read_sequence') != first.get('read_sequence'):
        fail('$.prepared_before', 'OBSERVATION_BINDING_MISMATCH', 'readonly prepare must derive from first actual read')
    if fact['result']['outcome'] != 'NOT_APPLIED' or fact['result']['effect_match'] != 'ABSENT':
        fail('$.fact', 'NOT_ATTEMPTED_WITHOUT_ABSENT', 'tail evidence cannot imply execution')
    # A prior result resource and its intent must agree with their exact events.
    for event in prefix['events']:
        p = event['payload']
        if event['event'] == 'WRITE_INTENT_COMMITTED':
            intent = ctx.resolve(p['intent_ref'], consumer, 'WriteIntent')
            ip = intent['payload']
            if (ip['journal_sequence'], ip['journal_head_hash'], ip['action_digest']) != (event['sequence'], event['previous_hash'], p['action_digest']):
                fail('$.prefix', 'RECOVERY_CHAIN_INVALID', 'intent event and immutable intent disagree')
        if event['event'] in ('ACTION_RESULT_COMMITTED', 'UNATTEMPTED_ABSENCE_COMMITTED'):
            _, prior = ctx.resource(p['fact'])
            if (prior['journal_sequence'], prior['predecessor_hash'], prior['action_id'], prior['action_digest']) != (event['sequence'], event['previous_hash'], p['action_id'], p['action_digest']):
                fail('$.prefix', 'RECOVERY_CHAIN_INVALID', 'prior immutable result and event disagree')


def _fact(ctx, resource, consumer):
    _, fact = ctx.resource(resource)
    ctx.schemas.check(fact, 'action-fact.schema.json')
    plan, action = _plan_action(ctx, fact['plan_ref'], fact['action_id'], consumer)
    if fact['action_digest'] != canonical_hash(action) or fact['result']['action_id'] != fact['action_id']:
        fail('$.fact', 'ACTION_DIGEST_MISMATCH', 'fact action differs')
    result = fact['result']
    # C01 result constraints are retained without weakening new required fields.
    from .models import ActionResult
    from pydantic import ValidationError
    try:
        ActionResult.model_validate({k: v for k, v in result.items() if k not in ('attempt_fact', 'attempt_evidence_refs', 'intent_ref') and k != 'readback'} |
                                    {'readback': {k: v for k, v in result['readback'].items() if k != 'origin'} if result['readback'] else None})
    except ValidationError as error:
        fail('$.fact.result', 'SCHEMA', str(error))
    if result['readback'] != fact['readback'] or result['intent_ref'] != fact['intent_ref']:
        fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'embedded result must exactly bind fact readback and intent')
    if not result['attempt_evidence_refs']:
        fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'every result requires explicit attempt evidence')
    if fact['origin_phase'] == 'UNATTEMPTED_ABSENCE':
        if result['attempt_fact'] != 'NOT_ATTEMPTED':
            fail('$.fact', 'NOT_ATTEMPTED_WITHOUT_ABSENT', 'tail fact must retain never-called classification')
        _unattempted(ctx, fact, consumer, plan, action)
    else:
        if fact['intent_ref'] is None or result['attempt_fact'] in ('NOT_ATTEMPTED', 'LEGACY_UNRECORDED') or fact['unattempted_basis'] is not None:
            fail('$.fact', 'LEGACY_UNRECORDED', 'attempted fact needs original intent, no tail basis')
        intent = ctx.resolve(fact['intent_ref'], consumer, 'WriteIntent')
        if fact['obligation_id'] != obligation_id(intent) or intent['payload']['plan_ref'] != fact['plan_ref'] or intent['payload']['action_id'] != fact['action_id']:
            fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'fact obligation or original action differs')
        if fact['prepared_before'] != intent['payload']['prepared_before']:
            fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'fact cannot replace original dispatch prepare')
        if fact['origin_phase'] == 'RECOVERY':
            if fact['resolution_ref'] is None:
                fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'recovery fact requires resolution')
            resolution = ctx.resolve(fact['resolution_ref'], consumer, 'ReconciliationResult')['payload']
            if resolution['intent_ref'] != fact['intent_ref'] or resolution['readback'] != fact['readback']:
                fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'recovery fact does not bind resolution')
            expected = {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[resolution['resolution']]
            if result['outcome'] != expected:
                fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'recovery fact outcome differs from resolution')
        elif fact['resolution_ref'] is not None:
            fail('$.fact', 'RECOVERY_CHAIN_INVALID', 'execution fact cannot claim later resolution')
    if fact['observed_snapshot_ref'] is not None:
        snapshot = ctx.resolve(fact['observed_snapshot_ref'], consumer, 'PlatformSnapshot')
        if fact['readback'] is not None:
            _, readback = ctx.resource(fact['readback'])
            if isinstance(readback, dict) and not _snapshot_business_equal(readback.get('view', {}).get('target'), snapshot['payload']):
                fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'result readback differs from exact snapshot')
    if fact['origin_phase'] != 'UNATTEMPTED_ABSENCE' and result['outcome'] != 'UNKNOWN':
        _, actual = ctx.resource(fact['readback'])
        if not isinstance(actual, dict):
            fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'conclusive result requires a complete JSON observation')
        # Both normal and recovered facts preserve the same public observation
        # binding rules. A content-addressed but forged state hash is not enough.
        observation_payload = {k: actual.get(k) for k in ('observed_at', 'observation_id', 'read_sequence',
                                                         'target_state_version', 'target_state_hash')}
        observation_payload.update(observed_snapshot_ref=fact['observed_snapshot_ref'], readback=fact['readback'],
                                   observation=result['effect_match'], evidence_refs=[fact['readback']], action_id=fact['action_id'])
        _observation_binding(ctx, dict(consumer, payload=observation_payload), intent)
    return fact


def unknown_fact_issue(fact):
    """Deterministic interpretation of an UNKNOWN fact, never write authority.

    Callers validating ownership must first validate the whole immutable fact;
    this pure constructor deliberately performs no I/O or runtime imports.
    """
    if fact['result']['outcome'] != 'UNKNOWN':
        return None
    return {'issue_id': 'issue-save-unknown-' + canonical_hash(fact)[:32], 'code': 'SAVE_UNKNOWN',
        'scope_type': 'action', 'scope_id': fact['action_id'],
        'evidence_refs': list(fact['result']['after_evidence_refs'] or fact['result']['before_evidence_refs']),
        'severity': 'blocking', 'blocks': ['APPLY', 'COMPLETE'],
        'suggested_strategy': {'strategy_id': 'RECONCILE', 'max_attempts': 0, 'max_cost': 0.0},
        'reason': 'Actual controlled read did not establish this action\'s effect; retain original UNKNOWN'}


def _native_receipt_issue_ownership(ctx):
    """Rebuild full, consumer-bound proofs from each receipt's own fact bytes.

    The private C01 caller supplies this original closure, never an ID whitelist.
    Recheck bytes/declarations/source/intents here so the proof is independently
    derived even when that private entry is called directly. No latest pointers
    or effective recovery outcome can replace an old receipt's facts.
    """
    if type(ctx) is not _Closure or not getattr(ctx, 'native', False):
        fail('$.receipt', 'NATIVE_ISSUE_PROOF_REQUIRED', 'original native closure required, not allowed IDs')
    ctx.check()
    _scope(ctx)
    _intents(ctx)
    _resolutions(ctx)
    proofs = {}
    for receipt in ctx.artifacts.values():
        if receipt['kind'] != 'ExecutionReceipt':
            continue
        p = receipt['payload']
        plan = ctx.resolve(p['plan'], receipt, 'ApplyPlan')
        results, resources = p['results'], p['action_fact_refs']
        if p['execution_mode'] == 'NOT_EXECUTED':
            if results or resources:
                fail('$.receipt', 'RECOVERY_CHAIN_INVALID', 'not executed has no result facts')
        elif ([r['action_id'] for r in results] != [a['action_id'] for a in plan['payload']['actions']]
                or len(resources) != len(results)):
            fail('$.receipt', 'ACTION_COVERAGE', 'one immutable fact per original action required')
        issues = []
        for result, resource in zip(results, resources):
            fact = _fact(ctx, resource, receipt)
            if fact['plan_ref'] != p['plan'] or fact['result'] != result:
                fail('$.receipt', 'RECOVERY_CHAIN_INVALID', 'receipt must aggregate its exact immutable facts')
            issue = unknown_fact_issue(fact)
            if issue is None:
                continue
            intent = ctx.resolve(fact['intent_ref'], receipt, 'WriteIntent')
            _, actual = ctx.resource(fact['readback'])
            if not isinstance(actual, dict) or fact['readback'] not in result['attempt_evidence_refs']:
                fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'UNKNOWN needs its actual attempted-read evidence')
            observation = {k: actual.get(k) for k in ('observed_at', 'observation_id', 'read_sequence',
                'target_state_version', 'target_state_hash')}
            observation.update(observed_snapshot_ref=fact['observed_snapshot_ref'], readback=fact['readback'],
                observation='INDETERMINATE', evidence_refs=[fact['readback']], action_id=fact['action_id'])
            _observation_binding(ctx, dict(receipt, payload=observation), intent)
            _, prepared = ctx.resource(intent['payload']['prepared_before'])
            if any(actual.get(k) != prepared.get(k) or actual.get(k) is None
                   for k in ('store_id', 'target_store_id')):
                fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'UNKNOWN read must bind original target store')
            for field, expected in (('before_evidence_refs', fact['prepared_before']),
                                    ('after_evidence_refs', fact['readback'])):
                if not result[field] or any(ctx.evidence[e]['resource'] != expected for e in result[field]):
                    fail('$.fact', 'OBSERVATION_BINDING_MISMATCH', 'UNKNOWN evidence must bind exact prepare/readback')
            issues.append(issue)
        if p['unresolved_issue_ids'] != [issue['issue_id'] for issue in issues]:
            fail('$.receipt.unresolved_issue_ids', 'NATIVE_ISSUE_OWNERSHIP',
                 'missing, extra, duplicated or borrowed UNKNOWN issue binding')
        proofs[_identity(receipt)] = {'consumer_ref': recovery_artifact_ref(receipt),
            'fact_refs': copy.deepcopy(resources), 'issues': issues}
    return proofs


def _receipts_progress(ctx, heads):
    for artifact in ctx.artifacts.values():
        p, kind = artifact['payload'], artifact['kind']
        if kind == 'ExecutionReceipt':
            plan = ctx.resolve(p['plan'], artifact, 'ApplyPlan')
            if p['execution_mode'] == 'NOT_EXECUTED':
                if p['results'] or p['action_fact_refs']:
                    fail('$.receipt', 'RECOVERY_CHAIN_INVALID', 'not executed has no result facts')
                continue
            if [r['action_id'] for r in p['results']] != [a['action_id'] for a in plan['payload']['actions']] or len(p['action_fact_refs']) != len(p['results']):
                fail('$.receipt', 'ACTION_COVERAGE', 'complete receipt requires one fact/result for every plan action in order')
            for result, resource in zip(p['results'], p['action_fact_refs']):
                fact = _fact(ctx, resource, artifact)
                if fact['plan_ref'] != p['plan'] or fact['result'] != result:
                    fail('$.receipt', 'RECOVERY_CHAIN_INVALID', 'receipt must aggregate exact immutable facts')
        if kind == 'ExecutionProgress':
            plan = ctx.resolve(p['plan_ref'], artifact, 'ApplyPlan')
            if [r['action_id'] for r in p['actions']] != [a['action_id'] for a in plan['payload']['actions']]:
                fail('$.progress', 'ACTION_COVERAGE', 'progress includes all actions exactly in original order')
            for item in p['actions']:
                outcome = 'UNDETERMINED'
                if item['attempt_fact'] == 'LEGACY_UNRECORDED':
                    outcome = 'UNKNOWN'
                    if item['intent_ref'] is not None or item['resolution_head_ref'] is not None:
                        fail('$.progress', 'LEGACY_UNRECORDED', 'legacy no-intent state cannot acquire a resolution')
                if item['result_fact'] is not None:
                    fact = _fact(ctx, item['result_fact'], artifact)
                    if fact['plan_ref'] != p['plan_ref'] or fact['action_id'] != item['action_id'] or fact['result']['attempt_fact'] != item['attempt_fact'] or fact['intent_ref'] != item['intent_ref']:
                        fail('$.progress', 'RECOVERY_CHAIN_INVALID', 'progress fact/action/attempt differs')
                    outcome = fact['result']['outcome']
                elif item['intent_ref'] is not None:
                    outcome = 'UNKNOWN'
                if item['resolution_head_ref'] is not None:
                    resolution = _consumer_resolution_head(ctx, artifact, item['resolution_head_ref'], heads,
                                                           intent_ref=item['intent_ref'], plan_ref=p['plan_ref'],
                                                           action_id=item['action_id'])
                    outcome = {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[resolution['payload']['resolution']]
                if item['effective_outcome'] != outcome:
                    fail('$.progress', 'RECOVERY_CHAIN_INVALID', 'effective projection lacks exact supporting fact/chain')
                if item['attempt_fact'] == 'NOT_ATTEMPTED' and outcome not in ('UNDETERMINED', 'NOT_APPLIED'):
                    fail('$.progress', 'NOT_ATTEMPTED_WITHOUT_ABSENT', 'never-called action cannot receive invented outcome')


def _consumer_resolution_head(ctx, consumer, ref, heads, *, intent_ref, plan_ref, action_id):
    """Validate a head in this immutable consumer's declared chain prefix.

    A later append does not rewrite an older progress/report. The complete
    global chain remains fork/terminal checked by _resolutions; only current
    eligibility projects that global head. Ordinary Artifact payloads are not
    inherited into this consumer's declarations while inspecting its prefix.
    """
    selected = ctx.resolve(ref, consumer, 'ReconciliationResult')
    p = selected['payload']
    if intent_ref is None or (p['intent_ref'], p['plan_ref'], p['action_id']) != (intent_ref, plan_ref, action_id):
        fail('$.recovery_refs', 'RECOVERY_CHAIN_INVALID', 'consumer resolution changes exact intent/plan/action binding')
    current = heads.get(canonical_hash(intent_ref))
    lineage = {}
    while current is not None:
        current_ref = recovery_artifact_ref(current)
        token = canonical_hash(current_ref)
        if token in lineage:
            fail('$.recovery_refs', 'RECOVERY_CHAIN_INVALID', 'resolution ancestry cycle')
        lineage[token] = len(lineage)
        previous = current['payload']['previous_resolution_ref']
        current = ctx.resolve(previous, consumer, 'ReconciliationResult') if previous else None
    token = canonical_hash(ref)
    if token not in lineage:
        fail('$.recovery_refs', 'RECOVERY_CHAIN_INVALID', 'selected head is not in the unique valid intent chain')
    selected_position = lineage[token]
    visited_resources = set()

    def declared(node):
        if node[0] == 'r':
            if node not in visited_resources:
                visited_resources.add(node)
                for child in ctx.graph.get(node, set()):
                    declared(child)
        elif node[0] == 'a':
            dependency = ctx.artifacts.get(tuple(node[1:]))
            if dependency and dependency['kind'] == 'ReconciliationResult' and dependency['payload']['intent_ref'] == intent_ref:
                position = lineage.get(canonical_hash(recovery_artifact_ref(dependency)))
                if position is None or position < selected_position:
                    fail('$.recovery_refs', 'RECOVERY_CHAIN_INVALID', 'consumer declares a successor beyond its selected historical head')
            # Do not traverse an ordinary referenced Artifact's payload.
    for dependency in ctx.graph.get(_artifact_node(consumer), set()):
        declared(dependency)
    return selected


def _legacy_projection(ctx):
    from .validation import validate_bundle, _validate_native_projection
    data, mapped = _legacy_projection_value(ctx)
    if data is None:
        return None, mapped
    return (_validate_native_projection(data, ctx) if getattr(ctx, 'native', False) else validate_bundle(data)), mapped


def _legacy_projection_value(ctx):
    """Reuse C01 geometry/ownership/check/plan rules on a private value projection.

No projected value escapes as history or execution authority. New recovery
chains/Resources are separately validated above; original inputs stay unchanged.
"""
    data = copy.deepcopy(ctx.bundle)
    keep = [a for a in data['artifacts'] if a['kind'] not in NEW_KINDS and a['kind'] != 'BatchReport']
    if getattr(ctx, 'native', False):
        # Native POST has its own stricter typed action/head/report-read grammar.
        # The full original history has already passed the mixed closure. This
        # private C01 business view is never returned as an admission package.
        keep = [a for a in keep if not (a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY')]
    # Keep CheckReport issue declarations and their unchanged C01 invariants.
    # Additional effective recovery semantics are validated separately below.
    if any(a['kind'] == 'SourceBundle' and not a['payload']['scope_manifest'] for a in keep):
        if any(a['kind'] in ('ApplyPlan', 'QuestionGraph', 'ExecutionReceipt') for a in keep):
            fail('$.scope_manifest', 'NO_ACTIONS', 'unknown/zero scope cannot create a plan or complete batch')
        return None, {}
    scopes = {(a['book_id'], a['scope_id']) for a in keep}
    if len(scopes) > 1:
        for book, scope in scopes:
            local = dict(ctx.bundle, artifacts=[a for a in ctx.bundle['artifacts'] if (a['book_id'], a['scope_id']) == (book, scope)])
            _legacy_projection(_Closure(local, ctx.root, synthetic=ctx.synthetic))
        # Eligibility invokes this function with only the requested scope.
        return None, {}
    known = {(a['artifact_id'], a['revision']): a for a in keep}

    def strip(value):
        if isinstance(value, list):
            return [strip(v) for v in value]
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in ('origin', 'scope_integrity', 'recovery_refs', 'progress_refs',
                    'action_fact_refs', 'attempt_fact', 'attempt_evidence_refs', 'intent_ref') and
                    (not getattr(ctx, 'native', False) or k not in ('synthetic_run_ref', 'verification_context'))}
        return value
    data = strip(data)
    data['format_version'] = 'c01-exchange-1'
    data['artifacts'] = []
    mapped = {}

    def convert(artifact):
        key = (artifact['artifact_id'], artifact['revision'])
        if key in mapped:
            return mapped[key]
        value = strip(artifact)
        value['schema_version'] = '1.0.0-a-proposal'
        value['input_refs'] = [r for r in value['input_refs'] if (r['artifact_id'], r['revision']) in known]

        def remap(item, envelope=False):
            if _is_ref(item):
                k = (item['artifact_id'], item['revision'])
                if k not in known:
                    fail('$.projection', 'MISSING_REFERENCE', 'legacy semantic projection lacks dependency')
                return recovery_artifact_ref(convert(known[k]))
            if isinstance(item, dict):
                return {k: remap(v) for k, v in item.items()}
            if isinstance(item, list):
                return [remap(v) for v in item]
            return item
        value = remap(value, True)
        if getattr(ctx, 'native', False):
            # C01 hashes its typed JSON representation (e.g. float boxes).
            # Normalize this private semantic view before computing its digest;
            # native input bytes, identities and authority remain untouched.
            from .models import ExchangeBundle
            typed = ExchangeBundle.model_validate({'format_version': 'c01-exchange-1',
                'evidence': data['evidence'], 'policies': data['policies'], 'artifacts': [value]})
            value = typed.artifacts[0].model_dump(mode='json')
        value['content_hash'] = content_digest(value)
        mapped[key] = value
        return value
    data['artifacts'] = [convert(a) for a in keep]
    # Byte checking has already used the original exact resource declarations;
    # C01 here only supplies the unchanged semantic/geometry rules.
    return data, mapped


def _outcomes(ctx, heads, target_key, scope_id):
    outcomes, unresolved, by_plan = {}, [], {}
    relevant = [a for a in ctx.artifacts.values() if a['book_id'] == target_key['book_id'] and a['scope_id'] == scope_id]
    for artifact in sorted(relevant, key=lambda a: {'WriteIntent': 0, 'ExecutionReceipt': 1, 'ExecutionProgress': 2}.get(a['kind'], 3)):
        if artifact['book_id'] != target_key['book_id'] or artifact['scope_id'] != scope_id:
            continue
        if artifact['kind'] == 'WriteIntent':
            ip = artifact['payload']
            if ip['target_key'] != target_key:
                continue
            outcomes[ip['action_id']] = 'UNKNOWN'
            by_plan[(canonical_hash(ip['plan_ref']), ip['action_id'])] = ('UNKNOWN', recovery_artifact_ref(artifact))
        if artifact['kind'] == 'ExecutionReceipt':
            plan = ctx.resolve(artifact['payload']['plan'], artifact, 'ApplyPlan')
            snapshot = ctx.resolve(plan['payload']['snapshot'], artifact, 'PlatformSnapshot')
            if snapshot['payload']['target_id'] != target_key['target_id']:
                continue
            for result in artifact['payload']['results']:
                outcomes[result['action_id']] = result['outcome']
                by_plan[(canonical_hash(artifact['payload']['plan']), result['action_id'])] = (result['outcome'], result['intent_ref'])
        if artifact['kind'] == 'ExecutionProgress':
            p = artifact['payload']
            plan = ctx.resolve(p['plan_ref'], artifact, 'ApplyPlan')
            snapshot = ctx.resolve(plan['payload']['snapshot'], artifact, 'PlatformSnapshot')
            if snapshot['payload']['target_id'] != target_key['target_id']:
                continue
            for item in p['actions']:
                if item['result_fact'] is not None:
                    _, fact = ctx.resource(item['result_fact'])
                    outcome = fact['result']['outcome']
                    outcomes[item['action_id']] = outcome
                    by_plan[(canonical_hash(p['plan_ref']), item['action_id'])] = (outcome, item['intent_ref'])
    for head in heads.values():
        p = head['payload']
        intent = ctx.resolve(p['intent_ref'], head, 'WriteIntent')
        if intent['payload']['target_key'] != target_key or head['scope_id'] != scope_id:
            continue
        result = {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[p['resolution']]
        outcomes[p['action_id']] = result
        by_plan[(canonical_hash(p['plan_ref']), p['action_id'])] = (result, p['intent_ref'])
    for (plan_hash, action_id), (outcome, intent_ref) in by_plan.items():
        if outcome == 'UNKNOWN':
            unresolved.append({'action_id': action_id, 'intent_ref': intent_ref,
                               'reason': 'LEGACY_UNRECORDED' if intent_ref is None else 'NEEDS_RECONCILIATION',
                               'plan_digest': plan_hash})
    return _node({'target_key': target_key, 'scope_id': scope_id, 'outcomes': outcomes,
                  'unresolved': unresolved, 'paused': bool(unresolved), 'authority': 'SAME_SCOPE_CONTRACT_ONLY'})


def _reports(ctx, heads):
    for artifact in ctx.artifacts.values():
        p = artifact['payload']
        if artifact['kind'] == 'CheckReport':
            if p['stage'] != 'POST_APPLY':
                if p['recovery_refs']:
                    fail('$.recovery_refs', 'RECOVERY_CHAIN_INVALID', 'only POST_APPLY may consume recovery results')
                continue
            receipt = ctx.resolve(p['receipt'], artifact, 'ExecutionReceipt')
            plan = ctx.resolve(receipt['payload']['plan'], artifact, 'ApplyPlan')
            if p['graph'] != plan['payload']['graph'] or p['policy'] != plan['payload']['policy'] or p['subject'] != p['receipt']:
                fail('$.postcheck', 'RECOVERY_CHAIN_INVALID', 'postcheck graph/policy/subject differs')
            effective = {r['action_id']: r['outcome'] for r in receipt['payload']['results']}
            for ref in p['recovery_refs']:
                resolution = ctx.resolve(ref, artifact, 'ReconciliationResult')
                rp = resolution['payload']
                _consumer_resolution_head(ctx, artifact, ref, heads, intent_ref=rp['intent_ref'],
                                          plan_ref=receipt['payload']['plan'], action_id=rp['action_id'])
                if rp['original_receipt_ref'] != p['receipt']:
                    fail('$.postcheck', 'RECOVERY_CHAIN_INVALID', 'postcheck must bind its exact original receipt')
                effective[rp['action_id']] = {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[rp['resolution']]
                if p['snapshot'] != rp['observed_snapshot_ref']:
                    fail('$.postcheck', 'OBSERVATION_BINDING_MISMATCH', 'postcheck needs the exact observation of its consumed historical head')
            if p['decision'] == 'PASS' and any(v != 'APPLIED' for v in effective.values()):
                fail('$.postcheck', 'UNPROVEN_APPLY', 'PASS requires every effective action applied')
        if artifact['kind'] == 'BatchReport':
            from .models import BatchPayload
            from pydantic import ValidationError
            # Shape alone cannot enforce denominator/status/cost invariants.
            try:
                BatchPayload.model_validate({k: v for k, v in p.items() if k not in ('recovery_refs', 'progress_refs')})
            except ValidationError as error:
                fail('$.batch', 'SCHEMA', str(error))
            receipt = ctx.resolve(p['receipt'], artifact, 'ExecutionReceipt')
            source = ctx.resolve(p['source'], artifact, 'SourceBundle')
            post = ctx.resolve(p['postcheck'], artifact, 'CheckReport')
            plan = ctx.resolve(receipt['payload']['plan'], artifact, 'ApplyPlan')
            if p['scope_manifest'] != source['payload']['scope_manifest'] or p['total_expected'] != len(p['scope_manifest']):
                fail('$.batch', 'DENOMINATOR_CHANGED', 'batch denominator must retain complete fixture scope')
            if post['payload']['receipt'] != p['receipt'] or post['payload']['graph'] != p['graph'] or p['graph'] != plan['payload']['graph']:
                fail('$.batch', 'BATCH_BINDING', 'batch graph/receipt/postcheck differs')
            if p['recovery_refs'] != post['payload']['recovery_refs']:
                fail('$.batch', 'RECOVERY_CHAIN_INVALID', 'batch and postcheck must consume exact same recovery heads')
            if p['state'] == 'COMPLETED' or p['submission_status'] != 'NOT_SUBMITTED' or p['content_check_status'] != 'PENDING':
                fail('$.batch', 'COMPLETION_GUARD', 'synthetic frame recovery does not prove content or human submission')
            effective = {r['action_id']: r['outcome'] for r in receipt['payload']['results']}
            for ref in p['recovery_refs']:
                rp = ctx.resolve(ref, artifact, 'ReconciliationResult')['payload']
                _consumer_resolution_head(ctx, artifact, ref, heads, intent_ref=rp['intent_ref'],
                                          plan_ref=receipt['payload']['plan'], action_id=rp['action_id'])
                effective[rp['action_id']] = {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[rp['resolution']]
            if 'UNKNOWN' in effective.values() and p['state'] != 'NEEDS_RECONCILIATION':
                fail('$.batch', 'BOOK_WRITE_PAUSED', 'unknown effective outcome keeps batch paused')
            statuses = {q['question_id']: q['state'] for q in p['questions']}
            action_questions = {a['action_id']: a['target']['question_id'] for a in plan['payload']['actions']}
            for action_id, outcome in effective.items():
                state = statuses.get(action_questions[action_id])
                if outcome == 'UNKNOWN' and (state != 'UNKNOWN' or not p['unresolved_issue_ids']):
                    fail('$.batch.questions', 'UNKNOWN_GUARD', 'each unknown effective action remains counted and paused')
                if outcome == 'NOT_APPLIED' and state == 'VERIFIED':
                    fail('$.batch.questions', 'UNAPPLIED_QUESTION', 'absent action target cannot be verified')


def validate_recovery_bundle(bundle, *, asset_root=None, _archive=False, bridge_context=None):
    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)
    if version == 'a03-exchange-4-proposal':
        from .a03_native import validate_native_bundle
        return validate_native_bundle(bundle, bridge_context=bridge_context, asset_root=asset_root)
    root = asset_root if asset_root is not None else getattr(bundle, 'asset_root', None)
    data = _data(bundle)
    if not isinstance(data, dict) or data.get('format_version') != RECOVERY_EXCHANGE_VERSION:
        fail('$', 'RECOVERY_VERSION_UNSUPPORTED', 'expected approved recovery exchange namespace')
    if any(a.get('schema_version') != RECOVERY_SCHEMA_VERSION for a in data.get('artifacts', [])):
        fail('$', 'CROSS_VERSION_REFERENCE', 'one recovery namespace required')
    FrozenSchemas().check(data)
    if root is None:
        fail('$', 'RESOURCE_ROOT_REQUIRED', 'recovery validation never skips actual resource bytes')
    ctx = _Closure(data, root, synthetic=not _archive)
    ctx.check()
    for a in data['artifacts']:
        _timestamp(a['created_at'])
    if not _archive:
        _scope(ctx)
    _intents(ctx)
    heads = _resolutions(ctx)
    _receipts_progress(ctx, heads)
    _legacy_projection(ctx)
    _reports(ctx, heads)
    return RecoveryExchangeBundle(data, root)


def load_recovery_bundle(path, *, asset_root=None):
    path = Path(path)
    try:
        data = read_json(path)
    except (OSError, ValueError) as error:
        fail('$', 'JSON_INPUT', str(error))
    return validate_recovery_bundle(data, asset_root=asset_root if asset_root is not None else path.parent)


def load_archive_bundle(path, verify_assets=True):
    from .validation import load_bundle
    path = Path(path)
    try:
        data = read_json(path)
    except (OSError, ValueError) as error:
        fail('$', 'JSON_INPUT', str(error))
    if data.get('format_version') == 'c01-exchange-1':
        value = load_bundle(path, verify_assets=verify_assets)
    elif data.get('format_version') == RECOVERY_EXCHANGE_VERSION:
        # Recovery archives still check bytes and chain identity. Archive-only
        # reading never grants synthetic admission or a runtime intent.
        value = validate_recovery_bundle(data, asset_root=path.parent, _archive=True)
    else:
        fail('$', 'RECOVERY_VERSION_UNSUPPORTED', 'unsupported archive namespace')
    return _node({'eligibility': 'ARCHIVE_ONLY', 'bundle': _data(value),
                  'path': str(path.resolve()), 'sha256': file_digest(path)})


def effective_recovery_outcomes(bundle, *, target_key, scope_id, bridge_context=None):
    data = _data(bundle)
    if data.get('format_version') == 'a03-exchange-4-proposal':
        from .a03_native import effective_native_outcomes
        return effective_native_outcomes(bundle, target_key=target_key, scope_id=scope_id, bridge_context=bridge_context)
    if data.get('format_version') == 'c01-exchange-1':
        from .validation import validate_bundle
        legacy = validate_bundle(bundle)
        unresolved = [{'action_id': r.action_id, 'intent_ref': None, 'reason': 'LEGACY_UNRECORDED'}
                      for a in legacy.artifacts if a.kind == 'ExecutionReceipt' and a.book_id == target_key['book_id']
                      and a.scope_id == scope_id for r in a.payload.results if r.outcome == 'UNKNOWN']
        return _node({'outcomes': {}, 'unresolved': unresolved, 'paused': bool(unresolved), 'authority': 'ARCHIVE_ONLY'})
    validated = validate_recovery_bundle(bundle)
    ctx = _Closure(_data(validated), validated.asset_root)
    return _outcomes(ctx, _resolutions(ctx), _data(target_key), scope_id)


def assert_recovery_plan_ready(bundle, plan_ref, current_snapshot_ref, *, bridge_context=None):
    version = bundle.get('format_version') if isinstance(bundle, dict) else getattr(bundle, 'format_version', None)
    if version == 'a03-exchange-4-proposal':
        from .a03_native import assert_native_plan_ready
        return assert_native_plan_ready(bundle, plan_ref, current_snapshot_ref, bridge_context=bridge_context)
    from .validation import _Context, _plan
    validated = validate_recovery_bundle(bundle)
    ctx = _Closure(_data(validated), validated.asset_root)
    plan = ctx.resolve(_data(plan_ref), kind='ApplyPlan')
    snapshot = ctx.resolve(_data(current_snapshot_ref), plan, 'PlatformSnapshot')
    if plan['payload']['readiness'] != 'READY':
        fail('$.plan', 'PLAN_BLOCKED', 'diagnostic plan has no action authority')
    if _data(current_snapshot_ref) != plan['payload']['snapshot']:
        fail('$.plan', 'TARGET_CHANGED', 'current snapshot differs from exact plan observation')
    local = dict(ctx.bundle, artifacts=[a for a in ctx.bundle['artifacts'] if (a['book_id'], a['scope_id']) == (plan['book_id'], plan['scope_id'])])
    projected, mapped = _legacy_projection(_Closure(local, ctx.root))
    if projected is None:
        fail('$.plan', 'NO_ACTIONS', 'zero scope has no executable plan')
    p = mapped[(plan['artifact_id'], plan['revision'])]
    s = mapped[(snapshot['artifact_id'], snapshot['revision'])]
    c = _Context(projected)
    _plan(c, c.artifacts[(p['artifact_id'], p['revision'])], '$.plan.payload', _node(recovery_artifact_ref(s)))
    # The ordinary contract may only inspect its same-scope closure. Runtime
    # separately scans every historical scope/run in the canonical book store.
    target_bindings = {canonical_hash(a['payload']['target_key']): a['payload']['target_key']
                       for a in ctx.artifacts.values() if a['kind'] == 'WriteIntent' and
                       (a['book_id'], a['scope_id']) == (plan['book_id'], plan['scope_id']) and
                       a['payload']['target_key']['target_id'] == snapshot['payload']['target_id']}
    if len(target_bindings) > 1:
        fail('$.plan', 'TARGET_IDENTITY_MISMATCH', 'plan cannot choose between multiple canonical platform namespaces')
    target_key = next(iter(target_bindings.values()),
                      {'platform_namespace': 'a02-mock', 'target_id': snapshot['payload']['target_id'], 'book_id': plan['book_id']})
    view = _outcomes(ctx, _resolutions(ctx), target_key, plan['scope_id'])
    if view.paused:
        code = 'LEGACY_UNRECORDED' if any(r.reason == 'LEGACY_UNRECORDED' for r in view.unresolved) else 'BOOK_WRITE_PAUSED'
        fail('$.plan', code, 'same-scope unresolved history blocks new actions')
    # Loading an immutable old plan remains legal. Claiming current eligibility
    # after a terminal reconciliation requires a genuinely newer observation,
    # its exact new TARGET report and a plan created after those inputs.
    terminal_times = []
    for head in _resolutions(ctx).values():
        hp = head['payload']
        intent = ctx.resolve(hp['intent_ref'], head, 'WriteIntent')
        if (intent['payload']['target_key'] == target_key and head['scope_id'] == plan['scope_id'] and
                hp['resolution'] != 'STILL_UNKNOWN'):
            terminal_times.append(_timestamp(hp['observed_at']))
    if terminal_times:
        observed_at = _timestamp(snapshot['payload']['observed_at'])
        target = ctx.resolve(plan['payload']['targetcheck'], plan, 'CheckReport')
        if observed_at <= max(terminal_times):
            fail('$.plan.snapshot', 'OBSERVATION_NOT_FRESH', 'new eligibility requires an observation after terminal reconciliation')
        if target['payload']['snapshot'] != _data(current_snapshot_ref) or target['payload']['subject'] != _data(current_snapshot_ref):
            fail('$.plan.targetcheck', 'TARGET_CHANGED', 'new TARGET must bind the exact new current observation')
        if (_timestamp(target['created_at']) < observed_at or _timestamp(plan['created_at']) < observed_at or
                _timestamp(plan['created_at']) < _timestamp(target['created_at'])):
            fail('$.plan', 'OBSERVATION_NOT_FRESH', 'new TARGET and plan must be created after their current observation')
    return _node(plan)


def convert_synthetic_fixture(source_path, output_dir, *, conversion_id, expected_input_sha256):
    """Create a new initial simulation fixture; never import execution history."""
    from .validation import load_bundle
    from .models import Identifier
    from pydantic import TypeAdapter
    TypeAdapter(Identifier).validate_python(conversion_id)
    source_path, output_dir = Path(source_path).resolve(), Path(output_dir).resolve()
    if file_digest(source_path) != expected_input_sha256:
        fail('$', 'CONVERSION_INPUT_HASH_MISMATCH', 'exact original file SHA256 differs')
    if output_dir.exists():
        fail('$', 'CONVERSION_TARGET_EXISTS', 'conversion requires a new output directory')
    original = load_bundle(source_path, verify_assets=True).model_dump(mode='json')
    if any(a['kind'] in ('ExecutionReceipt', 'BatchReport') for a in original['artifacts']):
        fail('$', 'LEGACY_UNRECORDED', 'execution results cannot become new simulated history')
    for value in _walk(original):
        if not isinstance(value, dict):
            continue
        if ('evidence_mode' in value and value['evidence_mode'] != 'SYNTHETIC' or
                'provenance' in value and value['provenance'] != 'SYNTHETIC' or
                'mode' in value and value['mode'] == 'OBSERVED' or
                'region_id' in value and value.get('source', 'SYNTHETIC') != 'SYNTHETIC' or
                'clue_id' in value and value.get('source', 'SYNTHETIC') != 'SYNTHETIC' or
                'execution_mode' in value and value['execution_mode'] not in ('SIMULATED', 'NOT_EXECUTED')):
            fail('$', 'SYNTHETIC_ONLY', 'conversion cannot relabel real provenance')
    output_dir.mkdir(parents=True)
    incomplete = output_dir / 'conversion-incomplete.json'
    incomplete.write_text(json.dumps({'conversion_id': conversion_id, 'status': 'INCOMPLETE',
                                      'source_sha256': expected_input_sha256}, indent=2) + '\n', encoding='utf-8')
    artifacts = {(a['artifact_id'], a['revision']): a for a in original['artifacts']}
    mapped, active, resource_cache = {}, set(), {}
    resource_records = []

    def save_json(value):
        raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
        digest = hashlib.sha256(raw).hexdigest()
        relative = 'assets/' + digest + '.json'
        target = output_dir / relative
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            with target.open('xb') as handle:
                handle.write(raw)
        return {'path': relative, 'sha256': digest, 'media_type': 'application/json', 'origin': 'SYNTHETIC'}

    def resource(value):
        key = (value['path'], value['sha256'], value['media_type'])
        if key in resource_cache:
            return copy.deepcopy(resource_cache[key])
        source_file = (source_path.parent / value['path']).resolve()
        source_file.relative_to(source_path.parent)
        if file_digest(source_file) != value['sha256']:
            fail('$', 'RESOURCE_HASH_MISMATCH', 'source changed during conversion')
        if value['media_type'] == 'application/json':
            body = read_json(source_file)
            for node in _walk(body):
                if isinstance(node, dict) and node.get('origin', 'SYNTHETIC') != 'SYNTHETIC':
                    fail('$', 'SYNTHETIC_ONLY', 'nested source resource has real origin')
            converted = save_json(rewrite(body))
        else:
            target = output_dir / value['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(source_file.read_bytes())
            converted = {k: value[k] for k in ('path', 'sha256', 'media_type')}
            converted['origin'] = 'SYNTHETIC'
        converted.update({k: v for k, v in value.items() if k not in ('path', 'sha256', 'media_type')})
        resource_cache[key] = converted
        resource_records.append({'old': value, 'new': converted})
        return copy.deepcopy(converted)

    def rewrite(value, envelope=False):
        if _is_ref(value):
            return recovery_artifact_ref(convert(artifacts[(value['artifact_id'], value['revision'])]))
        if _is_resource(value):
            return resource(value)
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        return value

    def convert(old):
        key = (old['artifact_id'], old['revision'])
        if key in mapped:
            return mapped[key]
        if key in active:
            fail('$', 'REFERENCE_CYCLE', 'conversion graph cycles')
        active.add(key)
        new = rewrite(copy.deepcopy(old), envelope=True)
        new['schema_version'] = RECOVERY_SCHEMA_VERSION
        if old['kind'] == 'SourceBundle':
            p = new['payload']
            # The explicit fixture conversion enumerates the known fixture
            # graph by original-image membership, retaining every scope item.
            graphs = [g for g in original['artifacts'] if g['kind'] == 'QuestionGraph' and g['payload']['source'] == artifact_ref(old)]
            per_page = {page: set() for page in p['pages_expected']}
            for graph in graphs:
                evidence = artifacts[(graph['payload']['evidence']['artifact_id'], graph['payload']['evidence']['revision'])]
                regions = {r['region_id']: r['box']['image']['asset_id'] for r in evidence['payload']['regions']}
                fragments = {f['fragment_id']: f['region_ids'] for f in graph['payload']['fragments']}
                for q in graph['payload']['questions']:
                    for fid in q['fragment_ids'] + q['shared_fragment_ids']:
                        for rid in fragments[fid]:
                            per_page[regions[rid]].add(q['question_id'])
            assigned = set().union(*per_page.values()) if per_page else set()
            if assigned != set(p['scope_manifest']):
                fail('$', 'CONVERSION_INPUT_UNSUPPORTED', 'fixture scope contains items without explicit page enumeration')
            proof = {'origin': 'SYNTHETIC', 'basis': 'FIXTURE', 'complete': True,
                     'book_id': new['book_id'], 'scope_id': new['scope_id'],
                     'pages_expected': p['pages_expected'], 'pages_acquired': p['pages_acquired'],
                     'scope_manifest': p['scope_manifest'],
                     'assets': [{k: a[k] for k in ('asset_id', 'path', 'sha256', 'width', 'height')} for a in p['assets']],
                     'per_page_questions': [{'asset_id': page, 'question_ids': sorted(ids), 'enumeration_complete': True}
                                            for page, ids in per_page.items()],
                     'conversion_id': conversion_id}
            p['scope_integrity'] = {'status': 'SYNTHETIC_COMPLETE', 'basis': 'FIXTURE', 'proof': save_json(proof)}
        if old['kind'] == 'CheckReport':
            new['payload']['recovery_refs'] = []
        new['content_hash'] = content_digest(new)
        mapped[key] = new
        active.remove(key)
        return new
    result = {'format_version': RECOVERY_EXCHANGE_VERSION,
              'evidence': rewrite(original['evidence']), 'policies': copy.deepcopy(original['policies']),
              'artifacts': [convert(a) for a in original['artifacts']]}
    # Explicit declaration closure is computed per new consumer, never copied
    # from an unrelated artifact or inferred from matching strings.
    for artifact in result['artifacts']:
        if artifact['kind'] == 'SourceBundle':
            continue
        # Converted initial fixtures currently have no nested ordinary refs
        # beyond those already declared in their C01 input graph. Validation
        # below rejects an unsupported graph rather than guessing new authority.
    validated = validate_recovery_bundle(result, asset_root=output_dir)
    bundle_path = output_dir / 'bundle.json'
    with bundle_path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(validated.model_dump(), ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    mappings = [{'old_namespace': {'schema_version': '1.0.0-a-proposal', 'exchange_version': 'c01-exchange-1'},
                 'new_namespace': {'schema_version': RECOVERY_SCHEMA_VERSION, 'exchange_version': RECOVERY_EXCHANGE_VERSION},
                 'book_id': old['book_id'], 'scope_id': old['scope_id'], 'old_ref': artifact_ref(old),
                 'new_ref': artifact_ref(mapped[key])} for key, old in artifacts.items()]
    manifest = {'conversion_id': conversion_id, 'source_path': str(source_path),
                'source_sha256': expected_input_sha256, 'bundle_path': str(bundle_path),
                'bundle_sha256': file_digest(bundle_path), 'mapping_path': str(output_dir / 'conversion-manifest.json'),
                'status': 'INITIAL_SIMULATED_INPUT_ONLY', 'artifact_mappings': mappings,
                'resource_mappings': resource_records, 'history_migrated': False}
    with (output_dir / 'conversion-manifest.json').open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    # Keep the initial marker as diagnostic history, now explicitly completed.
    incomplete.write_text(json.dumps({'conversion_id': conversion_id, 'status': 'COMPLETED_NEW_FIXTURE',
                                      'source_sha256': expected_input_sha256}, indent=2) + '\n', encoding='utf-8')
    return _node(manifest)
