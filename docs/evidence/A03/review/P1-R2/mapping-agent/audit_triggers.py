"""Independent bounded preservation checks of the 15 derived R1 cases."""
import hashlib
import json
import sys
from pathlib import Path

STAGE = Path(sys.argv[1]).resolve()
OUT = Path(__file__).resolve().parent
OLD = STAGE/'examples/a03/P1-R1/data'
NEW = STAGE/'examples/a03/P1-R2/data'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def get(base, resource):
    return load(base/resource['path'])


def artifact(case, kind):
    return next(a for a in case['bundle']['artifacts'] if a['kind']==kind)


def receipt_projection(case):
    p = artifact(case,'ExecutionReceipt')['payload']
    keys = ['action_id','outcome','attempt_fact','effect_match','replay_allowed','next_step','platform_ids']
    return {'write_disposition':p['write_disposition'], 'results':[{k:r.get(k) for k in keys} | {'has_intent':r.get('intent_ref') is not None} for r in p['results']]}


def progress_projection(case):
    ps = [a for a in case['bundle']['artifacts'] if a['kind']=='ExecutionProgress']
    return [[{k:r.get(k) for k in ['action_id','effective_outcome','attempt_fact','dependency_status']} |
             {'has_intent':r.get('intent_ref') is not None, 'has_resolution':r.get('resolution_head_ref') is not None} for r in a['payload']['actions']] for a in ps]


def basis(case, base):
    receipt = artifact(case,'ExecutionReceipt')
    fact = get(base,receipt['payload']['action_fact_refs'][-1])
    return get(base,fact['unattempted_basis'])


def primary(case, base, name):
    claim = case.get('runtime_claim', {})
    p = artifact(case,'ApplyPlan')
    actions = {a['action_id'] for a in p['payload']['actions']}
    r = artifact(case,'ExecutionReceipt')['payload']['results']
    if name in ['partial-with-complete-absent','unattempted-absence-commit']:
        return {'A_APPLIED_B_UNKNOWN_C_NOT_APPLIED': [x['outcome'] for x in r]==['APPLIED','UNKNOWN','NOT_APPLIED'],
                'C_not_attempted_without_intent': r[-1]['attempt_fact']=='NOT_ATTEMPTED' and r[-1]['intent_ref'] is None,
                'B_still_pending': bool(case['ledger_export']['unresolved']) and case['ledger_export']['pause']['paused']}
    if name in ['original-unknown-preserved','recovered-report-binding']:
        resolution = artifact(case,'ReconciliationResult')['payload']
        return {'original_A_UNKNOWN':r[0]['outcome']=='UNKNOWN', 'resolution_is_A_APPLIED':resolution['action_id']==r[0]['action_id'] and resolution['resolution']=='RESOLVED_APPLIED',
                'original_receipt_bound':resolution['original_receipt_ref']['content_hash']==artifact(case,'ExecutionReceipt')['content_hash'],
                'uncalled_B_C_unchanged':all(x['attempt_fact']=='NOT_ATTEMPTED' and x['intent_ref'] is None for x in r[1:])}
    req = claim['request']
    if name=='unattempted-missing-absent':
        obs = get(base,claim['candidate_second_observation'])
        return {'second_observation_incomplete':obs['scope_complete'] is False}
    if name=='unattempted-stale-observation':
        b = basis(case,base)
        return {'second_reuses_first_bytes':get(base,claim['candidate_second_observation'])==get(base,b['first_observation_ref'])}
    if name=='unattempted-incomplete-prefix':
        prefix=get(base,claim['candidate_uncalled_prefix'])
        return {'missing_acceptance_in_supplied_candidate':not any(e['event']=='PLAN_ACCEPTED' for e in prefix['events'])}
    if name=='unattempted-wrong-plan-action':
        return {'requested_action_absent_from_actual_plan':req['action_id'] not in actions}
    if name=='unattempted-stale-generation':
        return {'supplied_generation_differs_from_current':claim['supplied_generation']!=claim['current_generation']}
    if name=='unattempted-duplicate-fact':
        b=claim['current_library_existing_fact_binding']
        return {'same_key_binding':all(b[k]==req[k] for k in ['action_id','plan_ref','action_digest']),
                'same_existing_committed_fact':b['committed_fact']==artifact(case,'ExecutionReceipt')['payload']['action_fact_refs'][-1]}
    if name=='unattempted-conflicting-fact':
        b=claim['current_library_existing_fact_binding']
        return {'same_action_changed_digest':b['action_id']==req['action_id'] and b['action_digest']!=req['action_digest']}
    if name=='unattempted-wrong-plan-state':
        return {'current_plan_state_not_INTERRUPTED':claim['current_plan_status']!='INTERRUPTED'}
    if name=='unattempted-already-called':
        return {'current_dispatch_count_positive':claim['current_action_dispatch_count']>0}
    if name=='unattempted-event-head-stale':
        return {'CAS_differs_from_current_head':req['expected_event_head']!=claim['current_event_head']}
    if name=='unattempted-prepared-mismatch':
        return {'actual_prepared_action_differs':get(base,claim['candidate_readonly_prepared'])['action_id']!=req['action_id']}
    raise ValueError(name)


