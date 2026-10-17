"""Inspect only the four already-run frozen values. No checker/product imports."""
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout';EX=ROOT/'examples/a03/P2-R4-bridge-registration'
def sha(v):return hashlib.sha256(v).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def h(v):return sha(canon(v))
def ref(a):return {k:a[k]for k in['artifact_id','revision','kind','content_hash']}
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
rows=[]
for name in ['registration-positive','source-binding-negative','snapshot-binding-negative','target-tuple-negative']:
    case=load(EX/'cases'/name/'case.json');bundle=load(ROOT/case['bundle']);index={h(ref(a)):a for a in bundle['artifacts']}
    resources={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
    prefix=json.loads(resources[case['prefix_resource']['path']]);frame_rows=[]
    def ordinary(v,seen=None):
        seen=set()if seen is None else seen;found={}
        if isinstance(v,dict):
            if set(v)=={'artifact_id','revision','kind','content_hash'}:
                assert h(v)in index;return {h(v):v}
            if {'path','sha256','media_type'}<=set(v):
                raw=resources[v['path']];assert sha(raw)==v['sha256'];key=(v['path'],v['sha256'])
                if key not in seen and v['media_type']=='application/json':
                    seen.add(key);found.update(ordinary(json.loads(raw),seen))
                return found
            for x in v.values():found.update(ordinary(x,seen))
        elif isinstance(v,list):
            for x in v:found.update(ordinary(x,seen))
        return found
    for i,frame in enumerate(prefix['frames']):
        event=frame['event'];found=ordinary(event);declared={h(r):r for r in frame['input_refs']}
        assert set(found)<=set(declared)
        wrong=[r for r in declared.values()if index[h(r)]['book_id']!=prefix['target_key']['book_id']or index[h(r)]['scope_id']!=frame['consumer_scope_id']]
        frame_rows.append({'index':i,'event':event['event'],'scope':frame['consumer_scope_id'],
             'all_own_refs_declared':True,'ordinary_refs':list(found.values()),'wrong_scope_or_book':wrong})
    owner=next(a for a in bundle['artifacts']if a['artifact_id']=='r4-registration-prefix-consumer')
    assert owner['input_refs']==[prefix['subject_plan_ref']]
    owner_evidence=[eid for p in owner['payload']['external_page_mappings']for eid in p['evidence_refs']]
    assert set(owner_evidence)=={'proof-r4-registration'}
    record=next(r for r in bundle['evidence']if r['evidence_id']=='proof-r4-registration')
    assert record['resource']==case['prefix_resource']and record['resource']['media_type']=='application/json'
    payload=prefix['frames'][-1]['event']['payload'];snap=index[h(payload['snapshot_ref'])]
    obs=json.loads(resources[payload['observation']['path']]);target_match=snap['payload']['target_id']==prefix['target_key']['target_id']
    assert all(not x['wrong_scope_or_book']for x in frame_rows[:-1])
    if name in ['registration-positive','target-tuple-negative']:assert not frame_rows[-1]['wrong_scope_or_book']
    else:assert frame_rows[-1]['wrong_scope_or_book']
    if name=='registration-positive':
        assert target_match and snap['payload']['observed_hash']==payload['target_state_hash']==obs['target_state_hash']==h(obs['business_value'])
        assert snap['payload']['observed_version']==payload['target_state_version']==obs['target_state_version']
        assert snap['payload']['authorized_scope_id']==snap['scope_id']==payload['scope_id']
    if name=='target-tuple-negative':assert not target_match
    rows.append({'case':name,'prefix_is_full_synthetic_journal_not_native_history':True,'owner_scope':owner['scope_id'],
      'formal_evidence_path':'payload.external_page_mappings[].evidence_refs -> EvidenceRecord(proof-r4-registration).resource',
      'outer_subject_plan_declared_exactly':True,'frame_context_audit':frame_rows,'snapshot_target_matches_canonical_target':target_match,
      'no_new_Package_calls':True})
# The pinned field definitions admit JSON Resources and do not impose a
# placement prohibition on this formally referenced EvidenceRecord resource.
schema=load(ROOT/'examples/a03/P2-R2-proposal/candidate-final/schemas/exchange-v3.schema.json')
mapping=schema['$defs']['PageMapping']['properties']['evidence_refs'];record_schema=schema['$defs']['EvidenceRecord']
assert mapping['type']=='array'and mapping['items']['type']=='string'
write(OUT/'frozen-value-audit.json',{'method':'data/hash/ref inspection only, after the four actual runs; not an alternative successful Package entry',
 'cases':rows,'formal_PageMapping_evidence_field':mapping,'EvidenceRecord_resource_schema':record_schema['properties']['resource'],
 'positive_assessment':'No hash/ref/frame-declaration/scope/target inconsistency in the specified static boundary; full entry still fails before its remaining DAG/consumer/final-hash stages',
 'native_semantics':'not qualified; independent journal and observation are explicitly synthetic',
 'Package_calls':0,'product_calls':0})
print(json.dumps({'result':'FOUR_FROZEN_VALUE_AUDITS_COMPLETE','Package_calls':0,'positive_formal_placement_and_tuples_valid':True,'target_control_mismatch_confirmed_but_rejection_masked':True}))
