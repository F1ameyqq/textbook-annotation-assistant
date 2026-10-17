# -*- coding: utf-8 -*-
"""Inspect saved results and frozen JSON only; no checker or product imports."""
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';EX=ROOT/'examples/a03/P2-R5-registration-context';DATA=ROOT/'examples/a03/P2-R2-proposal/candidate-final'
def load(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def h(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def ref(a):return {k:a[k]for k in ['artifact_id','revision','kind','content_hash']}
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
indexes=load(EX/'case-index.json')['cases'][:6]+load(EX/'repair-case-index.json')['cases']
tags=['case-01','case-02','case-03','case-04','case-05','case-06','case-07-repair-01']
audits=[];summaries=[]
for tag,row in zip(tags,indexes):
    result=load(OUT/'runs'/tag/'stdout.log');assert result['id']==row['id']and result['actual']==row['expected']and result['matched']
    assert load(OUT/'call-counts'/(tag+'.json'))['observed_R3_entry_call_counter']==1
    case=load(ROOT/row['case']);raw=(ROOT/case['bundle']).read_bytes();assert sha(raw)==case['bundle_sha256']==result['bundle_sha256']
    b=json.loads(raw);artifacts={h(ref(a)):a for a in b['artifacts']};assert len(artifacts)==len(b['artifacts'])
    assert all(h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in b['artifacts'])
    overrides={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
    assert all(sha(overrides[r['logical']])==r['raw_sha256']for r in case['resources'])
    resources={};bad=[];refs={};prefixes=[]
    def walk(v,path='$'):
        if isinstance(v,dict):
            if set(v)=={'artifact_id','revision','kind','content_hash'}:
                assert h(v)in artifacts and ref(artifacts[h(v)])==v,(tag,path);refs[h(v)]=v;return
            if {'path','sha256','media_type'}<=set(v):
                logical=v['path'];token=(logical,v['sha256'])
                if token in resources:return
                body=overrides[logical]if logical in overrides else(DATA/logical).read_bytes()
                resources[token]={'path':logical,'declared_sha256':v['sha256'],'actual_sha256':sha(body),'bytes':len(body)}
                if sha(body)!=v['sha256']:bad.append(resources[token]);return
                if v['media_type']=='application/json':walk(json.loads(body),logical)
                return
            if v.get('format_version')=='a03-runtime-event-prefix-2':
                prev=v['predecessor']['hash'];assert v['predecessor']['sequence']==0 and v['from_sequence']==1
                heads=[]
                for number,frame in enumerate(v['frames'],1):
                    e=frame['event'];assert e['sequence']==number and e['previous_hash']==prev
                    assert h({k:x for k,x in e.items()if k!='event_hash'})==e['event_hash']
                    if e['event']=='READONLY_ABSENCE_STARTED':
                        heads.append({'event':e['event'],'sequence':number,'declared':e['payload']['initial_event_head'],
                            'actual_previous':{'sequence':number-1,'hash':prev},'matches':e['payload']['initial_event_head']=={'sequence':number-1,'hash':prev}})
                    prev=e['event_hash']
                assert v['expected_book_head']=={'sequence':len(v['frames']),'hash':prev}
                anchor=v['accepted_anchor'];assert v['frames'][anchor['sequence']-1]['event']['event_hash']==anchor['hash']
                prefixes.append({'resource':path,'event_count':len(v['frames']),'event_hash_chain_correct':True,'internal_initial_heads':heads})
            for key,x in v.items():walk(x,path+'/'+key)
        elif isinstance(v,list):
            for i,x in enumerate(v):walk(x,path+'/'+str(i))
    walk(b)
    if tag=='case-06':assert len(bad)==1 and bad[0]['path']=='r5-static/global-only-proof.txt'
    else:assert not bad,(tag,bad)
    if tag in tags[:4]:
        original=ROOT/'examples/a03/P2-R4-bridge-registration/cases'/row['id']/'bundle.json';assert raw==original.read_bytes()
    if tag=='case-05':assert sha(raw)=='b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653'
    audits.append({'tag':tag,'id':row['id'],'bundle_sha256':sha(raw),'artifact_count':len(b['artifacts']),
       'all_artifact_hashes_correct':True,'all_ordinary_refs_exact':True,'raw_resources':list(resources.values()),
       'intentional_resource_digest_mismatches':bad,'prefixes':prefixes})
    summaries.append({'tag':tag,'id':row['id'],'actual':result['actual'],'error':result['error'],'full_entry_returned':result['full_entry_returned'],
      'tail':result['inherited_tail_trace'],'none_book_real_consumers':result['none_book_real_consumers'],
      'scope':'ACCEPTED_STATIC_LIMITED'if tag!='case-07-repair-01'else'REWORK_CONTROL_INPUT_RESIDUAL'})

positive=load(OUT/'runs/case-01/stdout.log')
assert positive['full_entry_returned']and positive['inherited_tail_trace']==['MIXED_DAG','CONSUMER_DECLARATIONS_BOOK_SCOPE','ARTIFACT_HASH','FULL_R2_TAIL_RETURN']
assert positive['real_consumers']==16 and positive['none_book_real_consumers']==0 and len(positive['global_frames'])==6
assert [x['mode']for x in positive['prefix_visits']]==['REAL_CONSUMER','GLOBAL_GRAPH']
for tag in ['case-02','case-03']:
    r=load(OUT/'runs'/tag/'stdout.log');assert r['registration_checks']and not all(r['registration_checks'][0]['binding_checks'].values())
    assert all(x['mode']=='REAL_CONSUMER'for x in r['prefix_visits'])
target=load(OUT/'runs/case-04/stdout.log');check=target['registration_checks'][0]
assert all(check['binding_checks'].values())and check['target_checks']['snapshot_target_id']is False
assert target['error']['path'].endswith('/registration/target')and all(x['mode']=='REAL_CONSUMER'for x in target['prefix_visits'])
r3=load(OUT/'runs/case-05/stdout.log')
assert r3['error']['path']=='origin-a-SourceBundle'and any(x['schema_version']=='1.3.0-a03-static-proposal'and x['kind']=='ExecutionReceipt'and x['formal_path'].endswith('/results/0/before_evidence_refs')for x in r3['formal_evidence_refs'])
global_hash=load(OUT/'runs/case-06/stdout.log')
assert any(x['code']=='RESOURCE_HASH'and x['path']=='r5-static/global-only-proof.txt'and x['active_real_contexts']==0 for x in global_hash['resource_read_failures'])
mixed=load(OUT/'runs/case-07-repair-01/stdout.log');assert mixed['inherited_tail_trace']==['MIXED_DAG']and not mixed['full_entry_returned']
repair_audit=audits[-1];prefix=next(x for x in repair_audit['prefixes']if x['resource']=='r5-static/cycle-prefix.json')
mismatch=[x for x in prefix['internal_initial_heads']if not x['matches']];assert len(mismatch)==1
assert mismatch[0]['sequence']==8 and mismatch[0]['declared']=={'sequence':7,'hash':'87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84'}
assert mismatch[0]['actual_previous']=={'sequence':7,'hash':'28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9'}

# Static inspection of the invalid first control. Never run its Package.
first_row=load(EX/'case-index.json')['cases'][-1];first_case=load(ROOT/first_row['case'])
first_prefix_resource=next(x for x in first_case['resources']if 'prefix'in x['logical'])
first_prefix=load(ROOT/first_prefix_resource['file']);old_event=first_prefix['frames'][2]['event']
assert old_event['event']=='PLAN_ACCEPTED'and 'evidence'in old_event['payload']and 'event_version'not in old_event
schema=load(DATA/'schemas/prefix-v2.schema.json');closed_candidates=[]
def schema_walk(v,path='#'):
    if isinstance(v,dict):
        p=v.get('properties',{});event=p.get('event',{})
        if event.get('const')=='PLAN_ACCEPTED'or event.get('enum')==['PLAN_ACCEPTED']:
            payload=p.get('payload',{})
            if payload.get('additionalProperties')is False and 'evidence'not in payload.get('properties',{}):
                closed_candidates.append({'schema_pointer':path,'payload_properties':list(payload['properties']),'additionalProperties':False})
        for k,x in v.items():schema_walk(x,path+'/'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):schema_walk(x,path+'/'+str(i))
schema_walk(schema);assert closed_candidates
author_first=load(ROOT/'docs/evidence/A03/execution/P2-R5-registration-context/results/case-07.json')
assert author_first['actual']=='SHAPE_oneOf'and not author_first['inherited_tail_trace']
write(OUT/'invalid-first-control-static-audit.json',{'method':'input/schema/log inspection only; never executed',
 'case_sha256':sha((ROOT/first_row['case']).read_bytes()),'legacy_event':old_event,'closed_PLAN_ACCEPTED_candidates':closed_candidates,
 'frozen_author_result':{'actual':author_first['actual'],'error':author_first['error']},'new_Package_calls':0})
write(OUT/'frozen-values-audit.json',{'method':'saved JSON/hash/ref checks only; no checker import/call','cases':audits,'new_Package_calls':0})
write(OUT/'mixed-control-residual.json',{'conclusion':'REWORK_CONTROL_INPUT_PROOF','observed_rejection':'MIXED_CYCLE','mixed_DAG_stage_reached':True,
 'artifact_resource_event_hashes_correct':True,'internal_head_mismatches':mismatch,
 'implementation_defect_proved_by_this_control':False,'reason':'cycle is rejected before later semantic qualification; stale internal head prevents a single-fault clean control claim',
 'repair_rounds_author_used':1,'second_revision_or_new_candidates_or_retests_by_reviewer':0})
write(OUT/'independent-results.json',{'overall':'REWORK','registration_context_and_target':'ACCEPTED_STATIC_LIMITED',
 'formal_evidence_and_global_resource_hash':'ACCEPTED_STATIC_LIMITED','mixed_cycle_control':'REWORK_CONTROL_INPUT_PROOF',
 'seven_case_results':summaries,'qualified_scenarios':6,'codes_matching_expectation':7,'Package_calls':7,'invalid_first_case_reexecuted':False,
 'old_36_matrix_runs':0,'session_conversion_product_DB_native_oracle_model_runs':0,'I01_released':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
print(json.dumps({'result':'SEVEN_RESULTS_AND_FROZEN_VALUES_AUDITED','overall':'REWORK','qualified_scenarios':6,
 'matching_codes':7,'mixed_initial_head_mismatch':mismatch[0],'new_Package_calls':0}))