mapping = load(NEW/'r1-case-mapping.json')['mappings']
derived = []
for row in mapping:
    if row['bytes_unchanged']:
        continue
    old,new = load(OLD/row['r1_path']),load(NEW/row['r2_path'])
    name=row['r1_case_id']
    old_primary,new_primary=primary(old,OLD,name),primary(new,NEW,name)
    old_ledger,new_ledger=old['ledger_export'],new['ledger_export']
    ledger_projection = lambda x: {'pending_action_ids':x['pending_action_ids'], 'pause':x['pause'],
        'unresolved': [{k:r[k] for k in ['event_id','scope_id','classification']} for r in x['unresolved']]}
    checks={'same_actual_plan':artifact(old,'ApplyPlan')==artifact(new,'ApplyPlan'),
            'same_receipt_effect_attempt_projection':receipt_projection(old)==receipt_projection(new),
            'same_progress_projection':progress_projection(old)==progress_projection(new),
            'same_pause_pending_projection':ledger_projection(old_ledger)==ledger_projection(new_ledger),
            'same_primary_trigger_values':old_primary==new_primary,
            'primary_trigger_present_in_both':all(old_primary.values()) and all(new_primary.values())}
    derived.append({'case_id':name,'checks':checks,'old_primary':old_primary,'new_primary':new_primary,'all_checks':all(checks.values())})

# Case bytes alone would miss resource replacements; compare every reachable
# safe same-path Resource for the 54 unmodified cases. Deliberate invalid paths
# and absent resources remain untouched and are recorded without reading out.
resources,skipped={},{}
def walk(value, base, active):
    if isinstance(value, dict) and {'path','sha256','media_type'} <= set(value):
        rel=value['path']
        target=(base/rel).resolve()
        if '\\' in rel or ':' in rel or base not in target.parents:
            skipped[rel]='UNSAFE_PATH_NOT_READ'
            return
        if not target.is_file():
            skipped[rel]='ABSENT_IN_FROZEN_INPUT'
            return
        data=target.read_bytes()
        resources.setdefault(rel,{})[str(base)]=hashlib.sha256(data).hexdigest()
        if rel in active:
            return
        if value['media_type']=='application/json':
            walk(json.loads(data.decode('utf-8')),base,active|{rel})
    elif isinstance(value,dict):
        for child in value.values():walk(child,base,active)
    elif isinstance(value,list):
        for child in value:walk(child,base,active)
for row in mapping:
    if row['bytes_unchanged']:
        walk(load(OLD/row['r1_path']),OLD,set())
        walk(load(NEW/row['r2_path']),NEW,set())
resource_rows=[{'path':p,'r1_sha256':d.get(str(OLD)),'r2_sha256':d.get(str(NEW)),
                'bytes_equal':d.get(str(OLD))==d.get(str(NEW))} for p,d in sorted(resources.items())]
result={'method':'Actual R1/R2 semantic projections and explicit independently specified primary predicates; author expected labels ignored.',
        'derived_cases':derived,'all_15_primary_checks_pass':len(derived)==15 and all(r['all_checks'] for r in derived),
        'unchanged_case_resource_checks':resource_rows,'unchanged_case_resources_equal':all(r['bytes_equal'] for r in resource_rows),
        'unreadable_intentional_resources':skipped,
        'limitations':['Claims named current_library/current_owner are serialized static candidates, never verified current runtime state.',
                       '54 unchanged cases retain exact candidate inputs and safe reachable bytes; earlier acceptance/rejection meaning is not newly functionally executed.']}
(OUT/'trigger-resource-results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'all_15_primary_checks_pass':result['all_15_primary_checks_pass'],
                  'case_primary_checks':[{ 'case_id':r['case_id'],'checks':r['checks'],'primary':r['new_primary']} for r in derived],
                  'unchanged_case_resource_count':len(resource_rows),'unchanged_case_resources_equal':result['unchanged_case_resources_equal'],
                  'intentionally_unread_count':len(skipped)},indent=2))
raise SystemExit(0 if result['all_15_primary_checks_pass'] and result['unchanged_case_resources_equal'] else 1)
