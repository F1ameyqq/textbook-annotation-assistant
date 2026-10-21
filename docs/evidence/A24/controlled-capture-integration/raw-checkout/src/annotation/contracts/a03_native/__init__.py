"""A-internal native synthetic contracts. Serialized values grant no authority."""
from dataclasses import dataclass
import hashlib
from importlib import resources
import json
from pathlib import Path
from types import MappingProxyType

from ..a03_bridge._errors import need
from ..a03_bridge._json import canonical, copy_json, digest
from ..a03_bridge._resources import ResourceReader
from ..a03_bridge._schema import validate as schema_validate
from ..recovery import Node, _node
from ._closure import StaticPackage

VERSION = '1.4.0-a03-native-proposal'
EXCHANGE = 'a03-exchange-4-proposal'
PROFILE = 'a03-native-synthetic-1-PROPOSAL'
_REGISTRIES = {}
_CONTEXTS = {}


def _data(name):
    return resources.files(__package__).joinpath('data', name).read_bytes()


def _document(name):
    return json.loads(_data(name))


def _documents():
    return {name: _document('schemas/' + name + '.json')
            for name in ('exchange', 'fact', 'prefix', 'basis', 'conversion', 'pre_run')}


@dataclass(frozen=True)
class BridgeSelection:
    codec_id: str
    role: str
    exchange_version: str
    artifact_version: str
    profile_id: str
    profile_sha256: str
    schema_pins: tuple
    api_sha256: str
    interface_sha256: str
    oracle_sha256: str
    verifier_sha256: str
    implementation_pins: tuple
    adoption_sha256: str


@dataclass(frozen=True, eq=False)
class BridgeContext:
    selection: BridgeSelection
    asset_root: Path
    canonical_sha256: str
    resource_manifest: tuple
    _registry: object
    _binding: str
    _historical: bool = False


class NativeBundle(Node):
    def __init__(self, data, context):
        super().__init__(_node(data))
        self.asset_root = context.asset_root
        self.bridge_context = context
        self.profile = PROFILE


def select_native_codec():
    profile = _document('profile.json')
    for path, expected in profile['schema_pins']:
        need(hashlib.sha256(_data(path)).hexdigest() == expected, 'NATIVE_SCHEMA_PIN', path)
    for path, expected in profile['implementation_pins']:
        location = resources.files('annotation').joinpath(path[len('@annotation/'):]) if path.startswith('@annotation/') else resources.files(__package__).joinpath(path)
        need(hashlib.sha256(location.read_bytes()).hexdigest() == expected,
             'NATIVE_IMPLEMENTATION_PIN', path)
    for key, filename in (('api_sha256', 'api.json'), ('interface_sha256', 'interface-source.json'),
                          ('oracle_sha256', 'oracle.json')):
        need(profile[key] == hashlib.sha256(_data(filename)).hexdigest(), 'NATIVE_PROFILE_PIN', filename)
    adoption = _document('adoption.json')
    profile_sha = hashlib.sha256(_data('profile.json')).hexdigest()
    need(adoption['profile_sha256'] == profile_sha and adoption['scope'] == 'A_INTERNAL_FIXED_SYNTHETIC_ONLY',
         'NATIVE_ADOPTION_PIN', 'adoption.json')
    return BridgeSelection('a03-native-1', 'CURRENT', EXCHANGE, VERSION, PROFILE, profile_sha,
        tuple(tuple(row) for row in profile['schema_pins']), profile['api_sha256'], profile['interface_sha256'],
        profile['oracle_sha256'], profile['verifier_sha256'], tuple(tuple(row) for row in profile['implementation_pins']),
        hashlib.sha256(_data('adoption.json')).hexdigest())


def _attach_registry(registry, callback):
    """Runtime-only capability installation; callbacks are never read from JSON."""
    from annotation.runtime.storage.native import NativeRegistry
    need(type(registry) is NativeRegistry and registry._callback is callback, 'NATIVE_REGISTRY_TYPE', '$registry')
    _REGISTRIES[id(registry)] = (registry, callback)


def _registry(context):
    need(type(context) is BridgeContext and _CONTEXTS.get(id(context)) is context,
         'NATIVE_CONTEXT_REQUIRED', '$context')
    need(context.selection == select_native_codec(), 'NATIVE_SELECTION_PINS', '$context.selection')
    entry = _REGISTRIES.get(id(context._registry))
    need(entry is not None and entry[0] is context._registry, 'NATIVE_REGISTRY_REQUIRED', '$context.registry')
    need(context.asset_root.is_dir() and context.asset_root.resolve() == context.asset_root,
         'NATIVE_ROOT_CHANGED', '$context.asset_root')
    return entry[1]


