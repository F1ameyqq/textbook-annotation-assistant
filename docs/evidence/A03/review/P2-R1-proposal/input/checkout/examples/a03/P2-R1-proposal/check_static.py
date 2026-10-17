"""Bounded stdlib structural/reference checks of NEW proposal values only.

Never imports product modules or inspects DB/platform/process authority. The
schema interpreter rejects unsupported keywords; it is not a production validator.
"""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE_DATA = Path(__file__).resolve().parent
DATA = BASE_DATA/'candidate-v2'
if len(sys.argv) > 1:
    assert len(sys.argv) == 3 and sys.argv[1] == '--data-dir'
    DATA = (BASE_DATA/sys.argv[2]).resolve()
    assert DATA.is_relative_to(BASE_DATA)
EVIDENCE = ROOT / 'docs/evidence/A03/execution/P2-R1-proposal'
PROFILE = 'a03-p2-r1-amendment-1-PROPOSAL'
VERSION = '1.2.0-a03-amendment-proposal'
ZERO = '0'*64
CHECKS = []


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def canonical(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(v):
    return sha(canonical(v))


def load(p):
    return json.loads(p.read_bytes())


def walk(v):
    yield v
    if isinstance(v, dict):
        for child in v.values():
            yield from walk(child)
    elif isinstance(v, list):
        for child in v:
            yield from walk(child)


def ref(a):
    return {k: a[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


def is_ref(v):
    return isinstance(v, dict) and set(v) == {'artifact_id', 'revision', 'kind', 'content_hash'}


KEYWORDS = {'$schema', '$id', '$comment', '$defs', '$ref', 'title', 'description', 'discriminator',
    'type', 'properties', 'propertyNames', 'required', 'additionalProperties', 'anyOf', 'oneOf',
    'const', 'enum', 'pattern', 'format', 'minLength', 'minItems', 'maxItems', 'minimum',
    'maximum', 'exclusiveMinimum', 'items', 'uniqueItems', 'minProperties'}


def audit_schema(s):
    require(isinstance(s, dict), 'nonobject schema')
    require(not set(s)-KEYWORDS, 'unsupported keywords '+str(set(s)-KEYWORDS))
    for key in ('properties', '$defs'):
        for child in s.get(key, {}).values():
            audit_schema(child)
    for key in ('oneOf', 'anyOf'):
        for child in s.get(key, []):
            audit_schema(child)
    for key in ('items', 'propertyNames', 'additionalProperties'):
        if isinstance(s.get(key), dict):
            audit_schema(s[key])


def validate(v, s, document, path):
    if '$ref' in s:
        name, _, pointer = s['$ref'].partition('#')
        otherpath = (path.parent/name).resolve() if name else path
        require(otherpath.is_relative_to(DATA/'schemas'), 'schema ref escaped')
        other = load(otherpath) if name else document
        target = other
        for token in pointer.strip('/').split('/') if pointer else []:
            target = target[token.replace('~1', '/').replace('~0', '~')]
        validate(v, target, other, otherpath)
    for keyword in ('oneOf', 'anyOf'):
        if keyword in s:
            matches = 0
            for child in s[keyword]:
                try:
                    validate(v, child, document, path)
                    matches += 1
                except Invalid:
                    pass
            require(matches == 1 if keyword == 'oneOf' else matches >= 1, keyword+' branch count '+str(matches))
    if 'const' in s:
        require(v == s['const'] and (not isinstance(v, bool) or type(v) is type(s['const'])), 'const mismatch')
    if 'enum' in s:
        require(v in s['enum'], 'enum mismatch')
    if 'type' in s:
        types = {'object': lambda x: isinstance(x, dict), 'array': lambda x: isinstance(x, list),
            'string': lambda x: isinstance(x, str), 'integer': lambda x: type(x) is int,
            'number': lambda x: type(x) in (float, int), 'boolean': lambda x: type(x) is bool,
            'null': lambda x: x is None}
        require(types[s['type']](v), 'type mismatch '+s['type'])
    if isinstance(v, dict):
        require(set(s.get('required', [])) <= set(v), 'required missing '+str(set(s.get('required', []))-set(v)))
        require(len(v) >= s.get('minProperties', 0), 'minProperties')
        props = s.get('properties', {})
        for key, member in v.items():
            if 'propertyNames' in s:
                validate(key, s['propertyNames'], document, path)
            if key in props:
                validate(member, props[key], document, path)
            elif s.get('additionalProperties') is False:
                raise Invalid('additional property '+key)
            elif isinstance(s.get('additionalProperties'), dict):
                validate(member, s['additionalProperties'], document, path)
    if isinstance(v, list):
        require(len(v) >= s.get('minItems', 0) and len(v) <= s.get('maxItems', len(v)), 'array length')
        if s.get('uniqueItems'):
            require(len({canonical(x) for x in v}) == len(v), 'duplicate array')
        if 'items' in s:
            for member in v:
                validate(member, s['items'], document, path)
    if isinstance(v, str):
        require(len(v) >= s.get('minLength', 0), 'string length')
        if 'pattern' in s:
            require(re.search(s['pattern'], v) is not None, 'pattern mismatch')
        if 'format' in s:
            require(s['format'] == 'date-time', 'unsupported format')
            try:
                value = datetime.fromisoformat(v.replace('Z', '+00:00'))
                require(value.tzinfo is not None, 'timezone missing')
            except ValueError as error:
                raise Invalid('date-time') from error
    if type(v) in (int, float):
        for key, predicate in [('minimum', lambda x: v >= x), ('maximum', lambda x: v <= x), ('exclusiveMinimum', lambda x: v > x)]:
            if key in s:
                require(predicate(s[key]), key)


def shape(v, name):
    path = DATA/'schemas'/name
    document = load(path)
    validate(v, document, document, path)


def resource(root, r):
    p = (root/r['path']).resolve()
    require(p.is_relative_to(root.resolve()), 'resource path escaped')
    require(p.is_file() and sha(p.read_bytes()) == r['sha256'], 'resource missing/hash '+r['path'])
    return load(p) if r.get('media_type') == 'application/json' else None


def refs(v, root, seen=None):
    result, seen = {}, set() if seen is None else seen
    for x in walk(v):
        if is_ref(x):
            result[digest(x)] = x
        elif isinstance(x, dict) and {'path', 'sha256'} <= set(x):
            token = (x['path'], x['sha256'])
            value = resource(root, x)
            if value is not None and token not in seen:
                seen.add(token)
                result.update(refs(value, root, seen))
    return result


def artifacts(bundle, root):
    shape(bundle, 'exchange-v2.schema.json')
    values = {digest(ref(a)): a for a in bundle['artifacts']}
    require(len(values) == len(bundle['artifacts']), 'duplicate artifact')
    oldpath = DATA/'schemas/frozen-r2/recovery-exchange.schema.json'
    old = load(oldpath)
    adjacency = {}
    for a in bundle['artifacts']:
        body = {k: v for k, v in a.items() if k != 'content_hash'}
        require(digest(body) == a['content_hash'], 'artifact hash '+a['artifact_id'])
        template = copy.deepcopy(old['$defs'][a['kind']])
        if a['schema_version'] == VERSION:
            template['properties']['schema_version'] = {'const': VERSION}
            # Envelope adapted in memory; full exchange-2 Schema/API is a stated unclosed item.
            template['properties']['payload'] = {}
        validate(a, template, old, oldpath)
        if a['schema_version'] == VERSION:
            if a['kind'] == 'ExecutionReceipt':
                shape(a['payload'], 'receipt-payload-v2.schema.json')
            elif a['kind'] == 'BatchReport' or (a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY'):
                shape(a['payload'], 'report-payloads-v2.schema.json')
            elif a['kind'] == 'CheckReport' and a['payload']['stage'] == 'PRE_APPLY':
                shape(resource(root, a['payload']['synthetic_run_ref']), 'synthetic-precheck-run-v1.schema.json')
            else:
                raise Invalid('unregistered new kind')
        else:
            require(a['schema_version'] == '1.1.0-a-recovery-proposal', 'unknown artifact version')
        consumed = refs(a['payload'], root)
        declared = {digest(r) for r in a['input_refs']}
        require(set(consumed) <= declared, 'consumer declaration missing '+a['artifact_id'])
        adjacency[digest(ref(a))] = declared
        for r in list(consumed.values())+a['input_refs']:
            require(digest(r) in values and ref(values[digest(r)]) == r, 'unresolved exact ref')
            target = values[digest(r)]
            require((a['book_id'], a['scope_id']) == (target['book_id'], target['scope_id']), 'ordinary ref scope')
    active, done = set(), set()
    def visit(node):
        require(node not in active, 'artifact reference cycle')
        if node in done:
            return
        active.add(node)
        for target in adjacency[node]:
            visit(target)
        active.remove(node)
        done.add(node)
    for node in adjacency:
        visit(node)
    return values


def resolve(values, r):
    require(digest(r) in values, 'unresolved artifact')
    return values[digest(r)]


def prefix_check(prefix, bundle, root, action=None):
    shape(prefix, 'runtime-event-prefix-v1.schema.json')
    require(prefix['profile_id'] == PROFILE, 'unknown prefix profile')
    values = {digest(ref(a)): a for a in bundle['artifacts']}
    subject = resolve(values, prefix['subject_plan_ref'])
    previous, accepted, reserved = ZERO, None, None
    for number, frame in enumerate(prefix['frames'], 1):
        e = frame['event']
        require(e['sequence'] == number and e['previous_hash'] == previous, 'prefix continuity')
        require(digest({k: v for k, v in e.items() if k != 'event_hash'}) == e['event_hash'], 'event hash')
        require(e['journal_id'] == prefix['journal_id'] and e['target_key'] == prefix['target_key'], 'book/journal identity')
        require(('event_version' in e) == (frame['representation'] == 'RUNTIME_EVENT_2'), 'event representation mismatch')
        consumed = refs(e, root)
        require(set(consumed) <= {digest(r) for r in frame['input_refs']}, 'event consumer declaration')
        if e['plan_ref'] is not None:
            event_plan = resolve(values, e['plan_ref'])
            scope = event_plan['scope_id']
            require(frame['consumer_scope_id'] == scope, 'consumer frame scope')
            if 'plan_ref' in e['payload']:
                require(e['payload']['plan_ref'] == e['plan_ref'], 'event envelope/payload plan binding')
            if e['event'] in ('PLAN_ACCEPTED', 'PLAN_ACTIONS_RESERVED'):
                binding_key = 'actions' if e['event'] == 'PLAN_ACCEPTED' else 'reservations'
                require(e['payload'][binding_key] == [{'action_id':a['action_id'], 'action_digest':digest(a)} for a in event_plan['payload']['actions']], 'event plan action bindings')
        else:
            scope = frame['consumer_scope_id']
        for r in frame['input_refs']:
            a = resolve(values, r)
            require(a['book_id'] == subject['book_id'] and a['scope_id'] == scope, 'event ref book/scope')
        if e['event'] == 'PLAN_ACCEPTED' and e['plan_ref'] == prefix['subject_plan_ref']:
            require(accepted is None, 'duplicate accepted anchor')
            accepted = {'sequence': number, 'hash': e['event_hash']}
            require(prefix['accepted_predecessor'] == {'sequence': number-1, 'hash': previous}, 'accepted predecessor')
        if e['event'] == 'PLAN_ACTIONS_RESERVED' and e['plan_ref'] == prefix['subject_plan_ref']:
            reserved = e['payload']['reservations']
        if action and e['plan_ref'] == prefix['subject_plan_ref'] and e['payload'].get('action_id') == action['action_id']:
            require(e['event'] not in ('WRITE_INTENT_COMMITTED', 'DISPATCH_PERMIT_ISSUED', 'DISPATCH_PERMIT_CONSUMED', 'DISPATCH_STARTED', 'ACTION_RESULT_COMMITTED', 'UNATTEMPTED_ABSENCE_COMMITTED'), 'uncalled prefix has attempt/fact')
        previous = e['event_hash']
    require(prefix['accepted_anchor'] == accepted, 'accepted anchor')
    require(reserved == [{'action_id': a['action_id'], 'action_digest': digest(a)} for a in subject['payload']['actions']], 'permanent reservation bindings')
    require(prefix['expected_book_head'] == {'sequence': len(prefix['frames']), 'hash': previous}, 'book head stale')


def basis_check(basis, bundle, root):
    shape(basis, 'unattempted-basis-v2.schema.json')
    plan = next(a for a in bundle['artifacts'] if ref(a) == basis['plan_ref'])
    action = next(a for a in plan['payload']['actions'] if a['action_id'] == basis['action_id'])
    prefix = resource(root, basis['complete_uncalled_prefix'])
    prefix_check(prefix, bundle, root, action)
    require(basis['expected_event_head'] == prefix['expected_book_head'], 'basis final head')
    require(basis['action_digest'] == digest(action), 'basis action digest')
    reads = [resource(root, basis[k]) for k in ('first_observation_ref', 'second_observation_ref', 'currentness_assertion_ref')]
    require(len({r['observation_id'] for r in reads}) == 3 and [r['read_sequence'] for r in reads] == [1, 2, 3], 'distinct new reads')
    require(len({r['target_state_hash'] for r in reads}) == len({r['target_state_version'] for r in reads}) == 1, 'static second drift')
    prepared = resource(root, basis['readonly_prepared_ref'])
    require(prepared['facts'] == action['expected_before'] and prepared['capability_type'] == 'READONLY_ABSENCE_ONLY_NO_DISPATCH', 'readonly prepared')


def report_check(package, root, values):
    bundle = package['bundle']
    post = next(a for a in bundle['artifacts'] if a['artifact_id'] == 'static-new-post')
    batch = next(a for a in bundle['artifacts'] if a['artifact_id'] == 'static-new-batch')
    pp, bp = post['payload'], batch['payload']
    receipt = resolve(values, pp['receipt'])
    plan = resolve(values, receipt['payload']['plan'])
    require(pp['subject'] == pp['receipt'] and pp['graph'] == plan['payload']['graph'] and pp['policy'] == plan['payload']['policy'], 'post subject/graph/policy')
    actions, results, facts, bindings = plan['payload']['actions'], receipt['payload']['results'], receipt['payload']['action_fact_refs'], pp['action_bindings']
    require(len(actions) == len(results) == len(facts) == len(bindings), 'complete receipt')
    heads = []
    for action, result, fr, binding in zip(actions, results, facts, bindings):
        fact = resource(root, fr)
        shape(fact, 'action-fact-v2.schema.json')
        require(action['action_id'] == result['action_id'] == fact['action_id'] == binding['action_id'], 'action binding')
        require(binding['action_digest'] == fact['action_digest'] == digest(action), 'action digest binding')
        require(fr == binding['fact_ref'] and fact['result'] == result and fact['plan_ref'] == ref(plan), 'exact receipt fact')
        require(binding['effective_outcome'] == result['outcome'] and binding['intent_ref'] == result['intent_ref'], 'intent/outcome binding')
        headref = binding['resolution_head_ref']
        if headref:
            head = resolve(values, headref)
            hp = head['payload']
            require(hp['action_id'] == action['action_id'] and hp['action_digest'] == digest(action) and hp['plan_ref'] == ref(plan), 'head plan/action')
            require(hp['intent_ref'] == result['intent_ref'] == fact['intent_ref'] and fact['resolution_ref'] == headref, 'head exact intent')
            require(hp['original_receipt_ref'] == binding['head_original_receipt_ref'], 'original receipt rewritten')
            require(hp['observed_snapshot_ref'] == binding['observed_snapshot_ref'] == fact['observed_snapshot_ref'], 'per-action snapshot replaced')
            require(result['outcome'] == {'RESOLVED_APPLIED': 'APPLIED', 'RESOLVED_NOT_APPLIED': 'NOT_APPLIED', 'STILL_UNKNOWN': 'UNKNOWN'}[hp['resolution']], 'head outcome')
            intent = resolve(values, hp['intent_ref'])
            require(hp['obligation_id'] == 'obl-'+digest({k: intent['payload'][k] for k in ('journal_id','target_key','journal_sequence','journal_head_hash')} | {'intent_ref': hp['intent_ref']}), 'obligation binding')
            heads.append(headref)
        else:
            require(binding['head_original_receipt_ref'] is None and binding['observed_snapshot_ref'] is None, 'headless binding')
            require(fact['origin_phase'] == 'UNATTEMPTED_ABSENCE', 'headless fact origin')
            basis_check(resource(root, fact['unattempted_basis']), bundle, root)
    require(pp['recovery_refs'] == heads == bp['recovery_refs'], 'complete heads')
    require(pp['report_snapshot_ref'] not in [resolve(values, h)['payload']['observed_snapshot_ref'] for h in heads], 'separate report-wide read')
    require(bp['postcheck'] == ref(post) and bp['receipt'] == pp['receipt'] and bp['report_snapshot_ref'] == pp['report_snapshot_ref'], 'batch exact post/receipt/snapshot')
    source = resolve(values, bp['source'])
    require(bp['scope_manifest'] == source['payload']['scope_manifest'] and bp['total_expected'] == len(bp['scope_manifest']), 'denominator')
    require([q['question_id'] for q in bp['questions']] == bp['scope_manifest'], 'all source questions')
    require(pp['decision'] == 'HOLD' and pp['frame_structure'] == 'UNAVAILABLE' and bp['submission_status'] == 'NOT_SUBMITTED', 'unexecuted report stays hold')
    require((root/'head-before.json').read_bytes() == (root/'head-after.json').read_bytes(), 'head changed')


def positive(name, operation):
    operation()
    CHECKS.append({'case': name, 'result': 'PASS', 'layer': 'STATIC_VALUE_ONLY'})


def negative(name, value, operation):
    try:
        operation(value)
    except Invalid as error:
        CHECKS.append({'case': name, 'result': 'EXPECTED_REJECTION', 'reason': str(error), 'layer': 'STATIC_VALUE_ONLY'})
        output = EVIDENCE/'negative-values'/ (name+'.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(json.dumps({'case': name, 'value': value, 'rejected_by_static_check': str(error)}, ensure_ascii=False, indent=2).encode('utf8')+b'\n')
    else:
        raise Invalid('negative accepted '+name)


def rechain(prefix):
    previous = ZERO
    for number, frame in enumerate(prefix['frames'], 1):
        e = frame['event']
        e.update(sequence=number, previous_hash=previous)
        e['event_hash'] = digest({k:v for k,v in e.items() if k != 'event_hash'})
        if e['event'] == 'PLAN_ACCEPTED' and e['plan_ref'] == prefix['subject_plan_ref']:
            prefix['accepted_anchor'] = {'sequence':number, 'hash':e['event_hash']}
            prefix['accepted_predecessor'] = {'sequence':number-1, 'hash':previous}
        previous = e['event_hash']
    prefix['expected_book_head'] = {'sequence':len(prefix['frames']), 'hash':previous}


def main():
    profile = load(DATA/'profile.json')
    require(profile['profile_id'] == PROFILE and profile['status'] == 'PROPOSAL_UNIMPLEMENTED' and not profile['implementation_authorized'], 'profile')
    actual = {p.relative_to(DATA).as_posix(): sha(p.read_bytes()) for p in (DATA/'schemas').rglob('*.json')}
    require(actual == {p['path']:p['sha256'] for p in profile['schema_pins']}, 'complete schema pin set')
    require(profile['api_supplement_sha256'] == sha((DATA/'api-supplement-proposal.json').read_bytes()), 'API supplement pin')
    for p in (DATA/'schemas').rglob('*.schema.json'):
        audit_schema(load(p))
    for p in (DATA/'schemas/frozen-r2').glob('*.schema.json'):
        require(p.read_bytes() == (ROOT/'src/annotation/contracts/schemas'/p.name).read_bytes(), 'old Schema bytes')
    require((DATA/'schemas/frozen-r2/api-proposal.json').read_bytes() == (ROOT/'examples/a03/P1-R2/api-proposal.json').read_bytes(), 'old API bytes')
    CHECKS.append({'case': 'schema-profile-pins-and-frozen-copies', 'result': 'PASS', 'schema_pins': len(actual), 'layer': 'STATIC_VALUE_ONLY'})
    for directory in sorted((DATA/'cases').iterdir()):
        package = load(directory/'package.json')
        require(package['status'] == 'PROPOSAL_UNIMPLEMENTED' and not package['execution_authorized'], 'package authority')
        values = artifacts(package['bundle'], directory)
        CHECKS.append({'case': directory.name+'-artifact-resource-closure', 'result': 'PASS', 'artifacts': len(values), 'layer': 'STATIC_VALUE_ONLY'})
        if 'basis' in package:
            basis = resource(directory, package['basis'])
            positive(directory.name, lambda: basis_check(basis, package['bundle'], directory))
            prefix = resource(directory, package['prefix'])
            require(prefix['accepted_anchor']['sequence'] == package['expected_subject_accepted_sequence'], 'real anchor')
            if directory.name == 'first-unattempted-prefix':
                for name, mutate in [
                    ('dropped-owner-control', lambda p: p['frames'].pop(0)),
                    ('renumbered-plan-projection', lambda p: p['accepted_anchor'].update(sequence=1)),
                    ('stale-book-head', lambda p: p['expected_book_head'].update(sequence=1)),
                    ('unknown-event', lambda p: p['frames'][0]['event'].update(event='OPAQUE_EXTENSION')),
                    ('extra-owner-payload', lambda p: p['frames'][0]['event']['payload'].update(complete=True)),
                    ('caller-complete-boolean', lambda p: p.update(complete=True)),
                    ('foreign-consumer-scope', lambda p: p['frames'][2].update(consumer_scope_id='foreign-scope')),
                    ('unknown-profile', lambda p: p.update(profile_id='latest')),
                    ('undeclared-event-ref', lambda p: p['frames'][2].update(input_refs=[])),
                ]:
                    value = copy.deepcopy(prefix); mutate(value)
                    negative(name, value, lambda p: prefix_check(p, package['bundle'], directory))
                value = copy.deepcopy(prefix)
                value['frames'][2]['event']['payload']['actions'][0]['action_digest'] = 'f'*64
                rechain(value)
                negative('wrong-accepted-action-after-chain-reseal', value, lambda p: prefix_check(p, package['bundle'], directory))
        elif 'root_refs' in package:
            positive(directory.name+'-report-bindings', lambda: report_check(package, directory, values))
            post = next(a for a in package['bundle']['artifacts'] if a['artifact_id'] == 'static-new-post')
            heads = [resolve(values, r) for r in post['payload']['recovery_refs']]
            require(any(h['payload']['original_receipt_ref'] is None for h in heads), 'null original witness')
            if directory.name == 'different-snapshots':
                require(len({digest(h['payload']['observed_snapshot_ref']) for h in heads}) == 2, 'two snapshot witness')
                require(package['reachability'] == 'NOT_PRODUCED_BY_CURRENT_STOP_ON_FIRST_UNKNOWN_RUNTIME', 'runtime reachability disclosure')
            # Logical old-R17 equality witness only; old product validator was not run.
            CHECKS.append({'case': directory.name+'-old-r17-equality-witness', 'result': 'OLD_EQUALITIES_UNSATISFIABLE', 'layer': 'STATIC_LOGIC_NOT_PRODUCT_EXECUTION'})
            if directory.name == 'late-receipt':
                def bad_post_binding(p):
                    return next(a for a in p['bundle']['artifacts'] if a['artifact_id'] == 'static-new-post')['payload']
                def bad_receipt(p):
                    return next(a for a in p['bundle']['artifacts'] if a['kind'] == 'ExecutionReceipt')['payload']
                for name, mutate in [
                    ('null-original-replaced-with-later-receipt', lambda p: bad_post_binding(p)['action_bindings'][0].update(head_original_receipt_ref=bad_post_binding(p)['receipt'])),
                    ('action-snapshot-replaced-with-report-read', lambda p: bad_post_binding(p)['action_bindings'][0].update(observed_snapshot_ref=bad_post_binding(p)['report_snapshot_ref'])),
                    ('receipt-tail-action-omitted', lambda p: bad_receipt(p)['results'].pop()),
                    ('recovery-head-omitted', lambda p: bad_post_binding(p).update(recovery_refs=[])),
                    ('pending-frame-falsely-passed', lambda p: bad_post_binding(p).update(frame_structure='PASS')),
                ]:
                    value = copy.deepcopy(package); mutate(value)
                    negative(name, value, lambda p: report_check(p, directory, {digest(ref(a)):a for a in p['bundle']['artifacts']}))
        else:
            run = resource(directory, package['pre_run'])
            positive('pre-unavailable-shape', lambda: shape(run, 'synthetic-precheck-run-v1.schema.json'))
            require(run['decision'] == 'HOLD' and all(x['outcome'] == 'UNAVAILABLE' for x in run['checks'].values()), 'fake pre PASS')
            records = sorted((directory/'conversion/records').glob('*.json'))
            previous = None
            for p in records:
                record = load(p); shape(record, 'conversion-state-v2.schema.json')
                require(record['previous_record_sha256'] == previous and record['completion_manifest'] is None, 'conversion record chain')
                previous = sha(p.read_bytes())
            positive('conversion-failure-shape', lambda: shape(load(directory/'conversion/failure-branch.json'), 'conversion-state-v2.schema.json'))
            require(load(records[-1])['state'] == 'INCOMPLETE', 'incomplete not retained')
            CHECKS.append({'case': 'conversion-no-committed-or-native-bundle', 'result': 'PASS', 'layer': 'STATIC_VALUE_ONLY'})
    # Checker self-tests cover hidden Resource declarations and scope even after rehashing.
    directory = DATA/'cases/late-receipt'; package = load(directory/'package.json')
    bad = copy.deepcopy(package['bundle'])
    post = next(a for a in bad['artifacts'] if a['artifact_id'] == 'static-new-post')
    post['input_refs'] = []
    post['content_hash'] = digest({k:v for k,v in post.items() if k != 'content_hash'})
    negative('undeclared-recursive-report-refs', bad, lambda b: artifacts(b, directory))
    bad = copy.deepcopy(package['bundle'])
    post = next(a for a in bad['artifacts'] if a['artifact_id'] == 'static-new-post')
    post['scope_id'] = 'foreign-scope'
    post['content_hash'] = digest({k:v for k,v in post.items() if k != 'content_hash'})
    negative('foreign-ordinary-scope-after-reseal', bad, lambda b: artifacts(b, directory))
    result = {'status': 'STATIC_CHECKED_PROPOSAL_ONLY', 'checks': CHECKS,
        'profile_sha256': sha((DATA/'profile.json').read_bytes()),
        'checker_sha256': sha(Path(__file__).read_bytes()),
        'unproven': ['exchange-2 Schema/API approval/adoption', 'global native journal qualification of report packages',
            'native complete-book scan/CAS and read-only facts', 'cross-scope positive consumer-frame fixture',
            'current-runtime multihead reachability', 'fresh synthetic PRE production/admission', 'hold positive/second drift',
            'conversion committed bundle and interruption execution', 'failure-retention process harness execution'],
        'product_runs': 0, 'database_queries': 0, 'network_or_model_calls': 0,
        'field_reset_probe': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    (EVIDENCE/'static-check-result.json').write_bytes(json.dumps(result, ensure_ascii=False, indent=2).encode('utf8')+b'\n')
    print(json.dumps({'status': result['status'], 'checks': len(CHECKS), 'positive_checks': sum(x['result']=='PASS' for x in CHECKS),
        'expected_rejections': sum(x['result']=='EXPECTED_REJECTION' for x in CHECKS), 'product_runs': 0}))


if __name__ == '__main__':
    main()
