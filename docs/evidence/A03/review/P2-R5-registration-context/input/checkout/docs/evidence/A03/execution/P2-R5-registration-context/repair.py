"""One repair of the mixed-cycle control only; no validator import/call."""
import ast,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R5-registration-context';sys.path.insert(0,str(EX))
from common import BASE,OUT,canon,git,h,load,raw_write,ref,sha,write
assert sha((EX/'registration.py').read_bytes())=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
pins=[]
def pin(name):
    raw=git('show',BASE+':'+name);assert raw==(ROOT/name).read_bytes()
    pins.append({'commit':BASE,'path':name,'bytes':len(raw),'sha256':sha(raw),'git_blob':git('rev-parse',BASE+':'+name).decode().strip()});return raw
data=ROOT/'examples/a03/P2-R2-proposal/candidate-final'
bundle=json.loads(pin('examples/a03/P2-R2-proposal/candidate-final/scope-session.json'))
prefix=json.loads(pin('examples/a03/P2-R2-proposal/candidate-final/session/prefix.json'))
source=copy.deepcopy(next(a for a in bundle['artifacts']if a['kind']=='SourceBundle'and a['scope_id']=='original-a'))
plan=next(a for a in bundle['artifacts']if a['kind']=='ApplyPlan'and a['scope_id']=='original-a')
source.update(schema_version='1.3.0-a03-static-proposal',artifact_id='r5-mixed-cycle-source-consumer',input_refs=[ref(plan)])
source['producer'].update(module='R5_STATIC_CYCLE_CONTROL',implementation_version='UNIMPLEMENTED')
for m in source['payload']['external_page_mappings']:m['evidence_refs']=['proof-r5-mixed-cycle']
source['content_hash']=h({k:v for k,v in source.items()if k!='content_hash'});bundle['artifacts'].append(source)
frame=next(f for f in prefix['frames']if f['event']['event']=='PLAN_ACCEPTED'and f['consumer_scope_id']==source['scope_id'])
assert frame['event']['event_version']=='a03-runtime-event-3'and'evidence'in frame['event']['payload']
over={}
def resource(logical,value):
    raw=canon(value)+b'\n';over[logical]=raw;return{'path':logical,'sha256':sha(raw),'media_type':'application/json','origin':'SYNTHETIC'}
frame['event']['payload']['evidence']=resource('r5-static/cycle-return.json',{'ordinary_source_ref':ref(source)})
frame['input_refs'].append(ref(source))
previous='0'*64
for i,f in enumerate(prefix['frames'],1):
    event=f['event'];event.update(sequence=i,previous_hash=previous);event['event_hash']=h({k:v for k,v in event.items()if k!='event_hash'});previous=event['event_hash']
    if event['event']=='PLAN_ACCEPTED'and event['plan_ref']==prefix['subject_plan_ref']:prefix['accepted_anchor']={'sequence':i,'hash':previous}
prefix['expected_book_head']={'sequence':len(prefix['frames']),'hash':previous}
pr=resource('r5-static/cycle-prefix.json',prefix);record=copy.deepcopy(bundle['evidence'][0]);record.update(evidence_id='proof-r5-mixed-cycle',resource=pr,description='One hash-consistent Artifact/EvidenceRecord/Resource/frame cycle')
bundle['evidence'].append(record)
# Fixed legacy artifacts/facts keep their original prefix and hashes. Only the
# new Source consumes the independent cycle prefix. No event version is changed.
assert all(h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in bundle['artifacts'])
directory=EX/'cases/artifact-resource-frame-mixed-cycle/repair-01';raw=json.dumps(bundle,ensure_ascii=False,indent=2).encode('utf8')+b'\n';raw_write(directory/'bundle.json',raw)
resources=[]
for i,(logical,body)in enumerate(sorted(over.items())):
    p=directory/'resources'/(str(i)+'.json');raw_write(p,body);resources.append({'logical':logical,'file':p.relative_to(ROOT).as_posix(),'raw_sha256':sha(body),'bytes':len(body)})
case={'id':'artifact-resource-frame-mixed-cycle','bundle':(directory/'bundle.json').relative_to(ROOT).as_posix(),'bundle_sha256':sha(raw),'resources':resources,'expected':'MIXED_CYCLE','expected_layer':'GLOBAL_MIXED_DAG','source':{'commit':BASE,'bundle':'examples/a03/P2-R2-proposal/candidate-final/scope-session.json','prefix':'examples/a03/P2-R2-proposal/candidate-final/session/prefix.json'},'mutation':{'repair_round':1,'reason':'initial control added evidence to a closed legacy PLAN_ACCEPTED payload; use a frozen event branch that already has the Resource field','checker_changed':False,'old_versions_schema_pins_or_samples_changed':False,'new_prefix_event_versions_unchanged':True,'cycle':['new Source A','formal EvidenceRecord','new typed prefix Resource','existing frame A','new return Resource','same new Source A'],'all_artifact_resource_and_event_hashes_correct':True,'frame_reference_declared_same_scope':True},'native_qualification':False}
write(directory/'case.json',case)
write(EX/'repair-case-index.json',{'entry':'registration.Package.validate','repair_round':1,'affected_cases_only':['artifact-resource-frame-mixed-cycle'],'cases':[{'id':case['id'],'case':(directory/'case.json').relative_to(ROOT).as_posix(),'case_sha256':sha((directory/'case.json').read_bytes()),'expected':'MIXED_CYCLE','expected_layer':case['expected_layer']}]})
write(OUT/'repair-input-index.json',{'base':BASE,'inputs':pins,'checker_calls':0})
for p in(EX/'registration.py',EX/'run_case.py',Path(__file__)):ast.parse(p.read_text(encoding='utf8'))
write(OUT/'repair-static-check.json',{'status':'ONE_AFFECTED_CONTROL_REPAIR_READY','repair_round':1,'checker_sha256_unchanged':sha((EX/'registration.py').read_bytes()),'original_failed_case_and_result_preserved':True,'new_cases':0,'affected_case':'artifact-resource-frame-mixed-cycle','checker_calls':0,'local_error':'control selected legacy event branch without a Resource field','correction':'reuse existing frozen v3 event branch with its Resource field, without changing any version value'})
print(json.dumps({'status':'ONE_CONTROL_REPAIR_PREPARED','checker_calls':0,'checker_changed':False}))
