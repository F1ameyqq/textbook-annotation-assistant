"""Bounded R3 static review. Exact frozen sources; no product/native imports."""
import collections
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT/'input/checkout'
EX=ROOT/'examples/a03/P2-R3-evidence-closure'
EV=ROOT/'docs/evidence/A03/execution/P2-R3-evidence-closure'
RESUME='--resume-after-output-error'in sys.argv
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

# The only import-time side effect is the author's output mkdir. Redirect that
# exact directory before loading, so every frozen input remains read-only.
os.environ['A03_R3_RUN_ID']='review-static'
original_mkdir=Path.mkdir;redirects=[]
def output_mkdir(path,*args,**kwargs):
    assert path==EV/'r2-regression/review-static',str(path)
    dest=OUT/'import-initialization-output';redirects.append({'requested':str(path),'actual':str(dest)})
    return original_mkdir(dest,*args,**kwargs)
with patch.object(Path,'mkdir',output_mkdir):
    c=module('closure',EX/'closure.py')
c.base.EVID=OUT/'r2-regression'
c.base.EVID.mkdir(parents=True,exist_ok=RESUME)
assert c.base.Package is c.Package
write(OUT/('initialization-redirection-resume.json'if RESUME else'initialization-redirection.json'),{'redirected_mkdir':redirects,'validation_source_modified':False})

