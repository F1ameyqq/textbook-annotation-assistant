"""Bounded static neighbors with a separately written event/hash oracle.

Only serialized design values are inspected. Author prefix_rules is called as
the subject under test after the independent expectations have been computed.
No recovery/runtime/database/business modules are imported or executed.
"""
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

STAGE = Path(sys.argv[1]).resolve()
OUT = Path(__file__).resolve().parent
PKG = STAGE/'examples/a03/P1-R2'
DATA = PKG/'data'
ZERO = '0'*64


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def encoded(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(o):
    return hashlib.sha256(encoded(o)).hexdigest()


def rechain(prefix):
    last = ZERO
    for seq, event in enumerate(prefix['events'], 1):
        event['sequence'], event['previous_hash'] = seq, last
        event['event_hash'] = digest({k:v for k,v in event.items() if k != 'event_hash'})
        last = event['event_hash']
    prefix['through_sequence'], prefix['head_hash'] = len(prefix['events']), last
    return prefix


def independent_oracle(prefix, plan):
    # A narrow, independent grammar oracle for the omissions in this review.
    # It neither reads expected labels nor uses the implementation's state code.
    errors = []
    events = prefix['events']
    names = [e['event'] for e in events]
    if not names or names[0] != 'PLAN_ACCEPTED' or names.count('PLAN_ACCEPTED') != 1:
        errors.append('MISSING_ACCEPTANCE')
    prior = ZERO
    for seq, event in enumerate(events, 1):
        if event['sequence'] != seq or event['previous_hash'] != prior or event['event_hash'] != digest({k:v for k,v in event.items() if k != 'event_hash'}):
            errors.append('HASH_OR_SEQUENCE_BROKEN')
        prior = event['event_hash']
    if prefix['through_sequence'] != len(events) or prefix['head_hash'] != prior:
        errors.append('HASH_OR_SEQUENCE_BROKEN')
    per_action = {}
    for event in events:
        action = event['payload'].get('action_id')
        if action:
            per_action.setdefault(action, []).append(event['event'])
    required = ['WRITE_INTENT_COMMITTED', 'DISPATCH_PERMIT_ISSUED', 'DISPATCH_PERMIT_CONSUMED', 'DISPATCH_STARTED', 'ACTION_RESULT_COMMITTED']
    for action, action_events in per_action.items():
        if 'ACTION_RESULT_COMMITTED' in action_events and action_events != required:
            if 'DISPATCH_STARTED' not in action_events:
                errors.append('DISPATCH_REQUIRED')
            elif 'DISPATCH_PERMIT_CONSUMED' not in action_events:
                errors.append('PERMIT_CONSUMPTION_REQUIRED')
            else:
                errors.append('ACTION_ORDER_INVALID')
    # The subject C's proof is after B interruption, without C events.
    if events and not any(e['event']=='ACTION_RESULT_COMMITTED' and e['payload'].get('outcome')=='UNKNOWN' for e in events):
        errors.append('INTERRUPTION_REQUIRED')
    return sorted(set(errors))


case = load(DATA/'cases/unattempted-absence-commit.json')
plan = next(a for a in case['bundle']['artifacts'] if a['kind']=='ApplyPlan')
progress = next(a for a in case['bundle']['artifacts'] if a['kind']=='ExecutionProgress')
fact = load(DATA/progress['payload']['actions'][-1]['result_fact']['path'])
basis = load(DATA/fact['unattempted_basis']['path'])
positive = load(DATA/basis['complete_uncalled_prefix']['path'])
inputs = {'positive': positive}
for name in ['prefix-missing-acceptance', 'prefix-missing-dispatch', 'prefix-broken-hash']:
    neighbor = load(DATA/f'cases/{name}.json')
    inputs['author-'+name] = load(DATA/neighbor['runtime_claim']['candidate_uncalled_prefix']['path'])
v = copy.deepcopy(positive)
v['complete'] = False
inputs['independent-valid-complete-false'] = v
v = copy.deepcopy(positive)
v['events'] = [e for e in v['events'] if e['event'] != 'PLAN_ACCEPTED']
v['complete'] = True
inputs['independent-missing-acceptance-rehash-complete-true'] = rechain(v)
b_action = positive['events'][-1]['payload']['action_id']
for event_name, tag in [('DISPATCH_STARTED','dispatch'), ('DISPATCH_PERMIT_CONSUMED','permit-consumption')]:
    v = copy.deepcopy(positive)
    v['events'] = [e for e in v['events'] if not (e['event'] == event_name and e['payload'].get('action_id') == b_action)]
    v['complete'] = True
    inputs['independent-missing-B-'+tag+'-rehash-complete-true'] = rechain(v)
v = copy.deepcopy(positive)
v['events'][5]['previous_hash'] = 'f'*64
v['complete'] = True
inputs['independent-broken-hash-complete-true'] = v

# Freeze independent expectations before invoking the author module.
expected = {name: independent_oracle(value, plan) for name, value in inputs.items()}
spec = importlib.util.spec_from_file_location('subject_prefix_rules', PKG/'prefix_rules.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
results = []
(OUT/'neighbors').mkdir(exist_ok=True)
for name, value in inputs.items():
    path = OUT/'neighbors'/f'{name}.json'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    actual = subject.validate_prefix(value, plan, {'sequence':value['through_sequence'], 'hash':value['head_hash']}, basis['action_id'])
    results.append({'name':name, 'independent_findings':expected[name], 'expected_accept':not expected[name],
                    'subject_errors':actual, 'actual_accept':not actual,
                    'acceptance_matches':bool(actual)==bool(expected[name]),
                    'input_path':str(path.relative_to(OUT)), 'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'complete':value.get('complete'), 'through_sequence':value['through_sequence']})
(OUT/'neighbors/plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
result = {'scope':'Static prefix-only layer; no committed fact/intent authority or actual refusal tested.',
          'oracle':'Separately implemented canonical hashing and minimal per-action event grammar; author expected labels never read.',
          'subject_module':str(PKG/'prefix_rules.py'), 'results':results,
          'all_acceptance_matches':all(r['acceptance_matches'] for r in results),
          'runtime_actual':'NOT_EXECUTED', 'limitations':['Deletion/rechain prefixes are pre-admission candidates, not committed graphs. Old body references remain context; this check proves prefix-layer refusal, not valid commit reconstruction.', 'No full JSON Schema standards validation.']}
(OUT/'neighbors-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['all_acceptance_matches'] else 1)
