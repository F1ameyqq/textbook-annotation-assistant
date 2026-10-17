"""Complete only unrun R3 controls after two preserved reviewer-driver errors."""
import collections
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout'
EX=ROOT/'examples/a03/P2-R3-evidence-closure';EV=ROOT/'docs/evidence/A03/execution/P2-R3-evidence-closure'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
os.environ['A03_R3_RUN_ID']='review-static'
old_mkdir=Path.mkdir
def redirect(path,*args,**kwargs):
    assert path==EV/'r2-regression/review-static',path
    return old_mkdir(OUT/'import-initialization-output',*args,**kwargs)
spec=importlib.util.spec_from_file_location('closure',EX/'closure.py');c=importlib.util.module_from_spec(spec);sys.modules['closure']=c
with patch.object(Path,'mkdir',redirect):spec.loader.exec_module(c)
c.base.EVID=OUT/'r2-regression'
assert c.base.Package is c.Package and not(c.base.EVID/'static-results.json').exists()
original=load(OUT/'original-counterexample.json');assert original['actual']=='UNDECLARED_REFERENCE'
author=load(EV/'controls/controls-01/results.json')['controls']
rows=[{'id':original['id'],'actual':'UNDECLARED_REFERENCE','expected':'UNDECLARED_REFERENCE','new_receipt_path_confirmed':True}]
saved={}
for item in author:
    if 'expected'not in item:continue
    row=load(OUT/'controls'/(item['id']+'.json'));assert row['actual']==item['expected'];saved[item['id']]=row
    rows.append({'id':item['id'],'actual':row['actual'],'expected':item['expected'],
      'record_basis':'static-01 asserted control flow recovered after write error'if row.get('validation_rerun')is False else'static-02 persisted result'})
assert len(rows)==10 and sum(x['actual']=='STATIC_ACCEPTED'for x in rows)==3
frame=saved['typed-frame-formal-evidence-uses-frame-scope']
assert any(x['kind']=='TYPED_FRAME'and x['scope_id']=='original-b'and x['evidence_id']=='proof-frame'for x in frame['ordinary_evidence_refs'])
shared=saved['shared-resource-each-consumer-context']
assert {x['consumer']for x in shared['ordinary_evidence_refs']if x['evidence_id']=='proof-json'}=={'r3-json-consumer','r3-shared-resource-other-scope'}
completion=load(OUT/'runs/static-02/completion.json');assert completion['exit_code']==1 and not completion['alive_after_wait']
assert "assert any('/F:'in a and 'E:proof-frame'in bs"in(OUT/'runs/static-02/stderr.log').read_text(encoding='utf8')
write(OUT/'reviewer-driver-second-recovery.json',{'cause':'extra reviewer graph assertion incorrectly required frame -> EvidenceRecord to be a direct edge; embedded Artifact evidence has an intervening Resource',
 'product_defect':False,'source_snapshot':'scripts/review_static.attempt-02.py','failure':'runs/static-02/stderr.log',
 'completed_whole_entry_calls':8,'all_10_direct_controls_completed':True,'completed_controls_rerun':False,
 'remaining':'three bounded differential controls, schema pointer audit and one R2 matrix',
 'graph_evidence':'frozen source traversal + actual formal trace; new receipt-first direct control also records actual full mixed graph'})

def read_case(name):
    desc=load(EX/'cases/controls-01'/name/'case.json');raw=(ROOT/desc['bundle']).read_bytes();assert sha(raw)==desc['bundle_sha256']
    ov={}
    for r in desc['resources']:
        value=(ROOT/r['file']).read_bytes();assert sha(value)==r['sha256'];ov[r['logical']]=value
    return json.loads(raw),ov
def check(name,b,ov,want):
    directory=OUT/'independent-controls'/name;write(directory/'bundle.json',b)
    resources=[]
    for i,(logical,raw)in enumerate(sorted(ov.items())):
        path=directory/'resources'/('%02d.json'%i);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb')as f:f.write(raw)
        resources.append({'logical':logical,'file':path.relative_to(OUT).as_posix(),'sha256':sha(raw)})
    assert all(c.h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in b['artifacts'])
    p=c.Package(b,ov)
    try:p.validate();actual='STATIC_ACCEPTED';error=None
    except c.Rejected as e:actual=e.code;error={'code':e.code,'path':e.path}
    assert actual==want,(name,actual,error,want)
    result={'id':name,'actual':actual,'expected':want,'error':error,'all_artifact_hashes_correct':True,
     'entry':'closure.Package.validate','bundle_sha256':sha((directory/'bundle.json').read_bytes()),
     'resource_overrides':resources,'evidence_refs':p.evidence_refs,'consumer_failures':p.consumer_failures(),
     'mixed_graph_edges':{k:sorted(v)for k,v in sorted(p.edges.items())}}
    write(directory/'result.json',result);print(json.dumps({'id':name,'actual':actual,'error':error}))
    return p,result