def _issue_context(registry, bundle, asset_root, *, binding='', historical=False):
    entry = _REGISTRIES.get(id(registry))
    need(entry is not None and entry[0] is registry, 'NATIVE_REGISTRY_REQUIRED', '$registry')
    root = Path(asset_root).resolve(strict=True)
    data, manifest, selection = _validated_value(registry, bundle, root)
    context = BridgeContext(selection, root, digest(data), manifest, registry, binding, historical)
    _CONTEXTS[id(context)] = context
    return context


def _validate_native_for_registry(registry, bundle, asset_root):
    """One fresh complete validation and private issuance in the same call.

    No caller-supplied proof, prior NativeBundle qualification or PASS cache is
    consumed. Public context/derive and bundle consumers keep their own recheck.
    """
    entry = _REGISTRIES.get(id(registry))
    need(entry is not None and entry[0] is registry, 'NATIVE_REGISTRY_REQUIRED', '$registry')
    root = Path(asset_root).resolve(strict=True)
    data, manifest, selection = _validated_value(registry, bundle, root)
    context = BridgeContext(selection, root, digest(data), manifest, registry, '', False)
    _CONTEXTS[id(context)] = context
    # Recheck current pins/root/registry and exact data identity at return; this
    # does not re-run _validate_value or accept a serialized validation claim.
    require_context(context, data)
    return NativeBundle(data, context)


def derive_context(context, bundle, *, asset_root=None):
    callback = _registry(context)
    return callback('derive_context', context, bundle=bundle, asset_root=asset_root or context.asset_root)


def require_context(context, bundle=None):
    callback = _registry(context)
    if bundle is not None:
        need(digest(copy_json(bundle.model_dump() if hasattr(bundle, 'model_dump') else bundle)) == context.canonical_sha256,
             'NATIVE_CONTEXT_INPUT', '$context.canonical_sha256')
    return callback


def _validated_value(registry, bundle, root):
    """Registry-local pure closure reuse, qualified by fresh dependency bytes.

    No runtime eligibility is cached. Canonical input includes each consumer's
    declarations; all transitive resource bytes and implementation/schema pins
    are read again at every entry, including public consumers. A changed input
    takes the complete validator. A changed dependency fails closed. The cache
    stores no mutable bundle or caller-provided validation claim.
    """
    selection = select_native_codec()
    data = copy_json(bundle.model_dump() if hasattr(bundle, 'model_dump') else bundle)
    key = (root, selection, digest(data))
    cache = registry._validation_values
    stats = registry.validation_counts
    stats['entries'] += 1
    if key in cache:
        manifest = cache[key]
        reader = ResourceReader(root)
        for path, expected in manifest:
            reader.read({'path': path, 'sha256': expected, 'media_type': 'application/octet-stream'})
        stats['resource_reads'] += len(manifest)
        stats['reuse'] += 1
        cache.move_to_end(key)
    else:
        stats['complete'] += 1
        data, manifest = _validate_value(data, root)
        # A dependency mutation during validation must not create a reusable
        # qualification under an earlier implementation identity.
        need(selection == select_native_codec(), 'NATIVE_SELECTION_PINS', '$validation')
        cache[key] = manifest
        if len(cache) > 16:
            cache.popitem(last=False)
    return data, manifest, selection


def _validate_value(bundle, root):
    data = copy_json(bundle.model_dump() if hasattr(bundle, 'model_dump') else bundle)
    need(type(data) is dict and data.get('format_version') == EXCHANGE, 'NATIVE_VERSION_REQUIRED', '$')
    need(all(a.get('schema_version') == VERSION for a in data.get('artifacts', [])), 'NATIVE_VERSION_REQUIRED', '$artifacts')
    reader = ResourceReader(root)
    documents = _documents()
    package = StaticPackage(data, reader, documents, set(_document('api.json')['registry']))
    package.validate()
    # Retain 1.1's synthetic-origin, timestamp, source proof, intent, resolution,
    # fact, progress and unchanged C01 geometry/business invariants as well.
    from .. import recovery
    ctx = recovery._Closure(data, root, schema_version=VERSION, schemas=NativeSchemas(documents))
    ctx.native = True
    ctx.check()
    recovery._scope(ctx)
    for artifact in data['artifacts']:
        recovery._timestamp(artifact['created_at'])
    recovery._intents(ctx)
    heads = recovery._resolutions(ctx)
    recovery._native_receipt_issue_ownership(ctx)
    recovery._receipts_progress(ctx, heads)
    recovery._legacy_projection(ctx)
    _reports(ctx, heads)
    consumed = dict(reader.consumed)
    consumed.update({token[1]: token[2] for token in ctx.decoded})
    return data, tuple(sorted(consumed.items()))


