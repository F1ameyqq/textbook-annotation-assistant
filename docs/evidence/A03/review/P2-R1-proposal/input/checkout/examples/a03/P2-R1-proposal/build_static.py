"""Author design data only. No annotation imports, DB, adapter or runtime calls."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
if len(sys.argv) > 1:
    assert len(sys.argv) == 3 and sys.argv[1] == '--output-dir'
    candidate = (OUT / sys.argv[2]).resolve()
    assert candidate.is_relative_to(OUT) and not candidate.exists()
    OUT = candidate
OLD = ROOT / 'examples/a03/P1-R2/data'
VERSION = '1.2.0-a03-amendment-proposal'
PROFILE = 'a03-p2-r1-amendment-1-PROPOSAL'
ZERO = '0' * 64


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def write(path, value):
    path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8') + b'\n')


def ref(a):
    return {k: a[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


def resource(root, value, name=None):
    raw = canonical(value) + b'\n'
    relative = name or 'assets/new/' + sha(raw) + '.json'
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(raw)
    assert path.read_bytes() == raw
    return {'path': relative, 'sha256': sha(raw), 'media_type': 'application/json', 'origin': 'SYNTHETIC'}


def walk(value):
    yield value
    if isinstance(value, dict):
        for member in value.values():
            yield from walk(member)
    elif isinstance(value, list):
        for member in value:
            yield from walk(member)


def is_ref(v):
    return (isinstance(v, dict) and set(v) == {'artifact_id', 'revision', 'kind', 'content_hash'}
            and isinstance(v['artifact_id'], str) and type(v['revision']) is int and isinstance(v['content_hash'], str))


def ordinary_refs(value, root, seen=None):
    found, seen = {}, set() if seen is None else seen
    for v in walk(value):
        if is_ref(v):
            found[digest(v)] = v
        elif isinstance(v, dict) and {'path', 'sha256', 'media_type'} <= set(v):
            token = (v['path'], v['sha256'])
            if v['media_type'] == 'application/json' and token not in seen:
                seen.add(token)
                found.update({digest(r): r for r in ordinary_refs(json.loads((root / v['path']).read_bytes()), root, seen)})
    return list(found.values())


def seal(anchor, kind, identity, payload, root, version=VERSION):
    value = {k: copy.deepcopy(anchor[k]) for k in ('run_id', 'book_id', 'scope_id', 'producer')}
    value.update(schema_version=version, artifact_id=identity, revision=1, kind=kind,
                 created_at='2026-10-17T00:20:00Z', payload=payload)
    value['producer'].update(module='STATIC_PROPOSAL_AUTHOR', implementation_version='UNIMPLEMENTED')
    value['input_refs'] = ordinary_refs(payload, root)
    value['content_hash'] = digest(value)
    return value


def clone_seed(name):
    root = OUT / 'cases' / name
    root.mkdir(parents=True, exist_ok=False)
    seed = json.loads((OLD / 'cases/intent-no-receipt-match.json').read_bytes())
    bundle = seed['bundle']
    copied = set()
    def capture(value):
        for v in walk(value):
            if isinstance(v, dict) and {'path', 'sha256'} <= set(v) and isinstance(v['path'], str):
                token = (v['path'], v['sha256'])
                if token in copied:
                    continue
                copied.add(token)
                source = OLD / v['path']
                raw = source.read_bytes()
                assert sha(raw) == v['sha256']
                target = root / v['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                if v.get('media_type') == 'application/json':
                    capture(json.loads(raw))
    capture(bundle)
    # Original seed remains a separate exact-byte input; additions never rewrite it.
    (root / 'imported-r2-case.json').write_bytes((OLD / 'cases/intent-no-receipt-match.json').read_bytes())
    result = copy.deepcopy(bundle)
    result['format_version'] = 'a03-exchange-2-proposal'
    return root, result


STRING = {'type': 'string', 'minLength': 1}
HASH = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
INT = {'type': 'integer', 'minimum': 1}
BOOL = {'type': 'boolean'}
NULL = {'type': 'null'}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def arr(items, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum}


def nullable(item):
    return {'oneOf': [NULL, item]}


REF = obj({'artifact_id': STRING, 'revision': INT, 'kind': STRING, 'content_hash': HASH})
RES = obj({'path': STRING, 'sha256': HASH, 'media_type': STRING, 'origin': {'const': 'SYNTHETIC'}})
KEY = obj({k: STRING for k in ('platform_namespace', 'target_id', 'book_id')})
HEAD = obj({'sequence': {'type': 'integer', 'minimum': 0}, 'hash': HASH})
ACTION = obj({'action_id': STRING, 'action_digest': HASH})
MODE = {'const': 'SIMULATED'}
PLAN = {'plan_ref': REF}
BOUND = dict(PLAN, action_id=STRING, action_digest=HASH)
INTENT = dict(BOUND, intent_ref=REF, obligation_id=STRING)
PERMIT = dict(INTENT, permit_id=STRING)
OWNER = {'owner_id': STRING, 'process_instance_id': STRING, 'pid': INT, 'generation': INT,
         'lease_expires_at': STRING, 'target_session_id': STRING, 'fence_resource': RES}
READ = dict(BOUND, readonly_session_id=STRING, call_id=STRING, read_index={'type': 'integer', 'minimum': 1, 'maximum': 3})

# Full, closed payload catalog. Optional fields use explicit null, never free-form maps.
CATALOG = {
    'OWNER_CLAIM_RESERVED': obj(dict(OWNER, previous_owner_id=nullable(STRING), previous_generation={'type': 'integer', 'minimum': 0}, takeover_evidence=nullable(RES))),
    'OWNER_ACTIVE': obj(OWNER),
    'OWNER_RELEASED': obj({'departing_owner_id': STRING, 'generation': INT}),
    'RUNTIME_PROFILE_ADOPTED': obj({'previous_profile_id': STRING, 'new_profile_id': {'const': PROFILE}, 'previous_head': HEAD, 'known_db_version': {'const': 'a03-runtime-db-1'}, 'native_index_snapshot': RES}),
    'PLAN_ACCEPTED': obj(dict(PLAN, scope_id=STRING, source_ref=REF, actions=arr(ACTION, 1))),
    'PLAN_ACTIONS_RESERVED': obj(dict(PLAN, reservations=arr(ACTION, 1))),
    'PLAN_STARTED': obj(dict(PLAN, plan_state={'const': 'RUNNING'})),
    'PLAN_INTERRUPTED': obj(dict(PLAN, plan_state={'const': 'INTERRUPTED'}, reason={'enum': ['NONCONCLUSIVE_RESULT', 'OWNER_TAKEOVER', 'EXPLICIT_ABORT']})),
    'PLAN_STATE_AT_ADOPTION': obj(dict(PLAN, plan_state={'enum': ['INTERRUPTED', 'FINISHED']}, native_index_snapshot=RES)),
    'WRITE_INTENT_COMMITTED': obj(INTENT),
    'DISPATCH_PERMIT_ISSUED': obj(PERMIT),
    'DISPATCH_PERMIT_CONSUMED': obj(PERMIT),
    'DISPATCH_STARTED': obj(PERMIT),
    'ACTION_RESULT_COMMITTED': obj(dict(INTENT, fact=RES, outcome={'enum': ['APPLIED', 'NOT_APPLIED', 'UNKNOWN']}, plan_state={'enum': ['RUNNING', 'INTERRUPTED']})),
    'RECONCILIATION_COMMITTED': obj(dict(INTENT, resolution_ref=REF, observation_id=STRING, resolution={'enum': ['RESOLVED_APPLIED', 'RESOLVED_NOT_APPLIED', 'STILL_UNKNOWN']}, plan_state={'const': 'INTERRUPTED'})),
    'HISTORY_ARCHIVE_IMPORTED': obj({'archive_raw_sha256': HASH, 'legacy_rows': arr(obj({'legacy_id': STRING, 'scope_id': STRING, 'classification': {'const': 'LEGACY_UNRECORDED'}}))}),
    'TARGET_DRIFT_HOLD': obj({'hold_id': STRING, 'baseline_event': HEAD, 'baseline_resolution_ref': nullable(REF), 'observation': RES, 'snapshot_ref': REF, 'source_ref': REF, 'scope_id': STRING, 'target_session_id': STRING, 'target_state_hash': HASH, 'target_state_version': STRING}),
    'HOLD_CLEARED': obj({'hold_id': STRING, 'hold_event': HEAD, 'plan_ref': REF, 'snapshot_ref': REF, 'precheck_ref': REF, 'targetcheck_ref': REF, 'verification_observation': RES, 'verification_snapshot_ref': REF}),
    'READONLY_ABSENCE_STARTED': obj(dict(BOUND, readonly_session_id=STRING, call_id=STRING, initial_expected_head=HEAD)),
    'READONLY_ABSENCE_READ_STARTED': obj(dict(READ, attempt_record=RES)),
    'READONLY_ABSENCE_READ_FINISHED': obj(dict(READ, observation=RES, observation_id=STRING, read_sequence=INT)),
    'READONLY_ABSENCE_READ_FAILED': obj(dict(READ, failure_resource=RES)),
    'READONLY_ABSENCE_ABORTED': obj(dict(BOUND, readonly_session_id=STRING, reason=STRING)),
    'UNATTEMPTED_ABSENCE_COMMITTED': obj(dict(BOUND, readonly_session_id=STRING, fact=RES, initial_head=HEAD, commit_expected_head=HEAD, plan_state={'const': 'INTERRUPTED'})),
}


def schema(identity, body):
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:a03:p2-r1:proposal:' + identity, **body}


def build_schemas():
    dest = OUT / 'schemas/frozen-r2'
    dest.mkdir(parents=True, exist_ok=True)
    for p in (ROOT / 'src/annotation/contracts/schemas').glob('*.schema.json'):
        shutil.copyfile(p, dest / p.name)
    shutil.copyfile(ROOT / 'examples/a03/P1-R2/api-proposal.json', dest / 'api-proposal.json')
    event_base = {'sequence': INT, 'event_version': {'const': 'a03-runtime-event-2'}, 'event': STRING,
        'journal_id': STRING, 'target_key': KEY, 'plan_ref': nullable(REF), 'owner_id': nullable(STRING),
        'generation': INT, 'recorded_at': STRING, 'payload': {}, 'previous_hash': HASH, 'event_hash': HASH}
    variants = []
    for name, payload in CATALOG.items():
        properties = copy.deepcopy(event_base)
        properties.update(event={'const': name}, payload=payload)
        variants.append(obj(properties))
    # Explicit legacy tags preserve real old event bodies rather than defaulting absent fields.
    legacy_payloads = {
        'OWNER_CLAIM_RESERVED': obj({}), 'OWNER_ACTIVE': obj({}), 'OWNER_RELEASED': obj({}),
        'PLAN_ACCEPTED': obj(dict(PLAN, actions=arr(ACTION, 1))),
        'PLAN_ACTIONS_RESERVED': obj(dict(PLAN, reservations=arr(ACTION, 1))),
        'PLAN_STARTED': obj(dict(PLAN, plan_state={'const': 'RUNNING'})),
        'WRITE_INTENT_COMMITTED': obj(INTENT),
        'DISPATCH_PERMIT_ISSUED': obj(dict(PLAN, action_id=STRING, intent_ref=REF, permit_id=STRING)),
        'DISPATCH_PERMIT_CONSUMED': obj(dict(PLAN, action_id=STRING, intent_ref=REF, permit_id=STRING)),
        'DISPATCH_STARTED': obj(dict(PLAN, action_id=STRING, intent_ref=REF, permit_id=STRING)),
        'ACTION_RESULT_COMMITTED': CATALOG['ACTION_RESULT_COMMITTED'],
        'RECONCILIATION_COMMITTED': CATALOG['RECONCILIATION_COMMITTED'],
        'HISTORY_ARCHIVE_IMPORTED': obj({'archive_sha256': HASH, 'legacy_ids': arr(STRING)}),
        'TARGET_DRIFT_HOLD': obj({'hold_id': STRING, 'registration_id': STRING, 'plan_ref': nullable(REF),
            'baseline': obj({'event_sequence': INT, 'event_hash': HASH, 'event': STRING, 'binding': {'oneOf': [REF, RES]}, 'plan_ref': nullable(REF), 'target_state_hash': HASH, 'target_state_version': STRING, 'read_sequence': INT, 'observed_at': STRING}),
            'observation': RES, 'snapshot_ref': REF, 'observation_id': STRING, 'observed_at': STRING, 'read_sequence': INT,
            'target_state_hash': HASH, 'target_state_version': STRING, 'target_store_id': STRING, 'target_session_id': STRING, 'source_ref': REF, 'scope_id': STRING, 'prior_precheck_refs': arr(REF)}),
        'HOLD_CLEARED': obj({'hold_id': STRING, 'hold_event_hash': HASH, 'registration_id': STRING, 'plan_ref': REF, 'candidate_plan_ref': REF, 'snapshot_ref': REF, 'precheck_ref': REF, 'targetcheck_ref': REF,
            'candidate_observation': RES, 'verification_observation': RES, 'verification_snapshot_ref': REF, 'target_state_hash': HASH, 'target_state_version': STRING, 'read_sequence': INT}),
    }
    legacy = []
    for name, payload in legacy_payloads.items():
        properties = {k: copy.deepcopy(v) for k, v in event_base.items() if k != 'event_version'}
        properties.update(event={'const': name}, payload=payload)
        legacy.append(obj(properties))
    frame = obj({'frame_version': {'const': 'a03-journal-consumer-frame-1'},
        'representation': {'enum': ['FROZEN_EVENT_1', 'RUNTIME_EVENT_2']},
        'consumer_scope_id': nullable(STRING), 'input_refs': arr(REF),
        'event': {'oneOf': variants + legacy}})
    prefix = obj({'format_version': {'const': 'a03-runtime-event-prefix-1'}, 'profile_id': {'const': PROFILE},
        'journal_id': STRING, 'target_key': KEY, 'from_sequence': {'const': 1},
        'predecessor': obj({'sequence': {'const': 0}, 'hash': {'const': ZERO}}),
        'subject_plan_ref': REF, 'accepted_anchor': HEAD, 'accepted_predecessor': HEAD,
        'expected_book_head': HEAD, 'frames': arr(frame, 1)})
    write('schemas/runtime-event-prefix-v1.schema.json', schema('runtime-prefix-1', prefix))
    binding = obj({'action_id': STRING, 'action_digest': HASH, 'intent_ref': nullable(REF),
        'fact_ref': RES, 'resolution_head_ref': nullable(REF), 'head_original_receipt_ref': nullable(REF),
        'observed_snapshot_ref': nullable(REF), 'effective_outcome': {'enum': ['APPLIED', 'NOT_APPLIED', 'UNKNOWN']}})
    post = obj({'stage': {'const': 'POST_APPLY'}, 'subject': REF, 'graph': REF, 'policy': obj({'policy_id': STRING, 'revision': INT, 'content_hash': HASH}),
        'receipt': REF, 'report_snapshot_ref': REF, 'action_bindings': arr(binding, 1),
        'recovery_refs': arr(REF), 'frame_structure': {'enum': ['PASS', 'FAIL', 'UNAVAILABLE']},
        'content_check_status': {'const': 'PENDING'}, 'submission_status': {'const': 'NOT_SUBMITTED'},
        'decision': {'enum': ['HOLD', 'EXCEPTION']}, 'issues': arr(STRING, 1)})
    batch = obj({'source': REF, 'graph': REF, 'receipt': REF, 'postcheck': REF, 'report_snapshot_ref': REF,
        'recovery_refs': arr(REF), 'scope_manifest': arr(STRING), 'total_expected': {'type': 'integer', 'minimum': 0},
        'questions': arr(obj({'question_id': STRING, 'state': {'enum': ['PENDING', 'UNKNOWN', 'EXCEPTION', 'SKIPPED']}})),
        'state': {'enum': ['CONTENT_PENDING', 'NEEDS_REVIEW', 'NEEDS_RECONCILIATION']},
        'content_check_status': {'const': 'PENDING'}, 'submission_status': {'const': 'NOT_SUBMITTED'}})
    write('schemas/report-payloads-v2.schema.json', schema('reports-2', {'$defs': {'ActionBinding': binding, 'Post': post, 'Batch': batch}, 'oneOf': [post, batch]}))
    result = json.loads((dest / 'action-fact.schema.json').read_bytes())['$defs']['ActionResult']
    receipt = obj({'plan': REF, 'execution_mode': MODE, 'results': arr(result, 1),
        'action_fact_refs': arr(RES, 1), 'unresolved_issue_ids': arr(STRING),
        'write_disposition': {'enum': ['RECHECK_TARGET', 'PAUSE_RECONCILE', 'POSTCHECK']}})
    write('schemas/receipt-payload-v2.schema.json', schema('receipt-2', {'$defs': {'Resource': RES}, **receipt}))
    pre = obj({'format_version': {'const': 'a03-synthetic-precheck-run-1'}, 'producer_kind': {'const': 'REGISTERED_SYNTHETIC_FIXTURE_VERIFIER_1'},
        'oracle': RES, 'source_ref': REF, 'graph_ref': REF, 'policy_ref': obj({'policy_id': STRING, 'revision': INT, 'content_hash': HASH}),
        'hold_id': STRING, 'hold_event_head': HEAD, 'actual_snapshot_ref': REF, 'actual_observation': RES,
        'run_id': STRING, 'started_at': STRING, 'finished_at': STRING, 'implementation_digest': HASH,
        'input_hashes': arr(obj({'path': STRING, 'sha256': HASH}), 1),
        'checks': obj({k: obj({'outcome': {'enum': ['PASS', 'FAIL', 'UNAVAILABLE']}, 'comparison_digest': HASH, 'evidence': arr(RES, 1)})
            for k in ('source_integrity', 'structure', 'answer_matching', 'coverage', 'policy')}),
        'decision': {'enum': ['PASS', 'EXCEPTION', 'HOLD']}, 'authority': {'const': 'VALUE_ONLY_RUNTIME_ADMISSION_REQUIRED'}})
    write('schemas/synthetic-precheck-run-v1.schema.json', schema('pre-run-1', pre))
    conversion = obj({'format_version': {'const': 'a03-explicit-conversion-state-2'}, 'conversion_id': STRING,
        'source_sha256': HASH, 'source_profile_id': STRING, 'target_profile_id': {'const': PROFILE},
        'state': {'enum': ['CREATED', 'COPYING', 'VALIDATING', 'COMMITTED', 'FAILED', 'INCOMPLETE']},
        'previous_record_sha256': nullable(HASH), 'written_files': arr(obj({'path': STRING, 'sha256': HASH, 'bytes': {'type': 'integer', 'minimum': 0}})),
        'mapping': nullable(RES), 'completion_manifest': nullable(RES), 'failure': nullable(STRING), 'history_migrated': {'const': False}})
    write('schemas/conversion-state-v2.schema.json', schema('conversion-state-2', conversion))
    for old, new, fmt in [('action-fact.schema.json', 'action-fact-v2.schema.json', 'a03-action-fact-2'),
                           ('unattempted-basis.schema.json', 'unattempted-basis-v2.schema.json', 'a03-unattempted-basis-2')]:
        data = json.loads((dest / old).read_bytes())
        data['$id'] = 'urn:a03:p2-r1:proposal:' + new
        for node in walk(data):
            if isinstance(node, dict) and node.get('const') in ('a03-action-fact-1', 'a03-unattempted-basis-1'):
                node['const'] = fmt
        if 'basis' in new:
            data['properties']['initial_event_head'] = HEAD
            data['properties']['readonly_session_id'] = STRING
            data['properties'].pop('gate_held')
            data['required'].remove('gate_held')
            data['properties']['gate_binding'] = obj({'ledger_id': STRING, 'owner_id': STRING, 'generation': INT, 'session_id': STRING})
            data['properties']['currentness_assertion_ref'] = RES
            data['properties']['total_read_calls'] = {'const': 3}
            data['properties']['target_key'] = KEY
            data['required'] += ['initial_event_head', 'readonly_session_id', 'gate_binding', 'currentness_assertion_ref', 'total_read_calls']
        write('schemas/' + new, data)
    exchange = json.loads((dest / 'recovery-exchange.schema.json').read_bytes())
    exchange['$id'] = 'urn:a03:p2-r1:proposal:exchange-2'
    exchange['title'] = 'UNAPPROVED exchange-2 with immutable legacy read-only nodes'
    exchange['$comment'] = 'Structure only. Legacy nodes are not upgraded or granted execution eligibility. Native authority is outside JSON.'
    exchange['properties']['format_version'] = {'const': 'a03-exchange-2-proposal'}
    kinds = list(exchange['properties']['artifacts']['items']['discriminator']['mapping'])
    exchange['properties']['artifacts']['items'].pop('discriminator')
    for kind in kinds:
        amended = copy.deepcopy(exchange['$defs'][kind])
        amended['properties']['schema_version'] = {'const': VERSION}
        if kind == 'ExecutionReceipt':
            amended['properties']['payload'] = receipt
        elif kind == 'CheckReport':
            pre_payload = copy.deepcopy(exchange['$defs']['CheckPayload'])
            pre_payload['properties']['stage'] = {'const': 'PRE_APPLY'}
            pre_payload['properties']['synthetic_run_ref'] = RES
            pre_payload['required'].append('synthetic_run_ref')
            target_payload = copy.deepcopy(exchange['$defs']['CheckPayload'])
            target_payload['properties']['stage'] = {'const': 'TARGET'}
            amended['properties']['payload'] = {'oneOf': [pre_payload, target_payload, post]}
        elif kind == 'BatchReport':
            amended['properties']['payload'] = batch
        exchange['$defs']['Amended'+kind] = amended
        exchange['properties']['artifacts']['items']['oneOf'].append({'$ref': '#/$defs/Amended'+kind})
    write('schemas/exchange-v2.schema.json', exchange)
    write('api-supplement-proposal.json', {'profile_id': PROFILE, 'status': 'PROPOSAL_UNIMPLEMENTED',
        'runtime_api': [
            {'name': 'export_complete_book_prefix', 'input': 'known runtime store + native target key + current fenced owner + expected book head', 'output': 'prefix-1 + private equality attestation bound to exact native DB head; value alone is nonauthoritative'},
            {'name': 'begin_readonly_absence', 'input': 'exact plan/action/current head/call_id/current owner; all-book guard/index scan', 'output': 'native ReadOnlySession; append STARTED; no intent or dispatch capability'},
            {'name': 'prepare_readonly_absence', 'input': 'native first fresh read + session + exact plan/action/source', 'output': 'ReadOnlyPrepared private type; no issue/consume dispatch method'},
            {'name': 'commit_unattempted_absence_v2', 'input': 'session + ReadOnlyPrepared + two fresh observations + final currentness assertion + exact prefix/native equality + gate/CAS', 'output': 'immutable action-fact-2 and UNATTEMPTED_ABSENCE_COMMITTED; book-wide unrelated pending unchanged'},
            {'name': 'produce_synthetic_precheck', 'input': 'approved registered synthetic oracle + exact source/graph/policy + fresh post-hold native snapshot/observation + bounded call', 'output': 'new actual five-check run Resource + PRE 1.2 + native run handle; no B module'},
            {'name': 'admit_synthetic_precheck', 'input': 'native run handle + exact new PRE and run resource + current registered implementation/oracle', 'output': 'admitted PRE handle after private identity/input/result checks; caller JSON cannot grant admission'},
            {'name': 'build_recovery_reports_v2', 'input': 'exact complete receipt/plan/facts + immutable per-action current heads + genuine separate current report read', 'output': 'POST 1.2 + Batch 1.2; same old heads, full scope, content PENDING, NOT_SUBMITTED'},
            {'name': 'convert_synthetic_fixture_v2', 'input': 'known approved all-synthetic initial file + expected exact raw SHA + new dir/id + explicit approval', 'output': 'new initial namespace, complete bijective mappings/raw originals/append-only records/last atomic completion; no execution history'},
        ], 'ordinary_ref_scope': 'unchanged same book/scope; only exact recognized journal frames introduce reviewed per-event consumer boundaries',
        'native_types': ['ReadOnlySession', 'ReadOnlyPrepared', 'SyntheticPrecheckRunHandle', 'CompleteBookPrefixAttestation'],
        'native_types_serializable_as_authority': False})
    write('event-catalog.json', {'profile_id': PROFILE, 'new_event_count': len(CATALOG), 'payload_schemas': CATALOG,
        'frozen_event_1_payload_schemas': legacy_payloads, 'unknown_event_policy': 'REJECT_NO_OPAQUE_FALLBACK'})


def absence_value(root, bundle, action, suffix, prior_plan=False, view_snapshot=None):
    artifacts = bundle['artifacts']
    plan = next(a for a in artifacts if a['kind'] == 'ApplyPlan' and a['artifact_id'] == 'a02-plan')
    source = next(a for a in artifacts if a['kind'] == 'SourceBundle')
    initial = next(a for a in artifacts if a['kind'] == 'PlatformSnapshot' and a['artifact_id'] == 'a02-snapshot')
    key = {'platform_namespace': 'a02-mock', 'target_id': initial['payload']['target_id'], 'book_id': plan['book_id']}
    view_snapshot = view_snapshot or initial
    def timestamp(offset=0):
        return (datetime(2026, 10, 17, tzinfo=timezone.utc) + timedelta(milliseconds=len(frames)*100 + offset)).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    frames, previous, generation, owner = [], ZERO, 1, 'static-owner-1'
    def append(name, payload, event_plan=None, current=False):
        nonlocal previous
        event = {'sequence': len(frames) + 1, 'event': name, 'journal_id': 'static-journal-' + suffix,
            'target_key': key, 'plan_ref': event_plan, 'owner_id': owner, 'generation': generation,
            'recorded_at': timestamp(), 'payload': payload,
            'previous_hash': previous}
        if current:
            event['event_version'] = 'a03-runtime-event-2'
        event['event_hash'] = digest(event)
        frames.append({'frame_version': 'a03-journal-consumer-frame-1',
            'representation': 'RUNTIME_EVENT_2' if current else 'FROZEN_EVENT_1',
            'consumer_scope_id': plan['scope_id'] if event_plan is not None else None,
            'input_refs': ordinary_refs(event, root), 'event': event})
        previous = event['event_hash']
        return {'sequence': event['sequence'], 'hash': previous}
    append('OWNER_CLAIM_RESERVED', {})
    append('OWNER_ACTIVE', {})
    if prior_plan:
        other = copy.deepcopy(plan)
        other['artifact_id'] = 'prior-static-plan'
        old_ids = {}
        for a in other['payload']['actions']:
            old_ids[a['action_id']] = 'action-a02-' + digest({'plan_id': other['artifact_id'], 'question_id': a['target']['question_id'],
                'graph': other['payload']['graph'], 'snapshot': other['payload']['snapshot']})[:32]
        for a in other['payload']['actions']:
            a['action_id'] = old_ids[a['action_id']]
            a['depends_on'] = [old_ids[x] for x in a['depends_on']]
        other.pop('content_hash')
        other['content_hash'] = digest(other)
        artifacts.append(other)
        bindings = [{'action_id': a['action_id'], 'action_digest': digest(a)} for a in other['payload']['actions']]
        append('PLAN_ACCEPTED', {'plan_ref': ref(other), 'actions': bindings}, ref(other))
        append('PLAN_ACTIONS_RESERVED', {'plan_ref': ref(other), 'reservations': bindings}, ref(other))
        append('PLAN_STARTED', {'plan_ref': ref(other), 'plan_state': 'RUNNING'}, ref(other))
        generation, owner = 2, 'static-owner-2'
        append('OWNER_CLAIM_RESERVED', {})
        append('OWNER_ACTIVE', {})
    actions = [{'action_id': a['action_id'], 'action_digest': digest(a)} for a in plan['payload']['actions']]
    accepted = append('PLAN_ACCEPTED', {'plan_ref': ref(plan), 'actions': actions}, ref(plan))
    predecessor = {'sequence': accepted['sequence'] - 1, 'hash': frames[-1]['event']['previous_hash']}
    append('PLAN_ACTIONS_RESERVED', {'plan_ref': ref(plan), 'reservations': actions}, ref(plan))
    append('PLAN_STARTED', {'plan_ref': ref(plan), 'plan_state': 'RUNNING'}, ref(plan))
    generation += 1
    owner = 'static-current-owner'
    append('OWNER_CLAIM_RESERVED', {})
    append('OWNER_ACTIVE', {})
    native = resource(root, {'origin': 'SYNTHETIC', 'sample_status': 'PROPOSAL_UNIMPLEMENTED',
        'ledger_id': 'static-ledger', 'plan_identity_hash': digest(ref(plan)), 'plan_state': 'INTERRUPTED',
        'subject_action_id': action['action_id'], 'reservation_digest': digest(action),
        'subject_intent_count': 0, 'subject_permit_count': 0, 'subject_dispatch_count': 0,
        'all_book_pending': [], 'native_authority': 'UNIMPLEMENTED'})
    prior_head = {'sequence': len(frames), 'hash': previous}
    append('RUNTIME_PROFILE_ADOPTED', {'previous_profile_id': 'FROZEN_RUNTIME_EVENT_1', 'new_profile_id': PROFILE,
        'previous_head': prior_head, 'known_db_version': 'a03-runtime-db-1', 'native_index_snapshot': native}, current=True)
    append('PLAN_STATE_AT_ADOPTION', {'plan_ref': ref(plan), 'plan_state': 'INTERRUPTED', 'native_index_snapshot': native}, ref(plan), True)
    initial_head = {'sequence': len(frames), 'hash': previous}
    session = 'readonly-session-' + suffix
    base = {'plan_ref': ref(plan), 'action_id': action['action_id'], 'action_digest': digest(action),
            'readonly_session_id': session, 'call_id': 'readonly-call-' + suffix}
    append('READONLY_ABSENCE_STARTED', dict(base, initial_expected_head=initial_head), ref(plan), True)
    observations, snapshot = [], None
    for number in (1, 2, 3):
        attempt = resource(root, {'origin': 'SYNTHETIC', 'sample_status': 'PROPOSAL_UNIMPLEMENTED',
            **base, 'read_index': number, 'role': 'CURRENTNESS_ASSERTION' if number == 3 else 'FRESH_OBSERVATION',
            'status': 'REGISTERED_BEFORE_READ'})
        append('READONLY_ABSENCE_READ_STARTED', dict(base, read_index=number, attempt_record=attempt), ref(plan), True)
        body = {'format_version': 'a03-target-observation-1', 'origin': 'SYNTHETIC', 'execution_mode': 'SIMULATED',
            'target_key': key, 'source_ref': ref(source), 'scope_id': plan['scope_id'], 'store_id': 'static-target-store',
            'target_session_id': 'static-target-session', 'observation_id': suffix + '-read-' + str(number),
            'read_sequence': number, 'observed_at': timestamp(-50),
            'read_status': 'OK', 'scope_complete': True, 'relevant_scope_completeness': True,
            'target_state_version': 'static-unchanged-epoch', 'target_state_hash': digest(view_snapshot['payload']),
            'view': {'target': copy.deepcopy(view_snapshot['payload'])}}
        observed = resource(root, body)
        observations.append(observed)
        append('READONLY_ABSENCE_READ_FINISHED', dict(base, read_index=number, observation=observed,
            observation_id=body['observation_id'], read_sequence=number), ref(plan), True)
        if number == 2:
            snapshot = copy.deepcopy(view_snapshot)
            snapshot['artifact_id'] = 'static-absence-snapshot-' + suffix
            snapshot['created_at'] = body['observed_at']
            snapshot['payload'].update(observed_at=body['observed_at'], observed_version=body['target_state_version'], observed_hash=body['target_state_hash'])
            snapshot.pop('content_hash')
            snapshot['content_hash'] = digest(snapshot)
            artifacts.append(snapshot)
    prefix = {'format_version': 'a03-runtime-event-prefix-1', 'profile_id': PROFILE,
        'journal_id': 'static-journal-' + suffix, 'target_key': key, 'from_sequence': 1,
        'predecessor': {'sequence': 0, 'hash': ZERO}, 'subject_plan_ref': ref(plan), 'accepted_anchor': accepted,
        'accepted_predecessor': predecessor, 'expected_book_head': {'sequence': len(frames), 'hash': previous}, 'frames': frames}
    prefix_resource = resource(root, prefix, 'values/' + suffix + '-prefix.json')
    prepared = resource(root, {'format_version': 'a03-readonly-prepared-1', 'origin': 'SYNTHETIC',
        'source_ref': ref(source), 'plan_ref': ref(plan), 'action_id': action['action_id'], 'action_digest': digest(action),
        'observation_id': suffix + '-read-1', 'read_sequence': 1, 'first_observation_ref': observations[0],
        'facts': action['expected_before'], 'capability_type': 'READONLY_ABSENCE_ONLY_NO_DISPATCH'})
    basis = {'format_version': 'a03-unattempted-basis-2', 'origin': 'SYNTHETIC', 'plan_ref': ref(plan),
        'source_ref': ref(source), 'target_key': key, 'plan_status': 'INTERRUPTED', 'generation': generation,
        'action_digest': digest(action), 'expected_event_head': prefix['expected_book_head'], 'comparison': 'ABSENT',
        'observer_calls': 2, 'retries': 0, 'single_read_seconds': 2, 'entry_seconds': 8, 'parent_call_seconds': 60,
        'journal_id': prefix['journal_id'], 'registration_id': 'static-registration', 'action_id': action['action_id'],
        'owner_id': owner, 'target_store_id': 'static-target-store', 'target_session_id': 'static-target-session',
        'scope_id': plan['scope_id'], 'complete_uncalled_prefix': prefix_resource,
        'first_observation_ref': observations[0], 'readonly_prepared_ref': prepared, 'second_observation_ref': observations[1],
        'initial_event_head': initial_head, 'readonly_session_id': session,
        'gate_binding': {'ledger_id': 'static-ledger', 'owner_id': owner, 'generation': generation, 'session_id': session},
        'currentness_assertion_ref': observations[2], 'total_read_calls': 3}
    return basis, prepared, observations[1], ref(snapshot), prefix


def build_report_case(name, two_heads=False):
    root, bundle = clone_seed(name)
    artifacts = bundle['artifacts']
    source, graph, plan = [next(a for a in artifacts if a['kind'] == kind) for kind in ('SourceBundle', 'QuestionGraph', 'ApplyPlan')]
    head = next(a for a in artifacts if a['kind'] == 'ReconciliationResult')
    preserved = canonical(head)
    (root / 'head-before.json').write_bytes(preserved)
    # New fixture objects have new identities. This is not a conversion of actual execution history.
    heads = [head]
    if two_heads:
        original_intent = next(a for a in artifacts if a['kind'] == 'WriteIntent')
        action = plan['payload']['actions'][1]
        payload = copy.deepcopy(original_intent['payload'])
        payload.update(action_id=action['action_id'], action_digest=digest(action), question_id=action['target']['question_id'],
                       source_entity_ids=action['source_entity_ids'], journal_sequence=20, journal_head_hash=digest('fictional-second-intent-predecessor'))
        payload['prepared_before'] = resource(root, {'format_version': 'a03-static-prepared-facts-1',
            'status': 'PROPOSAL_UNIMPLEMENTED', 'plan_ref': ref(plan), 'action_id': action['action_id'],
            'action_digest': digest(action), 'facts': action['expected_before'],
            'source_ref': payload['source_ref'], 'before_snapshot_ref': payload['before_snapshot_ref'],
            'admission': 'NO_NATIVE_PREPARED_HANDLE'})
        intent = seal(original_intent, 'WriteIntent', 'static-second-intent', payload, root, original_intent['schema_version'])
        artifacts.append(intent)
        snapshot = copy.deepcopy(next(a for a in artifacts if a['kind'] == 'PlatformSnapshot' and a['artifact_id'] == 'snapshot-match'))
        snapshot['artifact_id'] = 'static-second-snapshot'
        snapshot['created_at'] = '2026-10-17T00:00:12Z'
        snapshot['payload'].update(observed_at=snapshot['created_at'], observed_version='static-snapshot-2')
        snapshot.pop('content_hash')
        snapshot['content_hash'] = digest(snapshot)
        artifacts.append(snapshot)
        payload = copy.deepcopy(head['payload'])
        payload.update(intent_ref=ref(intent), action_id=action['action_id'], action_digest=digest(action),
                       obligation_id='obl-' + digest({k: intent['payload'][k] for k in ('journal_id', 'target_key', 'journal_sequence', 'journal_head_hash')} | {'intent_ref': ref(intent)}),
                       observed_snapshot_ref=ref(snapshot), observation_id='static-observation-second',
                       observed_at='2026-10-17T00:00:12Z', recovery_call_id='static-second-call', read_sequence=12,
                       observation='ABSENT', resolution='RESOLVED_NOT_APPLIED', platform_ids=[], reason_code='STATIC_ABSENT_VALUE')
        payload['readback'] = resource(root, {'origin': 'SYNTHETIC', 'sample_status': 'PROPOSAL_UNIMPLEMENTED',
            'plan_ref': ref(plan), 'intent_ref': ref(intent), 'observed_snapshot_ref': ref(snapshot),
            'observation_id': payload['observation_id'], 'observed_at': payload['observed_at'], 'read_sequence': 12,
            'target_state_version': payload['target_state_version'], 'target_state_hash': payload['target_state_hash'],
            'scope_complete': True, 'view': {'target': snapshot['payload']}})
        payload['evidence_refs'] = [payload['readback']]
        second = seal(head, 'ReconciliationResult', 'static-second-head', payload, root, head['schema_version'])
        artifacts.append(second)
        heads.append(second)
    # Each plan result has an explicit fact: later receipt does not modify original null-head binding.
    facts, results, bindings = [], [], []
    for index, action in enumerate(plan['payload']['actions']):
        selected = next((h for h in heads if h['payload']['action_id'] == action['action_id']), None)
        basis = None
        if selected:
            readback = selected['payload']['readback']
            intent = next(a for a in artifacts if ref(a) == selected['payload']['intent_ref'])
            prepared = intent['payload']['prepared_before']
            snapshot_ref = selected['payload']['observed_snapshot_ref']
            commit_sequence, predecessor_hash = 100 + index, digest('static-recovery-fact-predecessor-' + str(index))
        else:
            view = next(a for a in artifacts if a['kind'] == 'PlatformSnapshot' and a['artifact_id'] == 'snapshot-match')
            basis, prepared, readback, snapshot_ref, prefix = absence_value(root, bundle, action, name + '-' + str(index), view_snapshot=view)
            commit_sequence = basis['expected_event_head']['sequence'] + 1
            predecessor_hash = basis['expected_event_head']['hash']
        outcome = {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[selected['payload']['resolution']] if selected else 'NOT_APPLIED'
        result = {'action_id': action['action_id'], 'outcome': outcome,
            'attempt_fact': 'MAY_HAVE_BEEN_ATTEMPTED' if selected else 'NOT_ATTEMPTED',
            'intent_ref': selected['payload']['intent_ref'] if selected else None,
            'platform_ids': selected['payload']['platform_ids'] if selected else [],
            'before_evidence_refs': ['proof-source'], 'after_evidence_refs': ['proof-source'],
            'readback': readback, 'effect_match': selected['payload']['observation'] if selected else 'ABSENT',
            'next_step': 'POSTCHECK' if selected else 'RECHECK_TARGET', 'replay_allowed': False,
            'attempt_evidence_refs': [readback], 'reason': 'PROPOSAL_UNIMPLEMENTED static value, not a recorded execution'}
        fact = resource(root, {'format_version': 'a03-action-fact-2', 'design_only': True,
            'plan_ref': ref(plan), 'action_id': action['action_id'], 'action_digest': digest(action),
            'origin_phase': 'RECOVERY' if selected else 'UNATTEMPTED_ABSENCE',
            'resolution_ref': ref(selected) if selected else None, 'result': result,
            'intent_ref': selected['payload']['intent_ref'] if selected else None,
            'obligation_id': selected['payload']['obligation_id'] if selected else None,
            'prepared_before': prepared, 'observed_snapshot_ref': snapshot_ref, 'readback': readback,
            'comparator_version': 'a02-facts-1', 'journal_sequence': commit_sequence,
            'predecessor_hash': predecessor_hash, 'unattempted_basis': resource(root, basis) if basis else None})
        facts.append(fact)
        results.append(result)
        bindings.append({'action_id': action['action_id'], 'action_digest': digest(action), 'intent_ref': result['intent_ref'],
            'fact_ref': fact, 'resolution_head_ref': ref(selected) if selected else None,
            'head_original_receipt_ref': selected['payload']['original_receipt_ref'] if selected else None,
            'observed_snapshot_ref': selected['payload']['observed_snapshot_ref'] if selected else None,
            'effective_outcome': result['outcome']})
    receipt = seal(plan, 'ExecutionReceipt', 'static-later-complete-receipt',
        {'plan': ref(plan), 'execution_mode': 'SIMULATED', 'results': results, 'action_fact_refs': facts,
         'unresolved_issue_ids': [], 'write_disposition': 'RECHECK_TARGET'}, root)
    artifacts.append(receipt)
    final_snapshot = copy.deepcopy(next(a for a in artifacts if a['kind'] == 'PlatformSnapshot' and a['artifact_id'] == 'snapshot-match'))
    final_snapshot['artifact_id'] = 'static-report-current-snapshot'
    final_snapshot['created_at'] = '2026-10-17T00:19:59Z'
    final_snapshot['payload'].update(observed_at=final_snapshot['created_at'], observed_version='static-report-read')
    final_snapshot.pop('content_hash')
    final_snapshot['content_hash'] = digest(final_snapshot)
    artifacts.append(final_snapshot)
    post = seal(plan, 'CheckReport', 'static-new-post', {'stage': 'POST_APPLY', 'subject': ref(receipt),
        'graph': plan['payload']['graph'], 'policy': plan['payload']['policy'], 'receipt': ref(receipt),
        'report_snapshot_ref': ref(final_snapshot), 'action_bindings': bindings, 'recovery_refs': [ref(h) for h in heads],
        'frame_structure': 'UNAVAILABLE', 'content_check_status': 'PENDING', 'submission_status': 'NOT_SUBMITTED',
        'decision': 'HOLD', 'issues': ['STATIC_ONLY_ACTUAL_FRAME_VERIFICATION_REQUIRED']}, root)
    artifacts.append(post)
    batch = seal(plan, 'BatchReport', 'static-new-batch', {'source': ref(source), 'graph': ref(graph), 'receipt': ref(receipt),
        'postcheck': ref(post), 'report_snapshot_ref': ref(final_snapshot), 'recovery_refs': [ref(h) for h in heads],
        'scope_manifest': source['payload']['scope_manifest'], 'total_expected': len(source['payload']['scope_manifest']),
        'questions': [{'question_id': q, 'state': 'PENDING'} for q in source['payload']['scope_manifest']],
        'state': 'NEEDS_REVIEW', 'content_check_status': 'PENDING', 'submission_status': 'NOT_SUBMITTED'}, root)
    artifacts.append(batch)
    assert canonical(head) == preserved
    (root / 'head-after.json').write_bytes(canonical(head))
    package = {'format_version': 'a03-static-amendment-package-1', 'profile_id': PROFILE,
        'status': 'PROPOSAL_UNIMPLEMENTED', 'execution_authorized': False, 'origin': 'SYNTHETIC',
        'bundle': bundle, 'root_refs': [ref(post), ref(batch)], 'legacy_heads': [ref(h) for h in heads],
        'expectation': 'NEW_REPORT_REFERENCE_RULES_ACCEPT_VALUE_ONLY_OLD_R2_POST_EQUALITIES_REJECT',
        'runtime_admission': 'NOT_AUTHORIZED_NO_NATIVE_RUNTIME_HISTORY_OR_OBSERVATIONS',
        'reachability': 'NOT_PRODUCED_BY_CURRENT_STOP_ON_FIRST_UNKNOWN_RUNTIME' if two_heads else 'SINGLE_HEAD_ROUTE_PROPOSED_NOT_RUN',
        'validation_layers': {'complete_resource_and_artifact_reference_package': True,
            'declared_report_binding_rules': 'STATIC_CHECKABLE', 'native_history_qualification': 'NOT_PROVIDED',
            'global_fact_journal_consistency': 'NOT_ASSERTED_ISOLATED_FACT_WITNESSES',
            'reason': 'Imported R2 design head is immutable and is not a native P2 journal. Absence fact witnesses are isolated serializations, not one admitted ledger. Runtime may not register this package.'}}
    write(root.relative_to(OUT) / 'package.json', package)
    write(root.relative_to(OUT) / 'consumer-closure.json', {'consumers': [{'consumer': ref(a), 'input_refs': a['input_refs']} for a in artifacts],
        'immutability': {'head_before_sha256': sha(preserved), 'head_after_sha256': sha(canonical(head))},
        'layer': 'STATIC_REFERENCE_DESIGN_NOT_PRODUCT_VALIDATION'})


def build_prefix_cases():
    for name, later in [('first-unattempted-prefix', False), ('later-plan-prefix', True)]:
        root, bundle = clone_seed(name)
        bundle['artifacts'] = [a for a in bundle['artifacts'] if a['kind'] not in ('WriteIntent', 'ReconciliationResult', 'ExecutionProgress') and a['artifact_id'] != 'snapshot-match']
        plan = next(a for a in bundle['artifacts'] if a['kind'] == 'ApplyPlan')
        basis, prepared, readback, snapshot, prefix = absence_value(root, bundle, plan['payload']['actions'][0], name, later)
        basis_resource = resource(root, basis, 'values/basis.json')
        write(root.relative_to(OUT) / 'package.json', {'status': 'PROPOSAL_UNIMPLEMENTED', 'profile_id': PROFILE,
            'execution_authorized': False, 'origin': 'SYNTHETIC', 'bundle': bundle,
            'basis': basis_resource, 'prefix': basis['complete_uncalled_prefix'],
            'native_admission': 'UNIMPLEMENTED_NO_CURRENT_DB_OR_TARGET_ASSERTION',
            'expected_subject_accepted_sequence': 8 if later else 3})


def build_pre_and_conversion():
    root, bundle = clone_seed('pre-and-conversion-design')
    source, graph, plan = [next(a for a in bundle['artifacts'] if a['kind'] == k) for k in ('SourceBundle', 'QuestionGraph', 'ApplyPlan')]
    # Explicit fixture-author oracle, not inferred completeness of a real book.
    oracle = resource(root, {'format_version': 'a03-fixture-author-oracle-1', 'origin': 'SYNTHETIC',
        'status': 'UNAPPROVED_STATIC_ORACLE', 'source_ref': ref(source), 'scope_id': source['scope_id'],
        'pages': {'asset-page-a1': ['question-alpha', 'question-child'],
                  'asset-page-a2': ['question-alpha', 'question-child'], 'asset-page-b1': ['question-beta']},
        'questions': ['question-alpha', 'question-child', 'question-beta'],
        'answers': {'question-alpha': ['fragment-alpha-answer'], 'question-child': ['fragment-child-answer'], 'question-beta': ['fragment-beta-answer']},
        'expected_graph_content_hash': graph['content_hash'], 'policy': plan['payload']['policy'],
        'raw_assets': [{k: a[k] for k in ('path', 'sha256')} for a in source['payload']['assets']],
        'qualification': 'Future registry approval must review this independently; this authoring script does not certify it.'}, 'values/oracle.json')
    unavailable = resource(root, {'status': 'NOT_RUN', 'reason': 'No verifier, native read, producer handle or hold operation was executed.'}, 'values/not-run.json')
    initial_snapshot = next(a for a in bundle['artifacts'] if a['artifact_id'] == 'a02-snapshot')
    run = {'format_version': 'a03-synthetic-precheck-run-1', 'producer_kind': 'REGISTERED_SYNTHETIC_FIXTURE_VERIFIER_1',
        'oracle': oracle, 'source_ref': ref(source), 'graph_ref': ref(graph), 'policy_ref': plan['payload']['policy'],
        'hold_id': 'static-not-an-active-hold', 'hold_event_head': {'sequence': 10, 'hash': digest('static-hold-event')},
        'actual_snapshot_ref': ref(initial_snapshot), 'actual_observation': unavailable,
        'run_id': 'static-unexecuted-pre-run', 'started_at': '2026-10-17T00:00:00Z', 'finished_at': '2026-10-17T00:00:00Z',
        'implementation_digest': digest('UNIMPLEMENTED_REGISTERED_SYNTHETIC_FIXTURE_VERIFIER_1'),
        'input_hashes': [{k: a[k] for k in ('path', 'sha256')} for a in source['payload']['assets']],
        'checks': {k: {'outcome': 'UNAVAILABLE', 'comparison_digest': digest({'check': k, 'status': 'NOT_RUN'}), 'evidence': [unavailable]}
            for k in ('source_integrity', 'structure', 'answer_matching', 'coverage', 'policy')},
        'decision': 'HOLD', 'authority': 'VALUE_ONLY_RUNTIME_ADMISSION_REQUIRED'}
    run_ref = resource(root, run, 'values/unexecuted-pre-run.json')
    pre = next(a for a in bundle['artifacts'] if a['kind'] == 'CheckReport' and a['payload']['stage'] == 'PRE_APPLY')
    pre_payload = copy.deepcopy(pre['payload'])
    pre_payload['synthetic_run_ref'] = run_ref
    pre_payload['decision'] = 'HOLD'
    pre_payload['reason'] = 'PROPOSAL_UNIMPLEMENTED: no actual verifier invocation or post-hold native snapshot'
    for check in pre_payload['checks']:
        check.update(outcome='UNAVAILABLE', reason='NOT_RUN; static shape only')
    new_pre = seal(pre, 'CheckReport', 'static-unavailable-new-pre', pre_payload, root)
    bundle['artifacts'].append(new_pre)
    write(root.relative_to(OUT) / 'package.json', {'status': 'PROPOSAL_UNIMPLEMENTED', 'profile_id': PROFILE,
        'execution_authorized': False, 'bundle': bundle, 'oracle': oracle, 'pre_run': run_ref, 'new_pre_ref': ref(new_pre),
        'expected_admission': 'REJECT_UNAVAILABLE_AND_NO_REGISTERED_RUN',
        'entry_proposal': {'produce_synthetic_precheck': 'exact registered fixture oracle + fresh post-hold native snapshot/observation + five new checks; returns new PRE and native run handle',
            'admit_synthetic_precheck': 'verify current known registry/implementation/input bytes, native run handle identity and complete five-check evidence; JSON/signature alone cannot grant admission'},
        'check_procedures': {'source_integrity': 'hash every exact original asset and require declared expected/acquired pages, dimensions and complete independent oracle enumeration',
            'structure': 'check all question/fragment/region IDs, references, boxes, sharing/cross-page structure against approved exact fixture oracle',
            'answer_matching': 'compare all selected answer links with explicit fixture-author answer relationships; no OCR or semantic matching inference',
            'coverage': 'account for every oracle page/question, every region and scope denominator including exception/skipped items',
            'policy': 're-read exact policy bytes and validate declared scope/type/platform mapping under registered implementation'},
        'hold_sequences': {'positive_expected_NOT_RUN': ['new native snapshot after hold', 'five checks actually executed after hold', 'admit new PRE', 'new TARGET', 'new candidate plan', 'canonical book gate/current owner/full pending scan', 'independent final reread + target fence + ledger CAS', 'append HOLD_CLEARED and fresh registration; terminal resolution unchanged; no dispatch'],
            'second_drift_expected_NOT_RUN': ['same candidate construction', 'change target in isolated future fixture before final reread', 'TARGET_CHANGED; hold persists; no terminal successor or permit'],
            'negative_expected_NOT_RUN': ['old PRE renamed/resealed', 'caller PASS', 'missing oracle/page/answer', 'unregistered producer handle', 'replayed run', 'foreign scope', 'stale final snapshot', 'foreign-book owner/index', 'other pending UNKNOWN must still pause writes']}})
    # A new static source file, explicitly not a reconstruction of any historical failure.
    initial = copy.deepcopy(bundle)
    initial['artifacts'] = [a for a in initial['artifacts'] if a['kind'] not in ('WriteIntent', 'ReconciliationResult', 'ExecutionProgress') and a['artifact_id'] != 'snapshot-match']
    source_file = resource(root, {'status': 'NEW_STATIC_PROPOSAL_INPUT_NOT_HISTORICAL_ORIGINAL', 'bundle': initial}, 'conversion/original/new-static-initial.json')
    mapping = resource(root, {'format_version': 'a03-static-conversion-map-2', 'status': 'UNIMPLEMENTED_MAPPING_PLAN',
        'namespace': 'new-fixture-01', 'history_migrated': False,
        'artifacts': [{'old_ref': ref(a), 'new_artifact_id': 'new-fixture-01:' + a['artifact_id'], 'new_revision': 1,
            'new_content_hash': None, 'digest_status': 'UNIMPLEMENTED_RECURSIVE_REWRITE_REQUIRED'} for a in initial['artifacts']],
        'resources': [{'original_path': p.relative_to(root).as_posix(), 'original_sha256': sha(p.read_bytes()),
            'new_path': None, 'new_sha256': None, 'disposition': 'COPY_OR_RECURSIVE_REF_REWRITE_REQUIRED'}
            for p in sorted((root / 'assets').rglob('*')) if p.is_file()],
        'qualification': 'No target bundle or new digest is claimed; null hashes forbid COMMITTED.'}, 'conversion/mapping-plan.json')
    records = []
    for state in ('CREATED', 'COPYING', 'VALIDATING', 'INCOMPLETE'):
        record = {'format_version': 'a03-explicit-conversion-state-2', 'conversion_id': 'static-conversion-01',
            'source_sha256': source_file['sha256'], 'source_profile_id': 'EXPLICIT_INITIAL_ALL_SYNTHETIC_R2',
            'target_profile_id': PROFILE, 'state': state, 'previous_record_sha256': sha(canonical(records[-1])+b'\n') if records else None,
            'written_files': [{'path': source_file['path'], 'sha256': source_file['sha256'], 'bytes': (root/source_file['path']).stat().st_size}],
            'mapping': mapping if state in ('VALIDATING', 'INCOMPLETE') else None, 'completion_manifest': None,
            'failure': 'STATIC_INTERRUPTION_EXPECTATION_NOT_AN_EXECUTED_CONVERSION' if state == 'INCOMPLETE' else None, 'history_migrated': False}
        records.append(record)
        resource(root, record, 'conversion/records/%02d-%s.json' % (len(records), state))
    failed = copy.deepcopy(records[2])
    failed.update(state='FAILED', failure='STATIC_FAILURE_EXPECTATION_INCOMPLETE_MAPPING')
    resource(root, failed, 'conversion/failure-branch.json')
    write(root.relative_to(OUT) / 'conversion-policy.json', {'status': 'PROPOSAL_UNIMPLEMENTED', 'source': source_file,
        'mapping_plan': mapping, 'actual_new_bundle': 'NOT_GENERATED', 'commit': 'NOT_EXECUTED_NOT_QUALIFIED',
        'admission': 'READ_ONLY_DIAGNOSTIC', 'reopen': 'existing incomplete directory cannot resume or become executable; explicitly requested new conversion_id/new dir only',
        'supported_future_input': 'exact hash, known all-synthetic initial fixture, full page enumeration/assets/refs; no execution history; new namespace and recursively recomputed hashes',
        'commit_protocol': 'copy immutable originals -> validate provenance/oracle -> rewrite refs/resources/DAG -> complete bijective mapping/new hashes -> validate complete new initial bundle -> fsync files/dir -> atomic completion manifest last -> append COMMITTED',
        'preserved': 'every original byte, every previous state record and failure; append-only corrections',
        'fault_points_NOT_RUN': ['after directory create', 'during original copy', 'during mapping', 'during target bundle write', 'before completion manifest rename', 'after rename before COMMITTED record'],
        'forbidden': ['automatic unknown DB migration', 'reuse incomplete namespace', 'receipt/UNKNOWN conversion', 'LEGACY_UNRECORDED to intent', 'PRE stub relabeled PASS', 'null/incomplete mapping COMMITTED']})


if __name__ == '__main__':
    build_schemas()
    build_prefix_cases()
    build_report_case('late-receipt')
    build_report_case('different-snapshots', True)
    build_pre_and_conversion()
    schemas = [{'path': p.relative_to(OUT).as_posix(), 'sha256': sha(p.read_bytes())} for p in sorted((OUT / 'schemas').rglob('*.json'))]
    write('profile.json', {'profile_id': PROFILE, 'status': 'PROPOSAL_UNIMPLEMENTED', 'implementation_authorized': False,
        'exchange_version': 'a03-exchange-2-proposal', 'new_artifact_schema_version': VERSION,
        'legacy_artifact_schema_version': '1.1.0-a-recovery-proposal', 'schema_pins': schemas,
        'api_supplement_sha256': sha((OUT/'api-supplement-proposal.json').read_bytes()),
        'selection': 'explicit exact profile_id plus complete schema pin set; never newest version string',
        'frozen_r2_role': 'read-only immutable source nodes; not automatic new execution eligibility',
        'unimplemented_domains': ['runtime authority', 'native observations', 'complete formal action-fact production', 'registered synthetic PRE verifier']})
    print(json.dumps({'status': 'STATIC_PROPOSAL_AUTHORED', 'new_event_types': len(CATALOG), 'schemas': len(schemas),
        'product_imports': 0, 'product_runs': 0, 'network_or_model_calls': 0}))