bundle=load(EV/'inputs/counterexample/bundle.json');description=load(EV/'inputs/counterexample/result.json')
ov={x['logical']:(EV/'inputs/counterexample'/Path(x['file']).name).read_bytes()for x in description['resource_overrides']}
receipt=next(a for a in bundle['artifacts']if a['kind']=='ExecutionReceipt'and a['schema_version']==c.base.VERSION)
ordered=copy.deepcopy(bundle);ordered['artifacts'].sort(key=lambda a:a['artifact_id']!=receipt['artifact_id'])
p,r=check('receipt-first-same-original-values',ordered,ov,'UNDECLARED_REFERENCE')
assert r['error']['path']==receipt['artifact_id']
receipt_node='A:'+c.h(c.ref(receipt));assert 'E:proof'in p.edges[receipt_node]
outer=next(x for x in bundle['evidence']if x['evidence_id']=='proof')['resource']
outer_node='R:'+outer['path']+':'+outer['sha256'];assert outer_node in p.edges['E:proof']
inner=json.loads(ov[outer['path']])['nested']
inner_node='R:'+inner['path']+':'+inner['sha256'];assert inner_node in p.edges[outer_node]
leaf_node='A:'+c.h(description['referenced_artifact']);assert leaf_node in p.edges[inner_node]
direct=[r['id']]
b,ov=read_case('shared-resource-each-consumer-context');second=b['artifacts'][-1]
second['scope_id']=b['artifacts'][0]['scope_id'];second['input_refs']=[];second['content_hash']=c.h({k:v for k,v in second.items()if k!='content_hash'})
p,r=check('same-scope-second-consumer-needs-own-declaration',b,ov,'UNDECLARED_REFERENCE')
assert r['error']['path']==second['artifact_id'];direct.append(r['id'])
b,ov=read_case('legal-json-evidence-declared-same-scope');consumer=b['artifacts'][0]
consumer['payload']['external_page_mappings'][0]['evidence_refs']=['review-missing-formal-id']
consumer['content_hash']=c.h({k:v for k,v in consumer.items()if k!='content_hash'})
p,r=check('schema-formal-id-replaced-by-missing-id',b,ov,'EVIDENCE_ID_MISSING')
assert '/external_page_mappings/0/evidence_refs[review-missing-formal-id]'in r['error']['path'];direct.append(r['id'])

registry=load(EV/'controls/controls-01/formal-field-registry.json')['fields']
assert len(registry)==17 and len({(x['schema'],x['schema_pointer'])for x in registry})==17
for field in registry:
    node=load(ROOT/field['schema'])
    for token in field['schema_pointer'][2:].split('/'):
        token=token.replace('~1','/').replace('~0','~');node=node[int(token)]if isinstance(node,list)else node[token]
    assert node['type']=='array'and node['items']['type']=='string'and node['items']['pattern']==field['id_pattern']
assert {(x['schema'],x['schema_pointer'])for x in registry}=={(x['schema'],x['schema_pointer'])for x in c.FIELDS.values()}
write(OUT/'formal-field-verification.json',{'fields':registry,'source':'raw frozen schema pointers',
 'all_17_verified':True,'ordinary_opaque_field_control':'STATIC_ACCEPTED','Resource_valued_evidence':'not misclassified as ID arrays'})

inputs=c.base.EVID/'inputs';inputs.mkdir(exist_ok=False)
for name in ['readonly-session-does-not-match-gate-binding.json','initial-head-not-in-canonical-prefix.json','amended-source-kind-coverage.json']:
    raw=c.pinned(ROOT/'docs/evidence/A03/execution/P2-R2-proposal/inputs'/name)
    with(inputs/name).open('xb')as f:f.write(raw)
before=c.Package.entry_calls;c.base.RESULTS.clear();c.base.main()
records=load(c.base.EVID/'static-results.json')['records'];counts=dict(collections.Counter(x['result']for x in records))
assert len(records)==36 and counts=={'STATIC_ACCEPTED':7,'EXPECTED_STATIC_REJECTION':23,'STATIC_MATCH':1,'EXPECTED_STATIC_MISMATCH':5}
assert c.Package.entry_calls-before==15
assert not any(x=='annotation'or x.startswith('annotation.')for x in sys.modules)
write(OUT/'independent-static-results.json',{'conclusion':'ACCEPTED_STATIC_LIMITED','scope':'EvidenceRecord consumer closure only',
 'entry':'closure.Package.validate','loaded_sources':c.loaded_sources(),'direct_controls':rows,
 'independent_differential_controls':direct,'R2_matrix_once':{'records':36,'classification':counts,'whole_package_calls':15},
 'current_process_package_calls':c.Package.entry_calls,'previous_completed_calls':10,'total_whole_package_calls':c.Package.entry_calls+10,
 'all_native_functions':'NOT_EXECUTED','oracle_adopted':False,'I01_released':False,
 'SESSION-02':'STATIC_ACCEPTED_LIMITED_PRESERVED','CONVERSION-07':'STATIC_ACCEPTED_LIMITED_PRESERVED',
 'R17_version_bridge':'BLOCKED','registration_derived_scope_positive':'BLOCKED_NOT_POSITIVELY_VERIFIED',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION','reviewer_driver_failures_preserved':2})
write(OUT/'process-release.json',{'pid':os.getpid(),'started_children':0,'background_workers':0,'native_sessions':0,
 'previous_pids':[58784,53440],'previous_status':'exited1; see parent wait records',
 'synchronous_runner':'runs/static-03/completion.json records parent wait and exit','product_DB_network_model_calls':0})
print(json.dumps({'result':'BOUNDED_STATIC_REVIEW_COMPLETE','conclusion':'ACCEPTED_STATIC_LIMITED','closure_controls':10,
 'additional_direct_controls':3,'R2_records_once':36,'R2_classification':counts,'whole_package_calls_total':c.Package.entry_calls+10}))