class NativeSchemas:
    def __init__(self, documents=None):
        self.documents = _documents() if documents is None else documents

    def check(self, value, name='recovery-exchange.schema.json', definition=None):
        docs = self.documents
        key = {'action-fact.schema.json': 'fact', 'event-prefix.schema.json': 'prefix',
               'unattempted-basis.schema.json': 'basis'}.get(name, 'exchange')
        document = docs[key]
        node = document['$defs']['Amended' + definition] if definition else document
        schema_validate(value, node, document)


def validate_native_bundle(bundle, *, bridge_context, asset_root=None):
    require_context(bridge_context, bundle)
    root = Path(asset_root).resolve() if asset_root is not None else bridge_context.asset_root
    need(root == bridge_context.asset_root, 'NATIVE_ROOT_MISMATCH', '$asset_root')
    data, manifest, _ = _validated_value(bridge_context._registry, bundle, root)
    need(manifest == bridge_context.resource_manifest, 'NATIVE_RESOURCE_MANIFEST', '$resources')
    return NativeBundle(data, bridge_context)


def seal_native_artifact(data, *, bridge_context):
    require_context(bridge_context)
    value = copy_json(json.loads(canonical(data.model_dump() if hasattr(data, 'model_dump') else data)))
    value['content_hash'] = '0' * 64
    NativeSchemas().check(value, definition=value.get('kind'))
    value['content_hash'] = digest({key: item for key, item in value.items() if key != 'content_hash'})
    return value


def assert_native_plan_ready(bundle, plan_ref, current_snapshot_ref, *, bridge_context):
    validated = validate_native_bundle(bundle, bridge_context=bridge_context)
    from .. import recovery
    ctx = recovery._Closure(validated.model_dump(), bridge_context.asset_root, schema_version=VERSION)
    ctx.native = True
    plan = ctx.resolve(recovery._data(plan_ref), kind='ApplyPlan')
    need(plan['payload']['readiness'] == 'READY' and plan['payload']['snapshot'] == recovery._data(current_snapshot_ref),
         'NATIVE_PLAN_NOT_READY', '$plan')
    callback = require_context(bridge_context)
    if not bridge_context._historical:
        callback('assert_pre', bridge_context, bundle=validated, pre_ref=plan['payload']['precheck'],
                 snapshot_ref=recovery._data(current_snapshot_ref))
    # The unchanged plan geometry/policy/action constraints were already checked
    # by the private C01 semantic projection above; no projection grants CURRENT.
    return _node(plan)


def effective_native_outcomes(bundle, *, target_key, scope_id, bridge_context):
    from .. import recovery
    validated = validate_native_bundle(bundle, bridge_context=bridge_context)
    ctx = recovery._Closure(validated.model_dump(), bridge_context.asset_root, schema_version=VERSION)
    return recovery._outcomes(ctx, recovery._resolutions(ctx), recovery._data(target_key), scope_id)