def hashes(bundle,overrides):
    correct=[];stale=[];resources={}
    for a in bundle['artifacts']:
        (correct if c.h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']else stale).append(a['artifact_id'])
    def walk(v):
        if isinstance(v,dict):
            if c.base.isres(v):
                key=(v['path'],v['sha256'])
                if key in resources:return
                raw=overrides[v['path']]if v['path']in overrides else(c.base.DATA/v['path']).read_bytes()
                assert sha(raw)==v['sha256'];resources[key]={'path':v['path'],'sha256':sha(raw),'bytes':len(raw)}
                if v['media_type']=='application/json':walk(json.loads(raw))
            else:
                for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk(bundle)
    return {'correct_artifact_hashes':correct,'stale_artifact_hashes':stale,'raw_resources':list(resources.values())}

# The author's shortest exact replay is executed once, retaining its Package
# object after expected SystemExit, so receipt trace is read from the same run.
replay_spec=importlib.util.spec_from_file_location('_review_exact_replay',EX/'replay.py')
replay=importlib.util.module_from_spec(replay_spec)
old_argv=sys.argv[:];sys.argv=[str(EX/'replay.py'),'--case','original','--expect','UNDECLARED_REFERENCE']
if not RESUME:
    try:
        try:replay_spec.loader.exec_module(replay)
        except SystemExit as e:assert e.code==0,e.code
    finally:sys.argv=old_argv
    assert replay.actual=='UNDECLARED_REFERENCE'
    pkg=replay.pkg;bundle=replay.bundle;overrides=replay.overrides
    proof=hashes(bundle,overrides);assert len(proof['correct_artifact_hashes'])==16 and not proof['stale_artifact_hashes']
    assert sha(replay.raw)=='b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653'
    receipt=next(a for a in bundle['artifacts']if a['kind']=='ExecutionReceipt'and a['schema_version']==c.base.VERSION)
    required=receipt['artifact_id']+'/results/0/before_evidence_refs'
    trace=[v for v in pkg.evidence_refs if v['consumer']==receipt['artifact_id']and v['formal_path']==required]
    assert trace and all(v['reference_scope']=='original-b'and v['scope_id']=='original-a'for v in trace)
    failures=pkg.consumer_failures();assert any(v['consumer']==receipt['artifact_id']and v['missing_declarations']and v['wrong_scope']for v in failures)
    write(OUT/'original-counterexample.json',{'id':'R2-SCOPE-EVIDENCE-ID-01','actual':replay.actual,'error':replay.error,
     'bundle_raw_sha256':sha(replay.raw),'entry':'closure.Package.validate','hashes':proof,'new_receipt_trace':trace,
     'consumer_failures':failures,'all_evidence_uses':pkg.evidence_uses})
else:
    sys.argv=old_argv
    frozen=load(OUT/'original-counterexample.json');assert frozen['actual']=='UNDECLARED_REFERENCE'
    completion=load(OUT/'runs/static-01/completion.json');assert completion['exit_code']==1 and not completion['alive_after_wait']
    error_text=(OUT/'runs/static-01/stderr.log').read_text(encoding='utf8')
    assert "write(OUT/'controls'/name+'.json',result)"in error_text and 'WindowsPath'in error_text
    bundle=load(EV/'inputs/counterexample/bundle.json');description=load(EV/'inputs/counterexample/result.json')
    overrides={x['logical']:(EV/'inputs/counterexample'/Path(x['file']).name).read_bytes()for x in description['resource_overrides']}
    receipt=next(a for a in bundle['artifacts']if a['kind']=='ExecutionReceipt'and a['schema_version']==c.base.VERSION)
    write(OUT/'reviewer-driver-recovery.json',{'cause':'reviewer WindowsPath + str output path TypeError, after original and first duplicate-ID control assertions passed',
     'first_source':'scripts/review_static.attempt-01.py','first_failure':'runs/static-01/stderr.log',
     'completed_whole_entry_calls':2,'skipped_completed_controls':['R2-SCOPE-EVIDENCE-ID-01','formal-evidence-id-duplicate'],
     'R2_matrix_before_failure':'NOT_RUN','product_defect':False,'completed_controls_rerun':False})
rows=[{'id':'R2-SCOPE-EVIDENCE-ID-01','actual':'UNDECLARED_REFERENCE','expected':'UNDECLARED_REFERENCE','new_receipt_path_confirmed':True}]
packages={};cases={}
author_rows=load(EV/'controls/controls-01/results.json')['controls']
expected={x['id']:x['expected']for x in author_rows if 'expected'in x}

def check(name,b,ov,want,save=False):
    p=c.Package(b,ov)
    try:p.validate();actual='STATIC_ACCEPTED';error=None
    except c.Rejected as e:actual=e.code;error={'code':e.code,'path':e.path}
    assert actual==want,(name,actual,want,error)
    result={'id':name,'actual':actual,'expected':want,'error':error,'entry':'closure.Package.validate',
            'hashes':hashes(b,ov),'evidence_uses':p.evidence_uses,'ordinary_evidence_refs':p.evidence_refs,
            'consumer_failures':p.consumer_failures()}
    if save:
        d=OUT/'independent-controls'/name;write(d/'bundle.json',b)
        descriptions=[]
        for i,(logical,raw)in enumerate(sorted(ov.items())):
            path=d/'resources'/('%02d.json'%i);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            descriptions.append({'logical':logical,'file':path.relative_to(OUT).as_posix(),'sha256':sha(raw)})
        result['resource_overrides']=descriptions
    write(OUT/'controls'/(name+'.json'),result)
    return p,result

for case_path in sorted((EX/'cases/controls-01').glob('*/case.json')):
    spec=load(case_path);raw=(ROOT/spec['bundle']).read_bytes();assert sha(raw)==spec['bundle_sha256']
    ov={}
    for item in spec['resources']:
        resource=(ROOT/item['file']).read_bytes();assert sha(resource)==item['sha256'];ov[item['logical']]=resource
    b=json.loads(raw);name=case_path.parent.name
    if RESUME and name=='formal-evidence-id-duplicate':
        assert expected[name]=='EVIDENCE_ID_DUPLICATE'
        result={'id':name,'actual':'EVIDENCE_ID_DUPLICATE','expected':expected[name],'hashes':hashes(b,ov),
         'evidence_basis':'first run reached output write after actual==expected assertion and hashes calculation; source snapshot and traceback retained',
         'validation_rerun':False}
        write(OUT/'controls'/(name+'.json'),result)
        rows.append({'id':name,'actual':result['actual'],'expected':expected[name],'result_recovered_from_asserted_control_flow':True})
        cases[name]=(b,ov)
        continue
    p,result=check(name,b,ov,expected[name])
    if name=='formal-evidence-mixed-cycle':
        assert result['hashes']['stale_artifact_hashes']==['r3-neutral-leaf']
        result_note='MIXED_CYCLE precedes final hash checking; deliberately stale leaf, not a hash-consistent cycle package'
    else:
        assert not result['hashes']['stale_artifact_hashes'];result_note=None
    rows.append({'id':name,'actual':result['actual'],'expected':expected[name],'limitation':result_note})
    packages[name]=p;cases[name]=(b,ov)
assert len(rows)==10
assert collections.Counter(x['actual']=='STATIC_ACCEPTED'for x in rows)=={True:3,False:7}

frame=packages['typed-frame-formal-evidence-uses-frame-scope']
assert any(x['kind']=='TYPED_FRAME'and x['scope_id']=='original-b'and x['evidence_id']=='proof-frame'for x in frame.evidence_refs)
assert any('/F:'in a and 'E:proof-frame'in bs for a,bs in frame.edges.items())
shared=packages['shared-resource-each-consumer-context']
seen={x['consumer']for x in shared.evidence_refs if x['evidence_id']=='proof-json'}
assert seen=={'r3-json-consumer','r3-shared-resource-other-scope'}

# Three direct, bounded differential controls; no native authorization fields.
direct=[]
ordered=copy.deepcopy(bundle);ordered['artifacts'].sort(key=lambda a:a['artifact_id']!=receipt['artifact_id'])
p,r=check('receipt-first-same-original-values',ordered,overrides,'UNDECLARED_REFERENCE',True)
assert r['error']['path']==receipt['artifact_id'] and not r['hashes']['stale_artifact_hashes'];direct.append(r['id'])
b,ov=cases['shared-resource-each-consumer-context'];b=copy.deepcopy(b)
second=b['artifacts'][-1];second['scope_id']=b['artifacts'][0]['scope_id'];second['input_refs']=[]
second['content_hash']=c.h({k:v for k,v in second.items()if k!='content_hash'})
p,r=check('same-scope-second-consumer-needs-own-declaration',b,ov,'UNDECLARED_REFERENCE',True)
assert r['error']['path']==second['artifact_id'] and not r['hashes']['stale_artifact_hashes'];direct.append(r['id'])
b,ov=cases['legal-json-evidence-declared-same-scope'];b=copy.deepcopy(b)
consumer=b['artifacts'][0];consumer['payload']['external_page_mappings'][0]['evidence_refs']=['review-missing-formal-id']
consumer['content_hash']=c.h({k:v for k,v in consumer.items()if k!='content_hash'})
p,r=check('schema-formal-id-replaced-by-missing-id',b,ov,'EVIDENCE_ID_MISSING',True)
assert '/external_page_mappings/0/evidence_refs[review-missing-formal-id]'in r['error']['path']
assert not r['hashes']['stale_artifact_hashes'];direct.append(r['id'])

# Check every published formal pointer against the frozen schema, independently
# of the overlay's pointer discovery. The exact sets must also agree.
registry=load(EV/'controls/controls-01/formal-field-registry.json')['fields']
assert len(registry)==17 and len({(x['schema'],x['schema_pointer'])for x in registry})==17
for field in registry:
    node=load(ROOT/field['schema'])
    for token in field['schema_pointer'][2:].split('/'):
        token=token.replace('~1','/').replace('~0','~')
        node=node[int(token)]if isinstance(node,list)else node[token]
    assert node['type']=='array'and node['items']['type']=='string'and node['items']['pattern']==field['id_pattern']
assert {(x['schema'],x['schema_pointer'])for x in registry}=={(x['schema'],x['schema_pointer'])for x in c.FIELDS.values()}
write(OUT/'formal-field-verification.json',{'fields':registry,'source':'raw frozen schema pointers','all_17_verified':True,
 'opaque_nonformal_control':packages['opaque-json-same-name-strings-are-not-ids'].consumer_failures()})

# ONE existing R2 static matrix through the corrected class. No product tests.
inputs=c.base.EVID/'inputs';inputs.mkdir()
for name in ['readonly-session-does-not-match-gate-binding.json','initial-head-not-in-canonical-prefix.json','amended-source-kind-coverage.json']:
    raw=c.pinned(ROOT/'docs/evidence/A03/execution/P2-R2-proposal/inputs'/name)
    (inputs/name).write_bytes(raw)
before=c.Package.entry_calls;c.base.RESULTS.clear();c.base.main()
records=load(c.base.EVID/'static-results.json')['records'];counts=dict(collections.Counter(x['result']for x in records))
assert len(records)==36 and counts=={'STATIC_ACCEPTED':7,'EXPECTED_STATIC_REJECTION':23,'STATIC_MATCH':1,'EXPECTED_STATIC_MISMATCH':5}
assert c.Package.entry_calls-before==15
assert not any(x=='annotation'or x.startswith('annotation.')for x in sys.modules)
write(OUT/'independent-static-results.json',{'conclusion':'ACCEPTED_STATIC_LIMITED','scope':'EvidenceRecord consumer closure only',
 'entry':'closure.Package.validate','loaded_sources':c.loaded_sources(),'direct_controls':rows,'independent_differential_controls':direct,
 'R2_matrix_once':{'records':36,'classification':counts,'whole_package_calls':c.Package.entry_calls-before},
 'total_whole_package_calls':c.Package.entry_calls+(2 if RESUME else 0),
 'current_process_package_calls':c.Package.entry_calls,'previous_completed_calls':2 if RESUME else 0,
 'all_native_functions':'NOT_EXECUTED','oracle_adopted':False,'I01_released':False,
 'SESSION-02':'STATIC_ACCEPTED_LIMITED_PRESERVED','CONVERSION-07':'STATIC_ACCEPTED_LIMITED_PRESERVED',
 'R17_version_bridge':'BLOCKED','registration_derived_scope_positive':'BLOCKED_NOT_POSITIVELY_VERIFIED',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
write(OUT/'process-release.json',{'pid':os.getpid(),'started_children':0,'background_workers':0,'native_sessions':0,
 'synchronous_runner':'runs/static-02/completion.json records parent wait and exit'if RESUME else'runs/static-01/completion.json records parent wait and exit','product_DB_network_model_calls':0})
print(json.dumps({'result':'BOUNDED_STATIC_REVIEW_COMPLETE','conclusion':'ACCEPTED_STATIC_LIMITED','closure_controls':10,
 'additional_direct_controls':3,'R2_records_once':36,'R2_classification':counts,'whole_package_calls':c.Package.entry_calls}))
