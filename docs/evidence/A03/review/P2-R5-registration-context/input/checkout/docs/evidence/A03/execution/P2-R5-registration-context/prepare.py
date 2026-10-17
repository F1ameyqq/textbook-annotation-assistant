"""Fix exactly seven inputs, without importing or running any checker."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R5-registration-context';sys.path.insert(0,str(EX))
from common import BASE,OUT,canon,git,h,load,raw_write,ref,sha,write
pool=EX/'inputs/resources';rows=[]
def asset(raw,suffix):
    p=pool/(sha(raw)+suffix)
    if p.exists():assert p.read_bytes()==raw
    else:raw_write(p,raw)
    return p.relative_to(ROOT).as_posix()
def save_case(name,bundle_raw,over,expected,layer,origin,source_case=None,mutation=None):
    directory=EX/'cases'/name;raw_write(directory/'bundle.json',bundle_raw)
    resources=[{'logical':logical,'file':asset(raw,'.json'if raw.lstrip().startswith((b'{',b'['))else'.bin'),'raw_sha256':sha(raw),'bytes':len(raw)}for logical,raw in sorted(over.items())]
    info={'id':name,'bundle':(directory/'bundle.json').relative_to(ROOT).as_posix(),'bundle_sha256':sha(bundle_raw),'resources':resources,'expected':expected,'expected_layer':layer,'source':origin,'mutation':mutation,'native_qualification':False}
    if source_case is not None:
        raw_write(directory/'source-case.json',source_case);info['source_case_copy']=(directory/'source-case.json').relative_to(ROOT).as_posix();info['source_case_sha256']=sha(source_case)
    write(directory/'case.json',info);rows.append({'id':name,'case':(directory/'case.json').relative_to(ROOT).as_posix(),'case_sha256':sha((directory/'case.json').read_bytes()),'expected':expected,'expected_layer':layer})
    return info
originals={}
for name,expected in [('registration-positive','STATIC_ACCEPTED'),('source-binding-negative','FRAME_REGISTRATION_BINDING'),('snapshot-binding-negative','FRAME_REGISTRATION_BINDING'),('target-tuple-negative','FRAME_REGISTRATION_TARGET')]:
    source=ROOT/'examples/a03/P2-R4-bridge-registration/cases'/name/'case.json';case=load(source)
    raw=(ROOT/case['bundle']).read_bytes();assert raw==git('show',BASE+':'+case['bundle'])and sha(raw)==case['bundle_sha256']
    over={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
    assert all(sha(over[r['logical']])==r['sha256']for r in case['resources'])
    origins={'commit':BASE,'case':source.relative_to(ROOT).as_posix(),'case_sha256':sha(source.read_bytes()),'bundle':case['bundle'],'bundle_sha256':sha(raw),'all_resource_bytes_unchanged':True}
    save_case(name,raw,over,expected,'FULL_ENTRY_RETURN'if name=='registration-positive'else'REAL_REGISTRATION_TARGET'if name=='target-tuple-negative'else'REAL_REGISTRATION_SOURCE_SNAPSHOT',origins,source.read_bytes())
    originals[name]=(json.loads(raw),over,case)
directory=ROOT/'docs/evidence/A03/execution/P2-R3-evidence-closure/inputs/counterexample';spec=load(directory/'result.json');raw=(directory/'bundle.json').read_bytes()
assert sha(raw)=='b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653'
over={r['logical']:(directory/Path(r['file']).name).read_bytes()for r in spec['resource_overrides']}
save_case('r3-original-undeclared-evidence',raw,over,'UNDECLARED_REFERENCE','REAL_CONSUMER_FORMAL_EVIDENCE_CLOSURE',{'commit':BASE,'bundle':(directory/'bundle.json').relative_to(ROOT).as_posix(),'bundle_sha256':sha(raw),'original_id':spec['id']},(directory/'result.json').read_bytes())
bundle,original_over,case=originals['registration-positive'];bad=copy.deepcopy(bundle);over=dict(original_over)
record=copy.deepcopy(bad['evidence'][0]);logical='r5-static/global-only-proof.txt';expected_raw=b'R5 global integrity control\n';actual_raw=expected_raw+b'INTENTIONAL_CORRUPTION\n'
record.update(evidence_id='proof-r5-global-integrity',description='Unconsumed global Resource: intentionally wrong raw digest',resource={'path':logical,'sha256':sha(expected_raw),'media_type':'text/plain','origin':'SYNTHETIC'})
bad['evidence'].append(record);over[logical]=actual_raw
save_case('global-resource-hash-corruption',json.dumps(bad,ensure_ascii=False,indent=2).encode('utf8')+b'\n',over,'RESOURCE_HASH','UNBOUND_GLOBAL_RESOURCE_READ',{'base_case':'registration-positive'},mutation={'only_semantic_change':'append unique unconsumed EvidenceRecord with one deliberately corrupt Resource body','logical':logical,'declared_sha256':sha(expected_raw),'actual_sha256':sha(actual_raw),'other_artifacts_and_resources_unchanged':True})
cyclic=copy.deepcopy(bundle);over=dict(original_over);pr=case['prefix_resource'];prefix=json.loads(over[pr['path']])
consumer=next(a for a in cyclic['artifacts']if a['artifact_id']=='r4-registration-prefix-consumer');frame=prefix['frames'][2];assert frame['event']['event']=='PLAN_ACCEPTED'and frame['consumer_scope_id']==consumer['scope_id']
logical='r5-static/mixed-cycle-back-to-consumer.json';value={'ordinary_source_ref':ref(consumer)};raw=canon(value)+b'\n';over[logical]=raw
frame['event']['payload']['evidence']={'path':logical,'sha256':sha(raw),'media_type':'application/json','origin':'SYNTHETIC'};frame['input_refs'].append(ref(consumer))
previous='0'*64
for i,f in enumerate(prefix['frames'],1):
    event=f['event'];event.update(sequence=i,previous_hash=previous);event['event_hash']=h({k:v for k,v in event.items()if k!='event_hash'});previous=event['event_hash']
    if event['event']=='PLAN_ACCEPTED'and event['plan_ref']==prefix['subject_plan_ref']:prefix['accepted_anchor']={'sequence':i,'hash':previous}
prefix['expected_book_head']={'sequence':len(prefix['frames']),'hash':previous};raw=canon(prefix)+b'\n';over[pr['path']]=raw
next(e for e in cyclic['evidence']if e['resource']==pr)['resource']=dict(pr,sha256=sha(raw))
save_case('artifact-resource-frame-mixed-cycle',json.dumps(cyclic,ensure_ascii=False,indent=2).encode('utf8')+b'\n',over,'MIXED_CYCLE','GLOBAL_MIXED_DAG',{'base_case':'registration-positive'},mutation={'only_semantic_change':'frame A PLAN_ACCEPTED consumes a new JSON Resource with exact ref back to outer Source A consumer; declare that ref and rechain event/prefix/Resource digests','cycle':['Source consumer A','formal EvidenceRecord','prefix Resource','frame A','new Resource','same Source consumer A'],'all_artifact_hashes_unchanged':True,'no_stale_hash_or_foreign_scope':True})
assert len(rows)==7
for row in rows:
    info=load(ROOT/row['case']);bundle=load(ROOT/info['bundle'])
    assert all(h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in bundle['artifacts'])
write(EX/'case-index.json',{'base':BASE,'entry':'registration.Package.validate','cases':rows,'checker_calls_during_preparation':0,'old_36_matrix_runs':0,'additional_cases':0})
print(json.dumps({'status':'EXACT_SEVEN_INPUTS_FIXED','cases':len(rows),'checker_calls':0}))