def _reports(ctx, heads):
    """Native reports consume an independent report read and immutable heads."""
    from .. import recovery
    for artifact in ctx.artifacts.values():
        payload = artifact['payload']
        if artifact['kind'] == 'CheckReport' and payload['stage'] == 'POST_APPLY':
            receipt = ctx.resolve(payload['receipt'], artifact, 'ExecutionReceipt')
            plan = ctx.resolve(receipt['payload']['plan'], artifact, 'ApplyPlan')
            snapshot = ctx.resolve(payload['report_snapshot_ref'], artifact, 'PlatformSnapshot')
            need(payload['subject'] == payload['receipt']
                 and payload['graph'] == plan['payload']['graph'] and payload['policy'] == plan['payload']['policy'],
                 'NATIVE_REPORT_BINDING', artifact['artifact_id'])
            need([b['action_id'] for b in payload['action_bindings']] == [a['action_id'] for a in plan['payload']['actions']],
                 'NATIVE_REPORT_ACTION_COVERAGE', artifact['artifact_id'])
            _, observation = ctx.resource(payload['report_observation'])
            need(observation['target_state_hash'] == snapshot['payload']['observed_hash']
                 and observation['target_state_version'] == snapshot['payload']['observed_version'],
                 'NATIVE_REPORT_READ_BINDING', artifact['artifact_id'])
            effective = {r['action_id']: r['outcome'] for r in receipt['payload']['results']}
            from annotation.delivery.planner import compare_action_effect
            comparisons = []
            for action, binding, fact_ref in zip(plan['payload']['actions'], payload['action_bindings'], receipt['payload']['action_fact_refs']):
                fact = recovery._fact(ctx, fact_ref, artifact)
                need(binding['action_digest'] == digest(action) and binding['fact_ref'] == fact_ref
                     and binding['intent_ref'] == fact['intent_ref']
                     and binding['resolution_head_ref'] == fact['resolution_ref']
                     and binding['observed_snapshot_ref'] == fact['observed_snapshot_ref']
                     and binding['effective_outcome'] == fact['result']['outcome'],
                     'NATIVE_REPORT_FACT_BINDING', artifact['artifact_id'])
                _, before = ctx.resource(fact['prepared_before'])
                comparisons.append(compare_action_effect(action, before, observation))
            need(payload['frame_structure'] == ('PASS' if all(c['effect_match'] == 'MATCH' for c in comparisons) else 'FAIL'),
                 'NATIVE_REPORT_FRAME_COMPARISON', artifact['artifact_id'])
            for ref in payload['recovery_refs']:
                head = ctx.resolve(ref, artifact, 'ReconciliationResult')
                hp = head['payload']
                recovery._consumer_resolution_head(ctx, artifact, ref, heads, intent_ref=hp['intent_ref'],
                    plan_ref=receipt['payload']['plan'], action_id=hp['action_id'])
                if hp['original_receipt_ref'] is None:
                    matches = [ctx.resource(r)[1] for r in receipt['payload']['action_fact_refs']]
                    need(any(f['intent_ref'] == hp['intent_ref'] and f['resolution_ref'] == ref for f in matches),
                         'NATIVE_LATE_RECEIPT_BINDING', artifact['artifact_id'])
                else:
                    original = ctx.resolve(hp['original_receipt_ref'], artifact, 'ExecutionReceipt')
                    need(original['payload']['plan'] == receipt['payload']['plan'],
                         'NATIVE_ORIGINAL_RECEIPT', artifact['artifact_id'])
                    originals = [recovery._fact(ctx, r, original) for r in original['payload']['action_fact_refs']]
                    need(any(f['intent_ref'] == hp['intent_ref'] and f['action_id'] == hp['action_id']
                             and f['result']['outcome'] == 'UNKNOWN' for f in originals),
                         'NATIVE_ORIGINAL_RECEIPT', artifact['artifact_id'])
                    if hp['original_receipt_ref'] != payload['receipt']:
                        need(any(b['resolution_head_ref'] == ref and b['intent_ref'] == hp['intent_ref']
                                 and b['head_original_receipt_ref'] == hp['original_receipt_ref']
                                 for b in payload['action_bindings']), 'NATIVE_LATE_RECEIPT_BINDING', artifact['artifact_id'])
                need(recovery._timestamp(snapshot['payload']['observed_at']) > recovery._timestamp(hp['observed_at']),
                     'NATIVE_REPORT_READ_NOT_FRESH', artifact['artifact_id'])
                effective[hp['action_id']] = {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[hp['resolution']]
            need(payload['decision'] != 'PASS' or all(v == 'APPLIED' for v in effective.values()),
                 'UNPROVEN_APPLY', artifact['artifact_id'])
        if artifact['kind'] == 'BatchReport':
            source = ctx.resolve(payload['source'], artifact, 'SourceBundle')
            post = ctx.resolve(payload['postcheck'], artifact, 'CheckReport')['payload']
            need(payload['receipt'] == post['receipt'] and payload['graph'] == post['graph']
                 and payload['report_snapshot_ref'] == post['report_snapshot_ref']
                 and payload['recovery_refs'] == post['recovery_refs'], 'NATIVE_BATCH_BINDING', artifact['artifact_id'])
            need(payload['scope_manifest'] == source['payload']['scope_manifest']
                 and payload['total_expected'] == len(payload['scope_manifest'])
                 and [q['question_id'] for q in payload['questions']] == payload['scope_manifest'],
                 'DENOMINATOR_CHANGED', artifact['artifact_id'])
            need(payload['content_check_status'] == 'PENDING' and payload['submission_status'] == 'NOT_SUBMITTED',
                 'COMPLETION_GUARD', artifact['artifact_id'])


__all__ = ['BridgeSelection', 'BridgeContext', 'NativeBundle', 'select_native_codec', 'validate_native_bundle']
